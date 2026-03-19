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
import { checkResearchStatus } from "./lib/gemini/browser.js";

const HOME = process.env.HOME ?? process.env.USERPROFILE;
if (!HOME) { console.error("❌ HOME not set"); process.exit(1); }
const DEBUG_PROFILE_DIR = `${HOME}/.chrome-debug-profile`;

async function checkStatus(url: string, context: Awaited<ReturnType<typeof chromium.launchPersistentContext>>, index: number): Promise<"completed" | "running" | "error"> {
  const page = await context.newPage();
  try {
    await page.goto(url);
    await page.waitForTimeout(6000);

    const status = await checkResearchStatus(page);
    await page.screenshot({ path: `/tmp/gemini-dr-check-${index}.png` });

    const emoji = status === "completed" ? "✅" : status === "running" ? "🔄" : "❌";
    console.log(`${emoji} ${status.toUpperCase()} — ${url}`);

    return status;
  } catch (e: unknown) {
    console.log(`❌ ERROR — ${url}: ${e instanceof Error ? e.message : String(e)}`);
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

  console.log(`\n━━━ Summary: ${completed} done, ${running} running, ${statuses.length - completed - running} error ━━━`);
  console.log(`   Concurrent slots available: ${3 - running}`);

  if (completed === statuses.length) {
    console.log("✅ All researches complete!");
  }

  await context.browser()?.close();
  process.exit(completed === statuses.length ? 0 : 1);
}

main().catch(e => { console.error("Fatal:", e.message); process.exit(1); });
