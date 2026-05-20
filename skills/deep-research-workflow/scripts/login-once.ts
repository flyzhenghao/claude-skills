#!/usr/bin/env npx tsx
/**
 * One-time Google login in Playwright-managed Chrome.
 * After login, the session is saved in the debug profile
 * and subsequent script runs will be authenticated.
 */
import { chromium } from "playwright";

const DEBUG_PROFILE_DIR = `${process.env.HOME}/.chrome-debug-profile`;

async function main() {
  console.log("🔓 Opening Chrome for Google login...");
  console.log("   Please log in to Google in the browser window.");
  console.log("   Waiting up to 5 minutes...\n");

  const context = await chromium.launchPersistentContext(DEBUG_PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-blink-features=AutomationControlled",
    ],
  });

  const page = await context.newPage();
  await page.goto("https://accounts.google.com/ServiceLogin?continue=https://gemini.google.com/app");

  // Wait up to 5 minutes for login
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(5000);
    const url = page.url();
    if (url.includes("gemini.google.com/app")) {
      console.log("✅ Login successful! Closing browser...");
      await page.waitForTimeout(3000);
      await context.close();
      console.log("✅ Session saved. Scripts will now work without re-login.");
      return;
    }
    if (i % 6 === 5) {
      console.log(`   ⏳ Still waiting... (${(i + 1) * 5}s)`);
    }
  }

  console.error("❌ Login timeout (5 minutes). Please try again.");
  await context.close();
  process.exit(1);
}

main().catch(console.error);
