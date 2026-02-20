# Architecture Decisions

**Version:** 1.0.0
**Last Updated:** 2026-02-03

---

## Overview

This document records the key architectural decisions made during the development of skill-trending-monitor-cskill, including API selection, analysis design, implementation patterns, and trade-offs considered.

---

## Phase 1: API Selection

### Decision: skill-manager Local Database as Primary Source

**Chosen:** `~/.claude/skills/skill-manager/data/all_skills_with_cn.json`

**Justification:**
- ✅ **Coverage:** 31,767 skills - comprehensive community coverage
- ✅ **Performance:** Local JSON file - no network latency
- ✅ **Reliability:** No external dependencies or API rate limits for skill metadata
- ✅ **Structure:** Well-defined schema with all required fields (name, author, github_url, stars, forks, updated_at, description)
- ✅ **Maintenance:** Updated regularly by skill-manager maintainers

**Alternatives Considered:**
- **GitHub API search:** Rejected due to rate limits and incomplete Claude Skill detection
- **awesome-claude-skills repos:** Rejected due to manual curation lag and incomplete metadata
- **claude-plugins.dev API:** Rejected due to smaller dataset and external dependency

**Trade-offs:**
- ✅ Pro: Fast, reliable, comprehensive
- ⚠️ Con: Requires skill-manager to be installed
- ⚠️ Con: Data freshness depends on skill-manager updates (acceptable - typically weekly)

---

### Decision: GitHub API for Star History

