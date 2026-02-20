# Analysis Methodologies Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-04

---

## Overview

This guide documents the five core analysis methodologies used by skill-trending-monitor to identify trending skills, calculate growth rates, find alternatives, and assess security.

**Analysis Types:**

1. **New Skills Discovery** - Identify uninstalled skills with quality filters
2. **Growth Rate Calculation** - Calculate week-over-week star growth from GitHub
3. **Similarity Matching** - Find functionally similar skills using TF-IDF
4. **Replacement Recommendations** - Multi-factor confidence scoring
5. **Security Evaluation** - Composite security assessment

**Integration Scripts:**

| Analysis Type | Script | Output |
|---------------|--------|--------|
| New Skills | `analyze_new_skills.py` | DataFrame with uninstalled skills |
| Growth Rates | `analyze_growth_rates.py` | DataFrame with WoW growth rates |
| Similarity | `analyze_similarity.py` | DataFrame with similar pairs |
| Replacements | `analyze_replacements.py` | DataFrame with replacements |
| Security | `evaluate_security.py` | DataFrame with security scores |
| Comprehensive | `analyze_comprehensive.py` | Unified report (all above) |

---

## 1. New Skills Discovery

### Methodology

Identify skills from skill-manager database (31,767 skills) that are:
- ✅ Not currently installed locally
- ✅ Meet quality thresholds (stars, recency)
- ✅ Have valid metadata

### Quality Filters

**Threshold Configuration:**

| Filter | Default Value | Rationale |
|--------|--------------|-----------|
| `min_stars` | 50 | Community validation |
| `max_months_old` | 6 | Active maintenance |
| `require_description` | True | Usability |
| `require_github_url` | True | Verification |

**Filter Logic:**

```python
def apply_quality_filters(
    skills_df: pd.DataFrame,
    min_stars: int = 50,
    max_months_old: int = 6
) -> pd.DataFrame:
    """
    Apply quality filters to skill list.

    Args:
        skills_df: DataFrame from skill-manager
        min_stars: Minimum GitHub stars
        max_months_old: Maximum months since last update

    Returns:
        Filtered DataFrame
    """
    from datetime import datetime, timedelta

    # Filter 1: Stars threshold
    filtered = skills_df[skills_df['stars'] >= min_stars].copy()

    # Filter 2: Recency threshold
    cutoff_date = datetime.now() - timedelta(days=max_months_old * 30)
    filtered = filtered[filtered['updated_at'] >= cutoff_date]

    # Filter 3: Required metadata
    filtered = filtered[filtered['description'].notna()]
    filtered = filtered[filtered['github_url'].notna()]

    return filtered
```

### Installation Detection

**Method 1: Directory Scan (Primary)**

```python
def get_installed_skills(
    skills_dir: Optional[Path] = None
) -> List[str]:
    """
    Scan ~/.claude/skills/ for installed skills.

    Args:
        skills_dir: Custom skills directory (None = default)

    Returns:
        List of installed skill names
    """
    if skills_dir is None:
        skills_dir = Path.home() / '.claude/skills'

    installed = []

    for skill_path in skills_dir.glob('*/'):
        if (skill_path / 'SKILL.md').exists():
            installed.append(skill_path.name)

    return installed
```

**Method 2: Plugin Registry (Fallback)**

```python
def get_installed_from_registry() -> List[str]:
    """
    Read from ~/.claude/plugins/installed_plugins.json.

    Returns:
        List of installed skill names
    """
    registry = Path.home() / '.claude/plugins/installed_plugins.json'

    if not registry.exists():
        return []

    with open(registry) as f:
        data = json.load(f)

    return list(data.get('plugins', {}).keys())
```

### Discovery Algorithm

