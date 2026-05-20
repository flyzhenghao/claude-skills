#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research Automation
 *
 * Unified entry point with two modes:
 *   --api (default): Uses Gemini Interactions API (Mode E) — stable, no Chrome needed
 *   --chrome:        Uses Chrome + Playwright (Mode D) — fallback when API quota exhausted
 *
 * Usage:
 *   npx tsx scripts/gemini-deep-research.ts <prompt-file-1> [prompt-file-2] ...
 *   npx tsx scripts/gemini-deep-research.ts --chrome <prompt-files...>
 *   npx tsx scripts/gemini-deep-research.ts --api <prompt-files...>
 *   npx tsx scripts/gemini-deep-research.ts --no-wait <prompt-files...>   (Chrome mode only)
 *
 * Default (no flag): API mode. Falls back to Chrome mode suggestion on 429.
 *
 * First run (Chrome mode): may require one-time Google re-login.
 * Chrome must be CLOSED before running Chrome mode.
 */

import { chromium, type Page } from "playwright";
import { existsSync, readFileSync } from "fs";
import { basename, resolve, dirname } from "path";
import { execSync } from "child_process";

import { extractPromptBody, getPromptTitle } from "./lib/gemini/prompt.js";
import { connectOrLaunchChrome } from "./lib/gemini/profile.js";
import { submitOne, checkResearchStatus, extractReport, saveReport } from "./lib/gemini/browser.js";
import { waitForAnyResearchComplete } from "./lib/gemini/monitor.js";
import {
  syncActiveLockFromBrowser,
  recordActiveResearch,
  removeActiveResearch,
  MAX_CONCURRENT_GEMINI_DR,
  type ActiveResearchEntry,
} from "./lib/gemini/active-lock.js";
import { notifyDone, notifyTimeout } from "./lib/gemini/notify.js";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;
const CWD = process.cwd();
const IS_PDT = existsSync(resolve(CWD, "scripts/append-research-chain.sh")) &&
  existsSync(resolve(CWD, "package.json")) &&
  (() => { try { return JSON.parse(readFileSync(resolve(CWD, "package.json"), "utf-8")).name === "personal-digital-twin"; } catch { return false; } })();
const DR_RESULTS_DIR = IS_PDT
  ? resolve(CWD, "ai-docs/research/deep-research-results")
  : resolve(CWD, "deep-research-results");

const waitMode = !process.argv.includes("--no-wait");
const forceApi = process.argv.includes("--api");
const forceChrome = process.argv.includes("--chrome");

// Determine mode: --api forces API, otherwise default to Chrome (quality priority)
const useApiMode = forceApi ? true : false;

