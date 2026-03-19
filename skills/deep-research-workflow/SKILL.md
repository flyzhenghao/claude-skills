---
name: deep-research-workflow
description: Semi-automated deep research pipeline — Claude Code decomposition → Gemini Deep Research → Opus synthesis
version: 6.0.0
author: flyzhenghao
created: 2026-02-06
triggers:
  - "deep research"
  - "深度研究"
  - "batch research"
  - "批量研究"
  - "market research"
  - "市场调研"
agents: [researcher, strategist]
---

# Deep Research Workflow

A semi-automated deep research pipeline that combines Claude Code's decomposition capability with Gemini's live web search (200+ sources per query) and Opus's synthesis power.

**Core pipeline:**
```
Claude Code (decompose) → Gemini Deep Research (concurrent) → Opus (synthesize)
```

**Quality:** Gemini Deep Research is NOT a web search — it's a multi-round agentic process that reads 200+ sources, follows citation trails, and produces structured reports. It is substantially higher quality than WebSearch.

---

## Installation

```bash
# Clone the skills repo
git clone https://github.com/flyzhenghao/claude-skills.git
cd claude-skills/skills/deep-research-workflow

# Install dependencies
npm install
npx playwright install chromium

# Or use setup script
bash setup.sh
```

**Prerequisites:**
- Google Chrome installed (the script copies your Chrome profile for login session)
- Google account with Gemini subscription (Pro or above)
- Node.js 18+ with `npx tsx` available

---

## Overview

### How It Works

1. **Phase 1** — You describe a research goal; Claude decomposes it into parallel sub-questions
2. **Phase 1.5** — Quality gate: challenge the research plan before spending time
3. **Phase 2** — Scripts automate Chrome → Gemini Deep Research submission (max 3 concurrent)
4. **Phase 2.5** — Quality gate: challenge raw reports before Opus synthesis
5. **Phase 3** — Opus synthesizes all reports into actionable insights
6. **Phase 4** — Extract action items and write to your project backlog

### Degradation Rules (CRITICAL)

**Execution priority (attempt in order, never skip):**

1. **Mode D (Chrome + Playwright)** — Copy Chrome profile → launch debug Chrome → submit Deep Research → poll → extract
2. **Inform user** — If Mode D fails, explain why and ask if WebSearch fallback is acceptable

**Forbidden:** Never auto-downgrade to WebSearch without attempting Mode D first.
**Reason:** Gemini Deep Research quality vastly exceeds WebSearch. Auto-downgrade loses research depth.

---

## Compaction Recovery Checklist

If your session was compacted, verify current phase before continuing:

| Check | Verification |
|-------|-------------|
| Which phase are you on? | Compare against the workflow below |
| Phase 1.5 challenge done? | Search conversation for challenge output |
| Phase 2.5 challenge done? | Search conversation for raw report challenge |
| Raw reports extracted? | `ls research-results/` |
| Summary report generated? | Check for synthesis document |

**Mnemonic: Challenge before submit, challenge before synthesis — two gates, then report.**

---

## Use Cases

- Market research (multiple segments in parallel)
- Competitive analysis (multiple products/companies)
- Technology evaluation (comparing solutions)
- Industry research (cross-domain information gathering)

---

## Workflow

### Phase 1: Problem Decomposition (Claude Code)

After user describes a research goal, Claude:

1. **Clarifies research objective** — identify the core questions
2. **Vision inventory (anti-omission)** — list related but easily-skipped angles (3–5 max), confirm with user before decomposing
3. **Decomposes into sub-tasks** — parallel, MECE sub-questions
4. **Generates task config** — outputs `tasks.json` in CWD
5. **Mandatory `known_context`** — `existing_knowledge` must not be empty. Write at least one "I already know X." If user says "no prior knowledge", write `["First research in this domain, no prior knowledge"]`.

**Output example:**
```json
{
  "research_config": {
    "total_markets": 3,
    "execution_mode": "concurrent",
    "output_dir": "research-results"
  },
  "known_context": {
    "existing_knowledge": ["Target market is B2B SaaS, not consumer"],
    "constraints": ["Budget under $10K/month"],
    "anti_patterns": []
  },
  "markets": [
    {
      "id": "market_1",
      "name": "AI Agent Development Platforms",
      "research_prompt": "Research the AI Agent development platforms market..."
    }
  ]
}
```

---

### Phase 1.5: Quality Gate — Pre-Submission Challenge

**Default: run for all deep research. Skip only when:**
- User explicitly says "no challenge" / "run directly"
- Pure re-run (same prompts as a previously validated `tasks.json`)

#### Adaptive Challenge System

1. If `/critic challenge` skill is available → use it (full proof-by-contradiction analysis)
2. If not available → run inline challenge directly:

**Inline Challenge — Phase 1.5 (Pre-submission)**

Evaluate the research plan against these criteria:

