# Codex Task L1: ML-based Skill Recommendations

## Priority
Low (v2.0+)

## Objective
Create a personalized skill recommendation system using multi-factor scoring based on existing infrastructure.

## Context
- Already have TF-IDF similarity in `scripts/analyze_similarity.py`
- Already have multi-factor scoring in `scripts/analyze_replacements.py`
- Need to combine these with user preferences for personalized recommendations

---

## CRITICAL: Existing Code Integration Points

### 1. `scripts/fetch_skill_manager.py` - Data Loading

**MUST use these functions (DO NOT reimplement)**:

```python
from fetch_skill_manager import fetch_all_skills, get_installed_skills

# Load skills (returns tuple of list and stats dict)
skills, stats = fetch_all_skills(min_stars=50, max_months_old=6)
# skills = List[Dict] with keys: name, description, stars, forks, updated_at, author, github_url, tags, category

# Get installed skill names
installed_skills = get_installed_skills()
# Returns: List[str] of skill names
```

### 2. `scripts/parse_skill_manager.py` - DataFrame Conversion

**MUST use this function (DO NOT reimplement)**:

```python
from parse_skill_manager import parse_skill_manager_response

# Convert to DataFrame
skills_df = parse_skill_manager_response(skills)
# Returns DataFrame with columns: name, description, stars, forks, updated_at, author, github_url, tags, category
# - updated_at is already parsed as datetime
# - stars/forks are int
```

### 3. `scripts/analyze_similarity.py` - TF-IDF Similarity

**MUST use this function (DO NOT reimplement)**:

```python
from analyze_similarity import calculate_skill_similarity

# Calculate similarity between skills
similarity_df = calculate_skill_similarity(
    skills_df,                    # DataFrame from parse_skill_manager_response
    similarity_threshold=0.3,     # Lower threshold to get more pairs
    installed_skills=installed_skills  # Optional: filter for installed skills
)
# Returns DataFrame with columns:
#   skill1_name, skill2_name, similarity_score,
#   skill1_stars, skill2_stars, skill1_author, skill2_author,
#   skill1_description, skill2_description
```

**IMPORTANT**: The TF-IDF vectorizer settings in analyze_similarity.py:
- `max_features=500`
- `stop_words='english'`
- `ngram_range=(1, 2)` - includes bigrams
- `min_df=1, max_df=0.8`

---

## Requirements

### 1. Create `scripts/analyze_recommendations.py`

**File location**: `scripts/analyze_recommendations.py`

**Imports (EXACT - copy these)**:
```python
#!/usr/bin/env python3
"""
ML-based personalized skill recommendations.
Combines TF-IDF similarity, quality signals, and user preferences.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Set
from datetime import datetime
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from fetch_skill_manager import fetch_all_skills, get_installed_skills
from parse_skill_manager import parse_skill_manager_response
from analyze_similarity import calculate_skill_similarity

logger = logging.getLogger(__name__)
```

---

### Function 1: `calculate_recommendation_score()`

**Signature**:
```python
def calculate_recommendation_score(
    skill: pd.Series,
    installed_skills: List[str],
    similarity_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> float:
```

**Parameters**:
- `skill`: A single row from skills DataFrame (pd.Series)
  - Access values with: `skill.get('stars', 0)`, `skill.get('updated_at')`, `skill.get('name', '')`
- `installed_skills`: List of installed skill names (used for category matching)
- `similarity_scores`: Dict mapping skill name → max similarity to any installed skill
  - Example: `{'skill-a': 0.85, 'skill-b': 0.62}`
- `weights`: Optional custom weights dict, must sum to 1.0

**Default weights**:
```python
weights = {
    'popularity': 0.25,
    'recency': 0.20,
    'similarity': 0.30,
    'category': 0.15,
    'momentum': 0.10
}
```

**Scoring formulas** (implement EXACTLY):

