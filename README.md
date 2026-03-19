# Claude Skills by flyzhenghao

A collection of Claude Code skills for skill ecosystem monitoring and analysis.

## Available Skills

### [critic](skills/critic/)

Quality control skill — code review, challenge/proof-by-contradiction, retrospective, system health, and codebase-wide sweep. The challenge mode uses a curated pattern library (15 known design blind spots) with anti-sycophancy safeguards and confidence anchoring.

**Install:** Copy `skills/critic/` to `~/.claude/skills/critic/`

**Trigger phrases:**
- `/critic review` — code review
- `/critic challenge` — proof-by-contradiction with pattern memory
- `/critic retro` — retrospective with root cause analysis
- `/critic sweep "<pattern>"` — find all instances of a known bug class

---

### [deep-research-workflow](skills/deep-research-workflow/)

Semi-automated deep research pipeline: Claude Code problem decomposition → Gemini Deep Research (200+ sources per query, concurrent) → Opus synthesis. Includes adaptive quality gates, Chrome profile automation, and auto-polling.

**Install:**
```bash
git clone https://github.com/flyzhenghao/claude-skills.git
cd claude-skills/skills/deep-research-workflow
bash setup.sh
```

**Prerequisites:** Google Chrome + Google Pro subscription (for Gemini Deep Research)

**Trigger phrases:**
- "deep research" / "深度研究"
- "market research" / "市场调研"
- "batch research" / "批量研究"

---

### [skill-trending-monitor-cskill](skills/skill-trending-monitor-cskill/)

Claude Code skill ecosystem monitoring with dual-source architecture. Fetches from claude-plugins.dev API (53,759+ skills, hourly updates) and skill-manager local DB (41,502 skills, offline fallback with Chinese descriptions). Calculates GitHub star growth rates, discovers new skills, finds similar alternatives using TF-IDF similarity, and generates weekly reports with security evaluations.

**Install:**
```bash
npx skills-installer install @flyzhenghao/claude-skills/skill-trending-monitor-cskill
```

**Trigger phrases:**
- "What are the trending Claude skills this week?"
- "Discover new high-quality skills"
- "Which of my skills should I replace?"
- "Generate weekly skill report"
- "Security evaluation of my skills"

## Installation

```bash
npx skills-installer install @flyzhenghao/claude-skills/<skill-name>
```

## License

MIT
