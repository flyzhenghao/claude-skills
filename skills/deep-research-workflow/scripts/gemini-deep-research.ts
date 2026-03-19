#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research Automation
 *
 * Copies Chrome profile to a debug directory (preserving Google login via
 * macOS Keychain — encryption key is per-app, not per-path), then launches
 * Chrome with Playwright using the copied profile.
 *
 * Usage:
 *   npx tsx scripts/gemini-deep-research.ts <prompt-file-1> [prompt-file-2] ...
 *   npx tsx scripts/gemini-deep-research.ts --no-wait <prompt-files...>
 *
 * By default, the script submits all prompts, then polls until all researches
 * complete, extracts reports, and saves them to ./research-results/.
 * Use --no-wait to exit immediately after submission (old behavior).
 *
 * First run: may require one-time Google re-login (device fingerprint change).
 * Chrome must be CLOSED before running (profile copy needs unlocked files).
 *
 * Output: ./research-results/YYYY-MM-DD-<slug>.md
 */

import { chromium, type Page } from "playwright";
import { existsSync } from "fs";
import { basename, resolve } from "path";

import { extractPromptBody, getPromptTitle } from "./lib/gemini/prompt.js";
import { ensureChromeNotRunning, syncProfileToDebug } from "./lib/gemini/profile.js";
import { submitOne, checkResearchStatus, extractReport, saveReport } from "./lib/gemini/browser.js";
import { waitForAnyResearchComplete } from "./lib/gemini/monitor.js";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;
const REPO_ROOT = process.cwd();
const DR_RESULTS_DIR = resolve(process.cwd(), "research-results");

const waitMode = !process.argv.includes("--no-wait");