```python
# 1. Popularity score (normalized log stars)
# Log scale: 10 stars = 0.3, 100 = 0.6, 1000 = 0.9, 10000 = 1.0
stars = skill.get('stars', 0)
popularity_score = min(np.log10(max(stars, 1)) / 4, 1.0)

# 2. Recency score (0 days = 1.0, 365 days = 0.0)
updated_at = skill.get('updated_at')
if pd.isna(updated_at):
    recency_score = 0.0
else:
    days_old = (datetime.now() - updated_at).days
    recency_score = max(1.0 - (days_old / 365), 0.0)

# 3. Similarity score (from pre-calculated similarity_scores dict)
skill_name = skill.get('name', '')
similarity_score = similarity_scores.get(skill_name, 0.0)

# 4. Category match score (use similarity as proxy, boost slightly)
category_score = min(similarity_score * 1.2, 1.0)

# 5. Momentum score (placeholder - use recency as proxy for now)
momentum_score = recency_score

# Final weighted score
final_score = (
    weights['popularity'] * popularity_score +
    weights['recency'] * recency_score +
    weights['similarity'] * similarity_score +
    weights['category'] * category_score +
    weights['momentum'] * momentum_score
)

return final_score
```

**Returns**: float between 0.0 and 1.0

---

### Function 2: `get_personalized_recommendations()`

**Signature**:
```python
def get_personalized_recommendations(
    all_skills_df: pd.DataFrame,
    installed_skills: Optional[List[str]] = None,
    exclude_installed: bool = True,
    min_stars: int = 50,
    max_results: int = 20,
    similarity_threshold: float = 0.3
) -> pd.DataFrame:
```

**Parameters**:
- `all_skills_df`: DataFrame with all available skills (from parse_skill_manager_response)
- `installed_skills`: List of installed skill names (auto-detected if None using `get_installed_skills()`)
- `exclude_installed`: Whether to exclude already installed skills from recommendations
- `min_stars`: Minimum stars to consider
- `max_results`: Maximum number of recommendations to return
- `similarity_threshold`: Minimum similarity to consider (for calculate_skill_similarity call)

**Implementation steps**:

```python
logger.info("Generating personalized recommendations...")

# Step 1: Get installed skills if not provided
if installed_skills is None:
    installed_skills = get_installed_skills()
    logger.info(f"Auto-detected {len(installed_skills)} installed skills")

installed_set = set(installed_skills)

# Step 2: Filter by min_stars
candidates = all_skills_df[all_skills_df['stars'] >= min_stars].copy()
logger.info(f"Filtered to {len(candidates)} candidates with >= {min_stars} stars")

# Step 3: Exclude installed if requested
if exclude_installed:
    candidates = candidates[~candidates['name'].isin(installed_set)]
    logger.info(f"After excluding installed: {len(candidates)} candidates")

if candidates.empty:
    logger.warning("No candidates available for recommendations")
    return pd.DataFrame()

# Step 4: Calculate similarity to installed skills
# IMPORTANT: Need to include both candidates AND installed skills in the similarity calculation
logger.info("Calculating similarity scores...")
skills_for_similarity = pd.concat([
    candidates,
    all_skills_df[all_skills_df['name'].isin(installed_set)]
])

similarity_df = calculate_skill_similarity(
    skills_for_similarity,
    similarity_threshold=similarity_threshold,
    installed_skills=installed_skills
)

# Step 5: Build similarity lookup: skill_name -> max similarity to any installed skill
similarity_lookup = {}
if not similarity_df.empty:
    for _, row in similarity_df.iterrows():
        skill1, skill2 = row['skill1_name'], row['skill2_name']
        score = row['similarity_score']

        # If one is installed and other is candidate
        if skill1 in installed_set and skill2 not in installed_set:
            similarity_lookup[skill2] = max(similarity_lookup.get(skill2, 0), score)
        elif skill2 in installed_set and skill1 not in installed_set:
            similarity_lookup[skill1] = max(similarity_lookup.get(skill1, 0), score)

logger.info(f"Found similarity scores for {len(similarity_lookup)} candidates")

# Step 6: Calculate recommendation score for each candidate
recommendations = []
for _, skill in candidates.iterrows():
    score = calculate_recommendation_score(
        skill,
        installed_skills,
        similarity_lookup
    )

    sim_score = similarity_lookup.get(skill['name'], 0.0)

    # Generate reason based on score components
    if sim_score > 0.7:
        reason = f"Very similar to your installed skills (similarity: {sim_score:.2f})"
    elif sim_score > 0.5:
        reason = f"Related to your installed skills (similarity: {sim_score:.2f})"
    elif skill['stars'] > 500:
        reason = f"Popular in community ({skill['stars']:,} stars)"
    else:
        reason = "Trending and well-maintained"

    # Truncate description to 150 chars
    desc = skill.get('description', '')
    if len(desc) > 150:
        desc = desc[:150] + '...'

    recommendations.append({
        'name': skill['name'],
        'recommendation_score': score,
        'stars': skill['stars'],
        'author': skill.get('author', ''),
        'description': desc,
        'similarity_to_installed': sim_score,
        'updated_at': skill.get('updated_at'),
        'reason': reason
    })

# Step 7: Convert to DataFrame and sort
result_df = pd.DataFrame(recommendations)
result_df = result_df.sort_values('recommendation_score', ascending=False)
result_df = result_df.head(max_results).reset_index(drop=True)

logger.info(f"Generated {len(result_df)} personalized recommendations")

return result_df
```

