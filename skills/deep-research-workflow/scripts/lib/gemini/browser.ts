/**
 * Gemini Deep Research — Playwright browser interactions.
 *
 * Contains: submitOne, checkResearchStatus, clickStartResearch,
 *           extractReport, saveReport.
 */

import type { BrowserContext, Page } from "playwright";
import { writeFileSync, mkdirSync } from "fs";
import { basename, resolve, dirname } from "path";

const GEMINI_URL = "https://gemini.google.com/app";

export async function clickStartResearch(page: Page, maxWaitMs = 90000): Promise<boolean> {
  const labels = ["开始研究", "Start research", "Start Research", "Begin research"];
  const startTime = Date.now();
  let attempt = 0;

  while (Date.now() - startTime < maxWaitMs) {
    attempt++;
    for (const label of labels) {
      try {
        const btn = page.getByText(label, { exact: true });
        if (await btn.isVisible({ timeout: 2000 })) {
          await btn.click();
          console.log(`  ✓ Clicked "${label}" (attempt ${attempt}, ${Math.round((Date.now() - startTime) / 1000)}s)`);
          return true;
        }
      } catch { continue; }
    }

    // Also try button with role="button" containing the text
    try {
      const altBtn = page.locator('button:has-text("Start research"), button:has-text("开始研究"), [role="button"]:has-text("Start research"), [role="button"]:has-text("开始研究")').first();
      if (await altBtn.isVisible({ timeout: 1000 })) {
        await altBtn.click();
        console.log(`  ✓ Clicked start button via selector (attempt ${attempt}, ${Math.round((Date.now() - startTime) / 1000)}s)`);
        return true;
      }
    } catch {}

    // Check if research already started (no confirmation needed)
    // IMPORTANT: Match specific running-state phrases, NOT generic words like "websites"
    // which appear in the research plan text (e.g., "Research Websites" heading)
    try {
      const researching = await page.evaluate(() => {
        const text = document.body.textContent || "";
        // "Researching websites" = active research; "Research Websites" = plan heading (ignore)
        return text.includes("Researching websites") ||
               text.includes("Researching ") ||
               text.includes("正在研究") ||
               /Browsing \d+ (website|source)/i.test(text) ||
               /Searching .+\.\.\./i.test(text);
      });
      if (researching) {
        console.log(`  ✓ Research already started (no confirmation needed)`);
        return true;
      }
    } catch {}

    console.log(`  ⏳ Waiting for research plan... (${Math.round((Date.now() - startTime) / 1000)}s)`);
    await page.waitForTimeout(5000);
  }

  return false;
}