```python
def discover_new_skills(
    all_skills_df: pd.DataFrame,
    installed_skills: List[str],
    min_stars: int = 50,
    max_months_old: int = 6
) -> pd.DataFrame:
    """
    Discover new skills not currently installed.

    Algorithm:
    1. Apply quality filters to all skills
    2. Exclude installed skills
    3. Sort by stars descending
    4. Return top candidates

    Args:
        all_skills_df: All skills from skill-manager
        installed_skills: List of installed skill names
        min_stars: Minimum stars threshold
        max_months_old: Maximum age threshold

    Returns:
        DataFrame with new skill recommendations
    """
    # Apply quality filters
    quality_skills = apply_quality_filters(
        all_skills_df,
        min_stars=min_stars,
        max_months_old=max_months_old
    )

    # Exclude installed
    new_skills = quality_skills[
        ~quality_skills['name'].isin(installed_skills)
    ].copy()

    # Sort by popularity
    new_skills = new_skills.sort_values('stars', ascending=False)

    return new_skills.reset_index(drop=True)
```

### Output Format

```python
# Example DataFrame columns
{
    'name': str,              # Skill name
    'author': str,            # Author/organization
    'stars': int,             # GitHub stars
    'updated_at': datetime,   # Last update
    'description': str,       # Description
    'github_url': str,        # GitHub URL
    'tags': List[str],        # Tags
    'category': str           # Category
}
```

---

## 2. Growth Rate Calculation

### Methodology

Calculate week-over-week (WoW) star growth using GitHub star history.

### Formula

**Week-over-Week Growth Rate:**

```
WoW Growth Rate (%) = ((Current Week Stars - Previous Week Stars) / Previous Week Stars) × 100
```

**Example:**
- Previous week: 100 stars
- Current week: 112 stars
- WoW Growth = ((112 - 100) / 100) × 100 = 12%

### Data Requirements

**Star History Record:**

```python
{
    "starred_at": "2025-11-15T10:00:00Z",  # ISO 8601 timestamp
    "user": {
        "login": "username",
        "id": 123456
    }
}
```

**Minimum Requirements:**
- ✅ At least 14 days of star history
- ✅ At least 1 star in previous week
- ✅ Valid timestamps in ascending order

### Implementation

```python
def calculate_wow_growth(
    star_history: List[Dict]
) -> Dict:
    """
    Calculate week-over-week growth from star history.

    Algorithm:
    1. Group stars by week (ISO week number)
    2. Count stars in current week (most recent)
    3. Count stars in previous week
    4. Calculate percentage growth
    5. Handle edge cases (no previous week data)

    Args:
        star_history: List of star records with timestamps

    Returns:
        Dict with growth metrics:
        {
            "total_stars": int,
            "current_week_stars": int,
            "previous_week_stars": int,
            "wow_growth_rate": float,
            "current_week_start": str,
            "has_previous_week": bool
        }

    Raises:
        ValueError: Insufficient data (< 14 days)
    """
    from datetime import datetime, timedelta
    from collections import defaultdict

    if not star_history:
        raise ValueError("Empty star history")

    # Parse timestamps
    stars_by_week = defaultdict(int)

    for record in star_history:
        dt = datetime.fromisoformat(record['starred_at'].replace('Z', '+00:00'))
        # ISO week: (year, week_number)
        week_key = dt.isocalendar()[:2]
        stars_by_week[week_key] += 1

    # Get current and previous week
    weeks = sorted(stars_by_week.keys())

    if len(weeks) < 2:
        raise ValueError("Need at least 2 weeks of data")

    current_week = weeks[-1]
    previous_week = weeks[-2]

    current_stars = stars_by_week[current_week]
    previous_stars = stars_by_week[previous_week]

    # Calculate growth rate
    if previous_stars > 0:
        growth_rate = ((current_stars - previous_stars) / previous_stars) * 100
    else:
        growth_rate = 0.0

    return {
        "total_stars": len(star_history),
        "current_week_stars": current_stars,
        "previous_week_stars": previous_stars,
        "wow_growth_rate": growth_rate,
        "current_week_start": f"{current_week[0]}-W{current_week[1]:02d}",
        "has_previous_week": True
    }
```

### Interpretation Guidelines

**Growth Rate Categories:**

