# Changelog

All notable changes to skill-trending-monitor-cskill will be documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-02-03

### Added

**Core Functionality:**
- `analyze_comprehensive.py`: Orchestrates all analyses into unified weekly trending report combining new skills, growth rates, similarity matches, replacements, and security assessments
- `analyze_new_skills.py`: Discovers high-quality skills not locally installed with quality filtering (minimum 50 stars, updated within 6 months)
- `analyze_growth_rates.py`: Calculates week-over-week growth rates using GitHub star history with intelligent caching
- `analyze_similarity.py`: TF-IDF + cosine similarity matching (threshold 0.75, max_features 500) for functional alternatives
- `analyze_replacements.py`: Multi-factor confidence scoring (star_ratio 0.4, recency 0.3, similarity 0.3) with threshold 0.70
- `evaluate_security.py`: Composite security scoring (stars 0.30, activity 0.25, license 0.25, updates 0.20) with threshold 70/100

**Data Sources:**
- skill-manager local database: `~/.claude/skills/skill-manager/data/all_skills_with_cn.json` (31,767 skills)
- GitHub API: REST API v3 for star history (5,000/hour authenticated, 60/hour unauthenticated)
- Authentication: `GITHUB_TOKEN` environment variable for enhanced rate limits

**Analysis Capabilities:**
- New skills discovery: Quality filters (min_stars=50, max_months_old=6) + local exclusion + star-based sorting
- Growth rate tracking: Week-over-week calculation `(current - previous) / previous * 100` using commit history
- Similarity matching: TF-IDF vectorization (max_features=500, ngram_range=[1,2]) + cosine similarity (sparse matrices)
- Replacement recommendations: Multi-factor scoring with conservative confidence threshold (0.70)
- Security evaluation: Composite score with graceful degradation when GitHub API unavailable
- Comprehensive report: All metrics combined into weekly Markdown reports to `meta/reports/YYYY-MM-DD-skill-trending-report.md`

**Utilities:**
- Cache system: Intelligent TTL-based caching (GitHub 24h, skills 7d, analysis 1h) with `.cache/` directory
- Rate limiting: Respects GitHub API limits with retry logic (3 attempts, 60s delay)
- Error handling: Graceful degradation with fallback to cached data, no complete failures
- Validation system: Four-layer validation (parameter → API response → DataFrame → output) with detailed error messages
- Helpers: Temporal context utilities, year detection with fallback logic

**Configuration:**
- `assets/config.json`: Basic configuration with GitHub token, cache settings, thresholds (quality, similarity, replacement, security)
- `assets/filters.json`: Four filter profiles (strict, balanced, permissive, experimental) with documentation and use cases
- Profile comparison table and customization guidelines included

**References:**
- `skill-manager-api-guide.md`: Database access patterns, schema documentation, query examples
- `github-api-guide.md`: API authentication, rate limiting strategies, star history fetching
- `analysis-methodologies.md`: Detailed algorithms for each analysis type with formulas
- `similarity-algorithms.md`: TF-IDF vectorization, cosine similarity, sparse matrix optimization
- `troubleshooting.md`: Common issues (rate limits, missing database, no results) with solutions

### Data Coverage

**Metrics implemented:**
- New skills discovery: 31,767 skills filtered by quality thresholds, local exclusion, star sorting
- Growth rates: Historical comparison using GitHub commit timestamps (7-day window)
- Similarity matching: TF-IDF on all 31,767 skill descriptions with configurable thresholds
- Replacements: Confidence scoring based on stars, recency, and similarity for installed skills
- Security assessment: Composite scoring with 4 components for quality signals
- Comprehensive report: All-in-one weekly trending report with 6 sections

**Source coverage:**
- Geographic: Worldwide (GitHub-hosted skills)
- Temporal: Current + historical (GitHub commit history for growth rates)
- Quality: 50+ stars (balanced profile), 10+ stars (permissive), 0+ stars (experimental)

### Known Limitations

- Historical star counts approximated from commit timestamps (acceptable accuracy for weekly trends)
- Similarity based on descriptions only (no code/AST analysis) - acceptable for MVP, planned for v2.0
- Conservative thresholds may miss emerging skills (<50 stars in balanced profile) - mitigated by permissive/experimental profiles
- Requires skill-manager installation as dependency (31,767 skills database)
- Data freshness depends on skill-manager updates (typically weekly syncs)
- GitHub API rate limits (60/hour unauthenticated, 5,000/hour authenticated) - mitigated by intelligent caching
- Security scoring is heuristic-based (no static code analysis) - acceptable for screening

### Planned for v2.0

**Enhanced Analysis:**
- Machine learning for skill quality prediction based on metadata patterns
- Code similarity analysis using AST-based comparison
- Skill dependency graph showing which skills are used together
- Sentiment analysis from skill descriptions and documentation

**Integration:**
- Integration with Claude Code telemetry for actual usage patterns
- Real-time monitoring using GitHub webhooks instead of weekly batch processing
- Cross-platform skill detection (Desktop, Web, API variants)

**Performance:**
- Parallel processing for faster analysis of large skill databases
- Incremental updates instead of full re-analysis
- Database indexing for faster queries

**User Experience:**
- Multi-language support (currently English descriptions only)
- Interactive CLI for on-demand analysis
- Web dashboard for visualization
- Email/Slack notifications for trending skills

## [Unreleased]

### Planned

- Add support for custom similarity algorithms beyond TF-IDF
- Improve performance for very large skill databases (>50,000 skills)
- Expand coverage to cross-platform skill variants
- Add skill category classification using LLM
- Create automated installation workflow for recommended skills