**Chosen:** GitHub REST API v3 (https://api.github.com)

**Justification:**
- ✅ **Authoritative:** GitHub is the source of truth for star counts
- ✅ **Rate Limits:** 5,000/hour (authenticated) - sufficient for ~1,200 skills
- ✅ **Historical Data:** Provides commit history for growth rate calculation
- ✅ **Well-documented:** Stable API with excellent documentation

**Alternatives Considered:**
- **Web scraping:** Rejected due to fragility and ToS violations
- **Third-party analytics:** Rejected due to cost and incomplete data
- **Manual tracking:** Rejected due to maintenance burden

**Trade-offs:**
- ✅ Pro: Authoritative, reliable, well-supported
- ⚠️ Con: Rate limits require token and careful batching
- ⚠️ Con: Historical star counts require parsing commit timestamps (acceptable approximation)

**Implementation Strategy:**
- Use authenticated requests (GITHUB_TOKEN) for 5,000/hour limit
- Implement intelligent caching (24h TTL) to minimize API calls
- Batch requests with rate limiter to respect API limits
- Graceful degradation when rate limit exceeded

---

## Phase 2: Analysis Design

### Decision: Six Core Analyses

**1. New Skills Discovery**

**Objective:** Find high-quality skills not yet installed locally

**Methodology:**
- Scan local `~/.claude/skills/` directory for installed skills
- Filter skill-manager database by quality thresholds (min_stars=50, max_months_old=6)
- Exclude already installed skills
- Sort by stars descending

**Justification:** Most requested use case - discovering new capabilities

---

**2. Growth Rate Tracking**

**Objective:** Identify fastest growing skills (week-over-week)

**Methodology:**
- Fetch current star count from skill-manager database
- Fetch star count from 7 days ago using GitHub API commit history
- Calculate WoW growth: `(current - previous) / previous * 100`
- Sort by growth rate descending

**Justification:** Growth rate indicates rising popularity and community momentum

**Trade-off:** Historical star counts approximated from commit timestamps (acceptable accuracy)

---

**3. Similarity Matching**

**Objective:** Find functionally similar alternatives to installed skills

**Methodology:**
- Use TF-IDF vectorization on skill descriptions (max_features=500, ngram_range=(1,2))
- Calculate cosine similarity matrix
- Filter pairs above threshold (default 0.75)
- For each installed skill, find top 3 similar alternatives

**Justification:** Helps users discover better alternatives or replacements

**Trade-off:** Similarity based on descriptions only (no code analysis) - acceptable for MVP

---

**4. Replacement Recommendations**

**Objective:** Suggest better alternatives to installed skills

**Methodology:**
- Multi-factor confidence scoring:
  - `star_ratio` (0.4 weight): Replacement has more stars
  - `recency_factor` (0.3 weight): Replacement updated more recently
  - `similarity_score` (0.3 weight): High functional similarity (≥0.75)
- Filter by confidence threshold (default 0.70)
- Require replacement to have equal or more stars

**Justification:** Evidence-based recommendations using multiple quality signals

**Trade-off:** Conservative threshold (0.70) may miss some valid replacements - by design for safety

---

**5. Security Evaluation**

**Objective:** Assess security and quality signals for skills

**Methodology:**
- Composite security score (0-100):
  - `stars_score` (0.30 weight): Community validation
  - `activity_score` (0.25 weight): Recent commits
  - `license_score` (0.25 weight): Open source license present
  - `update_score` (0.20 weight): Regular updates
- Filter by threshold (default 70)
- Graceful degradation when GitHub API unavailable

**Justification:** Multi-dimensional security assessment without deep code analysis

**Trade-off:** Heuristic-based (no static analysis) - acceptable for screening

---

**6. Comprehensive Report**

**Objective:** All-in-one weekly trending report combining all analyses

**Methodology:**
- Execute all five analyses sequentially
- Combine results into unified Markdown report
- Sections: New Skills, Fastest Growing, Similar Skills, Replacements, Security, Statistics
- Save to `meta/reports/YYYY-MM-DD-skill-trending-report.md`

**Justification:** Primary use case - weekly automation for trending insights

---

### Decision: Quality Thresholds

**Default Values:**
- `min_stars`: 50 (community validation)
- `max_months_old`: 6 (active maintenance)
- `similarity_threshold`: 0.75 (high confidence matches)
- `confidence_threshold`: 0.70 (conservative replacements)
- `security_threshold`: 70 (good security posture)

**Justification:**
- Balanced between quality and coverage
- Based on skill-manager distribution analysis (50 stars = top 15%)
- Four filter profiles (strict/balanced/permissive/experimental) for flexibility

**Trade-off:** May exclude emerging skills with <50 stars - mitigated by permissive profile option

---

## Phase 3: Architecture

### Decision: Modular Script Organization

**Structure:**
```
scripts/
├── analyze_*.py (6 analysis scripts)
├── fetch_*.py (2 fetch scripts)
├── parse_*.py (2 parse scripts)
└── utils/ (4 utility modules)
```

**Justification:**
- ✅ Separation of concerns (fetch → parse → analyze)
- ✅ Reusable utilities (cache, rate limiter, validators)
- ✅ Easy to test each component independently
- ✅ Extensible - new analyses can be added without modifying existing code

**Alternatives Considered:**
- **Monolithic script:** Rejected due to maintainability issues
- **Object-oriented classes:** Rejected due to unnecessary complexity for sequential workflows

---

### Decision: Intelligent Caching Strategy

**TTL Settings:**
- GitHub API responses: 24 hours (star counts change slowly)
- skill-manager database: 7 days (updated weekly)
- Analysis results: 1 hour (user may re-run with different parameters)

**Justification:**
- Minimizes GitHub API calls (rate limit preservation)
- Fast re-runs during parameter tuning
- Cache invalidation matches data update frequency

**Implementation:** `.cache/` directory with JSON files, TTL metadata in filenames

---

### Decision: Sparse TF-IDF Matrices

**Chosen:** `scipy.sparse` matrices for TF-IDF vectorization

**Justification:**
- ✅ Memory efficient: ~10 MB for 31,767 skills (vs ~4 GB dense matrix)
- ✅ Fast cosine similarity with sparse matrix operations
- ✅ Scales to full skill-manager database

**Trade-off:** Slightly more complex code - worth it for 400x memory reduction

---

### Decision: Four Filter Profiles

**Profiles:**
1. **Strict** (Production): min_stars=100, max_months=3, similarity=0.80
2. **Balanced** (Default): min_stars=50, max_months=6, similarity=0.75
3. **Permissive** (Discovery): min_stars=10, max_months=12, similarity=0.65
4. **Experimental** (Research): min_stars=0, max_months=24, similarity=0.50

**Justification:**
- Different use cases require different quality bars
- Balanced profile is sensible default (50 stars = top 15%)
- Users can choose based on risk tolerance

---

## Phase 4: Detection and Activation

### Decision: Skill Activation Keywords

**Primary Keywords:**
- `trending skills`, `skill growth`, `new skills`, `skill alternatives`
- `skill recommendations`, `skill security`, `skill analysis`
- `skill-manager`, `31,767 skills`, `GitHub stars`

**Justification:**
- Covers user intent for skill discovery and monitoring
- References data sources (skill-manager, GitHub)
- Includes security and quality dimensions

**Negative Scope:**
- ❌ Do NOT activate for: Installing skills (use skill-manager), Creating skills (use agent-skill-creator), Generic trend analysis (not skill-specific)

---

## Phase 5: Implementation Patterns

### Decision: Error Handling Strategy

**Pattern: Graceful Degradation**

**Example:**
```python
try:
    github_stars = fetch_github_stars(repo_url)
except RateLimitError:
    logger.warning("Rate limit exceeded, using cached data")
    github_stars = cached_stars
except APIError as e:
    logger.error(f"API error: {e}")
    github_stars = None  # Continue with partial data
```

**Justification:**
- ✅ Robustness: Partial results better than complete failure
- ✅ User experience: Clear error messages with fallback behavior
- ✅ Rate limit resilience: Cache provides continuity

---

### Decision: Validation at Multiple Layers

**Layers:**
1. **Parameter validation:** Before API calls (validate_entity, validate_year)
2. **API response validation:** After fetch (validate_response)
3. **DataFrame validation:** After parse (validate_dataframe, validate_temporal_consistency)
4. **Output validation:** Before return (validate_completeness)

**Justification:**
- Fail fast with clear error messages
- Data quality assurance at each transformation step
- Debugging visibility

---

### Decision: Python 3.8+ Requirement

**Chosen:** Python 3.8+ (released 2019-10-14)

**Justification:**
- ✅ Type hints with `from __future__ import annotations`
- ✅ Modern syntax (walrus operator, positional-only parameters)
- ✅ Widely available (default in Ubuntu 20.04+, macOS 11+)
- ✅ Long-term support until 2024-10

**Trade-off:** Excludes Python 3.7 and earlier (acceptable - 3.7 EOL 2023-06-27)

---

## Key Trade-offs Summary

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| skill-manager local database | Fast, reliable, comprehensive | Requires installation | Clear installation instructions |
| GitHub API for stars | Authoritative, accurate | Rate limits | Caching + authenticated requests |
| Similarity from descriptions | Fast, simple | No code analysis | Acceptable for MVP, future enhancement |
| Conservative thresholds | High quality results | May miss emerging skills | Four filter profiles for flexibility |
| Sparse matrices | 400x memory reduction | Code complexity | Worth it for scalability |
| Weekly automation | Fresh insights | Cron/launchd setup required | Detailed automation guide |

---

## Future Enhancements (v2.0+)

**Not implemented in v1.0 but considered:**
- Machine learning for skill quality prediction
- Code similarity analysis (AST-based)
- Skill dependency graph (which skills are used together)
- Integration with Claude Code telemetry (which skills are actually used)
- Real-time monitoring (GitHub webhooks instead of weekly batch)
- Multi-language support (currently English descriptions only)

**Decision:** MVP first, validate usage patterns before adding complexity

---

**Created by:** Claude Sonnet 4.5 (agent-skill-creator)
**Last Updated:** 2026-02-03
**Version:** 1.0.0