| WoW Growth | Category | Interpretation |
|------------|----------|----------------|
| > 50% | 🔥 Viral | Rapid adoption, trending |
| 20-50% | 📈 High Growth | Strong momentum |
| 5-20% | ✅ Steady Growth | Healthy growth |
| 0-5% | ➡️ Stable | Mature, stable |
| < 0% | 📉 Declining | Losing traction |

**Caveats:**
- ⚠️ New skills (< 100 stars) may have volatile growth rates
- ⚠️ Very popular skills (> 1000 stars) typically have lower % growth
- ⚠️ Weekly seasonality (Monday-Friday higher than weekends)

---

## 3. Similarity Matching

### Methodology

Use **TF-IDF (Term Frequency-Inverse Document Frequency) + Cosine Similarity** to find functionally similar skills based on descriptions.

### Algorithm: TF-IDF Vectorization

**Step 1: Text Preprocessing**

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    max_features=500,      # Top 500 terms
    stop_words='english',  # Remove common words
    ngram_range=(1, 2),    # Unigrams + bigrams
    min_df=1,              # Minimum document frequency
    max_df=0.8             # Maximum document frequency (80%)
)
```

**Parameters Explained:**
- `max_features=500`: Limit to 500 most important terms (performance)
- `stop_words='english'`: Remove "the", "a", "is", etc.
- `ngram_range=(1, 2)`: Include single words and two-word phrases
- `min_df=1`: Term must appear in at least 1 document
- `max_df=0.8`: Ignore terms in > 80% of documents (too common)

**Step 2: Create TF-IDF Matrix**

```python
tfidf_matrix = vectorizer.fit_transform(descriptions)
# Shape: (num_skills, 500)
```

**Step 3: Calculate Cosine Similarity**

```python
from sklearn.metrics.pairwise import cosine_similarity

similarity_matrix = cosine_similarity(tfidf_matrix)
# Shape: (num_skills, num_skills)
# Values: 0.0 (dissimilar) to 1.0 (identical)
```

### Similarity Formula

**Cosine Similarity:**

```
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)

Where:
- A, B = TF-IDF vectors for two skills
- A · B = dot product of vectors
- ||A|| = Euclidean norm of A
- ||B|| = Euclidean norm of B
```

**Interpretation:**
- 1.0 = Identical descriptions
- 0.75-0.99 = Very similar (functionally equivalent)
- 0.50-0.74 = Somewhat similar (related functionality)
- 0.25-0.49 = Slightly similar (some overlap)
- 0.0-0.24 = Dissimilar

### Threshold Selection

**Default: 0.75 (High Similarity)**

**Rationale:**
- ✅ Filters out false positives (unrelated skills)
- ✅ Ensures functional equivalence
- ✅ Suitable for replacement recommendations

**Alternative Thresholds:**
- 0.85: Very high confidence (stricter, fewer matches)
- 0.70: Moderate confidence (more matches, some false positives)
- 0.60: Exploratory (many matches, requires manual review)

### Implementation

```python
def calculate_similarity(
    skills_df: pd.DataFrame,
    similarity_threshold: float = 0.75,
    installed_skills: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Calculate pairwise similarity scores.

    Algorithm:
    1. Filter skills with valid descriptions
    2. Create TF-IDF vectors
    3. Calculate cosine similarity matrix
    4. Extract pairs above threshold
    5. Optionally filter for installed skills

    Args:
        skills_df: DataFrame with skills
        similarity_threshold: Minimum similarity (0.0-1.0)
        installed_skills: Filter for these skills (None = all)

    Returns:
        DataFrame with similar pairs:
        {
            'skill1_name': str,
            'skill2_name': str,
            'similarity_score': float,
            'skill1_stars': int,
            'skill2_stars': int,
            'skill1_description': str,
            'skill2_description': str
        }
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # Filter valid descriptions
    valid = skills_df[skills_df['description'].notna()].copy()
    valid = valid[valid['description'].str.strip() != '']

    if len(valid) < 2:
        return pd.DataFrame()

    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.8
    )

    tfidf_matrix = vectorizer.fit_transform(valid['description'])

    # Calculate similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Extract pairs
    pairs = []

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            score = similarity_matrix[i, j]

            if score >= similarity_threshold:
                skill1 = valid.iloc[i]
                skill2 = valid.iloc[j]

                # Filter by installed skills if provided
                if installed_skills:
                    if (skill1['name'] not in installed_skills and
                        skill2['name'] not in installed_skills):
                        continue

                pairs.append({
                    'skill1_name': skill1['name'],
                    'skill2_name': skill2['name'],
                    'similarity_score': score,
                    'skill1_stars': skill1.get('stars', 0),
                    'skill2_stars': skill2.get('stars', 0),
                    'skill1_description': skill1['description'][:100] + '...',
                    'skill2_description': skill2['description'][:100] + '...'
                })

    result = pd.DataFrame(pairs)
    return result.sort_values('similarity_score', ascending=False)
