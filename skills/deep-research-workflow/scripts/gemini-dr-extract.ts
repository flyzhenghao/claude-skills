#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research — Report Extractor
 *
 * Connects to Chrome via debug profile and extracts the completed Deep Research
 * report from a Gemini session as Markdown.
 *
 * Usage:
 *   npx tsx scripts/gemini-dr-extract.ts <session-url> [--output <path>]
 *
 * Examples:
 *   # Auto-save to research-results/
 *   npx tsx scripts/gemini-dr-extract.ts https://gemini.google.com/app/90ee40dbe8094e48
 *
 *   # Save to specific file
 *   npx tsx scripts/gemini-dr-extract.ts https://gemini.google.com/app/90ee40dbe8094e48 \
 *     --output research-results/my-report.md
 *
 * Prerequisites:
 *   Run gemini-deep-research.ts first (creates debug profile)
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync, rmSync } from "fs";
import { dirname, resolve, join } from "path";

const HOME = process.env.HOME ?? process.env.USERPROFILE;
if (!HOME) { console.error("❌ HOME not set"); process.exit(1); }
const DEBUG_PROFILE_DIR = `${HOME}/.chrome-debug-profile`;
const DR_RESULTS_DIR = resolve(process.cwd(), "research-results");

/**
 * Extract title from report text.
 * Gemini innerText strips HTML tags, so headings appear as plain text lines
 * (no `#` prefix). Try markdown heading first, then fall back to the first
 * non-empty line which is typically the report title.
 */
function extractReportTitle(report: string): string | null {
  // Try markdown heading (unlikely from Gemini innerText, but kept for robustness)
  const mdMatch = report.match(/^#\s+(.+)$/m);
  if (mdMatch) return mdMatch[1].trim();

  // First non-empty line is typically the title
  const firstLine = report.split("\n").find((l) => l.trim().length > 0)?.trim();
  if (firstLine && firstLine.length >= 5 && firstLine.length <= 200) return firstLine;

  return null;
}

function extractSessionId(url: string): string {
  const match = url.match(/\/app\/([a-f0-9]+)/);
  return match ? match[1] : url;
}

function parseArgs(): { sessionUrl: string; outputPath: string | null } {
  const args = process.argv.slice(2);
  let sessionUrl = "";
  let outputPath: string | null = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--output" && i + 1 < args.length) {
      outputPath = args[i + 1];
      i++;
    } else if (!args[i].startsWith("--")) {
      sessionUrl = args[i];
    }
  }

  return { sessionUrl, outputPath };
}

async function main() {
  const { sessionUrl, outputPath } = parseArgs();

  if (!sessionUrl) {
    console.error("Usage: npx tsx scripts/gemini-dr-extract.ts <session-url> [--output <path>]");
    console.error("Example: npx tsx scripts/gemini-dr-extract.ts https://gemini.google.com/app/90ee40dbe8094e48");
    process.exit(1);
  }

  const sessionId = extractSessionId(sessionUrl);

  // Clean lock files (same as gemini-dr-check.ts)
  for (const lf of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) {
    try { rmSync(join(DEBUG_PROFILE_DIR, lf), { force: true }); } catch {}
    try { rmSync(join(DEBUG_PROFILE_DIR, "Default", lf), { force: true }); } catch {}
  }

  // Launch persistent context (same approach as gemini-dr-check.ts)
  const context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    args: ["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
    ignoreDefaultArgs: ["--enable-automation"],
    viewport: { width: 1280, height: 900 },
  });

  {
    const page = await context.newPage();
    await page.goto(sessionUrl);
    await page.waitForTimeout(8000);

    // Extract the final Deep Research report (NOT the thinking process)
    //
    // Gemini Deep Research page structure:
    //   - thinking-panel: research PROCESS (searches, intermediate thoughts, source lists) — NOT the report
    //   - message-content[0]: research plan (pre-research)
    //   - message-content[1]: completion notice ("研究完成")
    //   - message-content[2]: FINAL REPORT (this is what we want)
    //
    // The final report is the longest .markdown block inside message-content elements
    // (explicitly excluding thinking-panel which contains process noise)
    const report = await page.evaluate(() => {
      // Strategy 1: Find the longest .markdown inside message-content (skip thinking-panel)
      // message-content contains the actual conversation messages, not the research process
      const msgContainers = document.querySelectorAll("message-content");
      let longestReport = "";
      for (const mc of msgContainers) {
        const markdownEl = mc.querySelector(".markdown");
        if (markdownEl) {
          const text = (markdownEl as HTMLElement).innerText;
          if (text.length > longestReport.length) {
            longestReport = text;
          }
        }
      }
      if (longestReport.length > 500) return longestReport;

      // Strategy 2: Find the longest .markdown NOT inside thinking-panel
      const allMarkdown = document.querySelectorAll(".markdown");
      let longest = "";
      for (const el of allMarkdown) {
        // Skip if inside thinking-panel (research process, not final report)
        if (el.closest("thinking-panel")) continue;
        // Skip if inside deep-research-processing-indicator
        if (el.closest("deep-research-processing-indicator")) continue;
        const text = (el as HTMLElement).innerText;
        if (text.length > longest.length) {
          longest = text;
        }
      }
      if (longest.length > 500) return longest;

      // Strategy 3: Fallback — longest model-response text (excluding thinking-panel)
      const modelResponses = document.querySelectorAll("model-response");
      let fallback = "";
      for (const mr of modelResponses) {
        if (mr.closest("thinking-panel")) continue;
        const text = (mr as HTMLElement).innerText;
        if (text.length > fallback.length) fallback = text;
      }
      if (fallback.length > 100) return fallback;

      return null;
    });

    if (!report || report.length < 100) {
      console.error("❌ Could not extract report or report too short.");
      console.error(`   Text length: ${report?.length ?? 0}`);
      console.error("   The research may still be in progress. Run gemini-dr-check.ts first.");
      await context.browser()?.close();
      process.exit(1);
    }

    // Build frontmatter
    const now = new Date().toISOString().split("T")[0];
    const markdown = `---
source: gemini-deep-research
session_url: ${sessionUrl}
extracted: ${now}
chars: ${report.length}
---

${report}
`;

    // Determine save path: explicit --output, or auto-generate in research-results/
    let savePath: string;
    if (outputPath) {
      savePath = resolve(outputPath);
    } else {
      // Auto-generate filename from report title or session ID
      const autoTitle = extractReportTitle(report);
      const slug = autoTitle
        ? autoTitle.slice(0, 60).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "")
        : sessionId;
      savePath = resolve(DR_RESULTS_DIR, `${now}-${slug}.md`);
    }

    mkdirSync(dirname(savePath), { recursive: true });
    writeFileSync(savePath, markdown, "utf-8");
    console.log(`✅ Report extracted (${report.length} chars) → ${savePath}`);

    await context.browser()?.close();
    process.exit(0);
  }
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
