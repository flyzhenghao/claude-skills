# Workflow Examples

This document demonstrates how users typically interact with this skill through natural language queries.

## Workflow 1: Weekly Skill Discovery

**User Query:** "What are the trending Claude skills this week?"

**Skill Activation:** Triggered by keyword "trending" + "claude skills"

**Processing Flow:**
1. Run Analysis 2 (Fastest Growing Skills)
2. Fetch top 100 skills by stars from skill-manager
3. Query GitHub API for star history (this week vs. last week)
4. Calculate WoW growth rates
5. Filter growth >= 5%
6. Rank by growth rate descending
7. Run Analysis 5 (Security Evaluation) on results
8. Return top 10 with security badges

**Output Example:**
```
🔥 Trending Skills This Week (WoW >= 5%):

1. **advanced-code-reviewer** (2,300 stars)
   - WoW Growth: +18.5% (64 new stars vs. 54 last week)
   - Security: 🛡️ Excellent (Score: 92)
   - Description: Deep code analysis with ML-based suggestions

2. **api-automation-suite** (1,850 stars)
   - WoW Growth: +12.3% (91 new stars vs. 81 last week)
   - Security: ✅ Good (Score: 78)
   - Description: Automate API testing and documentation
```

---

## Workflow 2: Finding New Skills to Install

**User Query:** "Show me high-quality skills I haven't installed yet"

**Skill Activation:** Triggered by "show" + "skills" + implied discovery intent

**Processing Flow:**
1. Run Analysis 1 (New Skills Discovery)
2. Scan `~/.claude/skills/` for installed skills
3. Load skill-manager database (31,767 skills)
4. Filter out installed skills
5. Apply quality filters (stars >= 50, updated < 6mo)
6. Rank by stars descending
7. Run Analysis 5 (Security Evaluation)
8. Return top 20 security-cleared skills

**Output Example:**
```
🆕 New Skills You Haven't Installed (Top 20):

| Skill Name | Stars | Updated | Security | Description |
|------------|-------|---------|----------|-------------|
| pdf-mastery | 850 | 2026-01-20 | 🛡️ 95 | Advanced PDF processing and analysis |
| data-viz-pro | 720 | 2026-01-18 | ✅ 82 | Create interactive data visualizations |
| sql-optimizer | 680 | 2026-01-22 | 🛡️ 90 | Optimize SQL queries with AI suggestions |
```

---

## Workflow 3: Replacing Outdated Skills

**User Query:** "Which of my installed skills should I replace?"

**Skill Activation:** Triggered by "replace" + "installed skills"

**Processing Flow:**
1. Run Analysis 4 (Replaceable Skills Recommendation)
2. List all installed skills
3. For each installed skill:
   - Find similar skills (cosine similarity >= 0.75)
   - Calculate confidence scores
   - Filter confidence >= 0.70
4. Run Analysis 5 (Security Evaluation) on candidates
5. Rank by confidence descending
6. Return replacement recommendations with justifications

**Output Example:**
```
🔄 Skills You Should Consider Replacing:

### Installed: `basic-code-formatter` (200 stars, updated 8 months ago)

**Replacement Candidates:**

1. **advanced-formatter-pro** (Confidence: 0.85)
   - Stars: 1,200 (6x more)
   - Similarity: 0.91 (very similar functionality)
   - Security: 🛡️ Excellent (Score: 94)
   - Last Updated: 2026-01-25 (actively maintained)
   - **Recommendation:** Strongly recommend replacement

2. **smart-formatter** (Confidence: 0.73)
   - Stars: 850 (4x more)
   - Similarity: 0.88
   - Security: ✅ Good (Score: 80)
   - Last Updated: 2026-01-20
   - **Recommendation:** Consider as alternative
```

---

## Workflow 4: Finding Similar Functionality

**User Query:** "Find skills similar to `my-pdf-tool`"

**Skill Activation:** Triggered by "find" + "similar" + "skills"

