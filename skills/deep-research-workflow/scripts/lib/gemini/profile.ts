/**
 * Gemini Deep Research — Chrome profile management.
 *
 * CRITICAL RULE: NEVER quit/kill/close Chrome. The user's login session is sacred.
 *
 * Strategy:
 * 1. Check if Chrome with debug port 9222 is already running → connect to it
 * 2. If not → launch a NEW Chrome with debug profile + port 9222
 * 3. If a non-debug Chrome is blocking → ask the user to close it manually
 * 4. NEVER call osascript quit, pkill, or any variant that kills Chrome
 *
 * The debug profile (~/.chrome-debug-profile) persists login state across restarts.
 * First run requires manual Google login; subsequent runs reuse saved cookies.
 */

import { existsSync, rmSync, cpSync, statSync } from "fs";
import { join } from "path";
import { execSync, spawn } from "child_process";

const CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
// Fallback: Playwright's bundled "Chrome for Testing" — independent process from
// user's daily Chrome, avoiding the macOS "Chrome master routes second instance"
// limitation. Glob-resolved at runtime since version dir varies.
const PLAYWRIGHT_CHROMIUM_GLOB = `${process.env.HOME}/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const REAL_CHROME_DIR = `${process.env.HOME}/Library/Application Support/Google/Chrome`;
const DEBUG_PORT = 9222;

function findPlaywrightChromium(): string | null {
  try {
    // Glob has spaces — use sh with double quotes carefully
    const cacheDir = `${process.env.HOME}/Library/Caches/ms-playwright`;
    if (!existsSync(cacheDir)) return null;
    // Find latest chromium-* dir
    const dirs = execSync(`ls -1d "${cacheDir}"/chromium-* 2>/dev/null | sort -V | tail -1`, { encoding: "utf-8" }).trim();
    if (!dirs) return null;
    const candidate = `${dirs}/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
    return existsSync(candidate) ? candidate : null;
  } catch {
    return null;
  }
}

/**
 * Connect to existing Chrome or launch a new one with debug port.
 * NEVER kills Chrome. Returns the CDP endpoint URL.
 *
 * Possible outcomes:
 * - Chrome with debug port already running → return endpoint (fast path)
 * - No Chrome running → launch with debug profile → return endpoint
 * - Non-debug Chrome running → throw error with instructions for user
 */
export function connectOrLaunchChrome(debugProfileDir: string): string {
  const endpoint = `http://127.0.0.1:${DEBUG_PORT}`;

  // Fast path: debug Chrome already running
  try {
    execSync(`curl -sf ${endpoint}/json/version`, { timeout: 3000 });
    console.log("♻️  Chrome debug instance already running on port 9222");
    console.log(`  ✓ CDP endpoint: ${endpoint}\n`);
    return endpoint;
  } catch {
    // Not running on 9222 — continue
  }

  // Check if ANY Chrome is running (would block port 9222)
  let chromeRunning = false;
  try {
    execSync("pgrep -f 'Google Chrome'", { encoding: "utf-8" });
    chromeRunning = true;
  } catch {
    // No Chrome running at all — we can launch freely
  }

  if (chromeRunning) {
    // Chrome is running but NOT on debug port. macOS routes second Google Chrome
    // instance to existing master process — we'd lose control over the debug profile.
    // 2026-04-30: Fallback to Playwright's bundled "Chrome for Testing" — it's a
    // separate macOS app bundle so it doesn't share the master process with daily Chrome.
    const cft = findPlaywrightChromium();
    if (cft) {
      console.log("⚠️  Daily Chrome is running. Falling back to Playwright's Chrome for Testing");
      console.log(`   (independent binary, no conflict): ${cft}\n`);
      ensureDebugProfile(debugProfileDir);
      return launchChromeWithDebugging(debugProfileDir, cft);
    }
    // DO NOT KILL daily Chrome. Ask the user.
    throw new Error(
      "Chrome is running without debug port (9222), and Playwright's Chrome for Testing\n" +
      "was not found. Either close Chrome manually, or install Playwright's Chromium:\n" +
      "  npx playwright install chromium"
    );
  }

  // No Chrome running — safe to launch using daily Chrome
  ensureDebugProfile(debugProfileDir);
  return launchChromeWithDebugging(debugProfileDir);
}

/**
 * Ensure debug profile directory exists with login-critical files.
 * Does NOT touch running Chrome.
 */