```

---

## 4. Replacement Recommendations

### Methodology

Multi-factor confidence scoring combining star ratio, recency, and text similarity.

### Confidence Formula

**Composite Confidence Score:**

```
Confidence = (0.4 × Star Ratio) + (0.3 × Recency Factor) + (0.3 × Similarity Score)
```

**Component Weights:**
- **40% Star Ratio** - Community adoption indicator
- **30% Recency Factor** - Maintenance activity indicator
- **30% Similarity Score** - Functional equivalence indicator

**Default Threshold: 0.70 (70%)**

### Component Calculations

**1. Star Ratio (0-1.0, capped)**

```python
def calculate_star_ratio(
    candidate_stars: int,
    installed_stars: int
) -> float:
    """
    Calculate star ratio, capped at 1.0.

    Args:
        candidate_stars: Replacement candidate stars
        installed_stars: Currently installed skill stars

    Returns:
        Ratio (0.0-1.0)

    Examples:
        >>> calculate_star_ratio(1000, 500)
        1.0  # Capped at 1.0

        >>> calculate_star_ratio(300, 500)
        0.6

        >>> calculate_star_ratio(0, 500)
        0.0
    """
    if installed_stars == 0:
        return 1.0 if candidate_stars > 0 else 0.0

    ratio = candidate_stars / installed_stars
    return min(ratio, 1.0)  # Cap at 1.0
```

**2. Recency Factor (0-1.0)**

```python
def calculate_recency_factor(
    updated_at: datetime,
    current_date: datetime
) -> float:
    """
    Calculate recency factor based on days since update.

    Formula:
        recency = max(1.0 - (days_since_update / 365), 0.0)

    Args:
        updated_at: Last update timestamp
        current_date: Current date

    Returns:
        Factor (0.0-1.0)

    Examples:
        >>> # Updated today
        >>> calculate_recency_factor(current_date, current_date)
        1.0

        >>> # Updated 6 months ago
        >>> calculate_recency_factor(current_date - timedelta(days=180), current_date)
        0.51

        >>> # Updated 1+ years ago
        >>> calculate_recency_factor(current_date - timedelta(days=400), current_date)
        0.0
    """
    days_since = (current_date - updated_at).days
    factor = max(1.0 - (days_since / 365), 0.0)
    return factor