**Returns**: DataFrame with columns:
- `name`: str
- `recommendation_score`: float (0.0-1.0)
- `stars`: int
- `author`: str
- `description`: str (truncated to 150 chars)
- `similarity_to_installed`: float
- `updated_at`: datetime
- `reason`: str (why recommended)

---

### Function 3: `format_recommendations_report()`

**Signature**:
```python
def format_recommendations_report(
    recommendations_df: pd.DataFrame,
    top_n: int = 10
) -> str:
```

**Implementation**:
```python
if recommendations_df.empty:
    return "No personalized recommendations available"

lines = [
    f"## 🎯 Personalized Skill Recommendations\n",
    f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
    "### Scoring Formula\n",
    "| Factor | Weight | Description |",
    "|--------|--------|-------------|",
    "| Similarity | 30% | Match to installed skills |",
    "| Popularity | 25% | Community stars (log scale) |",
    "| Recency | 20% | Days since last update |",
    "| Category | 15% | Topic overlap |",
    "| Momentum | 10% | Growth trend |",
    "",
    f"### Top {min(top_n, len(recommendations_df))} Recommendations\n"
]

for idx, rec in recommendations_df.head(top_n).iterrows():
    lines.append(f"#### {idx + 1}. {rec['name']}")
    lines.append(f"- **Score:** {rec['recommendation_score']:.3f}")
    lines.append(f"- **Stars:** {rec['stars']:,} ⭐")
    lines.append(f"- **Author:** {rec['author']}")
    lines.append(f"- **Why:** {rec['reason']}")
    lines.append(f"- **Description:** {rec['description']}")
    lines.append("")

return "\n".join(lines)
```

---

### Main block for testing

