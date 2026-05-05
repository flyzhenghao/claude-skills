# Deep Research Workflow

> **v7.5** — 5-Tier architecture (T0/T1/T2/T3/T4) × Quality Foundation Layer.
> Semi-automated research pipeline: Claude Code → Gemini Deep Research (200+ sources) → Opus synthesis.

## What's New in v7.5

- **5 Tier 任务难度纵向分层**：T0 Spot (1-2 min) / T1 Light (5-10 min) / T2 Standard (15-30 min, default) / T3 Deep (45-90 min) / T4 Strategic (2-4h)
- **Quality Foundation Layer 横向能力共享**：anti-patterns 词典 + 域名分级 + lessons-learned 跨项目教训库 + token 预算追踪 + format contract
- **新增 `scripts/validate-sources.ts`**：自动 URL 抽查 + 域名 A/B/C 分级 + 重复来源检测
- **4 个 Tier 模板**：`templates/tasks-template-t1/t2/t3/t4.json` 各按 Tier 配置 phases / token 预算 / 强制字段
- **Phase 0 决策树**：5 题机械判断 Tier，避免凭直觉选档（详见 `references/tier-decision-tree.md`）

完整双轴架构 + Phase 流程见 [SKILL.md](./SKILL.md)。

## Quick Start

```bash
# 1. Setup
bash setup.sh

# 2. Choose Tier and copy template (T2 Standard is default)
cp templates/tasks-template-t2.json tasks.json
# Or T1 light / T3 deep / T4 strategic
# Edit tasks.json with your research questions + known_context

# 3. Create prompt files (one per research topic)
# Each file = one Gemini Deep Research session

# 4. Run (submits, polls, extracts automatically)
npm run research -- prompt-1.md prompt-2.md prompt-3.md

# 5. Validate sources after Phase 2 completion
npm run validate -- dr-raw/*.md --anti-patterns

# 6. Manual status check / extract (if needed)
npm run check -- https://gemini.google.com/app/YOUR_SESSION_ID
npm run extract -- https://gemini.google.com/app/YOUR_SESSION_ID
```

Reports are saved to `./research-results/YYYY-MM-DD-<slug>.md`

## Prerequisites

- macOS (uses Chrome profile copy from `~/Library/Application Support/Google/Chrome`)
- Google Chrome installed
- Google account with Gemini subscription (Pro or above)
- Node.js 18+

## Quality Foundation Layer (Q1-Q7)

| Q | Capability | Implementation |
|---|------------|----------------|
| Q1 | Anti-Patterns Dict | `references/anti-patterns-dict.md` + `scripts/lib/quality/anti-patterns.ts` |
| Q2 | Source Validation | `scripts/validate-sources.ts` + `scripts/lib/quality/source-tier.ts` |
| Q3 | Lessons-Learned | `lessons-learned.md` (cross-project shared, anonymized) |
| Q4 | Format Contract | `dr-config.json` fields (T1+ enforced) |
| Q5 | Token Budget Tracker | `scripts/lib/quality/token-budget.ts` |
| Q6 | Midpoint Check | (P5, planned) |
| Q7 | Adversarial Loop | T3+ Phase 2.6 second pass |

## Full Documentation

See [SKILL.md](./SKILL.md) for:
- Complete dual-axis architecture (5 Tier × 7 Q-capability matrix)
- Phase 0 decision tree (5 yes/no questions)
- Phase details by Tier (Phase 0/0.5/1/1.5/2/2.4/2.5/2.6/2.7/3/4/4.0/4.5/4.6)
- Quality gates (pre-submission + pre-synthesis challenges + source validation)
- Token balance strategy (auto-downgrade triggers + model assignment matrix)
- Compaction recovery checklist
- Best practices

## How It Works

1. Chrome profile is copied to `~/.chrome-debug-profile` (preserves Google login)
2. Playwright launches Chrome with the debug profile
3. Script automates: Tools → Deep Research → insert prompt → submit
4. Polls every 30s until each research completes (configurable timeout)
5. Extracts final report and saves with YAML frontmatter
6. Validates sources (URL liveness + domain Tier + duplicate detection)
7. Synthesizes via Opus (single-pass for T2/T3, multi-pass for T4)

Max 3 concurrent researches (Gemini hard limit) — extras are queued automatically.

## License

MIT
