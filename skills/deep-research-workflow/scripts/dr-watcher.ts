#!/usr/bin/env npx tsx
/**
 * Deep Research Watcher Daemon
 *
 * Solves: When `gemini-deep-research.ts --no-wait` submits research and exits,
 * nobody polls completion. Claude (or the user) has to manually check, and
 * Claude routinely "forgets" to poll across conversation turns. Result:
 * researches finish but reports are never extracted, sitting forgotten in
 * Gemini's history.
 *
 * Solution: This daemon reads the active-lock file and polls every 60 seconds,
 * auto-extracting reports and writing a completion log that Claude can check
 * at any tool call.
 *
 * Usage:
 *   # Foreground (for testing):
 *   npx tsx scripts/dr-watcher.ts
 *
 *   # Background (production):
 *   nohup npx tsx scripts/dr-watcher.ts > /tmp/dr-watcher.log 2>&1 &
 *
 *   # Stop:
 *   pkill -f dr-watcher.ts
 *
 * Outputs:
 *   - Reports extracted to deep-research-results/ (in current cwd or PDT)
 *   - Completion notifications: ~/.dr-completion.log (line-per-completion)
 *   - Heartbeat: ~/.dr-watcher.heartbeat (touched every poll cycle)
 *
 * Claude can check ~/.dr-completion.log at any tool call to see if any
 * researches finished since last check.
 */

import { existsSync, readFileSync, writeFileSync, appendFileSync, statSync, mkdirSync } from "fs";
import { resolve, dirname, basename } from "path";
import { execSync } from "child_process";
import { chromium } from "playwright";

import {
  syncActiveLockFromBrowser,
  removeActiveResearch,
  type ActiveResearchEntry,
} from "./lib/gemini/active-lock.js";
import { connectOrLaunchChrome } from "./lib/gemini/profile.js";
import { extractReport, saveReport, checkResearchStatus } from "./lib/gemini/browser.js";

const HOME = process.env.HOME || "";
const HEARTBEAT_FILE = `${HOME}/.dr-watcher.heartbeat`;
const COMPLETION_LOG = `${HOME}/.dr-completion.log`;
const PID_FILE = `${HOME}/.dr-watcher.pid`;
const POLL_INTERVAL_MS = 60_000;
const STALE_HEARTBEAT_MS = 5 * 60_000; // If heartbeat older than 5min, daemon is dead

function logCompletion(entry: { url: string; file: string; report_path?: string; status: "completed" | "rejected" | "error"; error?: string; timestamp: string }) {
  const line = JSON.stringify(entry) + "\n";
  appendFileSync(COMPLETION_LOG, line, "utf-8");
  console.log(`📝 [${entry.timestamp}] ${entry.status.toUpperCase()}: ${entry.file} → ${entry.report_path || entry.error || "(no report)"}`);
}

function checkExistingDaemon(): boolean {
  if (!existsSync(HEARTBEAT_FILE)) return false;
  try {
    const age = Date.now() - statSync(HEARTBEAT_FILE).mtimeMs;
    if (age < STALE_HEARTBEAT_MS) {
      // Verify pid still exists
      if (existsSync(PID_FILE)) {
        const pid = parseInt(readFileSync(PID_FILE, "utf-8").trim(), 10);
        if (pid > 0) {
          try {
            process.kill(pid, 0); // signal 0 = check existence
            return true;
          } catch { /* not running */ }
        }
      }
    }
  } catch { /* ignore */ }
  return false;
}

function writeHeartbeat() {
  try { writeFileSync(HEARTBEAT_FILE, new Date().toISOString(), "utf-8"); } catch {}
}

function writePid() {
  try { writeFileSync(PID_FILE, String(process.pid), "utf-8"); } catch {}
}

// Determine where to save reports (PDT vs project)
function getDrResultsDir(): string {
  const cwd = process.cwd();
  const isPdt = existsSync(resolve(cwd, "scripts/append-research-chain.sh")) &&
    existsSync(resolve(cwd, "package.json")) &&
    (() => { try { return JSON.parse(readFileSync(resolve(cwd, "package.json"), "utf-8")).name === "personal-digital-twin"; } catch { return false; } })();
  return isPdt ? resolve(cwd, "ai-docs/research/deep-research-results") : resolve(cwd, "deep-research-results");
}