**Processing Flow:**
1. Run Analysis 3 (Functionally Similar Skills)
2. Load `my-pdf-tool` description from skill-manager
3. Build TF-IDF vectors for all skills
4. Calculate cosine similarity with `my-pdf-tool`
5. Filter similarity >= 0.75
6. Exclude `my-pdf-tool` itself
7. Run Analysis 5 (Security Evaluation)
8. Rank by similarity descending
9. Return top 10

**Output Example:**
```
Similar Skills to `my-pdf-tool`:

| Skill Name | Similarity | Stars | Security | Description |
|------------|------------|-------|----------|-------------|
| pdf-mastery | 0.89 | 850 | 🛡️ 95 | Advanced PDF processing with OCR |
| doc-converter-pro | 0.82 | 620 | ✅ 78 | Convert documents between formats |
| text-extraction-kit | 0.78 | 480 | ✅ 72 | Extract text from PDFs and images |
```

---

## Workflow 5: Security-First Skill Discovery

**User Query:** "Recommend skills with good security scores"

**Skill Activation:** Triggered by "security" + "skills"

**Processing Flow:**
1. Run Analysis 1 (New Skills Discovery)
2. Run Analysis 5 (Security Evaluation) on all results
3. Filter security score >= 70 (default threshold)
4. Rank by security score descending
5. Return top 15 most secure skills

**Output Example:**
```
🛡️ Secure Skills Recommended (Score >= 70):

| Skill Name | Security | Stars | Updated | Description |
|------------|----------|-------|---------|-------------|
| code-auditor | 🛡️ 98 | 1,200 | 2026-01-28 | Security-focused code review |
| privacy-guardian | 🛡️ 96 | 950 | 2026-01-25 | Privacy leak detection |
| safe-executor | 🛡️ 92 | 780 | 2026-01-22 | Sandboxed code execution |
```

---

## Workflow 6: Weekly Automated Report

**User Query:** "Generate my weekly skill ecosystem report"

**Skill Activation:** Triggered by "weekly" + "skill" + "report"

**Processing Flow:**
1. Run Analysis 6 (Comprehensive Weekly Report)
2. Execute all 5 sub-analyses sequentially
3. Aggregate statistics
4. Generate Markdown report
5. Save to `meta/reports/YYYY-MM-DD-skill-trending-report.md`
6. Return file path and summary

**Output Example:**
```
✅ Weekly Skill Ecosystem Report Generated!

📄 Report saved to: `meta/reports/2026-02-03-skill-trending-report.md`

📊 Summary:
- Total Skills in Ecosystem: 31,767
- Installed Skills: 47
- New Skills This Week: 12
- Trending Skills (WoW >= 5%): 8
- Replacement Candidates: 3
- Security-Cleared Recommendations: 15

💡 Top Recommendations:
1. Replace `basic-formatter` with `advanced-formatter-pro` (confidence 0.85)
2. Install `code-auditor` (trending +18.5%, security 98)
3. Explore alternatives to `old-pdf-tool` (3 better options found)
```

---

## Workflow 7: Growth Rate Analysis for Specific Skill

**User Query:** "What's the growth rate for `popular-skill`?"

**Skill Activation:** Triggered by "growth rate" + skill name

**Processing Flow:**
1. Run Analysis 2 (Growth Rates) with specific skill filter
2. Fetch star history from GitHub API
3. Calculate WoW growth for specified skill
4. Compare with ecosystem average
5. Return detailed growth metrics

**Output Example:**
```
📈 Growth Analysis for `popular-skill`:

**This Week:**
- Stars gained: 64
- Date range: 2026-01-27 to 2026-02-03

**Last Week:**
- Stars gained: 54
- Date range: 2026-01-20 to 2026-01-26

**WoW Growth Rate:** +18.5%
**Ecosystem Average:** +3.2%
**Trending:** ✅ Yes (threshold: 5%)

**Context:**
`popular-skill` is growing 5.8x faster than the ecosystem average.
This is in the top 5% of all skills by growth rate.
```

---

## Workflow 8: Audit Installed Skills for Quality

**User Query:** "Audit my installed skills for quality and security"

