# Codex Task: Fix Test Import Errors

## Priority
CRITICAL - Tests cannot run due to import errors

## Objective
Fix all 5 test files that have import errors by aligning import statements with actual exported functions.

## Context
- Tests were written based on expected function signatures
- Implementation uses different function names
- All 5 test files fail at collection time due to `ImportError`

---

## Error Summary

| Test File | Import Error | Root Cause |
|-----------|--------------|------------|
| `test_analyze.py` | `filter_new_skills`, `apply_quality_filters` not found | Functions don't exist in `analyze_new_skills.py` |
| `test_analyze.py` | `calculate_similarity_scores` not found | Function is `calculate_skill_similarity` |
| `test_helpers.py` | `get_current_skill_year`, etc. not found | Functions don't exist in `helpers.py` |
| `test_integration.py` | `analyze_similarity` not found | Function is `calculate_skill_similarity` |
| `test_parse.py` | `parse_skills` module not found | Module is `parse_skill_manager.py` |
| `test_validation.py` | `validate_entity` not found | Function doesn't exist |

---

## CRITICAL: Actual Function Signatures

### 1. `scripts/analyze_new_skills.py`

**Exported functions:**
```python
def analyze_new_skills(
    min_stars: int = 50,
    max_months_old: int = 6,
    include_installed: bool = False
) -> Dict[str, Any]:
    """Discover high-quality skills not locally installed."""

def filter_by_category(
    skills_df: pd.DataFrame,
    categories: List[str]
) -> pd.DataFrame:
    """Filter skills by category."""

def filter_by_tags(
    skills_df: pd.DataFrame,
    tags: List[str],
    match_all: bool = False
) -> pd.DataFrame:
    """Filter skills by tags."""

def format_new_skills_report(results: Dict[str, Any]) -> str:
    """Format new skills as Markdown report."""

def export_new_skills_report(results: Dict[str, Any], output_path: str) -> None:
    """Export report to file."""
```

