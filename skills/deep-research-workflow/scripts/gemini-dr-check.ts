#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research — Status Checker
 *
 * Opens research URLs in debug profile Chrome and checks completion status.
 *
 * Usage:
 *   npx tsx scripts/gemini-dr-check.ts <url1> [url2] ...
 *
 * Exit codes:
 *   0 — All researches complete
 *   1 — Some still running or error
 */

import { chromium } from "playwright";
import { existsSync, rmSync } from "fs";
import { join } from "path";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;

async function checkStatus(url: string, context: Awaited<ReturnType<typeof chromium.launchPersistentContext>>, index: number): Promise<"completed" | "running" | "error" | "rejected"> {
  const page = await context.newPage();
  try {
    await page.goto(url);
    await page.waitForTimeout(6000);

    // === Priority 0: AUTH CHECK ===
    // 2026-04-28: Bug fix — dr-check launched a fresh Chrome context that
    // didn't share login cookies with the submitting session. Result: every
    // URL redirected to landing page (no message-content), and the default
    // fallthrough returned "running" — false positive for ALL sessions.
    // Now: explicitly detect signed-out state and return "error".
    const finalUrl = page.url();
    const isSignedIn = finalUrl.includes("/app") && await page.evaluate(() => {
      const accountBtn = document.querySelector('button[aria-label*="Google Account"], button[aria-label*="Google 账号"]');
      if (accountBtn) return true;
      const avatar = document.querySelector('img[src*="googleusercontent.com"], img[data-src*="googleusercontent.com"]');
      if (avatar) return true;
      const signInBtn = document.querySelector('a[href*="accounts.google.com"], button:has-text("Sign in"), button:has-text("登录")');
      if (signInBtn) return false;
      // No clear signal — assume signed in if we landed on /app
      return true;
    });
    if (!isSignedIn) {
      console.log(`❌ NOT SIGNED IN — ${url}`);
      console.log(`   dr-check Chrome context lacks Google session cookies. Final URL: ${finalUrl}`);
      console.log(`   Fix: ensure debug profile cookies are synced before running dr-check.`);
      await page.screenshot({ path: `/tmp/gemini-dr-check-${index}-noauth.png` });
      return "error";
    }

    const status = await page.evaluate(() => {
      // === Priority 1: Check for COMPLETED signals FIRST ===
      // Completed report is the strongest signal — check before running signals
      // because report body text may contain "researching websites" etc.
      const msgContainers = document.querySelectorAll("message-content");
      let longestMarkdown = 0;
      let hasCompletedMarker = false;

      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        // "Completed" or "I've completed" marker in short message block
        if (mcText.length < 500 && (
          mcText.includes("Completed") || mcText.includes("已完成") ||
          mcText.includes("I've completed") || mcText.includes("completed your research")
        )) {
          hasCompletedMarker = true;
        }
        // Measure markdown report length
        const md = mc.querySelector(".markdown");
        if (md) {
          const mdLen = (md as HTMLElement).innerText.length;
          if (mdLen > longestMarkdown) longestMarkdown = mdLen;
        }
      }

      // Completed = marker + substantial report (>5K chars = real report, not thinking text)
      if (hasCompletedMarker && longestMarkdown > 5000) {
        return { status: "completed", detail: "completed marker + report", reportLength: longestMarkdown };
      }

      // 3+ message blocks with a long report (>10K) = very likely done
      if (msgContainers.length >= 3 && longestMarkdown > 10000) {
        return { status: "completed", detail: `${msgContainers.length} msgs + ${longestMarkdown} char report`, reportLength: longestMarkdown };
      }

      // Substantial report (>5K) even without explicit marker = likely done
      if (longestMarkdown > 5000) {
        return { status: "completed", detail: `report ${longestMarkdown} chars (no explicit marker)`, reportLength: longestMarkdown };
      }

      // === Priority 1.5: REJECTED — Gemini refused (concurrency/quota) ===
      // 2026-04-28: Bug fix — script previously fell through to "running" when
      // Gemini said "You have 3 research requests running right now, which is
      // the maximum I can do at one time". checkStatus would return false-positive
      // RUNNING for what was actually a rejected/never-started session.
      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length > 500) continue;
        const lower = mcText.toLowerCase();
        if (lower.includes("research requests running") ||
            lower.includes("maximum i can do") ||
            lower.includes("at one time") ||
            lower.includes("too many") ||
            lower.includes("正在进行的研究") ||
            lower.includes("同时进行") ||
            lower.includes("用量限额") || lower.includes("限额")) {
          return { status: "rejected", detail: `Gemini rejected: "${mcText.slice(0, 120).replace(/\n/g, " ")}"`, reportLength: 0 };
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
        ];
        for (const sig of runningSignals) {
          if (lower.includes(sig)) {
            return { status: "running", detail: `found "${sig}" in UI element`, reportLength: 0 };
          }
        }
      }

      // === Priority 3: Check for error signals (scoped to short messages) ===
      for (const mc of Array.from(msgContainers)) {
        const mcText = (mc as HTMLElement).innerText;
        if (mcText.length < 300) {
          const lower = mcText.toLowerCase();
          if (lower.includes("something went wrong") || lower.includes("couldn't complete") || lower.includes("出错")) {
            return { status: "error", detail: "error message found", reportLength: longestMarkdown };
          }
        }
      }

      // === Default: still running or unknown ===
      return { status: "running", detail: `${msgContainers.length} msgs, ${longestMarkdown} chars`, reportLength: longestMarkdown };
    });

    await page.screenshot({ path: `/tmp/gemini-dr-check-${index}.png` });

    const emoji = status.status === "completed" ? "✅" :
                  status.status === "running" ? "🔄" :
                  status.status === "rejected" ? "🚫" : "❌";
    console.log(`${emoji} ${status.status.toUpperCase()} — ${url}`);
    console.log(`   ${status.detail}, report ${status.reportLength} chars`);

    return status.status as "completed" | "running" | "error" | "rejected";
  } catch (e: any) {
    console.log(`❌ ERROR — ${url}: ${e.message}`);
    return "error";
  }
}