```

**3. Similarity Score (0-1.0)**

From TF-IDF + cosine similarity (already 0-1.0 range).

### Implementation

```python
def calculate_replacement_confidence(
    installed_df: pd.DataFrame,
    all_skills_df: pd.DataFrame,
    similarity_df: pd.DataFrame,
    confidence_threshold: float = 0.70
) -> pd.DataFrame:
    """
    Calculate replacement recommendations with confidence scores.

    Algorithm:
    1. For each installed skill
    2. Find similar skills from similarity_df
    3. For each similar skill (candidate):
       - Calculate star ratio
       - Calculate recency factor
       - Get similarity score
       - Compute weighted confidence
    4. Filter by threshold
    5. Sort by confidence descending

    Args:
        installed_df: Installed skills
        all_skills_df: All available skills
        similarity_df: Similar pairs from calculate_similarity()
        confidence_threshold: Minimum confidence (0.0-1.0)

    Returns:
        DataFrame with replacements:
        {
            'installed_skill': str,
            'replacement_candidate': str,
            'confidence_score': float,
            'star_ratio': float,
            'recency_factor': float,
            'similarity_score': float,
            'installed_stars': int,
            'candidate_stars': int,
            'installed_updated': datetime,
            'candidate_updated': datetime
        }
    """
    replacements = []
    current_date = datetime.now()

    for _, installed in installed_df.iterrows():
        # Find similar skills
        similar = similarity_df[
            (similarity_df['skill1_name'] == installed['name']) |
            (similarity_df['skill2_name'] == installed['name'])
        ]

        for _, sim_row in similar.iterrows():
            # Identify candidate
            candidate_name = (
                sim_row['skill2_name']
                if sim_row['skill1_name'] == installed['name']
                else sim_row['skill1_name']
            )

            # Get candidate details
            candidate = all_skills_df[all_skills_df['name'] == candidate_name]

            if candidate.empty:
                continue

            candidate = candidate.iloc[0]

            # Calculate components
            star_ratio = calculate_star_ratio(
                candidate['stars'],
                installed['stars']
            )

            recency_factor = calculate_recency_factor(
                candidate['updated_at'],
                current_date
            )

            similarity_score = sim_row['similarity_score']

            # Weighted confidence
            confidence = (
                0.4 * star_ratio +
                0.3 * recency_factor +
                0.3 * similarity_score
            )

            if confidence >= confidence_threshold:
                replacements.append({
                    'installed_skill': installed['name'],
                    'replacement_candidate': candidate_name,
                    'confidence_score': confidence,
                    'star_ratio': star_ratio,
                    'recency_factor': recency_factor,
                    'similarity_score': similarity_score,
                    'installed_stars': installed['stars'],
                    'candidate_stars': candidate['stars'],
                    'installed_updated': installed['updated_at'],
                    'candidate_updated': candidate['updated_at']
                })

    result = pd.DataFrame(replacements)
    return result.sort_values('confidence_score', ascending=False)
```

### Interpretation

**Confidence Levels:**

| Score | Level | Action |
|-------|-------|--------|
| ≥ 0.85 | Very High | Strong recommendation |
| 0.70-0.84 | High | Recommended |
| 0.50-0.69 | Moderate | Consider |
| < 0.50 | Low | Not recommended |

---

## 5. Security Evaluation

### Methodology

Composite security scoring with four weighted components.

### Security Score Formula

**Composite Security Score (0-100):**

```
Security = (0.30 × Stars Score) + (0.25 × Activity Score) +
           (0.25 × License Score) + (0.20 × Update Score)
