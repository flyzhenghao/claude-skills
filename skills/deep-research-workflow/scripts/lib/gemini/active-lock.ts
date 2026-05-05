/**
 * Cross-invocation active-research tracking.
 *
 * Problem: Gemini limits concurrent Deep Research to 3 per user.
 * If `gemini-deep-research.ts` is invoked twice (e.g., user submits 1 prompt,
 * then submits 4 more in a separate call), the second invocation has no
 * memory of the first invocation's still-running researches. It cheerfully
 * tries to submit 4 more, exceeding the 3-research limit, and the 4th/5th
 * are silently rejected by Gemini.
 *
 * Solution: Persist active research URLs to a lock file. On startup, every
 * invocation reads the lock, checks each URL's actual status (via lib import
 * of checkResearchStatus would create a cycle, so we use a lightweight
 * "is-still-running" probe), drops completed/rejected ones, and counts what
 * remains against MAX_CONCURRENT.
 *
 * Lock file: ~/.chrome-debug-profile/.dr-active.json
 * Format: { urls: [{ url, file, submitted_at }] }
 */

import { readFileSync, writeFileSync, existsSync } from "fs";
import type { Page } from "playwright";

const LOCK_PATH = `${process.env.HOME}/.chrome-debug-profile/.dr-active.json`;

export interface ActiveResearchEntry {
  url: string;
  file: string;
  submitted_at: string; // ISO timestamp
}

interface LockFile {
  urls: ActiveResearchEntry[];
}

function readLock(): LockFile {
  if (!existsSync(LOCK_PATH)) return { urls: [] };
  try {
    const content = readFileSync(LOCK_PATH, "utf-8");
    const parsed = JSON.parse(content);
    if (!parsed.urls || !Array.isArray(parsed.urls)) return { urls: [] };
    return parsed;
  } catch {
    return { urls: [] };
  }
}

function writeLock(data: LockFile): void {
  try {
    writeFileSync(LOCK_PATH, JSON.stringify(data, null, 2), "utf-8");
  } catch (e) {
    console.error(`  ⚠ Could not write lock file ${LOCK_PATH}:`, e instanceof Error ? e.message : e);
  }
}

/**
 * Add a newly-submitted research URL to the lock file.
 */
export function recordActiveResearch(url: string, file: string): void {
  const lock = readLock();
  // Avoid duplicates
  if (lock.urls.some(e => e.url === url)) return;
  lock.urls.push({ url, file, submitted_at: new Date().toISOString() });
  writeLock(lock);
}

/**
 * Remove a research URL from the lock (called when known-complete).
 */
export function removeActiveResearch(url: string): void {
  const lock = readLock();
  lock.urls = lock.urls.filter(e => e.url !== url);
  writeLock(lock);
}

/**
 * Drop entries older than 4 hours (Deep Research max ~30min, so 4h is safe stale-cutoff).
 * Useful to auto-clean abandoned locks from crashed runs.
 */
function pruneStaleEntries(entries: ActiveResearchEntry[]): ActiveResearchEntry[] {
  const cutoff = Date.now() - 4 * 60 * 60 * 1000;
  return entries.filter(e => {
    const t = new Date(e.submitted_at).getTime();
    return !isNaN(t) && t > cutoff;
  });
}

/**
 * Read the lock and probe each URL's actual status.
 * Returns the subset of entries that are still actively running.
 *
 * Probe: open URL in given context, check page text for completion/rejection
 * markers. Lightweight to avoid cyclic import of checkResearchStatus.
 *
 * @param context Playwright BrowserContext to use for probing
 * @returns entries that are still RUNNING (UI shows researching activity, no completion/rejection)
 */
export async function syncActiveLockFromBrowser(
  context: import("playwright").BrowserContext
): Promise<ActiveResearchEntry[]> {
  const lock = readLock();
  const fresh = pruneStaleEntries(lock.urls);
  if (fresh.length === 0) {
    if (lock.urls.length > 0) writeLock({ urls: [] });
    return [];
  }

  const stillRunning: ActiveResearchEntry[] = [];
  for (const entry of fresh) {
    let page: Page | null = null;
    try {
      page = await context.newPage();
      await page.goto(entry.url, { timeout: 30000, waitUntil: "domcontentloaded" });
      // 2026-04-28: Bug fix — Gemini Web is a SPA. message-content elements are
      // hydrated AFTER the document loads. 2500ms was too short; daemon ran 12
      // cycles with mcCount=0 and falsely judged "unknown" → kept entries
      // forever. Now: wait for message-content to render (or 12s timeout).
      await page.waitForSelector("message-content", { timeout: 12000 }).catch(() => {});
      await page.waitForTimeout(2500); // settle after SPA render

      const status = await page.evaluate(() => {
        const msgContainers = document.querySelectorAll("message-content");
        let longestMarkdown = 0;
        let hasCompletedMarker = false;

        for (const mc of Array.from(msgContainers)) {
          const mcText = (mc as HTMLElement).innerText;
          if (mcText.length < 500 && (
            mcText.includes("Completed") || mcText.includes("已完成") ||
            mcText.includes("I've completed") || mcText.includes("completed your research")
          )) hasCompletedMarker = true;
          const md = mc.querySelector(".markdown");
          if (md) {
            const mdLen = (md as HTMLElement).innerText.length;
            if (mdLen > longestMarkdown) longestMarkdown = mdLen;
          }
        }
        if (hasCompletedMarker && longestMarkdown > 5000) return "completed";
        if (longestMarkdown > 5000) return "completed";

        // Rejection
        for (const mc of Array.from(msgContainers)) {
          const mcText = (mc as HTMLElement).innerText;
          if (mcText.length > 500) continue;
          const lower = mcText.toLowerCase();
          if (lower.includes("research requests running") ||
              lower.includes("maximum i can do") ||
              lower.includes("at one time") ||
              lower.includes("too many") ||
              lower.includes("用量限额") || lower.includes("限额")) {
            return "rejected";
          }
        }

        // Running signal
        const shortElements = document.querySelectorAll("p, span, div");
        for (const el of Array.from(shortElements)) {
          const text = (el as HTMLElement).innerText || "";
          if (text.length > 200) continue;
          const lower = text.toLowerCase();
          for (const sig of ["researching websites", "searching the web", "browsing", "reading websites", "正在研究"]) {
            if (lower.includes(sig)) return "running";
          }
        }
        return "unknown";
      });

      // 2026-04-28: Bug fix — previously "unknown" status caused entries to be
      // dropped from the lock, even when the research was still in early phase
      // (no "Researching websites" / "正在研究" UI signal yet). This led to
      // newly-submitted researches being lost from the lock seconds after
      // recordActiveResearch() wrote them in.
      // Fix: keep entry on running OR unknown. Only drop on completed/rejected.
      if (status === "running" || status === "unknown") {
        stillRunning.push(entry);
      }
      // completed / rejected → drop from lock
    } catch {
      // network / page error → keep entry (don't lose track on transient failure)
      stillRunning.push(entry);
    } finally {
      if (page) try { await page.close(); } catch {}
    }
  }

  // Persist pruned lock
  writeLock({ urls: stillRunning });
  return stillRunning;
}

export const MAX_CONCURRENT_GEMINI_DR = 3;
