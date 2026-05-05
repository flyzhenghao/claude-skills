#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research — Report Extractor
 *
 * Connects to Chrome via Remote Debugging Protocol and extracts
 * the completed Deep Research report from a Gemini session as Markdown.
 *
 * Usage:
 *   npx tsx scripts/gemini-dr-extract.ts <session-url> [--output <path>]
 *
 * Examples:
 *   # Print to stdout
 *   npx tsx scripts/gemini-dr-extract.ts https://gemini.google.com/app/90ee40dbe8094e48
 *
 *   # Save to file
 *   npx tsx scripts/gemini-dr-extract.ts https://gemini.google.com/app/90ee40dbe8094e48 \
 *     --output knowledge-base/ai-generated/analysis/research-reports/report-E.md
 *
 * Prerequisites:
 *   bash scripts/chrome-debug.sh start
 */

import { chromium, type BrowserContext } from "playwright";
import { readFileSync, writeFileSync, mkdirSync, rmSync, cpSync, existsSync } from "fs";
import { dirname, resolve, join } from "path";
import { execSync } from "child_process";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;
const CWD = process.cwd();
const IS_PDT = existsSync(resolve(CWD, "scripts/append-research-chain.sh")) &&
  existsSync(resolve(CWD, "package.json")) &&
  (() => { try { return JSON.parse(readFileSync(resolve(CWD, "package.json"), "utf-8")).name === "personal-digital-twin"; } catch { return false; } })();
const DR_RESULTS_DIR = IS_PDT
  ? resolve(CWD, "ai-docs/research/deep-research-results")
  : resolve(CWD, "deep-research-results");

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

  // Try to connect to existing Chrome on port 9222 (e.g. Playwright MCP or gemini-deep-research.ts)
  // Do NOT call ensureChromeNotRunning() — it would kill Playwright MCP's Chrome session
  let context: BrowserContext;
  let connectedViaCDP = false;

  try {
    execSync("curl -sf http://127.0.0.1:9222/json/version", { timeout: 3000 });
    console.error("📁 Found Chrome on port 9222, connecting via CDP...");
    const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
    const existingContext = browser.contexts()[0];
    if (existingContext) {
      context = existingContext;
      connectedViaCDP = true;
      console.error("  ✓ Connected to existing Chrome via CDP");
    } else {
      throw new Error("No browser context found");
    }
  } catch {
    // No Chrome on 9222 — launch our own with persistent context
    console.error("📁 No Chrome on port 9222, launching fresh instance...");

    // Sync login cookies from real Chrome profile (lightweight — no Chrome kill needed)
    const realDefault = join(process.env.HOME!, "Library/Application Support/Google/Chrome/Default");
    const debugDefault = join(DEBUG_PROFILE_DIR, "Default");
    if (existsSync(realDefault) && existsSync(debugDefault)) {
      const loginFiles = ["Cookies", "Cookies-journal", "Login Data", "Login Data-journal", "Web Data", "Web Data-journal"];
      let synced = 0;
      for (const f of loginFiles) {
        const src = join(realDefault, f);
        if (existsSync(src)) {
          try { cpSync(src, join(debugDefault, f)); synced++; } catch (e) { console.error(`⚠️ Failed to sync ${f}: ${(e as Error).message}`); }
        }
      }
      if (synced > 0) console.error(`📁 Synced ${synced} login files to debug profile`);
    }

    // Clean lock files
    for (const lf of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) {
      try { rmSync(join(DEBUG_PROFILE_DIR, lf), { force: true }); } catch {}
      try { rmSync(join(DEBUG_PROFILE_DIR, "Default", lf), { force: true }); } catch {}
    }

    context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
      channel: "chrome",
      headless: false,
      args: ["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
      ignoreDefaultArgs: ["--enable-automation"],
      viewport: { width: 1280, height: 900 },
    });
  }

  {
    const page = await context.newPage();
    await page.goto(sessionUrl);
    await page.waitForTimeout(8000);

    const found = true;

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
      await context.close();
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

    // Determine save path: explicit --output, or auto-generate in deep-research-results/
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
    console.error(`✅ Report extracted (${report.length} chars) → ${savePath}`);

    // Auto-append research chain entry + initiatives sync (PDT only)
    if (IS_PDT) {
      try {
        const chainTitle = extractReportTitle(report);
        if (!chainTitle) {
          console.error(`⚠️  Could not extract title from report — falling back to session ID. First 100 chars: ${report.slice(0, 100)}`);
        }
        const chainName = chainTitle ? chainTitle.slice(0, 80) : `Deep Research ${sessionId}`;
        const relPath = savePath.startsWith(CWD) ? savePath.slice(CWD.length + 1) : savePath;
        const pathSlug = savePath.split("/").pop()?.replace(/\.md$/, "").slice(0, 60).toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "") ?? sessionId;
        const chainId = `research-${now}-${pathSlug}`;
        const workPathMatch = relPath.match(/^ai-docs\/work\/([^/]+)\//);
        const inferredProjectId = workPathMatch?.[1] ?? "";
        if (!inferredProjectId) {
          console.error(`⚠️  Could not infer project ID from path: ${relPath}.`);
        }
        const chainJson = JSON.stringify({
          id: chainId, name: chainName, name_en: chainName,
          date_start: now, date_end: now, trigger: "Gemini Deep Research",
          status: "completed", domain: "work",
          tools_used: [{ name: "gemini-deep-research", count: 1, description: "Gemini Deep Research API" }],
          reports_generated: [{ path: relPath, description: chainName }],
          decisions: [], deliverables: [{ path: relPath, type: "report", description: chainName }],
        });
        const tmpChain = resolve(CWD, `.tmp-chain-${Date.now()}.json`);
        writeFileSync(tmpChain, chainJson, "utf-8");
        const projectArg = inferredProjectId ? ` --project "${inferredProjectId}"` : "";
        execSync(
          `bash "${resolve(CWD, "scripts/append-research-chain.sh")}" --input "${tmpChain}"${projectArg}`,
          { cwd: CWD, stdio: "pipe" }
        );
        try { rmSync(tmpChain); } catch {}
        console.error("🔗 Research chain entry appended");
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.error(`⚠️  Research chain append skipped: ${msg}`);
      }

      try {
        execSync(`python3 "${resolve(CWD, "scripts/generate-initiatives.py")}"`, { cwd: CWD, stdio: "pipe" });
        console.error("🔄 UI data synced (initiatives regenerated)");
      } catch {
        console.error("⚠️  UI sync skipped");
      }
    } else {
      console.error("⏭️  PDT sync skipped (not in PDT project)");
    }

    // Only close browser if we launched it ourselves (not if we connected to existing CDP)
    if (connectedViaCDP) {
      // Just close the page we opened, not the whole browser
      console.error("  ℹ️  Leaving shared Chrome running (connected via CDP)");
    } else {
      await context.browser()?.close();
    }
    process.exit(0);
  }
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