```

**Component Weights:**
- **30% Stars Score** - Community trust indicator
- **25% Activity Score** - Development health indicator
- **25% License Score** - Legal compatibility indicator
- **20% Update Score** - Maintenance commitment indicator

**Default Threshold: 70**

### Component Scoring

**1. Stars Score (0-100)**

```python
def calculate_stars_score(stars: int) -> int:
    """
    Stars score with progressive scale.

    Scale:
    - 0-9 stars: 0-30
    - 10-99 stars: 30-60
    - 100-999 stars: 60-85
    - 1000+ stars: 85-100 (capped)

    Args:
        stars: GitHub star count

    Returns:
        Score (0-100)
    """
    if stars >= 1000:
        return min(85 + (stars - 1000) // 200, 100)
    elif stars >= 100:
        return 60 + int((stars - 100) / 900 * 25)
    elif stars >= 10:
        return 30 + int((stars - 10) / 90 * 30)
    else:
        return min(stars * 3, 30)
```

**2. Activity Score (0-100)**

```python
def calculate_activity_score(
    updated_at: datetime,
    current_date: datetime
) -> int:
    """
    Activity score based on recency.

    Scale:
    - < 1 month: 90-100
    - 1-3 months: 70-90
    - 3-6 months: 50-70
    - 6-12 months: 30-50
    - > 12 months: 0-30

    Args:
        updated_at: Last update timestamp
        current_date: Current date

    Returns:
        Score (0-100)
    """
    days_since = (current_date - updated_at).days

    if days_since < 30:
        return 100 - (days_since // 3)
    elif days_since < 90:
        return 90 - int((days_since - 30) / 60 * 20)
    elif days_since < 180:
        return 70 - int((days_since - 90) / 90 * 20)
    elif days_since < 365:
        return 50 - int((days_since - 180) / 185 * 20)
    else:
        return max(30 - (days_since - 365) // 30, 0)
```

**3. License Score (0-100)**

```python
def calculate_license_score(license_name: str) -> int:
    """
    License compatibility score.

    Categories:
    - Permissive (MIT, Apache, BSD): 100
    - Copyleft (GPL, LGPL): 70
    - Other OSI-approved: 50
    - No license: 0

    Args:
        license_name: License identifier

    Returns:
        Score (0-100)
    """
    if not license_name or license_name.lower() in ['none', 'unknown', '']:
        return 0

    license_lower = license_name.lower()

    # Permissive
    permissive = ['mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0']
    if any(lic in license_lower for lic in permissive):
        return 100

    # Copyleft
    copyleft = ['gpl', 'lgpl', 'agpl', 'mpl']
    if any(lic in license_lower for lic in copyleft):
        return 70

    # Other recognized
    other = ['cc-by', 'artistic', 'epl', 'eupl']
    if any(lic in license_lower for lic in other):
        return 50

    # Unknown
    return 25
```

**4. Update Score (0-100)**

```python
def calculate_update_score(
    updated_at: datetime,
    current_date: datetime
) -> int:
    """
    Maintenance frequency score.

    Scale:
    - < 1 month: 100
    - < 3 months: 80
    - < 6 months: 60
    - < 1 year: 40
    - > 1 year: 20

    Args:
        updated_at: Last update timestamp
        current_date: Current date

    Returns:
        Score (0-100)
    """
    days_since = (current_date - updated_at).days

    if days_since < 30:
        return 100
    elif days_since < 90:
        return 80
    elif days_since < 180:
        return 60
    elif days_since < 365:
        return 40
    else:
        return 20
```

### Assessment Levels

**Security Score Interpretation:**

| Score | Level | Status |
|-------|-------|--------|
| 85-100 | EXCELLENT | ✅ Highly trusted |
| 70-84 | GOOD | ✅ Recommended |
| 50-69 | MODERATE | ⚠️ Review needed |
| 30-49 | LOW | ⚠️ Caution |
| 0-29 | POOR | ❌ Not recommended |

### Graceful Degradation

If security evaluation fails (e.g., missing data), system continues with:
- Default score: 0
- Assessment: "EVALUATION_FAILED"
- Warning in report
- No blocking of other analyses

---

## 6. Comprehensive Report Orchestration

### Methodology

Unify all analysis outputs into single weekly trending report.

### Report Structure

```markdown
# Skill Trending Report - YYYY-MM-DD

## 📊 Summary
- Total Skills Analyzed: X
- New Skills Found: Y
- Fast Growing Skills: Z
- Replacement Candidates: W
- Security Assessments: V

## 🆕 New Skills (Top 10)
[From analyze_new_skills.py]

## 🔥 Fastest Growing Skills (Top 10)
[From analyze_growth_rates.py]

## 🔄 Replacement Recommendations (Top 10)
[From analyze_replacements.py]

## 🛡️ Security Assessments (Top 10)
[From evaluate_security.py]

## 📈 Statistics
[Aggregate metrics]
```

### Implementation

See `scripts/analyze_comprehensive.py` for complete orchestration logic.

---

## Related Documentation

- **skill-manager API Guide**: `skill-manager-api-guide.md` - Data source details
- **GitHub API Guide**: `github-api-guide.md` - Star history fetching
- **Similarity Algorithms**: `similarity-algorithms.md` - Deep dive into TF-IDF
- **Troubleshooting**: `troubleshooting.md` - Common issues and solutions

---

**End of Guide**