- Are sub-tasks MECE? Any missing angles?
- Do prompts anchor on `known_context` to avoid redundant research?
- Is decomposition granularity appropriate (too fine / too coarse)?
- Any "research baseline gap" (P8) or "over-decomposition" (P10) risks?

**Output:** Improved `tasks.json`, or "Passed — ready to execute."

---

### Phase 2: Concurrent Execution (Mode D: Chrome + Playwright)

**One command handles full lifecycle:** submit → auto-poll → auto-extract. Max 3 concurrent.

```bash
# From your project directory
npx tsx /path/to/skill/scripts/gemini-deep-research.ts <prompt-file-1> [prompt-file-2] [prompt-file-3]

# Or from within the skill directory
npm run research -- <prompt-file-1> [prompt-file-2]
```

The script automatically:
1. Copies your Chrome profile to `~/.chrome-debug-profile` (preserves Google login)
2. Launches Chrome with the debug profile
3. Submits all prompts (≤3 concurrent, queues the rest)
4. Polls every 30 seconds (20-minute timeout)
5. Extracts each report when complete → saves to `./research-results/`

**Optional: `--no-wait`** — exit after submission (skip auto-poll, extract manually later)

#### Manual Poll / Extract (only needed with `--no-wait` or after timeout)

```bash
# Check status
npm run check -- <url1> [url2]
# Exit code 0 = all complete

# Extract report
npm run extract -- <session-url> [--output <path>]
```

---

### Phase 2.5: Result Challenge — Pre-Synthesis Gate (MANDATORY)

**This gate cannot be skipped. Even after compaction, execute this.**

After extracting raw reports, before Opus synthesis:

#### Adaptive Challenge System

1. If `/critic challenge` is available → use it
2. If not available → run inline challenge:

**Inline Challenge — Phase 2.5 (Pre-synthesis, MANDATORY)**

Evaluate raw reports against:

- Contradictions between reports? (conflicting numbers, recommendations, conclusions)
- "Sounds good but not actionable" recommendations? (vague best practices)
- Are data sources verifiable? (not just "according to industry reports")
- Do technical proposals respect real constraints? (budget, free tier limits, timeline)
- Coverage: does every original research question have an answer?

**Output:** Issue list + fix recommendations. Synthesis must incorporate fixes.

> **No skip condition.** Even under time pressure, run a quick 5-minute version.

---

### Phase 3: Synthesis (Opus)

Provide all extracted reports plus the `summary_for_opus.md` to Opus for synthesis.

**Analysis dimensions:**
1. Cross-topic trends — common patterns and divergences
2. Opportunity identification — highest-potential directions
3. Strategic recommendations — prioritized entry points
4. Risk assessment — barriers and failure modes per topic
5. Action plan — concrete next steps

---

### Phase 4: Research Landing (Best Practice)

**Research complete ≠ research landed. Recommended post-synthesis steps:**

#### 4.1 Extract Action Items

From the synthesis, extract the top 3–5 actionable items. Each should include:

```markdown
### A[N]. [Title]

**Action:** [What to do]
**Implementation:** [How to do it, which files/commands]
**Acceptance criteria:** [Specific, verifiable completion condition]
**Dependencies:** [Other action items this depends on, or "None"]
**Owner:** [Claude Code / User decision / External tool]
**Expected outcome:** [Effect when done]
```

**Decision gate (30 seconds):**
- Do action items have dependency chains? Irreversible operations? Total time >2h?
- **All No** → execute directly; the synthesis doc is your plan
- **Any Yes** → create a separate implementation doc before executing

#### 4.2 Write to Project Backlog (Optional)

Write action items to your project's `backlog.md` with source and acceptance criteria:

```markdown
## From research: [Research topic] (YYYY-MM-DD)
- [ ] [Action 1] — Source: DR report X §Section; Acceptance: [one-line criteria] `#DR-YYYY-MM-DD`
- [ ] [Action 2] — Source: DR report Y §Section; Acceptance: [one-line criteria] `#DR-YYYY-MM-DD`
```

---

## Quick Start

### Step 1: Create task config

```bash
# Copy the template
cp templates/tasks-template.json tasks.json
# Edit tasks.json — fill in your research questions
```

### Step 2: Run research

```bash
# Create prompt files from tasks.json markets
# (Claude will help generate prompt files from tasks.json)

# Submit and wait for completion
npm run research -- prompt-1.md prompt-2.md prompt-3.md
```

### Step 3: Check results

```bash
ls research-results/
# Reports saved as: research-results/YYYY-MM-DD-<slug>.md
```

### Step 4: Synthesize with Opus

Provide the extracted reports to Opus (via claude.ai or API) for synthesis.

---

## Prompt Writing Guide

Structure each research prompt for best results:

```markdown
# Research Task: [Topic]

## Research Goal
[State the core questions to answer]

