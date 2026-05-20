/**
 * Notification helpers for Gemini DR completion / timeout.
 *
 * macOS: spawns `terminal-notifier` (silent if not installed).
 * Telegram: opt-in via `DR_NOTIFY_TG=1` env — spawns `tgctl.sh send --topic pdt-alerts`.
 *           Looks for tgctl.sh in `$PDT_ROOT/scripts/` or current working dir.
 *
 * Never throws — notification failures must not break the main flow.
 */

import { spawn } from "child_process";
import { existsSync } from "fs";
import { resolve, basename } from "path";

const TG_ENABLED = process.env.DR_NOTIFY_TG === "1";

function findTgctl(): string | null {
  const candidates = [
    process.env.PDT_ROOT && resolve(process.env.PDT_ROOT, "scripts/tgctl.sh"),
    resolve(process.cwd(), "scripts/tgctl.sh"),
    resolve(process.env.HOME || "", "Workspace/Personal-Digital-Twin/scripts/tgctl.sh"),
  ].filter((p): p is string => Boolean(p));
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  return null;
}

function osascriptFallback(title: string, message: string): void {
  const escapeAS = (s: string) => s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  const script = `display notification "${escapeAS(message)}" with title "${escapeAS(title)}"`;
  const child = spawn("osascript", ["-e", script], { detached: true, stdio: "ignore" });
  child.on("error", () => { /* osascript should always exist on macOS, but stay silent */ });
  child.unref();
}

function macNotify(title: string, message: string, openPath?: string): void {
  if (process.platform !== "darwin") return;
  const args = ["-title", title, "-message", message];
  if (openPath) args.push("-open", openPath);
  try {
    const child = spawn("terminal-notifier", args, { detached: true, stdio: "ignore" });
    child.on("error", () => {
      // terminal-notifier not installed → fall back to osascript
      osascriptFallback(title, message);
    });
    child.unref();
  } catch {
    osascriptFallback(title, message);
  }
}

function tgPush(message: string): void {
  if (!TG_ENABLED) return;
  const tgctl = findTgctl();
  if (!tgctl) {
    console.error("  ⚠ DR_NOTIFY_TG=1 set but tgctl.sh not found");
    return;
  }
  try {
    const child = spawn(tgctl, ["send", "--topic", "pdt-alerts", message], {
      detached: true,
      stdio: "ignore",
    });
    child.on("error", (e) => {
      console.error("  ⚠ tgctl.sh push failed:", String(e).slice(0, 100));
    });
    child.unref();
  } catch (e) {
    console.error("  ⚠ tgctl.sh push failed:", String(e).slice(0, 100));
  }
}

/**
 * Notify on single research completion.
 * @param file       prompt filename (e.g. "Q3.md")
 * @param url        Gemini share URL
 * @param reportPath path to saved markdown (or empty if save skipped)
 * @param elapsedSec seconds since wait started
 */
export function notifyDone(file: string, url: string, reportPath: string, elapsedSec: number): void {
  const min = Math.round(elapsedSec / 60);
  const minStr = min > 0 ? `${min}m` : `${elapsedSec}s`;
  macNotify(
    `✅ DR Done: ${file}`,
    `Completed in ${minStr}. Click to open report.`,
    reportPath || undefined,
  );
  // TG message: send only basename to avoid leaking absolute paths/usernames if forwarded.
  const reportName = reportPath ? basename(reportPath) : "";
  tgPush(`✅ DR completed: ${file} (${minStr})\n${url}\n${reportName ? `Saved: ${reportName}` : "(extract failed)"}`);
}

/**
 * Notify on timeout (some researches still running).
 * @param stillRunning array of {file, url} still pending
 * @param maxWaitMin   the timeout threshold in minutes
 */
export function notifyTimeout(stillRunning: Array<{ file: string; url: string }>, maxWaitMin: number): void {
  const summary = stillRunning.map(r => `  - ${r.file}: ${r.url}`).join("\n");
  macNotify(
    `⚠️ DR Timeout (${maxWaitMin}min)`,
    `${stillRunning.length} still running. Check terminal for URLs.`,
  );
  tgPush(`⚠️ DR timeout after ${maxWaitMin}min — ${stillRunning.length} still running:\n${summary}\n\nExtract manually with gemini-dr-extract.ts <url>`);
}