**NOT exported (tests expect these but they don't exist):**
- ❌ `filter_new_skills` → Use `analyze_new_skills` instead
- ❌ `apply_quality_filters` → Quality filtering is internal to `analyze_new_skills`

---

### 2. `scripts/analyze_similarity.py`

**Exported functions:**
```python
def calculate_skill_similarity(
    skills_df: pd.DataFrame,
    similarity_threshold: float = 0.75,
    installed_skills: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Calculate cosine similarity between skills using TF-IDF.

    Returns:
        DataFrame with columns: skill1_name, skill2_name, similarity_score,
                                skill1_stars, skill2_stars, skill1_author, skill2_author
    """

def find_alternatives(
    target_skill_name: str,
    skills_df: pd.DataFrame,
    similarity_threshold: float = 0.75
) -> List[Dict[str, Any]]:
    """Find similar alternatives to a specific skill."""

def aggregate_similarity_clusters(similarity_df: pd.DataFrame) -> List[List[str]]:
    """Group similar skills into clusters."""

def format_similarity_report(similarity_df: pd.DataFrame) -> str:
    """Format similarity results as Markdown."""
```

**NOT exported:**
- ❌ `analyze_similarity` → Use `calculate_skill_similarity`
- ❌ `calculate_similarity_scores` → Use `calculate_skill_similarity`

---

### 3. `scripts/utils/helpers.py`

**Exported functions:**
```python
def get_current_week() -> Tuple[datetime, datetime]:
    """Get start and end of current week."""

def get_week_number(date: Optional[datetime] = None) -> int:
    """Get ISO week number."""

def get_week_with_fallback(week: Optional[int] = None) -> Tuple[int, int]:
    """Get week with fallback to previous week. Returns (week, year)."""

def should_try_previous_week(
    week: int,
    current_data_count: int = 0,
    min_data_threshold: int = 10
) -> bool:
    """Determine if should try previous week due to insufficient data."""

def format_week_message(week_used: int, week_requested: Optional[int]) -> str:
    """Format message about which week is being used."""

def get_week_date_range(week: int, year: Optional[int] = None) -> Tuple[datetime, datetime]:
    """Get date range for a specific week."""

def format_iso_week(week: int, year: Optional[int] = None) -> str:
    """Format week as ISO string."""

def parse_iso_week(iso_week: str) -> Tuple[int, int]:
    """Parse ISO week string to (week, year)."""

def get_weeks_ago(weeks: int) -> int:
    """Get week number for N weeks ago."""
```

**NOT exported (tests expect these but they don't exist):**
- ❌ `get_current_skill_year` → Helpers use WEEK, not YEAR
- ❌ `get_skill_year_with_fallback` → Use `get_week_with_fallback` (week-based)
- ❌ `should_try_previous_year` → Use `should_try_previous_week`
- ❌ `format_year_message` → Use `format_week_message`
- ❌ `parse_skill_date` → Not implemented
- ❌ `normalize_date_format` → Not implemented

---

### 4. `scripts/parse_skill_manager.py`

**Exported functions:**
```python
def parse_skill_manager_response(skills: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert skill-manager JSON to DataFrame.

    Returns DataFrame with columns:
        name, description, stars, forks, updated_at, author, github_url, tags, category
    """

def validate_skill_schema(skill: Dict[str, Any]) -> bool:
    """Validate a single skill has required fields."""

def extract_skill_metadata(skill: Dict[str, Any]) -> Dict[str, Any]:
    """Extract standardized metadata from skill."""
```

**NOT exported:**
- ❌ `parse_github_response` → This is in `parse_github_stars.py`, not `parse_skill_manager.py`

---

### 5. `scripts/parse_github_stars.py`

**Exported functions:**
```python
def parse_github_repo_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse GitHub repository API response."""

def parse_star_history(commits: List[Dict[str, Any]]) -> List[Tuple[datetime, int]]:
    """Parse commit history to star timeline."""

def calculate_growth_rate(
    current_stars: int,
    previous_stars: int
) -> float:
    """Calculate percentage growth rate."""
```

---

### 6. `scripts/analyze_growth_rates.py`

**Exported functions:**
```python
def analyze_growth_rates(
    skills_df: pd.DataFrame,
    time_window_days: int = 7
) -> Dict[str, Any]:
    """Analyze week-over-week growth rates."""

def calculate_skill_growth(
    skill_name: str,
    github_url: str,
    time_window_days: int = 7
) -> Optional[Dict[str, Any]]:
    """Calculate growth for a single skill."""

def format_growth_report(results: Dict[str, Any]) -> str:
    """Format growth rates as Markdown."""
```

---

### 7. `scripts/analyze_replacements.py`

**Exported functions:**
```python
def analyze_replacements(
    installed_skills_dir: str,
    confidence_threshold: float = 0.70
) -> Dict[str, Any]:
    """Find replacement recommendations for installed skills."""

def calculate_replacement_score(
    installed: Dict[str, Any],
    candidate: Dict[str, Any],
    similarity_score: float,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Calculate multi-factor replacement confidence score."""

def format_replacements_report(results: Dict[str, Any]) -> str:
    """Format replacements as Markdown."""
```

**NOT exported:**
- ❌ `calculate_replacement_confidence` → Use `calculate_replacement_score`

---

### 8. `scripts/evaluate_security.py`

**Exported functions:**
```python
def evaluate_security(
    skills_df: pd.DataFrame,
    threshold: int = 70
) -> Dict[str, Any]:
    """Evaluate security scores for skills."""

def calculate_security_score(
    skill: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Calculate composite security score for a skill."""

def format_security_report(results: Dict[str, Any]) -> str:
    """Format security evaluation as Markdown."""
```

---

### 9. `scripts/utils/validators/parameter_validator.py`

**Exported functions:**
```python
def validate_year(year: Optional[int]) -> Tuple[bool, str]:
    """Validate year parameter."""

def validate_threshold(threshold: float, min_val: float = 0.0, max_val: float = 1.0) -> Tuple[bool, str]:
    """Validate threshold parameter."""

def validate_path(path: str, must_exist: bool = True) -> Tuple[bool, str]:
    """Validate file/directory path."""

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate configuration dictionary."""
```

**NOT exported:**
- ❌ `validate_entity` → Not implemented
- ❌ `validate_year_range` → Not implemented
- ❌ `validate_filter_profile` → Not implemented

---

### 10. `scripts/utils/cache_manager.py`

**Exported:**
```python
class CacheManager:
    def __init__(self, cache_dir: str = ".cache"):
        ...

    def get(self, key: str) -> Optional[Any]:
        ...

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        ...

    def clear(self) -> None:
        ...

def generate_cache_key(*args) -> str:
    """Generate cache key from arguments."""
```

---

### 11. `scripts/utils/rate_limiter.py`

**Exported:**
```python
class RateLimiter:
    def __init__(self, max_requests: int = 60, time_window: int = 3600):
        ...

    def acquire(self, wait: bool = True) -> bool:
        ...

    def reset(self) -> None:
        ...
```

---

## Requirements

### Fix Strategy: TWO OPTIONS

**Option A (Recommended): Update tests to match actual implementation**

Tests should be rewritten to use actual function names and signatures.

**Option B: Add wrapper functions to implementation**

NOT recommended - would add complexity without value.

---

## Files to Modify

### 1. `tests/test_analyze.py`

**Current (broken):**
```python
from analyze_new_skills import filter_new_skills, apply_quality_filters
from analyze_growth_rates import calculate_growth_rate
from analyze_similarity import calculate_similarity_scores
from analyze_replacements import calculate_replacement_confidence
from evaluate_security import calculate_security_score
```

**Fixed:**
```python
from analyze_new_skills import analyze_new_skills, filter_by_category, filter_by_tags
from analyze_growth_rates import analyze_growth_rates, calculate_skill_growth
from analyze_similarity import calculate_skill_similarity, find_alternatives
from analyze_replacements import analyze_replacements, calculate_replacement_score
from evaluate_security import evaluate_security, calculate_security_score
```

**Test function changes:**

1. `test_filter_new_skills()` → `test_analyze_new_skills()`
   - Use `analyze_new_skills()` instead of `filter_new_skills()`
   - Adjust parameters and assertions

2. `test_quality_filters()` → Remove or rewrite
   - Quality filtering is internal, test via `analyze_new_skills(min_stars=X)`

3. `test_growth_rate_calculation()` → Keep, use `parse_github_stars.calculate_growth_rate()`
   - Import from correct module

4. `test_similarity_calculation()` → `test_skill_similarity()`
   - Use `calculate_skill_similarity()` instead of `calculate_similarity_scores()`

5. `test_replacement_confidence()` → Keep, use `calculate_replacement_score()`
   - Adjust parameters

6. `test_security_score_calculation()` → Keep, adjust parameters

---

### 2. `tests/test_helpers.py`

**Current (broken):**
```python
from utils.helpers import (
    get_current_skill_year,
    get_skill_year_with_fallback,
    should_try_previous_year,
    format_year_message
)
```

**Fixed:**
```python
from utils.helpers import (
    get_current_week,
    get_week_number,
    get_week_with_fallback,
    should_try_previous_week,
    format_week_message,
    get_week_date_range,
    format_iso_week,
    parse_iso_week
)
```

**Test function changes:**

1. `test_get_current_year()` → `test_get_current_week()`
   - Use `get_current_week()` and `get_week_number()`

2. `test_year_with_fallback()` → `test_week_with_fallback()`
   - Use `get_week_with_fallback()`
   - Returns `(week, year)` tuple

3. `test_should_try_previous_year()` → `test_should_try_previous_week()`
   - Use `should_try_previous_week()`
   - Different logic: based on data count, not month

4. `test_format_year_message()` → `test_format_week_message()`
   - Use `format_week_message()`

5. `test_date_parsing()` → Remove or implement parsing functions first
   - `parse_skill_date` and `normalize_date_format` don't exist

---

### 3. `tests/test_integration.py`

**Current (broken):**
```python
from analyze_similarity import analyze_similarity
```

**Fixed:**
```python
from analyze_similarity import calculate_skill_similarity, find_alternatives
```

**Test function changes:**

1. `test_analyze_similarity()` → Update to use `calculate_skill_similarity()`
   - Different parameters: `(skills_df, threshold)` not `(target_skill, skills_df, similarity_matrix)`

---

### 4. `tests/test_parse.py`

**Current (broken):**
```python
from parse_skills import parse_skill_manager_response, parse_github_response
```

**Fixed:**
```python
from parse_skill_manager import parse_skill_manager_response, validate_skill_schema
from parse_github_stars import parse_github_repo_response, parse_star_history
```

---

### 5. `tests/test_validation.py`

**Current (broken):**
```python
from utils.validators.parameter_validator import (
    validate_entity,
    validate_year_range,
    validate_filter_profile
)
```

**Fixed:**
```python
from utils.validators.parameter_validator import (
    validate_year,
    validate_threshold,
    validate_path,
    validate_config
)
```

**Test function changes:**

1. `test_validate_entity()` → `test_validate_year()` and `test_validate_threshold()`
2. `test_validate_year_range()` → Remove or rewrite for `validate_year()`
3. `test_validate_filter_profile()` → `test_validate_config()`

---

## Testing

After fixing, run:

```bash
cd skill-trending-monitor-cskill

# Test each file individually
python3 -m pytest tests/test_analyze.py -v --tb=short
python3 -m pytest tests/test_helpers.py -v --tb=short
python3 -m pytest tests/test_integration.py -v --tb=short
python3 -m pytest tests/test_parse.py -v --tb=short
python3 -m pytest tests/test_validation.py -v --tb=short

# Run all tests
python3 -m pytest tests/ -v --tb=short
```

---

## Acceptance Criteria

- [ ] `pytest tests/test_analyze.py --collect-only` → No import errors
- [ ] `pytest tests/test_helpers.py --collect-only` → No import errors
- [ ] `pytest tests/test_integration.py --collect-only` → No import errors
- [ ] `pytest tests/test_parse.py --collect-only` → No import errors
- [ ] `pytest tests/test_validation.py --collect-only` → No import errors
- [ ] `pytest tests/ -v` → All tests pass (or skip gracefully with fixtures)

---

## Notes for Codex

1. **DO NOT modify implementation files** - Only fix test files
2. **Match actual function signatures exactly** - Check imports match exports
3. **Preserve test intent** - Rewrite tests to test same functionality with correct functions
4. **Use existing fixtures from conftest.py** - `sample_skills_df`, `sample_config`, etc.
5. **Add `@pytest.mark.skip` if function truly doesn't exist** - Better than import error

---

## Post-Implementation: Code Review Checklist

After Codex completes, Claude will verify:

1. [ ] All import statements resolve correctly
2. [ ] Function signatures match actual implementation
3. [ ] Test logic still validates intended functionality
4. [ ] No hardcoded values that should use fixtures
5. [ ] Error messages are descriptive
6. [ ] All tests can be collected without errors
