---
name: skill-trending-monitor-cskill
description: "This skill should be used when the user asks about \"trending claude skills\", \"what skills are popular\", \"skill growth rate\", \"discover new skills\", \"find better alternatives to my skills\", \"replace outdated skills\", \"skill security evaluation\", \"weekly skill report\", or \"monitor skill ecosystem\". Dual-source architecture (53,759+ API skills + 41,502 local DB) with Chinese description enrichment. Calculates GitHub star growth rates, finds similar alternatives using TF-IDF similarity, and generates weekly reports with security evaluations."
version: 1.0.0
---

# Skill Trending Monitor

Comprehensive skill ecosystem monitoring and recommendation system for Claude Code. Dual-source architecture fetches from claude-plugins.dev API (53,759+ skills, hourly updates) and skill-manager local DB (41,502 skills, offline fallback). Surfaces trending skills, identifies replacement candidates, and generates weekly ecosystem health reports.

## When to Use This Skill

**Activate when user asks about:**

- Trending Claude Skills or skill popularity
- Discovering new high-quality skills
- Comparing installed skills with alternatives
- Finding better or similar functionality skills
- Security evaluation of skills
- Weekly/periodic skill monitoring reports
- Skill recommendations or alternative suggestions

**Do NOT activate for:**

- Specific skill usage docs (use the skill's own docs)
- Creating new skills (use agent-skill-creator)
- Basic CLI installation commands
- Editing existing skill code

---

## Core Capabilities

### 6 Available Analyses

| Analysis | Purpose | Key Output |
|----------|---------|------------|
| **New Skills Discovery** | Find high-quality skills not installed | Top 20 by stars, filtered (stars≥50, updated<6mo) |
| **Growth Rate Analysis** | Calculate week-over-week star growth | Top 10 trending (≥5% WoW growth) |
| **Similarity Detection** | Find functionally similar skills | TF-IDF + cosine similarity ≥0.75 |
| **Replacement Recommendations** | Identify better alternatives | Confidence score ≥0.70 |
| **Security Evaluation** | Assess security risks | Score 0-100, threshold 70 |
| **Comprehensive Report** | Weekly ecosystem health report | Combined analysis to `meta/reports/` |

### Data Architecture (Dual-Source)

**Tier 0: claude-plugins.dev API (Primary)**
- Endpoint: `api.claude-plugins.dev/api/skills/search`
- 53,759+ skills, hourly updates, real-time data
- Fields: name, description, stars, installs, namespace, sourceUrl

**Tier 1: skill-manager Local DB (Fallback)**
- Location: `~/.claude/skills/skill-manager/data/all_skills_with_cn.json`
- 41,502 skills, offline access, includes `description_cn` (Chinese translations)

**Tier 2: GitHub API**
- Star history for growth calculations
- 5,000 requests/hour (authenticated)

**Merge Strategy:** API takes precedence → local DB fills gaps + enriches with `description_cn` → dedup by (name, author)

### Cache System

| Cache | TTL | Purpose |
|-------|-----|---------|
| API Response | 1 hour | Match API update frequency |
| Skill Metadata | 30 days | Avoid re-parsing database |
| Security Evaluations | 7 days | Cache security scores |

---

## Quick Reference

### Main Scripts

```bash
# Comprehensive weekly report
python3 scripts/analyze_comprehensive.py

# Individual analyses
python3 scripts/analyze_new_skills.py --limit 20
python3 scripts/analyze_growth_rates.py --threshold 5.0
python3 scripts/analyze_similarity.py --skill <name>
python3 scripts/analyze_replacements.py --confidence-threshold 0.70
```

### Key Algorithms

**TF-IDF Similarity:**
```
similarity = cosine(vec_A, vec_B)
threshold = 0.75 (high similarity)
```

**Confidence Score:**
```
confidence = star_ratio×0.4 + recency×0.3 + similarity×0.3
recommend if >= 0.70
```

**WoW Growth Rate:**
```
growth = (stars_this_week - stars_last_week) / stars_last_week × 100
trending if >= 5%
```

---

## Usage Examples

### Example 1: Trending Skills

```
User: "What are the trending claude skills this week?"

Response:
🔥 Trending Skills This Week (WoW >= 5%):

1. **advanced-code-reviewer** (2,300 stars, +18.5% WoW)
   - Security: 🛡️ Excellent (92)

2. **api-automation-suite** (1,850 stars, +12.3% WoW)
   - Security: ✅ Good (78)
```

### Example 2: Find Replacements

```
User: "Which of my skills should I replace?"

Response:
🔄 Replacement Recommendations:

### Replace `basic-formatter` (200 stars, 8mo old)

**Best Alternative: `advanced-formatter-pro`**
- Confidence: 0.85 (strongly recommended)
- Stars: 1,200 (6x more)
- Security: 🛡️ Excellent (94)
```

### Example 3: Weekly Report

```
User: "Generate weekly skill report"

Response:
✅ Weekly Report Generated!

📄 Saved to: meta/reports/2026-02-03-skill-trending-report.md

📊 Summary:
- Total Skills: 53,759+ (API) + 41,502 (local)
- Installed: 47
- Trending (WoW >= 5%): 8
- Replacement Candidates: 3
```

---

## Additional Resources

### Reference Files

For detailed documentation, consult:
- **`references/analysis-methodologies.md`** — Detailed analysis workflows and scoring logic
- **`references/similarity-algorithms.md`** — TF-IDF and cosine similarity implementation details
- **`references/github-api-guide.md`** — GitHub API usage and rate limit management
- **`references/skill-manager-api-guide.md`** — skill-manager database access patterns
- **`references/troubleshooting.md`** — Common issues and error handling

### Setup & Automation

See **`INSTALLATION.md`** for:
- Prerequisites (skill-manager, Python dependencies)
- GitHub token configuration
- macOS launchd / Linux cron scheduling for weekly reports

---

**Version:** 1.1.0 | **Created:** 2026-02-03 | **Updated:** 2026-02-21 | **License:** MIT
