#!/usr/bin/env npx tsx
/**
 * Gemini Deep Research — API Mode (Interactions API)
 *
 * Uses @google/genai SDK to submit Deep Research prompts via the
 * Interactions API (agent: deep-research-pro-preview-12-2025).
 *
 * Usage:
 *   npx tsx scripts/gemini-dr-api.ts <prompt-file-1> [prompt-file-2] ...
 *
 * Environment:
 *   GEMINI_API_KEY — Google AI API key (required)
 *
 * Features:
 *   - Accepts multiple prompt files, submits sequentially
 *   - Background mode: polls every 15s, timeout 15 min per interaction
 *   - Saves reports to CWD/deep-research-results/ (or ai-docs/research/deep-research-results/ in PDT)
 *   - 429/quota errors → clear message suggesting Chrome fallback
 */

import { GoogleGenAI } from "@google/genai";
import { existsSync, readFileSync, writeFileSync, mkdirSync, rmSync } from "fs";
import { basename, resolve, dirname } from "path";
import { execSync } from "child_process";
import { extractPromptBody, getPromptTitle } from "./lib/gemini/prompt.js";

const AGENT = "deep-research-pro-preview-12-2025";
const POLL_INTERVAL_MS = 15_000;
const MAX_WAIT_MS = 15 * 60 * 1000; // 15 min

const CWD = process.cwd();
const IS_PDT =
  existsSync(resolve(CWD, "scripts/append-research-chain.sh")) &&
  existsSync(resolve(CWD, "package.json")) &&
  (() => {
    try {
      return JSON.parse(readFileSync(resolve(CWD, "package.json"), "utf-8")).name === "personal-digital-twin";
    } catch {
      return false;
    }
  })();
const DR_RESULTS_DIR = IS_PDT
  ? resolve(CWD, "ai-docs/research/deep-research-results")
  : resolve(CWD, "deep-research-results");


