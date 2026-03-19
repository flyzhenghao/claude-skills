/**
 * Gemini Deep Research — Chrome profile management.
 *
 * Copies the real Chrome profile to a debug directory so Playwright can
 * reuse the Google login session. On macOS the cookie encryption key
 * ("Chrome Safe Storage" in Keychain) is tied to the application binary,
 * NOT the user-data-dir path, so copied profiles can decrypt cookies.
 */

import { existsSync, rmSync, cpSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";

const REAL_CHROME_DIR = `${process.env.HOME}/Library/Application Support/Google/Chrome`;

/** Ensure Chrome is not running (Playwright needs exclusive profile access). */
export function ensureChromeNotRunning(): void {
  try {
    const result = execSync("pgrep -f 'Google Chrome'", { encoding: "utf-8" }).trim();
    if (result) {
      console.log("⚠️  Chrome is running. Closing it gracefully...");
      try {
        execSync(`osascript -e 'tell application "Google Chrome" to quit'`, { timeout: 10000 });
      } catch {
        // osascript may fail if Chrome is unresponsive
      }
      // Wait for Chrome to close
      let attempts = 0;
      while (attempts < 15) {
        try {
          execSync("pgrep -f 'Google Chrome'", { encoding: "utf-8" });
          // Still running
          execSync("sleep 1");
          attempts++;
        } catch {
          // pgrep returns non-zero = Chrome is gone
          break;
        }
      }
      if (attempts >= 15) {
        console.log("  → Force killing Chrome...");
        try { execSync("pkill -f 'Google Chrome'"); } catch {}
        execSync("sleep 2");
      }
      console.log("  ✓ Chrome closed\n");
    }
  } catch {
    // pgrep returns non-zero when no process found — Chrome not running, good
  }
}

/**
 * Sync real Chrome profile to debug profile directory.
 * Copies essential dirs/files, handles both files and directories correctly.
 * Cleans lock files that would block Playwright.
 *
 * First-time use: Google may require one-time re-login (device fingerprint change).
 * After that, the debug profile persists sessions across runs.
 */
export function syncProfileToDebug(debugProfileDir: string): void {
  const isFirstTime = !existsSync(debugProfileDir) ||
    !existsSync(join(debugProfileDir, "Default"));

  if (isFirstTime) {
    // First time: copy essential data from real Chrome profile
    console.log("📁 Creating debug profile (first time — this may take a minute)...");
    execSync(`mkdir -p "${debugProfileDir}"`);

    // Copy Default profile directory
    const src = join(REAL_CHROME_DIR, "Default");
    const dst = join(debugProfileDir, "Default");
    if (existsSync(src)) {
      try {
        execSync(`rsync -a "${src}/" "${dst}/"`, { timeout: 180000 });
      } catch {
        cpSync(src, dst, { recursive: true });
      }
    }

    // Copy individual files
    for (const file of ["Local State", "First Run"]) {
      const fileSrc = join(REAL_CHROME_DIR, file);
      const fileDst = join(debugProfileDir, file);
      if (existsSync(fileSrc)) {
        try { execSync(`cp "${fileSrc}" "${fileDst}"`); } catch {}
      }
    }

    console.log("  ✓ Debug profile created from real Chrome data");
    console.log("  ⚠ First run: you may need to log into Google once\n");
  } else {
    // Subsequent runs: do NOT overwrite — debug profile has its own login state
    console.log("📁 Using existing debug profile (login state preserved)");
  }

  // Always clean lock files that block Playwright
  const lockFiles = ["SingletonLock", "SingletonSocket", "SingletonCookie"];
  for (const lf of lockFiles) {
    try { rmSync(join(debugProfileDir, lf), { force: true }); } catch {}
    try { rmSync(join(debugProfileDir, "Default", lf), { force: true }); } catch {}
  }
  console.log("  ✓ Lock files cleaned\n");
}