**Skill Activation:** Triggered by "audit" + "skills" + "quality|security"

**Processing Flow:**
1. List all installed skills from `~/.claude/skills/`
2. For each skill:
   - Fetch metadata from skill-manager (stars, last update)
   - Run Analysis 5 (Security Evaluation)
   - Check for replacement candidates (Analysis 4)
3. Categorize skills:
   - ✅ High Quality (stars >= 500, security >= 80, active)
   - ⚠️ Moderate Quality (stars 100-499, security 70-79)
   - 🚨 Low Quality (stars < 100, security < 70, or outdated)
4. Generate audit report

**Output Example:**
```
🔍 Skill Quality & Security Audit

**Installed Skills:** 47

### ✅ High Quality (35 skills)
- `code-reviewer` - 2,300 stars, security 95, updated 5 days ago
- `api-tester` - 1,850 stars, security 88, updated 8 days ago
[...]

### ⚠️ Moderate Quality (8 skills)
- `old-formatter` - 450 stars, security 75, updated 2 months ago
  → **Replacement Available:** `new-formatter` (1,200 stars, security 92)

### 🚨 Low Quality (4 skills)
- `abandoned-tool` - 80 stars, security 55, updated 9 months ago
  → **Action:** Consider uninstalling or replacing

**Recommendations:**
1. Replace 8 moderate-quality skills with better alternatives
2. Uninstall or replace 4 low-quality skills
3. All high-quality skills are secure and up-to-date
```

---

## Workflow 9: Compare Two Skills

**User Query:** "Compare `skill-a` and `skill-b`"

**Skill Activation:** Triggered by "compare" + skill names

**Processing Flow:**
1. Fetch metadata for both skills from skill-manager
2. Run Analysis 2 (Growth Rates) for both
3. Run Analysis 5 (Security Evaluation) for both
4. Calculate functional similarity between them (Analysis 3)
5. Generate side-by-side comparison

**Output Example:**
```
⚖️ Skill Comparison: `skill-a` vs `skill-b`

| Metric | skill-a | skill-b | Winner |
|--------|---------|---------|--------|
| Stars | 1,200 | 850 | skill-a (+41%) |
| Last Updated | 5 days ago | 12 days ago | skill-a |
| Security Score | 🛡️ 92 | ✅ 78 | skill-a |
| WoW Growth | +8.5% | +12.3% | skill-b |
| Functional Similarity | - | 0.88 (very similar) | - |

**Recommendation:**
Both skills serve similar purposes (88% functional similarity).
`skill-a` has better security and more stars, but `skill-b` is growing faster.

**Use Case Fit:**
- Choose `skill-a` if: Security and stability are priorities
- Choose `skill-b` if: Cutting-edge features and rapid development matter
```

---

## Workflow 10: Identify Skill Gaps

**User Query:** "What skill categories am I missing?"

**Skill Activation:** Triggered by "missing" + "skill categories|gaps"

**Processing Flow:**
1. Analyze installed skills and extract categories (from topics/tags)
2. Load skill-manager database and extract all categories
3. Identify top categories NOT represented in installed skills
4. Find top skills in missing categories
5. Run Analysis 5 (Security Evaluation)
6. Recommend skills to fill gaps

**Output Example:**
```
🔍 Skill Gap Analysis

**Your Installed Skills Cover:**
- Code Analysis (8 skills)
- Automation (12 skills)
- Testing (6 skills)

**Missing High-Value Categories:**

1. **Security & Privacy** (0 skills installed)
   - Top Skill: `privacy-guardian` (950 stars, security 96)
   - Recommendation: Install to cover security auditing needs

2. **Data Visualization** (0 skills installed)
   - Top Skill: `data-viz-pro` (720 stars, security 82)
   - Recommendation: Useful for reporting and dashboards

3. **Database Management** (0 skills installed)
   - Top Skill: `sql-optimizer` (680 stars, security 90)
   - Recommendation: Optimize database performance

**Action Plan:**
Install 1-2 skills from each missing category to build a well-rounded ecosystem.
```