function slugify(text: string): string {
  return text
    .slice(0, 60)
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-")
    .replace(/^-|-$/g, "");
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

interface SavedReport {
  path: string;
  title: string;
  chars: number;
  citations: number;
}

function saveReport(
  reportText: string,
  citations: Array<{ title?: string; url?: string }>,
  interactionId: string,
  promptFile: string,
): SavedReport {
  const now = new Date().toISOString().split("T")[0];

  // Extract title from first heading or first line
  const headingMatch = reportText.match(/^#\s+(.+)$/m);
  const firstLine = reportText.split("\n").find((l) => l.trim().length > 0)?.trim();
  const title =
    headingMatch?.[1]?.trim() ??
    (firstLine && firstLine.length >= 5 && firstLine.length <= 200 ? firstLine : basename(promptFile, ".md"));

  const slug = slugify(title);
  const savePath = resolve(DR_RESULTS_DIR, `${now}-${slug}.md`);

  // Build citation appendix
  let citationBlock = "";
  if (citations.length > 0) {
    citationBlock = "\n\n---\n\n## Sources\n\n";
    for (let i = 0; i < citations.length; i++) {
      const c = citations[i];
      const label = c.title || c.url || `Source ${i + 1}`;
      citationBlock += c.url ? `${i + 1}. [${label}](${c.url})\n` : `${i + 1}. ${label}\n`;
    }
  }

  const markdown = `---
source: gemini-deep-research-api
interaction_id: ${interactionId}
extracted: ${now}
chars: ${reportText.length}
citations: ${citations.length}
---

${reportText}${citationBlock}
`;

  mkdirSync(dirname(savePath), { recursive: true });
  writeFileSync(savePath, markdown, "utf-8");
  console.log(`  📄 Saved report (${reportText.length} chars, ${citations.length} citations) → ${savePath}`);

  // Append research chain entry (PDT only)
  const chainScript = resolve(CWD, "scripts/append-research-chain.sh");
  if (existsSync(chainScript)) {
    try {
      const relPath = savePath.startsWith(CWD) ? savePath.slice(CWD.length + 1) : savePath;
      const pathSlug = basename(savePath, ".md")
        .slice(0, 60)
        .toLowerCase()
        .replace(/[^a-z0-9-]+/g, "-");
      const chainId = `research-${now}-${pathSlug}`;
      const chainJson = JSON.stringify({
        id: chainId,
        name: title.slice(0, 80),
        name_en: title.slice(0, 80),
        date_start: now,
        date_end: now,
        trigger: "Gemini Deep Research API",
        status: "completed",
        domain: "work",
        tools_used: [{ name: "gemini-dr-api", count: 1, description: "Gemini Interactions API" }],
        reports_generated: [{ path: relPath, description: title.slice(0, 80) }],
        decisions: [],
        deliverables: [{ path: relPath, type: "report", description: title.slice(0, 80) }],
      });
      const tmpChain = resolve(CWD, `.tmp-chain-${Date.now()}.json`);
      writeFileSync(tmpChain, chainJson, "utf-8");
      const workPathMatch = relPath.match(/^ai-docs\/work\/([^/]+)\//);
      const projectArg = workPathMatch?.[1] ? ` --project "${workPathMatch[1]}"` : "";
      execSync(`bash "${chainScript}" --input "${tmpChain}"${projectArg}`, { cwd: CWD, stdio: "pipe" });
      try {
        rmSync(tmpChain);
      } catch {}
      console.log("  🔗 Research chain entry appended");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ⚠️  Research chain append skipped: ${msg}`);
    }
  }

  return { path: savePath, title, chars: reportText.length, citations: citations.length };
}

async function submitAndPoll(
  client: GoogleGenAI,
  promptText: string,
  promptFile: string,
  index: number,
  total: number,
): Promise<SavedReport | null> {
  const title = getPromptTitle(promptFile);
  console.log(`\n━━━ [${index}/${total}] ${title} ━━━`);
  console.log(`  ${basename(promptFile)} (${promptText.length} chars)\n`);

  // Submit
  console.log("  → Submitting via Interactions API...");
  let interaction;
  try {
    interaction = await client.interactions.create({
      agent: AGENT,
      input: promptText,
      background: true,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("429") || msg.includes("quota") || msg.includes("RESOURCE_EXHAUSTED")) {
      console.error(`  ❌ API 配额不足 (429): ${msg}`);
      console.error("  💡 请用 Chrome 模式降级:");
      console.error(
        `     npx tsx ~/.claude/skills/deep-research-workflow/scripts/gemini-deep-research.ts --chrome ${promptFile}`,
      );
      return null;
    }
    console.error(`  ❌ API error: ${msg}`);
    return null;
  }

  const interactionId = interaction.id;
  console.log(`  ✓ Submitted (interaction: ${interactionId})`);
  console.log(`  ⏳ Polling every ${POLL_INTERVAL_MS / 1000}s (timeout ${MAX_WAIT_MS / 60000}min)...`);

  // Poll
  const startTime = Date.now();
  while (Date.now() - startTime < MAX_WAIT_MS) {
    await sleep(POLL_INTERVAL_MS);
    const elapsed = Math.round((Date.now() - startTime) / 1000);

    let result;
    try {
      result = await client.interactions.get(interactionId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ⚠️  Poll error (${elapsed}s): ${msg}`);
      continue;
    }

    const status = result.status;
    if (status === "completed") {
      console.log(`  ✅ Completed (${elapsed}s)`);

      // Extract report text and citations from outputs
      let reportText = "";
      const citations: Array<{ title?: string; url?: string }> = [];

      if (result.outputs && result.outputs.length > 0) {
        for (const output of result.outputs) {
          if (output.type === "text") {
            const textOutput = output as { type: "text"; text: string; annotations?: Array<{ type: string; title?: string; url?: string }> };
            reportText += textOutput.text;
            if (textOutput.annotations) {
              for (const ann of textOutput.annotations) {
                if (ann.type === "url_citation") {
                  citations.push({ title: ann.title, url: (ann as { url?: string }).url });
                }
              }
            }
          }
        }
      }

      if (reportText.length < 500) {
        console.error(`  ⚠️  Report too short (${reportText.length} chars). Raw outputs: ${JSON.stringify(result.outputs)?.slice(0, 200)}`);
        return null;
      }

      return saveReport(reportText, citations, interactionId, promptFile);
    } else if (status === "failed" || status === "cancelled") {
      console.error(`  ❌ Interaction ${status} (${elapsed}s)`);
      return null;
    } else {
      console.log(`  ⏳ ${elapsed}s — status: ${status}`);
    }
  }

  console.error(`  ⚠️  Timeout after ${MAX_WAIT_MS / 60000}min. Interaction ${interactionId} may still be running.`);
  console.error(`  → Check manually: client.interactions.get("${interactionId}")`);
  return null;
}

async function main() {
  const promptFiles = process.argv.slice(2).filter((a) => !a.startsWith("--"));

  if (promptFiles.length === 0) {
    console.log("Usage: npx tsx scripts/gemini-dr-api.ts <prompt-file-1> [prompt-file-2] ...");
    console.log("\nSubmits prompts via Gemini Interactions API → polls → extracts reports.");
    console.log("\nRequires: GEMINI_API_KEY environment variable");
    console.log("\nExample:");
    console.log("  npx tsx scripts/gemini-dr-api.ts research/prompt-1.md research/prompt-2.md");
    process.exit(0);
  }

  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    console.error("❌ GEMINI_API_KEY environment variable is not set.");
    console.error("   Set it via: export GEMINI_API_KEY='your-api-key'");
    process.exit(1);
  }

  // Validate prompt files exist
  for (const f of promptFiles) {
    if (!existsSync(resolve(f))) {
      console.error(`❌ Not found: ${f}`);
      process.exit(1);
    }
  }

  console.log(`🔬 Gemini Deep Research API — Submitting ${promptFiles.length} prompt(s)\n`);
  console.log(`   Agent: ${AGENT}`);
  console.log(`   Output: ${DR_RESULTS_DIR}\n`);

  const client = new GoogleGenAI({ apiKey });

  let ok = 0;
  let fail = 0;
  const savedReports: SavedReport[] = [];

  for (let i = 0; i < promptFiles.length; i++) {
    const f = promptFiles[i];
    const body = extractPromptBody(f);
    const result = await submitAndPoll(client, body, f, i + 1, promptFiles.length);

    if (result) {
      ok++;
      savedReports.push(result);
    } else {
      fail++;
    }
  }

  // Final summary
  console.log(`\n━━━ Final Results ━━━`);
  console.log(`  Submitted: ${promptFiles.length} | Completed: ${ok} | Failed: ${fail}`);
  for (const r of savedReports) {
    console.log(`  📄 ${r.path} (${r.chars} chars, ${r.citations} citations)`);
  }

  // Auto-sync initiatives (PDT only)
  if (savedReports.length > 0 && IS_PDT) {
    try {
      execSync(`python3 "${resolve(CWD, "scripts/generate-initiatives.py")}"`, { cwd: CWD, stdio: "pipe" });
      console.log("🔄 UI data synced (initiatives regenerated)");
    } catch {
      console.log("⚠️  UI sync skipped");
    }
  }

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error("Fatal:", e.message);
  process.exit(1);
});