async function main() {
  const promptFiles = process.argv.slice(2).filter(a => !a.startsWith("--"));

  if (promptFiles.length === 0) {
    console.log("Usage: npx tsx scripts/gemini-deep-research.ts [--no-wait] <prompt-files...>");
    console.log("\nSubmits prompts → polls until complete → extracts reports automatically.");
    console.log("Use --no-wait to exit after submission without polling.\n");
    console.log("Output: ./research-results/YYYY-MM-DD-<slug>.md\n");
    console.log("Example:");
    console.log("  npx tsx scripts/gemini-deep-research.ts research/prompt-1.md research/prompt-2.md");
    process.exit(0);
  }

  for (const f of promptFiles) {
    if (!existsSync(resolve(f))) {
      console.error(`❌ Not found: ${f}`);
      process.exit(1);
    }
  }

  console.log("🔬 Gemini Deep Research — Submitting", promptFiles.length, "prompt(s)\n");

  // Ensure Chrome is closed (need exclusive access to profile files for copy)
  ensureChromeNotRunning();

  // Sync real Chrome profile to debug directory
  syncProfileToDebug(DEBUG_PROFILE_DIR);

  // Launch Chrome with copied profile (non-default dir allows remote debugging)
  console.log("🚀 Launching Chrome with debug profile...");
  const context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-blink-features=AutomationControlled",
    ],
    ignoreDefaultArgs: ["--enable-automation"],
    viewport: { width: 1280, height: 900 },
  });
  console.log("✓ Chrome launched with debug profile\n");

  const MAX_CONCURRENT = 3;  // Gemini Deep Research hard limit
  let ok = 0, fail = 0;
  const results: Array<{ file: string; success: boolean; url: string }> = [];
  // Track active research pages for completion monitoring
  const activeResearches: Array<{ page: Page; file: string; url: string }> = [];

  try {
    for (let i = 0; i < promptFiles.length; i++) {
      const f = promptFiles[i];
      const title = getPromptTitle(f);
      const body = extractPromptBody(f);

      console.log(`━━━ [${i + 1}/${promptFiles.length}] ${title} ━━━`);
      console.log(`  ${basename(f)} (${body.length} chars)\n`);

      // If at concurrency limit, wait for one to complete before proceeding
      if (activeResearches.length >= MAX_CONCURRENT) {
        console.log(`  🔒 At concurrency limit (${MAX_CONCURRENT}). Waiting for a research to complete...`);
        const completedIdx = await waitForAnyResearchComplete(activeResearches);
        if (completedIdx >= 0) {
          const completed = activeResearches.splice(completedIdx, 1)[0];
          console.log(`  ✓ Slot freed: "${completed.file}" is done. Proceeding with next prompt.\n`);
        } else {
          console.error(`  ❌ Timeout waiting for researches to complete. Skipping remaining prompts.`);
          results.push({ file: basename(f), success: false, url: "(timeout waiting for slot)" });
          fail++;
          continue;
        }
      }

      const result = await submitOne(context, body, i + 1, DEBUG_PROFILE_DIR);

      // If hit concurrency limit at runtime, wait and retry once
      if (result.hitConcurrencyLimit && activeResearches.length > 0) {
        console.log(`  🔄 Concurrency limit detected at runtime. Waiting for a slot...`);
        const completedIdx = await waitForAnyResearchComplete(activeResearches);
        if (completedIdx >= 0) {
          activeResearches.splice(completedIdx, 1);
          console.log(`  ✓ Slot freed. Retrying submission...\n`);
          const retry = await submitOne(context, body, i + 1, DEBUG_PROFILE_DIR);
          results.push({ file: basename(f), success: retry.success, url: retry.url });
          if (retry.success) {
            ok++;
            activeResearches.push({ page: retry.page, file: basename(f), url: retry.url });
          } else {
            fail++;
          }
          continue;
        }
      }

      results.push({ file: basename(f), success: result.success, url: result.url });
      if (result.success) {
        ok++;
        activeResearches.push({ page: result.page, file: basename(f), url: result.url });
      } else {
        fail++;
      }

      if (i < promptFiles.length - 1) {
        console.log("\n  ⏳ 5s pause...\n");
        await new Promise(r => setTimeout(r, 5000));
      }
    }
  } finally {
    console.log(`\n━━━ Submission Results: ${ok} submitted, ${fail} failed ━━━`);
    for (const r of results) {
      console.log(`  ${r.success ? "✅" : "❌"} ${r.file} ${r.url}`);
    }

    if (ok === 0 || !waitMode) {
      // No successful submissions or --no-wait: exit without polling
      if (!waitMode && ok > 0) {
        console.log("\n📌 --no-wait: Browser left open. Poll manually:");
        console.log("   npx tsx scripts/gemini-dr-check.ts <urls...>");
      }
      await context.browser()?.close();
    } else {
      // === Auto-poll + extract loop ===
      console.log(`\n⏳ Waiting for ${activeResearches.length} research(es) to complete (polling every 30s, max 20min)...`);
      console.log(`   Reports will be saved to: ${DR_RESULTS_DIR}`);
      const extractedPaths: string[] = [];
      const POLL_INTERVAL = 30000;
      const MAX_WAIT = 1200000; // 20 min
      const waitStart = Date.now();

      while (activeResearches.length > 0 && Date.now() - waitStart < MAX_WAIT) {
        await new Promise(r => setTimeout(r, POLL_INTERVAL));
        const elapsed = Math.round((Date.now() - waitStart) / 1000);

        for (let i = activeResearches.length - 1; i >= 0; i--) {
          const { page, file, url } = activeResearches[i];
          const status = await checkResearchStatus(page);

          if (status === "completed") {
            console.log(`\n  ✅ "${file}" completed (${elapsed}s). Extracting...`);
            const report = await extractReport(page);
            if (report && report.length > 500) {
              const origFile = promptFiles.find(f => basename(f) === file) ?? file;
              const saved = saveReport(report, url, origFile, REPO_ROOT, DR_RESULTS_DIR);
              extractedPaths.push(saved);
            } else {
              console.log(`  ⚠️  "${file}" extraction failed (${report?.length ?? 0} chars). Use gemini-dr-extract.ts manually.`);
            }
            activeResearches.splice(i, 1);
          } else if (status === "error") {
            console.log(`\n  ❌ "${file}" errored (${elapsed}s). Skipping.`);
            activeResearches.splice(i, 1);
          }
        }

        if (activeResearches.length > 0) {
          console.log(`  ⏳ ${elapsed}s — ${activeResearches.length} still running...`);
        }
      }

      if (activeResearches.length > 0) {
        console.log(`\n  ⚠️  Timeout after ${MAX_WAIT / 60000}min. ${activeResearches.length} research(es) still running:`);
        for (const { file, url } of activeResearches) {
          console.log(`    - ${file}: ${url}`);
        }
        console.log("  Extract manually: npx tsx scripts/gemini-dr-extract.ts <url>");
      }

      // Final summary
      console.log(`\n━━━ Final Results ━━━`);
      console.log(`  Submitted: ${ok} | Extracted: ${extractedPaths.length} | Failed: ${fail}`);
      for (const p of extractedPaths) {
        console.log(`  📄 ${p}`);
      }

      await context.browser()?.close();
    }
  }
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
