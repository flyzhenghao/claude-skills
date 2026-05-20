# Setup, Configuration & Cost Reference

> Read this when setting up the workflow for the first time or checking cost/config details.

## Prerequisites

1. **Node.js 18+**: Required for all TS scripts
2. **GEMINI_API_KEY**: Google AI API key for API mode (Mode E)
3. **Dependencies**: `cd scripts && npm install` (installs `@google/genai` + `playwright`)
4. **Chrome mode only**: Playwright chromium (`npx playwright install chromium`) + Google login in debug profile

## tasks.json Configuration

```json
{
  "research_config": {
    "total_markets": 6,
    "execution_mode": "concurrent",
    "output_dir": "deep-research-results"
  },
  "known_context": {
    "existing_knowledge": ["至少 1 条已知信息"],
    "constraints": [],
    "anti_patterns": []
  },
  "markets": [
    {
      "id": "market_1",
      "name": "市场名称",
      "research_prompt": "详细的研究提示词..."
    }
  ]
}
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `total_markets` | Number of research tasks | - |
| `execution_mode` | `concurrent` or `sequential` | concurrent |
| `output_dir` | Output directory | `deep-research-results` |

Use the template: `cp templates/tasks-template.json tasks.json`

## Cost Estimates (Gemini API)

| Tasks | Est. Tokens | Est. Cost |
|-------|-------------|-----------|
| 3 | 150K | ~$0.5 |
| 6 | 300K | ~$1 |
| 10 | 500K | ~$2 |

## Deprecated Modes (historical, do not use)

- **Mode B (Interactions API, old version)**: Disabled — quality not up to standard
- **Mode C (generateContent)**: Disabled — no multi-turn search, low quality

Current modes: Mode E (API, default) and Mode D (Chrome, fallback). See SKILL.md Phase 2.

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `login-once.ts` | One-time Google auth helper for Chrome debug profile |
| `extract-share.ts` | Batch extract reports from Gemini share URLs |