export async function submitOne(
  context: BrowserContext,
  promptText: string,
  index: number,
  debugProfileDir: string,
): Promise<{ success: boolean; url: string; page: Page; hitConcurrencyLimit?: boolean }> {
  const page = await context.newPage();

  try {
    await page.goto(GEMINI_URL);
    await page.waitForTimeout(4000);

    // Verify logged in
    const isLoggedIn = await page.evaluate(() => {
      const hasPro = !!document.querySelector('[data-test-id="pro-badge"], [aria-label*="Account"], img[alt*="avatar"], img[alt*="Account"]');
      const hasGreeting = document.body.textContent?.includes("Hi ") || document.body.textContent?.includes("Where should we start");
      const hasSignInPage = !!document.querySelector('button[data-action="sign in"], [data-signin], a[href*="accounts.google.com/ServiceLogin"]');
      return hasPro || hasGreeting || !hasSignInPage;
    });
    if (!isLoggedIn) {
      console.error("  ❌ Not logged in to Google!");
      console.error("");
      console.error("  The debug profile needs a one-time login. Run this command:");
      console.error(`    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --user-data-dir="${debugProfileDir}" --no-first-run https://accounts.google.com`);
      console.error("");
      console.error("  Log into Google, close Chrome, then re-run this script.");
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-notloggedin.png` });
      await context.browser()?.close();
      process.exit(1);
    }
    console.log("  ✓ Logged in");

    // 1. Click Tools → Deep Research
    console.log("  → Selecting Deep Research tool...");
    await page.locator('button:has-text("Tools")').click();
    await page.waitForTimeout(1500);
    await page.getByText("Deep Research", { exact: true }).click();
    await page.waitForTimeout(2000);

    // 2. Fill prompt via direct DOM insertion
    console.log("  → Inserting prompt...");
    const inputBox = page.locator('div[contenteditable="true"]').first();
    await inputBox.click();
    await page.waitForTimeout(500);

    // Use execCommand('insertText') which triggers React/Gemini's input handlers
    const inserted = await page.evaluate((text) => {
      const el = document.querySelector('div[contenteditable="true"]');
      if (!el) return false;
      (el as HTMLElement).focus();
      const ok = document.execCommand("insertText", false, text);
      if (!ok) {
        (el as HTMLElement).textContent = text;
        el.dispatchEvent(new Event("input", { bubbles: true }));
      }
      return true;
    }, promptText);

    if (!inserted) {
      console.error("  ❌ Could not find contenteditable input");
      return { success: false, url: "", page };
    }
    await page.waitForTimeout(2000);

    // Verify insertion length
    let len = await inputBox.evaluate(el => el.textContent?.length || 0);
    console.log(`  → First attempt: ${len} / ${promptText.length} chars`);

    // If insertion was significantly truncated, retry with chunked approach
    if (len < promptText.length * 0.8) {
      console.log("  → Retrying with chunked insertion...");
      await inputBox.evaluate(el => {
        (el as HTMLElement).textContent = "";
        el.dispatchEvent(new Event("input", { bubbles: true }));
      });
      await page.waitForTimeout(500);
      await inputBox.click();
      await page.waitForTimeout(300);

      const CHUNK_SIZE = 2000;
      for (let offset = 0; offset < promptText.length; offset += CHUNK_SIZE) {
        const chunk = promptText.slice(offset, offset + CHUNK_SIZE);
        await page.evaluate((text) => {
          document.execCommand("insertText", false, text);
        }, chunk);
        await page.waitForTimeout(100);
      }
      await page.waitForTimeout(1500);
      len = await inputBox.evaluate(el => el.textContent?.length || 0);
      console.log(`  → Chunked result: ${len} / ${promptText.length} chars`);
    }

    console.log(`  ✓ Prompt inserted (${len} chars)`);

    if (len < 50) {
      console.error("  ❌ Paste failed");
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-fail.png` });
      return { success: false, url: "", page };
    }

    // 3. Submit by clicking the send button
    console.log("  → Submitting...");
    let submitted = false;

    const sendSelectors = [
      'button[aria-label="Send message"]',
      'button[aria-label="Send"]',
      'button[aria-label="发送"]',
      'button[data-tooltip="Send message"]',
      'button.send-button',
      'div[contenteditable="true"] ~ button',
    ];

    for (const sel of sendSelectors) {
      try {
        const btn = page.locator(sel).first();
        if (await btn.isVisible({ timeout: 2000 })) {
          await btn.click();
          submitted = true;
          console.log(`  ✓ Clicked send button (${sel})`);
          break;
        }
      } catch { continue; }
    }

    // Fallback: find any clickable send-like button near the input area
    if (!submitted) {
      try {
        const sendBtn = page.locator('button:has(svg path[d*="M2"]), button:has(mat-icon:has-text("send")), button:has(mat-icon:has-text("arrow"))').last();
        if (await sendBtn.isVisible({ timeout: 2000 })) {
          await sendBtn.click();
          submitted = true;
          console.log("  ✓ Clicked send button (svg fallback)");
        }
      } catch {}
    }

    // Last resort: keyboard shortcut
    if (!submitted) {
      console.log("  → Trying Ctrl+Enter...");
      await page.keyboard.press("Control+Enter");
      await page.waitForTimeout(1000);
      await page.keyboard.press("Meta+Enter");
      submitted = true;
      console.log("  ⚠ Used keyboard shortcut (may not work)");
    }

    await page.waitForTimeout(5000);

    // Verify submission
    const postSubmitLen = await inputBox.evaluate(el => el.textContent?.length || 0).catch(() => -1);
    const postSubmitUrlChanged = page.url() !== GEMINI_URL && page.url() !== `${GEMINI_URL}?hl=en_GB`;

    if (postSubmitLen > 100 && !postSubmitUrlChanged) {
      console.error("  ⚠ Input box still has text — submission may have failed");
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-stuck.png` });
      try {
        await inputBox.press("Tab");
        await page.waitForTimeout(500);
        await page.keyboard.press("Enter");
        await page.waitForTimeout(5000);
        console.log("  → Retried with Tab+Enter");
      } catch {}
    }

    // 4. Check for concurrency limit (Gemini allows max 3 simultaneous deep researches)
    // Scope to short UI messages only — avoid matching "limit" in prompt text or report body
    await page.waitForTimeout(3000);
    const hitLimit = await page.evaluate(() => {
      const msgContainers = document.querySelectorAll("message-content");
      for (const mc of Array.from(msgContainers)) {
        const text = (mc as HTMLElement).innerText;
        // Only check short messages (UI notices, not user prompts or reports)
        if (text.length > 500) continue;
        const lower = text.toLowerCase();
        if (lower.includes("too many") || lower.includes("already running") ||
            lower.includes("concurrent") || lower.includes("上限") ||
            lower.includes("maximum number of deep research")) {
          return true;
        }
      }
      return false;
    });
    if (hitLimit) {
      console.error("  ❌ Hit Gemini concurrent research limit (max 3 simultaneous)");
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-limit.png` });
      return { success: false, url: "", page, hitConcurrencyLimit: true };
    }

    // 5. Wait for research plan and click confirmation
    console.log("  → Waiting for research plan & confirmation button (up to 90s)...");
    const confirmed = await clickStartResearch(page, 90000);
    if (!confirmed) {
      console.error("  ❌ Research confirmation button not found after 90s");
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-noconfirm.png` });
      return { success: false, url: page.url(), page };
    }
    console.log("  ✓ Research confirmed/started");

    await page.waitForTimeout(5000);

    // 6. VERIFY research is actually running (not just submitted)
    // IMPORTANT: Match specific running-state phrases to avoid false positives
    // from research plan text (e.g., "Research Websites" heading, "sources" in plan)
    const isResearching = await page.evaluate(() => {
      const text = document.body.textContent || "";
      return text.includes("Researching websites") ||
        text.includes("Researching ") ||
        text.includes("正在研究") ||
        /Browsing \d+ (website|source)/i.test(text) ||
        /Searching .+\.\.\./i.test(text) ||
        /\d+ sources? found/i.test(text);
    });

    const finalUrl = page.url();
    await page.screenshot({ path: `/tmp/gemini-dr-${index}-done.png` });

    if (isResearching) {
      console.log(`  ✅ Verified: research is running. URL: ${finalUrl}`);
      return { success: true, url: finalUrl, page };
    }

    // Fallback: check if URL changed (indicates submission went through)
    const urlChanged = finalUrl !== GEMINI_URL && finalUrl !== `${GEMINI_URL}?hl=en_GB`;
    if (urlChanged) {
      console.log(`  ✅ Submitted (URL changed). URL: ${finalUrl}`);
      console.log(`  ⚠ Could not verify active research — check manually`);
      return { success: true, url: finalUrl, page };
    }

    console.error("  ❌ Research did not start — no activity detected on page");
    await page.screenshot({ path: `/tmp/gemini-dr-${index}-failed.png` });
    return { success: false, url: "", page };
  } catch (e: any) {
    try { await page.screenshot({ path: `/tmp/gemini-dr-${index}-error.png` }); } catch {}
    console.error(`  ❌ Error: ${e.message}`);
    return { success: false, url: "", page };
  }
}

/**
 * Check if a research page has completed (shows final report).
 * Returns: "running" | "completed" | "error"
 */
export async function checkResearchStatus(page: Page): Promise<"running" | "completed" | "error"> {
  try {
    return await page.evaluate(() => {
      const bodyLower = (document.body.textContent || "").toLowerCase();

      // Priority 1: RUNNING signals (most reliable — check first)
      const runningSignals = [
        "researching websites", "researching", "正在研究",
        "searching the web", "browsing", "reading websites",
      ];
      for (const sig of runningSignals) {
        if (bodyLower.includes(sig)) return "running" as const;
      }

      // Priority 2: COMPLETED — check message-content structure
      const msgContainers = document.querySelectorAll("message-content");
      let longestMarkdown = 0;
      let hasCompletedMarker = false;

      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length < 500 && (mcText.includes("Completed") || mcText.includes("已完成"))) {
          hasCompletedMarker = true;
        }
        const md = mc.querySelector(".markdown");
        if (md) {
          const mdLen = (md as HTMLElement).innerText.length;
          if (mdLen > longestMarkdown) longestMarkdown = mdLen;
        }
      }

      if (hasCompletedMarker && longestMarkdown > 5000) return "completed" as const;
      if (msgContainers.length >= 3 && longestMarkdown > 10000) return "completed" as const;

      // Priority 3: ERROR — scoped to short messages only
      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length < 300) {
          const lower = mcText.toLowerCase();
          if (lower.includes("something went wrong") || lower.includes("couldn't complete") || lower.includes("出错")) {
            return "error" as const;
          }
        }
      }

      return "running" as const;
    });
  } catch {
    return "error";
  }
}

/**
 * Extract the final Deep Research report from a completed page.
 * Returns the report text, or null if extraction fails.
 */
export async function extractReport(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    // Strategy 1: longest .markdown inside message-content (skip thinking-panel)
    const msgContainers = document.querySelectorAll("message-content");
    let longestReport = "";
    for (const mc of msgContainers) {
      const markdownEl = mc.querySelector(".markdown");
      if (markdownEl) {
        const text = (markdownEl as HTMLElement).innerText;
        if (text.length > longestReport.length) longestReport = text;
      }
    }
    if (longestReport.length > 500) return longestReport;

    // Strategy 2: longest .markdown NOT inside thinking-panel
    const allMarkdown = document.querySelectorAll(".markdown");
    let longest = "";
    for (const el of allMarkdown) {
      if (el.closest("thinking-panel")) continue;
      if (el.closest("deep-research-processing-indicator")) continue;
      const text = (el as HTMLElement).innerText;
      if (text.length > longest.length) longest = text;
    }
    if (longest.length > 500) return longest;

    // Strategy 3: fallback — longest model-response (excluding thinking-panel)
    const modelResponses = document.querySelectorAll("model-response");
    let fallback = "";
    for (const mr of modelResponses) {
      if (mr.closest("thinking-panel")) continue;
      const text = (mr as HTMLElement).innerText;
      if (text.length > fallback.length) fallback = text;
    }
    return fallback.length > 100 ? fallback : null;
  });
}

/**
 * Save extracted report to disk with frontmatter.
 * Returns the saved file path.
 */
export function saveReport(
  report: string,
  sessionUrl: string,
  promptFile: string,
  repoRoot: string,
  drResultsDir: string,
): string {
  const now = new Date().toISOString().split("T")[0];

  // Extract title from first non-empty line
  const firstLine = report.split("\n").find(l => l.trim().length > 0)?.trim();
  const title = firstLine && firstLine.length >= 5 && firstLine.length <= 200 ? firstLine : basename(promptFile, ".md");
  const slug = title.slice(0, 60).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "");
  const savePath = resolve(drResultsDir, `${now}-${slug}.md`);

  const markdown = `---\nsource: gemini-deep-research\nsession_url: ${sessionUrl}\nextracted: ${now}\nchars: ${report.length}\n---\n\n${report}\n`;
  mkdirSync(dirname(savePath), { recursive: true });
  writeFileSync(savePath, markdown, "utf-8");
  console.log(`  📄 Saved report (${report.length} chars) → ${savePath}`);

  return savePath;
}