function ensureDebugProfile(debugProfileDir: string): void {
  const defaultDir = join(debugProfileDir, "Default");
  const realDefault = join(REAL_CHROME_DIR, "Default");
  const isFirstTime = !existsSync(defaultDir);

  if (isFirstTime) {
    console.log("📁 Creating debug profile (first time — may take a minute)...");
    execSync(`mkdir -p "${debugProfileDir}"`);
    if (existsSync(realDefault)) {
      try {
        execSync(`rsync -a --exclude='Service Worker' --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' "${realDefault}/" "${defaultDir}/"`, { timeout: 180000 });
      } catch {
        cpSync(realDefault, defaultDir, { recursive: true });
      }
    }
    for (const file of ["Local State", "First Run"]) {
      const src = join(REAL_CHROME_DIR, file);
      const dst = join(debugProfileDir, file);
      if (existsSync(src)) {
        try { execSync(`cp "${src}" "${dst}"`); } catch {}
      }
    }
    console.log("  ✓ Debug profile created\n");
  } else {
    // Only re-sync if debug profile cookies are OLDER than real profile cookies.
    const debugCookies = join(defaultDir, "Cookies");
    const realCookies = join(realDefault, "Cookies");
    if (existsSync(debugCookies) && existsSync(realCookies)) {
      const debugMtime = statSync(debugCookies).mtimeMs;
      const realMtime = statSync(realCookies).mtimeMs;
      if (debugMtime > realMtime) {
        console.log("📁 Debug profile cookies are newer — skipping sync\n");
        return;
      }
    }

    // Sync login files from main profile (Chrome must NOT be running when we do this)
    console.log("📁 Syncing login state to debug profile...");
    const loginFiles = ["Cookies", "Cookies-journal", "Login Data", "Login Data-journal", "Web Data", "Web Data-journal"];
    let synced = 0;
    for (const file of loginFiles) {
      const src = join(realDefault, file);
      const dst = join(defaultDir, file);
      if (existsSync(src)) {
        try { execSync(`cp "${src}" "${dst}"`); synced++; } catch {}
      }
    }
    const lsSrc = join(REAL_CHROME_DIR, "Local State");
    const lsDst = join(debugProfileDir, "Local State");
    if (existsSync(lsSrc)) {
      try { execSync(`cp "${lsSrc}" "${lsDst}"`); } catch {}
    }
    console.log(`  ✓ Synced ${synced} login files\n`);
  }

  // Clean lock files (safe even when Chrome is not running)
  for (const lf of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) {
    try { rmSync(join(debugProfileDir, lf), { force: true }); } catch {}
    try { rmSync(join(defaultDir, lf), { force: true }); } catch {}
  }
}

/**
 * Launch Chrome with --remote-debugging-port using the debug profile.
 * Only call this when NO Chrome is running.
 */
function launchChromeWithDebugging(debugProfileDir: string, customBin?: string): string {
  const endpoint = `http://127.0.0.1:${DEBUG_PORT}`;
  const binary = customBin || CHROME_BIN;

  console.log(`🚀 Launching Chrome with remote debugging... (${binary.split('/').pop()})`);
  const child = spawn(binary, [
    `--user-data-dir=${debugProfileDir}`,
    `--remote-debugging-port=${DEBUG_PORT}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
    "about:blank",
  ], { detached: true, stdio: "ignore" });
  child.unref();

  // Wait for port (up to 30s)
  for (let i = 0; i < 30; i++) {
    try {
      execSync(`curl -sf ${endpoint}/json/version`, { timeout: 2000 });
      console.log(`  ✓ Chrome launched — CDP endpoint: ${endpoint}\n`);
      return endpoint;
    } catch {
      execSync("sleep 1");
    }
  }

  throw new Error(`Chrome failed to start with debugging port ${DEBUG_PORT}.`);
}

// ── Legacy exports (kept for backward compat, but they are now safe) ──────

/** @deprecated Use connectOrLaunchChrome() instead. This is now a no-op. */
export function ensureChromeNotRunning(): void {
  console.log("⚠️  ensureChromeNotRunning() is deprecated and now a no-op. Chrome will NOT be killed.");
}

/** @deprecated Use connectOrLaunchChrome() instead. */
export function syncProfileToDebug(debugProfileDir: string): void {
  ensureDebugProfile(debugProfileDir);
}

/** @deprecated Use connectOrLaunchChrome() instead. */
export { launchChromeWithDebugging };