async function main() {
  const urls = process.argv.slice(2);
  if (urls.length === 0) {
    console.log("Usage: npx tsx scripts/gemini-dr-check.ts <gemini-url-1> [url-2] ...");
    process.exit(0);
  }

  if (!existsSync(DEBUG_PROFILE_DIR)) {
    console.error("❌ Debug profile not found. Run gemini-deep-research.ts first.");
    process.exit(1);
  }

  // Clean lock files
  for (const lf of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) {
    try { rmSync(join(DEBUG_PROFILE_DIR, lf), { force: true }); } catch {}
    try { rmSync(join(DEBUG_PROFILE_DIR, "Default", lf), { force: true }); } catch {}
  }

  console.log("🔍 Checking research status...\n");

  const context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    args: ["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
    ignoreDefaultArgs: ["--enable-automation"],
    viewport: { width: 1280, height: 900 },
  });

  const statuses: Array<{ url: string; status: string }> = [];

  for (let i = 0; i < urls.length; i++) {
    const status = await checkStatus(urls[i], context, i + 1);
    statuses.push({ url: urls[i], status });
  }

  const completed = statuses.filter(s => s.status === "completed").length;
  const running = statuses.filter(s => s.status === "running").length;
  const rejected = statuses.filter(s => s.status === "rejected").length;
  const errored = statuses.length - completed - running - rejected;

  console.log(`\n━━━ Summary: ${completed} done, ${running} running, ${rejected} rejected, ${errored} error ━━━`);
  console.log(`   Concurrent slots available: ${Math.max(0, 3 - running)}`);

  if (rejected > 0) {
    console.log(`   ⚠ ${rejected} session(s) were REJECTED by Gemini (concurrency limit). Resubmit when slots free up.`);
    statuses.filter(s => s.status === "rejected").forEach(s => console.log(`     - ${s.url}`));
  }

  if (completed === statuses.length) {
    console.log("✅ All researches complete!");
  }

  await context.browser()?.close();
  process.exit(completed === statuses.length ? 0 : 1);
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
