#!/usr/bin/env npx tsx
/**
 * Extract Gemini Deep Research reports from share URLs.
 * Usage: npx tsx extract-share.ts <url1> [url2] [url3] ...
 */
import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";
import { resolve, basename } from "path";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;

async function extractFromShare(url: string, index: number, outputDir: string): Promise<string | null> {
  const context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    args: ["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
  });

  try {
    const page = await context.newPage();
    console.log(`\n━━━ [${index}] ${url} ━━━`);
    await page.goto(url);
    await page.waitForTimeout(8000);

    // Extract the longest markdown/text block
    const report = await page.evaluate(() => {
      // Try .markdown elements first
      const markdownEls = document.querySelectorAll(".markdown");
      let longest = "";
      for (const el of markdownEls) {
        const text = (el as HTMLElement).innerText;
        if (text.length > longest.length) longest = text;
      }
      if (longest.length > 500) return longest;

      // Fallback: message-content
      const msgContainers = document.querySelectorAll("message-content");
      for (const mc of msgContainers) {
        const text = (mc as HTMLElement).innerText;
        if (text.length > longest.length) longest = text;
      }
      if (longest.length > 500) return longest;

      // Last resort: body text
      return document.body.innerText.length > 500 ? document.body.innerText : null;
    });

    if (!report || report.length < 500) {
      console.log(`  ❌ Could not extract (${report?.length || 0} chars)`);
      await page.screenshot({ path: `/tmp/gemini-share-${index}.png` });
      await context.close();
      return null;
    }

    // Get title from first line
    const firstLine = report.split("\n").find(l => l.trim().length > 0)?.trim() || `share-${index}`;
    const slug = firstLine.slice(0, 60).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "");
    const now = new Date().toISOString().split("T")[0];
    const savePath = resolve(outputDir, `${now}-${slug}.md`);

    const markdown = `---\nsource: gemini-deep-research-share\nshare_url: ${url}\nextracted: ${now}\nchars: ${report.length}\n---\n\n${report}\n`;
    mkdirSync(outputDir, { recursive: true });
    writeFileSync(savePath, markdown, "utf-8");
    console.log(`  ✅ Saved (${report.length} chars) → ${savePath}`);

    await context.close();
    return savePath;
  } catch (e) {
    console.error(`  ❌ Error: ${(e as Error).message}`);
    await context.close();
    return null;
  }
}

async function main() {
  const urls = process.argv.slice(2).filter(a => a.startsWith("http"));
  if (urls.length === 0) {
    console.error("Usage: npx tsx extract-share.ts <url1> [url2] ...");
    process.exit(1);
  }

  const outputDir = resolve(process.cwd(), "deep-research-results");
  console.log(`🔬 Extracting ${urls.length} share link(s)...\n`);

  const results: string[] = [];
  for (let i = 0; i < urls.length; i++) {
    const path = await extractFromShare(urls[i], i + 1, outputDir);
    if (path) results.push(path);
  }

  console.log(`\n━━━ Done: ${results.length}/${urls.length} extracted ━━━`);
  for (const r of results) console.log(`  📄 ${r}`);
}

main().catch(console.error);
