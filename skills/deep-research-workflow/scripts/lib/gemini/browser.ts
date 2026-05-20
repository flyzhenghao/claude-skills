/**
 * Gemini Deep Research — Playwright browser interactions.
 *
 * Contains: submitOne, checkResearchStatus, clickStartResearch,
 *           extractReport, saveReport.
 */

import type { BrowserContext, Page } from "playwright";
import { writeFileSync, rmSync, mkdirSync, existsSync } from "fs";
import { basename, resolve, dirname } from "path";
import { execSync } from "child_process";

// Support multi-account Chrome profiles via GEMINI_ACCOUNT_INDEX env var.
// Chrome routes to /u/<N>/app for the Nth account (e.g. set =3 to use the 4th).
// Set GEMINI_ACCOUNT_INDEX=N to force a specific account.
const GEMINI_ACCOUNT_INDEX = process.env.GEMINI_ACCOUNT_INDEX;
const GEMINI_URL = GEMINI_ACCOUNT_INDEX
  ? `https://gemini.google.com/u/${GEMINI_ACCOUNT_INDEX}/app`
  : "https://gemini.google.com/app";

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

    // Check for quota/concurrency-limit/error messages to fail fast instead of waiting full timeout.
    // 2026-04-28: Real-world Gemini rejection observed:
    // "You have 3 research requests running right now, which is the maximum I can do at one time."
    // Without these keywords, script waited 90s before giving up, instead of failing in <10s.
    try {
      const quotaHit = await page.evaluate(() => {
        const msgContainers = document.querySelectorAll("message-content");
        for (const mc of Array.from(msgContainers)) {
          const text = (mc as HTMLElement).innerText;
          if (text.length > 500) continue;
          const lower = text.toLowerCase();
          if (lower.includes("用量限额") || lower.includes("限额") ||
              lower.includes("quota") || lower.includes("rate limit") ||
              lower.includes("too many") || lower.includes("无法提供帮助") ||
              lower.includes("research requests running") ||
              lower.includes("maximum i can do") ||
              lower.includes("at one time") ||
              lower.includes("正在进行的研究") || lower.includes("同时进行") ||
              lower.includes("something went wrong") || lower.includes("couldn't complete")) {
            return text.slice(0, 200);
          }
        }
        return null;
      });
      if (quotaHit) {
        console.log(`  ❌ Quota/concurrency-limit detected: "${quotaHit}"`);
        return false;
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
  _debugProfileDir?: string,
): Promise<{ success: boolean; url: string; page: Page; hitConcurrencyLimit?: boolean; contentMismatch?: boolean; loginFailed?: boolean }> {
  const page = await context.newPage();

  try {
    // P3: Screenshot helper for diagnostics at key steps
    const diagScreenshot = async (step: string) => {
      try { await page.screenshot({ path: `/tmp/gemini-dr-${index}-${step}.png` }); } catch {}
    };

    await page.goto(GEMINI_URL);
    await page.waitForTimeout(4000);

    // Bug 1 fix: if a previous session is residually loaded (URL contains a hex session ID),
    // navigate back to the clean /app URL to start a fresh conversation.
    const postGotoUrl = page.url();
    if (/\/app\/[a-f0-9]+/.test(postGotoUrl)) {
      console.log(`  ⚠ Stale session detected (${postGotoUrl}), navigating to fresh /app...`);
      await page.goto(GEMINI_URL);
      await page.waitForTimeout(4000);
    }

    // P0: Login check — URL-based check FIRST, then DOM signals.
    // Root cause: gemini.google.com/ (no /app) means we got redirected = not logged in.
    // The old fallthrough logic (`!hasSignInPage → logged in`) gave false positives
    // because the landing page has no explicit sign-in form elements.
    const currentUrl = page.url();
    const urlIndicatesLoggedIn = currentUrl.includes("/app");

    const isLoggedIn = urlIndicatesLoggedIn && await page.evaluate(() => {
      // Signal 1: Google Account button (most reliable, language-independent)
      const accountBtn = document.querySelector('button[aria-label*="Google Account"], button[aria-label*="Google 账号"], button[aria-label*="Google アカウント"]');
      if (accountBtn) return true;
      // Signal 2: avatar image
      const avatarImg = document.querySelector('img[data-src*="googleusercontent.com"], img[src*="googleusercontent.com"]');
      if (avatarImg) return true;
      // Signal 3: greeting text
      const body = document.body.textContent || "";
      if (body.includes("Hi ") || body.includes("Where should we start") ||
          body.includes("你好") || body.includes("需要我为你做些什么")) return true;
      // Signal 4: toolbox exists (only on /app when logged in)
      if (document.querySelector('button.toolbox-drawer-button')) return true;
      return false;
    });

    if (!urlIndicatesLoggedIn) {
      console.log(`  ⚠ Not logged in — URL redirected to: ${currentUrl} (expected /app)`);
    }
    await diagScreenshot("login-check");

    if (!isLoggedIn) {
      console.log("  ⚠ Not logged in — opening Google sign-in page...");
      console.log("  → Please log in to Google in the browser window that just opened.");
      console.log("  → Waiting up to 120 seconds for login...");
      await page.goto("https://accounts.google.com/ServiceLogin?continue=https://gemini.google.com/app");

      // Wait for user to complete login (poll every 5s for up to 120s)
      let loggedIn = false;
      for (let i = 0; i < 24; i++) {
        await page.waitForTimeout(5000);
        const currentUrl = page.url();
        if (currentUrl.includes("gemini.google.com/app")) {
          loggedIn = true;
          break;
        }
        // Also check if redirected to Gemini main page
        const nowLoggedIn = await page.evaluate(() => {
          const hasPro = !!document.querySelector('[data-test-id="pro-badge"], [aria-label*="Account"], img[alt*="avatar"], img[alt*="Account"]');
          const hasGreeting = document.body.textContent?.includes("Hi ") || document.body.textContent?.includes("Where should we start");
          return hasPro || hasGreeting;
        });
        if (nowLoggedIn) {
          loggedIn = true;
          break;
        }
        console.log(`  ⏳ Waiting for login... (${(i + 1) * 5}s)`);
      }

      if (!loggedIn) {
        console.error("  ❌ Login timeout (120s). Cookie resync may be needed.");
        await diagScreenshot("login-timeout");
        return { success: false, url: "", page, loginFailed: true };
      }
      await page.waitForTimeout(3000);
    }
    console.log("  ✓ Logged in");
    await diagScreenshot("logged-in");

    // 1. Activate Deep Research tool
    console.log("  → Selecting Deep Research tool...");

    // Helper: check if Deep Research is active.
    // Primary signal: the Deep Research menu item has aria-checked="true".
    // Fallback: input placeholder changes to "你想研究什么?" when DR is active.
    const isDRActive = async (): Promise<boolean> => {
      return page.evaluate(() => {
        // Signal 1 (2026-04-30): "Deselect Deep Research" aria-label button visible after activation
        const buttons = Array.from(document.querySelectorAll('button')) as HTMLButtonElement[];
        for (const b of buttons) {
          const al = b.getAttribute('aria-label') || '';
          if (/Deselect Deep Research/i.test(al)) return true;
        }
        // Signal 2: placeholder text changes when DR is active (legacy)
        const editors = document.querySelectorAll('div[contenteditable]');
        for (const ed of editors) {
          const ph = ed.getAttribute('aria-placeholder') || ed.getAttribute('data-placeholder') || '';
          if (ph.includes('研究') || ph.includes('research')) return true;
        }
        // Signal 3 (legacy): menuitemcheckbox aria-checked=true with .toolbox-drawer class
        const drItems = document.querySelectorAll('button[role="menuitemcheckbox"].toolbox-drawer');
        for (const item of drItems) {
          const text = item.textContent?.toLowerCase() || '';
          if ((text.includes('deep research') || text.includes('深度研究')) &&
              item.getAttribute('aria-checked') === 'true') {
            return true;
          }
        }
        return false;
      });
    };

    if (await isDRActive()) {
      console.log("  ✓ Deep Research already active");
    } else {
      // 2026-04-30 fix: Gemini Web UI changed — Tools button no longer has
      // .toolbox-drawer-button class. Use text-based selector primarily.
      // The Tools button only appears AFTER the contenteditable input is focused.
      // Strategy:
      //   1. Focus contenteditable input to make Tools button render
      //   2. Find Tools button by visible text ("Tools" or "工具")
      //   3. Click via DOM event (CDP overlay can intercept Playwright clicks)
      //   4. Find Deep Research menuitemcheckbox by text
      // NOTE: tsx/esbuild injects __name helper into named arrow functions (esbuild "keepNames").
      // Workaround: pass evaluate body as a string template — Playwright accepts string expressions
      // and runs them as-is in browser context without esbuild rewriting.
      const activatedRaw = await page.evaluate(`(async () => {
        const tb = document.querySelector('div[contenteditable="true"]');
        if (!tb) return { ok: false, step: 'no_textbox' };
        tb.focus();
        await new Promise(r => setTimeout(r, 400));

        const allButtons = Array.from(document.querySelectorAll('button'));
        let toolsBtn = null;
        for (const b of allButtons) {
          if (b.disabled) continue;
          const t = (b.innerText || '').trim();
          if (t === 'Tools' || t === '工具') { toolsBtn = b; break; }
        }
        if (!toolsBtn) return { ok: false, step: 'no_tools_btn' };
        toolsBtn.click();
        await new Promise(r => setTimeout(r, 700));

        const menuItems = Array.from(document.querySelectorAll('[role="menuitemcheckbox"]'));
        let drItem = null;
        for (const el of menuItems) {
          const t = (el.innerText || '').trim();
          if (/Deep Research/i.test(t) || t.includes('深度研究')) { drItem = el; break; }
        }
        if (!drItem) return { ok: false, step: 'no_dr_item', menuItemCount: menuItems.length };
        drItem.click();
        await new Promise(r => setTimeout(r, 700));

        const after = Array.from(document.querySelectorAll('button'));
        let verified = false;
        for (const b of after) {
          const al = b.getAttribute('aria-label') || '';
          if (/Deselect Deep Research/i.test(al)) { verified = true; break; }
        }
        return { ok: verified, step: verified ? 'verified' : 'no_deselect_btn' };
      })()`);
      const activated = activatedRaw as { ok: boolean; step: string; menuItemCount?: number };

      if (!activated.ok) {
        await diagScreenshot("dr-activation-failed");
        throw new Error(
          `Deep Research activation FAILED at step "${activated.step}". ` +
          `Refusing to submit as plain Gemini (silent quality downgrade). ` +
          `Diagnostics in /tmp/gemini-dr-*-dr-activation-failed*.png. ` +
          `Possible causes: (1) Gemini Web UI changed text/structure (run with --debug to see DOM), ` +
          `(2) account has no Pro/Advanced access, (3) DR feature gated by region. ` +
          `Manual workaround: open Gemini in browser, manually toggle "深度研究/Deep research" once.`
        );
      }
      console.log("  ✓ Deep Research activated (text-based selector)");
    }

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
    await diagScreenshot("prompt-inserted");

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
        // 2026-04-28: Real-world Gemini rejection text observed:
        // "You have 3 research requests running right now, which is the maximum I can do at one time."
        // Previous keyword list missed both "research requests running" and "maximum I can do at one time".
        if (lower.includes("too many") || lower.includes("already running") ||
            lower.includes("research requests running") ||
            lower.includes("maximum i can do") ||
            lower.includes("maximum number of") ||
            lower.includes("at one time") ||
            lower.includes("concurrent") || lower.includes("上限") ||
            lower.includes("用量限额") || lower.includes("限额") ||
            lower.includes("正在进行的研究") || lower.includes("同时进行") ||
            lower.includes("maximum number of deep research") ||
            lower.includes("rate limit") || lower.includes("quota")) {
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

    // Verify the page contains our prompt (not a stale/reused session).
    // Bug 3 fix: extract contiguous Chinese character segments (length >= 2) from the
    // actual promptText and require the page to contain at least 2 of them.
    // The old approach used the first-80-chars snippet split on whitespace, which fails
    // for Chinese prompts because individual English "words" from the file-name slug
    // don't appear in the Chinese report body.
    const pageContainsPrompt = await page.evaluate((pText) => {
      const body = document.body.textContent || "";
      // Extract contiguous Chinese character runs of length >= 2
      const chineseSegments = (pText.match(/[\u4e00-\u9fff]{2,}/g) || []).slice(0, 20);
      if (chineseSegments.length >= 2) {
        const matched = chineseSegments.filter(seg => body.includes(seg));
        return matched.length >= 2;
      }
      // Fallback for non-Chinese prompts: use significant words (length >= 4)
      const snippet = pText.slice(0, 80).replace(/[#*\n]/g, " ").trim();
      const words = snippet.split(/\s+/).filter(w => w.length >= 4);
      const matched = words.filter(w => body.includes(w));
      return matched.length >= Math.min(3, words.length);
    }, promptText);

    if (!pageContainsPrompt) {
      console.error(`  ⚠️ CONTENT MISMATCH: page does not contain prompt keywords. This session may be stale/reused.`);
      console.log(`  → Prompt snippet: "${promptText.slice(0, 60).replace(/\n/g, ' ')}..."`);
      console.log(`  → URL: ${finalUrl}`);
      console.log(`  → This research may need manual re-submission.`);
      await page.screenshot({ path: `/tmp/gemini-dr-${index}-mismatch.png` });
      return { success: false, url: finalUrl, page, contentMismatch: true };
    }

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
  } catch (e: unknown) {
    try { await page.screenshot({ path: `/tmp/gemini-dr-${index}-error.png` }); } catch {}
    const msg = e instanceof Error ? e.message : String(e);
    console.error(`  ❌ Error: ${msg}`);
    return { success: false, url: "", page };
  }
}

/**
 * Check if a research page has completed (shows final report).
 * Returns: "running" | "completed" | "error" | "rejected"
 *
 * IMPORTANT: Check COMPLETED signals FIRST, then RUNNING signals.
 * Report body text often contains words like "researching", "browsing",
 * "searching the web" — checking running signals on full body text
 * causes false negatives (forever "running" even after completion).
 * Running signals must be scoped to short UI elements only.
 *
 * "rejected" = Gemini refused to start the research (concurrency limit, quota).
 * 2026-04-28: Bug — script previously fell through to "running" when
 * Gemini said "You have 3 research requests running right now, which is
 * the maximum I can do at one time", causing false positive in dr-check.
 */
export async function checkResearchStatus(page: Page): Promise<"running" | "completed" | "error" | "rejected"> {
  try {
    return await page.evaluate(() => {
      // === Priority 1: Check for COMPLETED signals FIRST ===
      // Completed report is the strongest signal — check before running signals
      // because report body text may contain "researching websites" etc.
      const msgContainers = document.querySelectorAll("message-content");
      let longestMarkdown = 0;
      let hasCompletedMarker = false;

      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length < 500 && (
          mcText.includes("Completed") || mcText.includes("已完成") ||
          mcText.includes("I've completed") || mcText.includes("completed your research")
        )) {
          hasCompletedMarker = true;
        }
        const md = mc.querySelector(".markdown");
        if (md) {
          const mdLen = (md as HTMLElement).innerText.length;
          if (mdLen > longestMarkdown) longestMarkdown = mdLen;
        }
      }

      // Completed = marker + substantial report
      if (hasCompletedMarker && longestMarkdown > 5000) return "completed" as const;
      // 3+ message blocks with a long report = very likely done
      if (msgContainers.length >= 3 && longestMarkdown > 10000) return "completed" as const;
      // Substantial report even without explicit marker = likely done
      if (longestMarkdown > 5000) return "completed" as const;

      // === Priority 1.5: REJECTED — Gemini refused due to concurrency/quota ===
      // Must check before "running" to avoid false positive in dr-check.ts.
      // Real-world rejection text (2026-04-28):
      // "You have 3 research requests running right now, which is the maximum I can do at one time."
      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length > 500) continue;
        const lower = mcText.toLowerCase();
        if (lower.includes("research requests running") ||
            lower.includes("maximum i can do") ||
            lower.includes("at one time") ||
            lower.includes("too many") ||
            lower.includes("已经在运行") ||
            lower.includes("正在进行的研究") ||
            lower.includes("同时进行") ||
            lower.includes("用量限额") || lower.includes("限额")) {
          return "rejected" as const;
        }
      }

      // === Priority 2: Check for RUNNING signals ===
      // Only check in SHORT elements (progress panel, status text), NOT in report body
      // This prevents false positives from completed reports containing "researching websites"
      const shortElements = document.querySelectorAll("p, span, div");
      for (const el of Array.from(shortElements)) {
        const text = (el as HTMLElement).innerText || "";
        if (text.length > 200) continue; // skip long content (report body)
        const lower = text.toLowerCase();
        const runningSignals = [
          "researching websites", "searching the web", "browsing", "reading websites",
          "正在研究",
        ];
        for (const sig of runningSignals) {
          if (lower.includes(sig)) return "running" as const;
        }
      }

      // === Priority 3: ERROR — scoped to short messages only ===
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
 * Save extracted report to disk with frontmatter + research chain append.
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

  // Append research chain entry (PDT only — detect via script existence)
  const chainScript = resolve(repoRoot, "scripts/append-research-chain.sh");
  if (existsSync(chainScript)) {
    try {
      const relPath = savePath.startsWith(repoRoot) ? savePath.slice(repoRoot.length + 1) : savePath;
      const sessionId = sessionUrl.match(/\/app\/([a-f0-9]+)/)?.[1] ?? "unknown";
      const pathSlug = basename(savePath, ".md").slice(0, 60).toLowerCase().replace(/[^a-z0-9-]+/g, "-");
      const chainId = `research-${now}-${pathSlug}`;
      const chainJson = JSON.stringify({
        id: chainId, name: title.slice(0, 80), name_en: title.slice(0, 80),
        date_start: now, date_end: now, trigger: "Gemini Deep Research",
        status: "completed", domain: "work",
        tools_used: [{ name: "gemini-deep-research", count: 1, description: "Gemini Deep Research API" }],
        reports_generated: [{ path: relPath, description: title.slice(0, 80) }],
        decisions: [], deliverables: [{ path: relPath, type: "report", description: title.slice(0, 80) }],
      });
      const tmpChain = resolve(repoRoot, `.tmp-chain-${Date.now()}.json`);
      writeFileSync(tmpChain, chainJson, "utf-8");
      const workPathMatch = relPath.match(/^ai-docs\/work\/([^/]+)\//);
      const projectArg = workPathMatch?.[1] ? ` --project "${workPathMatch[1]}"` : "";
      execSync(`bash "${chainScript}" --input "${tmpChain}"${projectArg}`, { cwd: repoRoot, stdio: "pipe" });
      try { rmSync(tmpChain); } catch {}
      console.log("  🔗 Research chain entry appended");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ⚠️  Research chain append skipped: ${msg}`);
    }
  } else {
    console.log("  ⏭️  Research chain skipped (not in PDT project)");
  }

  return savePath;
}
