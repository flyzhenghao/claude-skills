# Architecture Documentation

## Two-Tier Data Architecture

This skill uses a sophisticated two-tier data architecture for comprehensive skill monitoring:

### Tier 1 (Primary): skill-manager Local Database

**Source:** `~/.claude/skills/skill-manager/data/all_skills_with_cn.json`

**Coverage:** 31,767 skills with metadata

**Access:** Direct JSON parsing, zero rate limits

**Used for:**
- New skill discovery (skills not locally installed)
- Similarity matching (TF-IDF + cosine similarity)
- Base metadata (name, description, author, repository URL)
- Quality filtering (stars, last update date)

**Schema:**
```json
{
  "skills": [
    {
      "name": "skill-name",
      "description": "Skill description",
      "description_cn": "中文描述",
      "author": "author-name",
      "repository": "https://github.com/owner/repo",
      "stars": 150,
      "forks": 25,
      "last_updated": "2026-01-15",
      "topics": ["claude", "automation"]
    }
  ]
}
```

**Quality Filters Applied:**
- Stars >= 50 (excludes low-quality/abandoned skills)
- Last updated within 6 months (active maintenance)
- Valid repository URL (GitHub format)

**Coverage Statistics:**
- Total skills: 31,767
- With Chinese descriptions: 31,752 (99.95%)
- Active (updated < 6 months): ~18,500

---

### Tier 2 (Secondary): GitHub API

**Endpoint:** `https://api.github.com/repos/{owner}/{repo}/stargazers`

**Header:** `Accept: application/vnd.github.star+json`

**Rate Limit:** 5,000 requests/hour (authenticated)

**Used for:**
- Historical star timestamps for growth calculation
- Week-over-week (WoW) growth rate analysis
- Repository activity verification

**Endpoint for Star History:**
```bash
curl -H "Accept: application/vnd.github.star+json" \
     -H "Authorization: token ${GITHUB_TOKEN}" \
     https://api.github.com/repos/{owner}/{repo}/stargazers?per_page=100
```

**Response Format:**
```json
[
  {
    "starred_at": "2026-01-28T10:30:00Z",
    "user": {"login": "username"}
  }
]
```

**Rate Limiting Strategy:**
- **Unauthenticated:** 60 requests/hour (NOT USED)
- **Authenticated:** 5,000 requests/hour (REQUIRED)
- **Implementation:** Token from `assets/config.json`
- **Backoff:** Exponential backoff on 429 responses
- **Caching:** 7-day cache for star timestamps

**Token Configuration:**
```json
{
  "github_token": "ghp_YOUR_TOKEN_HERE",
  "rate_limit_buffer": 100,
  "max_retries": 3
}
```

Get token at: https://github.com/settings/tokens (scope: `public_repo` read-only)

---

## Dual Cache System

### Cache 1: Skill Metadata Cache

- **Location:** `data/cache/skill-metadata.json`
- **TTL:** 30 days
- **Purpose:** Avoid re-parsing skill-manager database
- **Content:** Skill list with normalized metadata

### Cache 2: Security Evaluation Cache

- **Location:** `data/security-cache/evaluations.json`
- **TTL:** 7 days
- **Purpose:** Avoid redundant security evaluations
- **Content:** Security scores and assessment details

**Cache Format (Security):**
```json
{
  "skill_name": "candidate-skill",
  "evaluated_at": "2026-02-03T10:30:00Z",
  "security_score": 85,
  "risk_level": "low",
  "issues_found": [],
  "expires_at": "2026-02-10T10:30:00Z"
}
```

---

## Machine Learning Similarity Detection

### TF-IDF Vectorization

1. Extract skill descriptions from all skills
2. Build TF-IDF vocabulary from corpus
3. Transform each description into feature vector
4. Store vectors for comparison

**Implementation:**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer(
    max_features=1000,
    stop_words='english',
    ngram_range=(1, 2)
)

tfidf_matrix = vectorizer.fit_transform(descriptions)
similarities = cosine_similarity(tfidf_matrix[target_idx], tfidf_matrix)
```

### Cosine Similarity Calculation

```
similarity = (vec_A · vec_B) / (||vec_A|| × ||vec_B||)
threshold = 0.75 (high similarity)
```

### Confidence Scoring (Multi-Factor)

- **Star Ratio:** `candidate_stars / installed_stars` (weight: 0.4)
- **Recency Factor:** `days_since_update < 180 ? 1.0 : 0.5` (weight: 0.3)
- **Text Similarity:** `cosine_similarity(descriptions)` (weight: 0.3)
- **Final Confidence:** `weighted_sum >= 0.70` for recommendation

**Formula:**
```python
confidence = (
    (candidate_stars / installed_stars) * 0.4 +
    (1.0 if days_since_update < 180 else 0.5) * 0.3 +
    cosine_similarity * 0.3
)
```

---

## Temporal Growth Analysis

### Week-over-Week (WoW) Growth Rate

```python
# Fetch stargazer timestamps from GitHub API
stars_this_week = count_stars_between(week_start, week_end)
stars_last_week = count_stars_between(week_start - 7, week_end - 7)

wow_growth_rate = ((stars_this_week - stars_last_week) / stars_last_week) * 100
trending_threshold = 5.0  # >= 5% growth considered trending
```

**Temporal Boundaries:**
- This week: `[week_start_date, today]`
- Last week: `[week_start_date - 7, week_start_date - 1]`
- Week start: Monday 00:00 UTC

**Trending Detection:**
- Calculate WoW growth for top 100 skills by stars
- Filter skills with growth >= 5%
- Rank by growth rate descending
- Report top 10 fastest growing skills