```python
# Main for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 70)
    print("ML-BASED RECOMMENDATIONS - Test")
    print("=" * 70)

    try:
        # Fetch skills
        print("\n1. Fetching skills...")
        skills, _ = fetch_all_skills(min_stars=50, max_months_old=6)
        df = parse_skill_manager_response(skills)
        print(f"   Loaded {len(df)} skills")

        # Get recommendations
        print("\n2. Generating recommendations...")
        recommendations = get_personalized_recommendations(
            df,
            min_stars=50,
            max_results=10,
            similarity_threshold=0.3
        )

        print(f"   Generated {len(recommendations)} recommendations")

        # Format report
        print("\n3. Formatting report...")
        report = format_recommendations_report(recommendations)
        print("\n" + report)

        print("\n✅ Test completed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

## 2. Create Tests

### File: `tests/test_recommendations.py`

```python
#!/usr/bin/env python3
"""Tests for ML-based recommendations."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analyze_recommendations import (
    calculate_recommendation_score,
    get_personalized_recommendations,
    format_recommendations_report
)


# ============================================================
# Test Fixtures (local to this file)
# ============================================================

@pytest.fixture
def sample_skill():
    """Sample skill data as pd.Series."""
    return pd.Series({
        'name': 'test-skill',
        'stars': 100,
        'author': 'test-author',
        'description': 'A test skill for testing',
        'updated_at': datetime.now() - timedelta(days=30)
    })


@pytest.fixture
def sample_skills_df():
    """Sample skills DataFrame with 5 skills."""
    return pd.DataFrame([
        {
            'name': 'skill-a',
            'stars': 500,
            'author': 'author-a',
            'description': 'Code review and linting tool for Python',
            'updated_at': datetime.now() - timedelta(days=10)
        },
        {
            'name': 'skill-b',
            'stars': 200,
            'author': 'author-b',
            'description': 'Testing framework helper for Jest',
            'updated_at': datetime.now() - timedelta(days=60)
        },
        {
            'name': 'skill-c',
            'stars': 1000,
            'author': 'author-c',
            'description': 'Documentation generator for APIs',
            'updated_at': datetime.now() - timedelta(days=5)
        },
        {
            'name': 'installed-skill-1',
            'stars': 300,
            'author': 'author-d',
            'description': 'Code review tool for JavaScript',
            'updated_at': datetime.now() - timedelta(days=20)
        },
        {
            'name': 'installed-skill-2',
            'stars': 150,
            'author': 'author-e',
            'description': 'Testing utilities for Python pytest',
            'updated_at': datetime.now() - timedelta(days=40)
        }
    ])


# ============================================================
# Tests for calculate_recommendation_score
# ============================================================

def test_calculate_recommendation_score_basic(sample_skill):
    """Test basic recommendation score calculation."""
    score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.5}
    )

    assert 0.0 <= score <= 1.0, "Score must be between 0 and 1"
    assert isinstance(score, float), "Score must be float"


def test_calculate_recommendation_score_high_similarity(sample_skill):
    """Test that high similarity increases score."""
    low_sim_score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.1}
    )

    high_sim_score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.9}
    )

    assert high_sim_score > low_sim_score, "Higher similarity should increase score"


def test_calculate_recommendation_score_high_stars():
    """Test that high stars increases score."""
    low_star_skill = pd.Series({
        'name': 'low-star-skill',
        'stars': 10,
        'updated_at': datetime.now()
    })

    high_star_skill = pd.Series({
        'name': 'high-star-skill',
        'stars': 1000,
        'updated_at': datetime.now()
    })

    low_score = calculate_recommendation_score(
        low_star_skill,
        installed_skills=[],
        similarity_scores={}
    )

    high_score = calculate_recommendation_score(
        high_star_skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert high_score > low_score, "Higher stars should increase score"


def test_calculate_recommendation_score_recent_update():
    """Test that recent updates increase score."""
    old_skill = pd.Series({
        'name': 'old-skill',
        'stars': 100,
        'updated_at': datetime.now() - timedelta(days=300)
    })

    new_skill = pd.Series({
        'name': 'new-skill',
        'stars': 100,
        'updated_at': datetime.now() - timedelta(days=7)
    })

    old_score = calculate_recommendation_score(
        old_skill,
        installed_skills=[],
        similarity_scores={}
    )

    new_score = calculate_recommendation_score(
        new_skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert new_score > old_score, "More recent update should increase score"


def test_calculate_recommendation_score_custom_weights(sample_skill):
    """Test custom weights."""
    # All weight on popularity
    score = calculate_recommendation_score(
        sample_skill,
        installed_skills=[],
        similarity_scores={},
        weights={
            'popularity': 1.0,
            'recency': 0.0,
            'similarity': 0.0,
            'category': 0.0,
            'momentum': 0.0
        }
    )

    assert 0.0 <= score <= 1.0, "Score with custom weights must be in range"


def test_calculate_recommendation_score_missing_updated_at():
    """Test handling of missing updated_at."""
    skill = pd.Series({
        'name': 'skill-no-date',
        'stars': 100,
        'updated_at': None  # Missing date
    })

    score = calculate_recommendation_score(
        skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert 0.0 <= score <= 1.0, "Should handle missing updated_at gracefully"


# ============================================================
# Tests for get_personalized_recommendations
# ============================================================

def test_get_personalized_recommendations_returns_dataframe(sample_skills_df):
    """Test that function returns a DataFrame."""
    # Mock installed skills
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1', 'installed-skill-2'],
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    assert isinstance(result, pd.DataFrame), "Must return DataFrame"


def test_get_personalized_recommendations_excludes_installed(sample_skills_df):
    """Test that installed skills are excluded."""
    installed = ['installed-skill-1', 'installed-skill-2']

    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=installed,
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    # Check no installed skills in results
    for name in installed:
        assert name not in result['name'].values, f"Installed skill {name} should be excluded"


def test_get_personalized_recommendations_respects_max_results(sample_skills_df):
    """Test that max_results is respected."""
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=50,
        max_results=2  # Only want 2 results
    )

    assert len(result) <= 2, "Should respect max_results"


def test_get_personalized_recommendations_sorted_by_score(sample_skills_df):
    """Test that results are sorted by recommendation_score descending."""
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    if len(result) > 1:
        scores = result['recommendation_score'].tolist()
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"


def test_get_personalized_recommendations_empty_candidates(sample_skills_df):
    """Test handling when no candidates pass filters."""
    # Use very high min_stars to filter out everything
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=10000,  # Very high threshold
        max_results=10
    )

    assert isinstance(result, pd.DataFrame), "Should return empty DataFrame, not None"
    assert len(result) == 0, "Should have no results"


# ============================================================
# Tests for format_recommendations_report
# ============================================================

def test_format_recommendations_report_basic():
    """Test report formatting with valid data."""
    recommendations = pd.DataFrame([
        {
            'name': 'skill-a',
            'recommendation_score': 0.85,
            'stars': 500,
            'author': 'author-a',
            'description': 'Test description',
            'similarity_to_installed': 0.7,
            'reason': 'Similar to installed'
        }
    ])

    report = format_recommendations_report(recommendations)

    assert 'Personalized Skill Recommendations' in report
    assert 'skill-a' in report
    assert '0.85' in report or '.850' in report  # Score formatting may vary
    assert '500' in report  # Stars


def test_format_recommendations_report_empty():
    """Test empty recommendations handling."""
    report = format_recommendations_report(pd.DataFrame())

    assert 'No personalized recommendations' in report


def test_format_recommendations_report_respects_top_n():
    """Test that top_n parameter is respected."""
    recommendations = pd.DataFrame([
        {'name': f'skill-{i}', 'recommendation_score': 0.9 - i*0.1,
         'stars': 100, 'author': 'author', 'description': 'desc',
         'similarity_to_installed': 0.5, 'reason': 'test'}
        for i in range(5)
    ])

    report = format_recommendations_report(recommendations, top_n=2)

    assert 'skill-0' in report
    assert 'skill-1' in report
    # skill-2, skill-3, skill-4 should NOT be in report
    assert 'skill-4' not in report


def test_format_recommendations_report_contains_scoring_table():
    """Test that report contains scoring formula table."""
    recommendations = pd.DataFrame([
        {'name': 'skill-a', 'recommendation_score': 0.85,
         'stars': 500, 'author': 'author', 'description': 'desc',
         'similarity_to_installed': 0.7, 'reason': 'test'}
    ])

    report = format_recommendations_report(recommendations)

    assert 'Scoring Formula' in report
    assert 'Similarity' in report
    assert '30%' in report
    assert 'Popularity' in report
    assert '25%' in report
```

---

## 3. Testing Commands

```bash
cd skill-trending-monitor-cskill

# Run new tests
python3 -m pytest tests/test_recommendations.py -v

# Test standalone script
python3 scripts/analyze_recommendations.py

# Run all tests to ensure no regressions
python3 -m pytest tests/ -v
```

---

## 4. Acceptance Criteria Checklist

- [ ] `scripts/analyze_recommendations.py` created with all 3 functions
- [ ] `tests/test_recommendations.py` created with 12+ tests
- [ ] All tests pass: `python3 -m pytest tests/test_recommendations.py -v`
- [ ] Standalone test works: `python3 scripts/analyze_recommendations.py`
- [ ] No import errors from existing modules
- [ ] Existing tests still pass: `python3 -m pytest tests/ -v`

---

## Dependencies

**Existing modules (MUST import, NOT reimplement)**:
- `fetch_skill_manager.py` - `fetch_all_skills()`, `get_installed_skills()`
- `parse_skill_manager.py` - `parse_skill_manager_response()`
- `analyze_similarity.py` - `calculate_skill_similarity()`

**External dependencies (already in requirements.txt)**:
- pandas
- numpy
- scikit-learn (for TF-IDF in analyze_similarity.py)

**No new external dependencies required**

---

## Notes for Codex

1. **DO NOT modify** existing files (`analyze_similarity.py`, `fetch_skill_manager.py`, etc.)
2. **DO NOT reimplement** functions that already exist - import them
3. **Copy the exact function signatures** provided above
4. **Use the exact import pattern** at the top of the file
5. If `get_installed_skills()` returns empty list, that's OK - the code handles it
6. The TF-IDF similarity calculation may be slow with many skills - that's expected
7. If tests fail due to mock data issues, check that fixtures match expected schema

---

## Post-Implementation: Code Review Checklist

After Codex completes, Claude will review:

1. **Imports correct?** - Using existing modules, not reimplementing
2. **Function signatures match?** - Parameters and return types as specified
3. **Scoring formula correct?** - Weights sum to 1.0, formulas as specified
4. **Error handling?** - Empty DataFrames, missing fields handled gracefully
5. **Tests comprehensive?** - All edge cases covered
6. **Integration works?** - Standalone script runs without errors
