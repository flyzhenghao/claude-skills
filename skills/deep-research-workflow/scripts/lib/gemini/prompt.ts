/**
 * Gemini Deep Research — prompt file parsing helpers.
 */

import { readFileSync } from "fs";
import { basename, resolve } from "path";

/** Strip YAML frontmatter and return the body text. */
export function extractPromptBody(filePath: string): string {
  const content = readFileSync(resolve(filePath), "utf-8");
  const lines = content.split("\n");
  let fmCount = 0, fmEnd = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      fmCount++;
      if (fmCount === 2) { fmEnd = i + 1; break; }
    }
  }
  return lines.slice(fmEnd).join("\n").trim();
}

/** Extract the first `# Heading` as a title, falling back to the filename. */
export function getPromptTitle(filePath: string): string {
  const content = readFileSync(resolve(filePath), "utf-8");
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1] : basename(filePath, ".md");
}
