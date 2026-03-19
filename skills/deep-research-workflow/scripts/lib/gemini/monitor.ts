/**
 * Gemini Deep Research — completion polling monitor.
 */

import type { Page } from "playwright";
import { checkResearchStatus } from "./browser.js";

/**
 * Wait for any one of the active research pages to complete.
 * Returns the index of the completed page, or -1 on timeout.
 */
export async function waitForAnyResearchComplete(
  activePages: Array<{ page: Page; file: string; url: string }>,
  timeoutMs = 900000, // 15 min max
  pollIntervalMs = 30000, // check every 30s
): Promise<number> {
  const startTime = Date.now();
  console.log(`\n⏳ Waiting for a research to complete (checking every ${pollIntervalMs / 1000}s, timeout ${timeoutMs / 60000}min)...`);
  console.log(`   Active researches: ${activePages.map(p => p.file).join(", ")}`);

  while (Date.now() - startTime < timeoutMs) {
    for (let i = 0; i < activePages.length; i++) {
      const { page, file } = activePages[i];
      const status = await checkResearchStatus(page);

      if (status === "completed") {
        console.log(`\n  ✅ "${file}" research completed! (${Math.round((Date.now() - startTime) / 1000)}s)`);
        return i;
      }
      if (status === "error") {
        console.log(`\n  ❌ "${file}" research errored. (${Math.round((Date.now() - startTime) / 1000)}s)`);
        return i; // Free up a slot even on error
      }
    }

    const elapsed = Math.round((Date.now() - startTime) / 1000);
    console.log(`  ⏳ ${elapsed}s — all ${activePages.length} researches still running...`);
    await new Promise(r => setTimeout(r, pollIntervalMs));
  }

  console.log(`  ⚠ Timeout after ${timeoutMs / 60000}min — no research completed`);
  return -1;
}