async function main() {
  const promptFiles = process.argv.slice(2).filter(a => !a.startsWith("--"));

  if (promptFiles.length === 0) {
    console.log("Usage: npx tsx scripts/gemini-deep-research.ts [--api|--chrome] [--no-wait] <prompt-files...>");
    console.log("\nModes:");
    console.log("  --chrome  (default) Use Chrome + Playwright — Gemini 2.5 Pro, highest quality");
    console.log("  --api     Use Gemini Interactions API — fallback when Chrome unavailable (Flash quality)");
    console.log("  --no-wait Exit after submission without polling (Chrome mode only)\n");
    console.log("Example:");
    console.log("  npx tsx scripts/gemini-deep-research.ts research/prompt-1.md research/prompt-2.md");
    console.log("  npx tsx scripts/gemini-deep-research.ts --chrome research/prompt-1.md");
    process.exit(0);
  }

  // API mode: delegate to gemini-dr-api.ts
  if (useApiMode) {
    const scriptDir = dirname(new URL(import.meta.url).pathname);
    const apiScript = resolve(scriptDir, "gemini-dr-api.ts");

    if (!existsSync(apiScript)) {
      console.error(`❌ API script not found: ${apiScript}`);
      process.exit(1);
    }

    if (!process.env.GEMINI_API_KEY) {
      console.log("⚠️  GEMINI_API_KEY not set. Falling back to Chrome mode.");
      console.log("   Set it via: export GEMINI_API_KEY='your-api-key'\n");
      // Fall through to Chrome mode below
    } else {
      console.log("🔬 Using API mode (Gemini Interactions API)\n");
      try {
        execSync(`npx tsx "${apiScript}" ${promptFiles.map(f => `"${f}"`).join(" ")}`, {
          cwd: CWD,
          stdio: "inherit",
          env: process.env,
        });
        process.exit(0);
      } catch (e: unknown) {
        const code = (e as { status?: number }).status ?? 1;
        process.exit(code);
      }
    }
  }

  for (const f of promptFiles) {
    if (!existsSync(resolve(f))) {
      console.error(`❌ Not found: ${f}`);
      process.exit(1);
    }
  }

  console.log("🔬 Gemini Deep Research (Chrome mode) — Submitting", promptFiles.length, "prompt(s)\n");

  // Connect to existing debug Chrome or launch new one. NEVER kills Chrome.
  const cdpEndpoint = connectOrLaunchChrome(DEBUG_PROFILE_DIR);

  // Connect Playwright to Chrome via CDP
  let browser = await chromium.connectOverCDP(cdpEndpoint);
  let context = browser.contexts()[0];
  if (!context) {
    console.error("❌ No browser context found. Chrome may not have started correctly.");
    process.exit(1);
  }
  console.log("✓ Connected to Chrome via CDP\n");

  // Cross-invocation concurrency tracking: probe lock file for previously-submitted
  // researches that may still be running. This prevents the 4th/5th submission in a
  // batch from being silently rejected when an earlier `--no-wait` invocation already
  // saturated the 3-research limit.
  console.log("🔒 Checking lock file for previously-submitted researches...");
  const externalActive = await syncActiveLockFromBrowser(context);
  if (externalActive.length > 0) {
    console.log(`  Found ${externalActive.length} research(es) still running from prior invocations:`);
    externalActive.forEach(e => console.log(`    - ${e.file}: ${e.url}`));
    console.log(`  Effective concurrent slots: ${MAX_CONCURRENT_GEMINI_DR - externalActive.length}/${MAX_CONCURRENT_GEMINI_DR}\n`);
  } else {
    console.log(`  No active researches from prior runs. Full ${MAX_CONCURRENT_GEMINI_DR} slots available.\n`);
  }
  const externalActiveCount = externalActive.length;

  const MAX_CONCURRENT = MAX_CONCURRENT_GEMINI_DR;  // Gemini Deep Research hard limit
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

      // If at concurrency limit (own + external from lock), wait for one to complete.
      // externalActiveCount is the count from prior --no-wait invocations still running.
      const totalActive = activeResearches.length + externalActiveCount;
      if (totalActive >= MAX_CONCURRENT) {
        if (activeResearches.length === 0) {
          // All slots held by external researches — we have nothing to wait on in-process.
          // Re-probe the lock to see if any external slot has freed up.
          console.log(`  🔒 All ${MAX_CONCURRENT} slots held by external researches from prior invocations.`);
          console.log(`     Polling lock file every 30s (max 20min)...`);
          let freed = false;
          for (let polls = 0; polls < 40; polls++) {
            await new Promise(r => setTimeout(r, 30000));
            const stillExternal = await syncActiveLockFromBrowser(context);
            if (stillExternal.length < externalActiveCount) {
              const newCount = stillExternal.length;
              console.log(`     ✓ External slot freed (${newCount}/${MAX_CONCURRENT} now busy). Proceeding.`);
              // Update local view of external count — stay conservative (use new count)
              (externalActive as ActiveResearchEntry[]).length = 0;
              externalActive.push(...stillExternal);
              // mutate the captured count via re-reading
              freed = true;
              break;
            }
            console.log(`     ⏳ Still ${stillExternal.length}/${MAX_CONCURRENT} external slots busy (poll ${polls + 1}/40)...`);
          }
          if (!freed) {
            console.error(`  ❌ Timeout waiting for external slot. Skipping ${promptFiles.length - i} remaining prompt(s).`);
            for (let j = i; j < promptFiles.length; j++) {
              results.push({ file: basename(promptFiles[j]), success: false, url: "(timeout: external slots full)" });
              fail++;
            }
            break;
          }
        } else {
          console.log(`  🔒 At concurrency limit (own ${activeResearches.length} + external ${externalActiveCount} = ${totalActive}/${MAX_CONCURRENT}). Waiting for in-process research to complete...`);
          const completedIdx = await waitForAnyResearchComplete(activeResearches);
          if (completedIdx >= 0) {
            const completed = activeResearches.splice(completedIdx, 1)[0];
            removeActiveResearch(completed.url);
            console.log(`  ✓ Slot freed: "${completed.file}" is done. Proceeding with next prompt.\n`);
          } else {
            console.error(`  ❌ Timeout waiting for researches to complete. Skipping remaining prompts.`);
            results.push({ file: basename(f), success: false, url: "(timeout waiting for slot)" });
            fail++;
            continue;
          }
        }
      }

      const result = await submitOne(context, body, i + 1);

      // P2: If login failed (cookie stale), resync cookies and retry once
      if (result.loginFailed) {
        console.log("  🔄 Login failed — resyncing cookies and restarting Chrome...");
        try { await result.page.close(); } catch {}
        // Close existing browser connection
        try { browser.close(); } catch {}
        // Full restart: kill Chrome, resync cookies from real profile, relaunch
        ensureChromeNotRunning();
        syncProfileToDebug(DEBUG_PROFILE_DIR);
        cdpEndpoint = launchChromeWithDebugging(DEBUG_PROFILE_DIR);
        browser = await chromium.connectOverCDP(cdpEndpoint);
        const newCtx = browser.contexts()[0];
        if (!newCtx) {
          console.error("  ❌ Could not reconnect after cookie resync.");
          results.push({ file: basename(f), success: false, url: "(login retry failed)" });
          fail++;
          continue;
        }
        console.log("  ✓ Chrome restarted with fresh cookies. Retrying...\n");
        const retry = await submitOne(newCtx, body, i + 1);
        if (retry.loginFailed) {
          console.error("  ❌ Login still failing after resync. Manual Google login required.");
          console.log("  → Open Chrome and log into Google, then re-run this script.");
          results.push({ file: basename(f), success: false, url: "(login failed)" });
          fail++;
          continue;
        }
        results.push({ file: basename(f), success: retry.success, url: retry.url });
        if (retry.success) {
          ok++;
          activeResearches.push({ page: retry.page, file: basename(f), url: retry.url });
          recordActiveResearch(retry.url, basename(f));
        } else {
          fail++;
        }
        // Update context reference for subsequent prompts
        context = newCtx;
        continue;
      }

      // If hit concurrency limit at runtime, wait and retry once
      if (result.hitConcurrencyLimit && activeResearches.length > 0) {
        console.log(`  🔄 Concurrency limit detected at runtime. Waiting for a slot...`);
        const completedIdx = await waitForAnyResearchComplete(activeResearches);
        if (completedIdx >= 0) {
          activeResearches.splice(completedIdx, 1);
          console.log(`  ✓ Slot freed. Retrying submission...\n`);
          const retry = await submitOne(context, body, i + 1);
          results.push({ file: basename(f), success: retry.success, url: retry.url });
          if (retry.success) {
            ok++;
            activeResearches.push({ page: retry.page, file: basename(f), url: retry.url });
            recordActiveResearch(retry.url, basename(f));
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
        recordActiveResearch(result.url, basename(f));
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
      browser.close();
    } else {
      // === Auto-poll + extract loop ===
      // 2026-05-03: MAX_WAIT now configurable via DR_MAX_WAIT_MIN env (default 30min,
      // raised from 20 — Gemini complex prompts often run 25-30 min).
      const POLL_INTERVAL = 30000;
      const parsedWait = parseInt(process.env.DR_MAX_WAIT_MIN || "30", 10);
      const MAX_WAIT_MIN = Number.isFinite(parsedWait) && parsedWait > 0 ? parsedWait : 30;
      const MAX_WAIT = MAX_WAIT_MIN * 60 * 1000;
      console.log(`\n⏳ Waiting for ${activeResearches.length} research(es) to complete (polling every 30s, max ${MAX_WAIT_MIN}min)...`);
      const extractedPaths: string[] = [];
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
              // Content mismatch check: verify extracted report relates to the prompt
              const origFile = promptFiles.find(f => basename(f) === file) ?? file;
              const promptBody = existsSync(resolve(origFile)) ? readFileSync(resolve(origFile), "utf-8") : "";
              if (promptBody.length > 0) {
                // Extract keywords: Chinese segments (2+ chars) + English words (4+ chars)
                const chineseSegments = promptBody.slice(0, 300).match(/[\u4e00-\u9fff]{2,8}/g) || [];
                const englishWords = promptBody.slice(0, 300).split(/[\s#*\n]+/).filter(w => /^[a-zA-Z]{4,}$/.test(w));
                const promptKeywords = [...chineseSegments.slice(0, 10), ...englishWords.slice(0, 5)];
                const reportHead = report.slice(0, 3000);
                const matchCount = promptKeywords.filter(w => reportHead.includes(w)).length;
                // Only skip if report is short AND no keywords match — long reports are always saved
                if (report.length < 5000 && matchCount === 0 && promptKeywords.length > 0) {
                  console.log(`  ⚠️ CONTENT MISMATCH: extracted report does not match prompt "${file}".`);
                  console.log(`     Prompt keywords matched: ${matchCount}/${promptKeywords.length}. This may be a stale session.`);
                  console.log(`     Report title: "${report.split("\n")[0]?.slice(0, 80)}"`);
                  console.log(`     → Skipping save. Extract manually with correct share URL.`);
                  activeResearches.splice(i, 1);
                  continue;
                }
                if (matchCount === 0 && promptKeywords.length > 0) {
                  console.log(`  ⚠️ Low keyword match (${matchCount}/${promptKeywords.length}), but report is long (${report.length} chars). Saving anyway.`);
                }
              }
              const saved = saveReport(report, url, origFile, CWD, DR_RESULTS_DIR);
              extractedPaths.push(saved);
              notifyDone(file, url, saved, elapsed);
            } else {
              console.log(`  ⚠️  "${file}" extraction failed (${report?.length ?? 0} chars). Use gemini-dr-extract.ts manually.`);
              notifyDone(file, url, "", elapsed);
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
        console.log(`  Override timeout: DR_MAX_WAIT_MIN=45 npx tsx ... (current: ${MAX_WAIT_MIN}min)`);
        notifyTimeout(activeResearches.map(({ file, url }) => ({ file, url })), MAX_WAIT_MIN);
      }

      // Final summary
      console.log(`\n━━━ Final Results ━━━`);
      console.log(`  Submitted: ${ok} | Extracted: ${extractedPaths.length} | Failed: ${fail}`);
      for (const p of extractedPaths) {
        console.log(`  📄 ${p}`);
      }

      // Auto-sync initiatives (PDT only)
      if (extractedPaths.length > 0 && IS_PDT) {
        try {
          execSync(`python3 "${resolve(CWD, "scripts/generate-initiatives.py")}"`, { cwd: CWD, stdio: "pipe" });
          console.log("🔄 UI data synced (initiatives regenerated)");
        } catch {
          console.log("⚠️  UI sync skipped");
        }
      } else if (extractedPaths.length > 0) {
        console.log("⏭️  PDT sync skipped (not in PDT project)");
      }

      browser.close();
    }
  }
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