## Information Requirements
1. Market size and growth forecast (2024-2028)
2. Key players and competitive landscape
3. Pricing models and business models
4. Target customers and use cases
5. Technical trends and innovation direction
6. Entry barriers and risk factors

## Output Requirements
- Use Markdown format
- Include data tables with comparisons
- Cite all data sources
- Provide actionable insights
```

**Key rule:** Always include `known_context` in `tasks.json`. Gemini will use this to skip redundant research on things you already know.

---

## Best Practices

### 1. MECE Decomposition

- Sub-tasks must be mutually exclusive and collectively exhaustive
- Each sub-task should be independently researchable
- Appropriate granularity: not so fine that they overlap, not so coarse they miss angles

### 2. Single-Focus Principle

**Research must pair with implementation in a closed loop.**

| Type | When to use concurrent topics | Closed-loop definition |
|------|-------------------------------|------------------------|
| **Exploration** (next step: write docs) | Multiple angles on the same theme | Document committed |
| **Feature** (next step: write code) | Single feature only | Code committed (passing `tsc --noEmit`) |

For feature research: one feature per round. Research → Implement → Verify → next round.

### 3. Result Validation

- Check data source credibility
- Cross-validate key data points
- Prioritize recent data (2024–2026)

---

## File Structure

```
deep-research-workflow/
├── SKILL.md                    # This file
├── package.json                # Dependencies
├── setup.sh                    # First-time setup
├── README.md                   # Quick reference
├── scripts/
│   ├── gemini-deep-research.ts # Main: submit + poll + extract
│   ├── gemini-dr-check.ts      # Status checker
│   ├── gemini-dr-extract.ts    # Manual extractor
│   └── lib/gemini/
│       ├── browser.ts          # Playwright browser interactions
│       ├── prompt.ts           # Prompt file parsing
│       ├── profile.ts          # Chrome profile management
│       └── monitor.ts          # Completion polling
└── templates/
    └── tasks-template.json     # Task config template
```

---

## Mode Details

### Mode D: Chrome + Playwright (only supported mode)

Playwright copies your Chrome profile to `~/.chrome-debug-profile`, launches it with remote debugging enabled, and automates the Gemini web UI directly.

**Why copy profile?** Chrome v136+ forbids remote debugging on the default `user-data-dir`. Copying to a separate directory allows Playwright to control it while preserving your Google login session (macOS Keychain encryption is tied to the Chrome binary, not the profile path).

**First run:** Google may require one-time re-login due to device fingerprint change. After that, the debug profile retains login state across runs.

| Property | Value |
|----------|-------|
| Quality | ★★★★★ (200+ sources, multi-round search) |
| Cost | Free (consumes Google Pro subscription, not API tokens) |
| Concurrency | Max 3 simultaneous (Gemini hard limit) |
| Scripts | `gemini-deep-research.ts` + `gemini-dr-check.ts` + `gemini-dr-extract.ts` |

**Disabled modes:**
- Mode A (Gemini CLI) — produces standard LLM generation, not real Deep Research
- Mode B (Interactions API) — subpar quality in testing
- Mode C (generateContent) — no multi-round search, poor quality

---

## Troubleshooting

**Chrome not closing:**
```bash
pkill -f "Google Chrome"
# Wait 2 seconds, then re-run
```

**Not logged into Google (debug profile):**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/.chrome-debug-profile" \
  --no-first-run https://accounts.google.com
# Log in, close Chrome, then re-run the script
```

**Research stuck at "running" after 20 minutes:**
```bash
npm run check -- <session-url>
# If completed, extract manually:
npm run extract -- <session-url>
```

**Concurrency limit hit:**
The script handles this automatically — it queues submissions and waits for a slot. If you see "Hit Gemini concurrent research limit", just wait; the script retries.

---

## Changelog

### v6.0.0 (2026-03-19) — Public Release

- Extracted from PDT (Personal Digital Twin) project as standalone skill
- Removed PDT-specific integrations (research-chains, initiatives.json, UI sync)
- Changed output directory to `./research-results/` (relative to CWD)
- Added adaptive challenge system (方案3): detects `/critic challenge` availability, falls back to inline challenge prompt
- Added installation section and `setup.sh`
- Bilingual: English primary, Chinese trigger phrases preserved
- Removed Phase 4.3 (research index) and Phase 4.5 (landing rate tracking) — PDT-specific

### v5.6.0 (2026-03-14)

- Auto-poll + extract: full lifecycle in one command (submit → poll → extract)
- `--no-wait` flag to restore old behavior
- Root cause fix: previously relied on AI memory to invoke check/extract scripts

### v5.3.0 (2026-02-26)

- Chrome v136+ compatibility: copy profile to `~/.chrome-debug-profile`
- Max 3 concurrent researches with automatic queuing
- Three-script chain: submit → check → extract

---

**Author:** haozheng
**Created:** 2026-02-06
**Last Updated:** 2026-03-19
