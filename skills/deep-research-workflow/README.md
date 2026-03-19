# Deep Research Workflow

Semi-automated research pipeline: Claude Code → Gemini Deep Research (200+ sources) → Opus synthesis.

## Quick Start

```bash
# 1. Setup
bash setup.sh

# 2. Create task config
cp templates/tasks-template.json tasks.json
# Edit tasks.json with your research questions

# 3. Create prompt files (one per research topic)
# Each file = one Gemini Deep Research session

# 4. Run (submits, polls, extracts automatically)
npm run research -- prompt-1.md prompt-2.md prompt-3.md

# 5. Check status manually (if needed)
npm run check -- https://gemini.google.com/app/YOUR_SESSION_ID

# 6. Extract manually (if needed)
npm run extract -- https://gemini.google.com/app/YOUR_SESSION_ID
```

Reports are saved to `./research-results/YYYY-MM-DD-<slug>.md`

## Prerequisites

- macOS (uses Chrome profile copy from `~/Library/Application Support/Google/Chrome`)
- Google Chrome installed
- Google account with Gemini subscription (Pro or above)
- Node.js 18+

## Full Documentation

See [SKILL.md](./SKILL.md) for:
- Complete workflow (Phase 1–4)
- Quality gates (pre-submission + pre-synthesis challenges)
- Prompt writing guide
- Troubleshooting
- Best practices

## How It Works

1. Chrome profile is copied to `~/.chrome-debug-profile` (preserves Google login)
2. Playwright launches Chrome with the debug profile
3. Script automates: Tools → Deep Research → insert prompt → submit
4. Polls every 30s until each research completes (max 20 min)
5. Extracts final report and saves with YAML frontmatter

Max 3 concurrent researches (Gemini hard limit) — extras are queued automatically.