async function pollOnce(): Promise<{ activeCount: number; completedThisCycle: number }> {
  // Check Chrome connectivity
  let cdpEndpoint: string;
  try {
    cdpEndpoint = connectOrLaunchChrome(`${HOME}/.chrome-debug-profile`);
  } catch (e) {
    console.error("⚠ Chrome unavailable:", e instanceof Error ? e.message : e);
    return { activeCount: -1, completedThisCycle: 0 };
  }

  const browser = await chromium.connectOverCDP(cdpEndpoint);
  const ctx = browser.contexts()[0];
  if (!ctx) {
    console.error("⚠ No browser context");
    try { browser.close(); } catch {}
    return { activeCount: -1, completedThisCycle: 0 };
  }

  // Sync lock file — drops completed/rejected/stale automatically
  let active: ActiveResearchEntry[];
  try {
    active = await syncActiveLockFromBrowser(ctx);
  } catch (e) {
    console.error("⚠ syncActiveLockFromBrowser failed:", e instanceof Error ? e.message : e);
    return { activeCount: -1, completedThisCycle: 0 };
  }

  // For entries that were just dropped (completed), extract their reports.
  // syncActiveLockFromBrowser already pruned the lock; but it doesn't tell us
  // WHICH ones completed. We compare before/after:
  //   pre-sync = readLock + pruneStale
  //   post-sync = active (still running)
  //   completed-or-rejected = pre-sync \ active
  // Read pre-sync state from a fresh probe (not ideal, but reading lock file
  // before sync would race). Instead: probe each URL not in `active` from the
  // pre-sync set we never captured. For simplicity, re-read all URLs that were
  // in lock file at pollOnce START.
  // Alternative: extend syncActiveLockFromBrowser to return both kept+dropped.
  // TODO: refactor active-lock.ts to return {running, completed, rejected} triple.

  // Workaround for now: re-read the JSON file ourselves to know what was in
  // it before this cycle, then probe URLs we lost.
  // (See active-lock.ts internal layout)
  const LOCK_PATH = `${HOME}/.chrome-debug-profile/.dr-active.json`;
  let preCycleEntries: ActiveResearchEntry[] = [];
  // Read the BACKUP file we maintain here to track previous cycle state.
  const PREV_CYCLE_FILE = `${HOME}/.chrome-debug-profile/.dr-watcher-prev.json`;
  if (existsSync(PREV_CYCLE_FILE)) {
    try { preCycleEntries = JSON.parse(readFileSync(PREV_CYCLE_FILE, "utf-8")); } catch { preCycleEntries = []; }
  }

  const activeUrls = new Set(active.map(e => e.url));
  const droppedThisCycle = preCycleEntries.filter(e => !activeUrls.has(e.url));

  // For each dropped entry, probe the URL to determine outcome and extract if completed
  let completedCount = 0;
  for (const dropped of droppedThisCycle) {
    const page = await ctx.newPage();
    try {
      await page.goto(dropped.url);
      await page.waitForTimeout(5000);
      const status = await checkResearchStatus(page);
      if (status === "completed") {
        const report = await extractReport(page);
        if (report) {
          const drDir = getDrResultsDir();
          mkdirSync(drDir, { recursive: true });
          // Use the original prompt file name as report basename (no slug guessing)
          const reportPath = resolve(drDir, dropped.file.replace(/^prompts?[\/_]/, "").replace(/\.md$/, "") + "-report.md");
          await saveReport(reportPath, report, { sourceUrl: dropped.url });
          logCompletion({
            url: dropped.url,
            file: dropped.file,
            report_path: reportPath,
            status: "completed",
            timestamp: new Date().toISOString(),
          });
          completedCount++;
        } else {
          logCompletion({ url: dropped.url, file: dropped.file, status: "completed", error: "extract returned null", timestamp: new Date().toISOString() });
        }
      } else if (status === "rejected") {
        logCompletion({ url: dropped.url, file: dropped.file, status: "rejected", timestamp: new Date().toISOString() });
      } else {
        logCompletion({ url: dropped.url, file: dropped.file, status: "error", error: `status=${status}`, timestamp: new Date().toISOString() });
      }
    } catch (e) {
      logCompletion({ url: dropped.url, file: dropped.file, status: "error", error: e instanceof Error ? e.message : String(e), timestamp: new Date().toISOString() });
    } finally {
      try { await page.close(); } catch {}
    }
  }

  // Save current active set for next cycle's diff
  try { writeFileSync(PREV_CYCLE_FILE, JSON.stringify(active, null, 2), "utf-8"); } catch {}

  try { browser.close(); } catch {}
  return { activeCount: active.length, completedThisCycle: completedCount };
}

async function main() {
  if (checkExistingDaemon()) {
    console.error(`⚠ Another dr-watcher daemon is already running (heartbeat fresh).`);
    console.error(`  Stop it first: pkill -f dr-watcher.ts`);
    process.exit(1);
  }

  writePid();
  console.log(`🔬 Deep Research Watcher started (pid ${process.pid})`);
  console.log(`   Lock file: ${HOME}/.chrome-debug-profile/.dr-active.json`);
  console.log(`   Completion log: ${COMPLETION_LOG}`);
  console.log(`   Heartbeat: ${HEARTBEAT_FILE}`);
  console.log(`   Poll interval: ${POLL_INTERVAL_MS / 1000}s`);
  console.log("");

  let consecutiveEmptyCycles = 0;
  const MAX_EMPTY_CYCLES = 5; // Auto-exit after 5 minutes of empty lock

  while (true) {
    writeHeartbeat();
    try {
      const { activeCount, completedThisCycle } = await pollOnce();
      const ts = new Date().toISOString().slice(11, 19);
      console.log(`[${ts}] active=${activeCount}, completed-this-cycle=${completedThisCycle}`);

      if (activeCount === 0) {
        consecutiveEmptyCycles++;
        if (consecutiveEmptyCycles >= MAX_EMPTY_CYCLES) {
          console.log(`💤 No active researches for ${MAX_EMPTY_CYCLES} cycles. Exiting daemon.`);
          break;
        }
      } else {
        consecutiveEmptyCycles = 0;
      }
    } catch (e) {
      console.error(`Cycle error:`, e instanceof Error ? e.message : e);
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
  }

  process.exit(0);
}

process.on("SIGINT", () => { console.log("\n👋 dr-watcher stopped"); process.exit(0); });
process.on("SIGTERM", () => { console.log("\n👋 dr-watcher stopped"); process.exit(0); });

main().catch(e => { console.error("Fatal:", e); process.exit(1); });
