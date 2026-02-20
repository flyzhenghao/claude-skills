# Validation System

This skill implements a comprehensive 4-layer validation system to ensure data quality and parameter correctness.

---

## Validation Architecture

```
User Input
    ↓
┌─────────────────────────────┐
│ Layer 1: Parameter Validator │
│ (Validate CLI arguments)     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 2: Data Validator      │
│ (Validate data structure)    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 3: Temporal Validator  │
│ (Validate time consistency)  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 4: Completeness Check  │
│ (Validate result coverage)   │
└─────────────────────────────┘
    ↓
Analysis Results
```

---

## Layer 1: Parameter Validator

**File**: `scripts/validators/parameter_validator.py`

**Purpose**: Validate CLI arguments and configuration parameters

### Validation Rules

#### 1. Similarity Threshold

```python
def validate_similarity_threshold(threshold: float) -> bool:
    """
    Valid range: 0.0 - 1.0
    Recommended: 0.75 (high similarity)
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Similarity threshold must be between 0.0 and 1.0, got {threshold}")

    if threshold < 0.5:
        warnings.warn("Threshold < 0.5 may produce too many false positives")

    return True
```

**Error Message**:
```
❌ Invalid threshold: 1.5

Similarity threshold must be between 0.0 and 1.0
Example: --similarity-threshold 0.75
```

---

#### 2. Growth Rate Threshold

```python
def validate_growth_threshold(threshold: float) -> bool:
    """
    Valid range: 0.0 - 100.0 (percentage)
    Default: 5.0 (5% WoW growth)
    """
    if not 0.0 <= threshold <= 100.0:
        raise ValueError(f"Growth threshold must be between 0.0 and 100.0, got {threshold}")

    return True
```

---

#### 3. Confidence Threshold

```python
def validate_confidence_threshold(threshold: float) -> bool:
    """
    Valid range: 0.0 - 1.0
    Recommended: 0.70 (high confidence)
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Confidence threshold must be between 0.0 and 1.0, got {threshold}")

    if threshold < 0.5:
        warnings.warn("Threshold < 0.5 may recommend low-quality replacements")

    return True
```

---

#### 4. Security Score Threshold

```python
def validate_security_threshold(threshold: int) -> bool:
    """
    Valid range: 0 - 100
    Default: 70 (good security)
    Recommended: 80 (excellent security)
    """
    if not 0 <= threshold <= 100:
        raise ValueError(f"Security threshold must be between 0 and 100, got {threshold}")

    return True
```

---

#### 5. Star Filters

```python
def validate_star_filters(min_stars: int, max_stars: int = None) -> bool:
    """
    Valid range: min_stars >= 0
    If max_stars specified: max_stars > min_stars
    """
    if min_stars < 0:
        raise ValueError(f"Minimum stars must be >= 0, got {min_stars}")

    if max_stars is not None and max_stars <= min_stars:
        raise ValueError(f"Max stars ({max_stars}) must be > min stars ({min_stars})")

    return True
```

---

#### 6. Date Ranges

```python
from datetime import datetime, timedelta

def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Valid format: YYYY-MM-DD
    Constraint: end_date >= start_date
    Constraint: start_date not in future
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}")

    if end < start:
        raise ValueError(f"End date ({end_date}) must be >= start date ({start_date})")

    if start > datetime.now():
        raise ValueError(f"Start date ({start_date}) cannot be in the future")

    return True
```

---

### Usage Example

```python
from validators.parameter_validator import ParameterValidator

validator = ParameterValidator()

# Validate all parameters at once
validator.validate_all(
    similarity_threshold=0.75,
    growth_threshold=5.0,
    confidence_threshold=0.70,
    security_threshold=70,
    min_stars=50,
    date_range=("2026-01-01", "2026-02-03")
)
```

---

## Layer 2: Data Validator

**File**: `scripts/validators/data_validator.py`

**Purpose**: Validate data structure and required fields

### Validation Rules

#### 1. Skill Data Structure

```python
def validate_skill_data(skill: dict) -> bool:
    """
    Required fields:
    - name (str)
    - description (str)
    - repository (str, valid GitHub URL)
    - stars (int, >= 0)
    - last_updated (str, YYYY-MM-DD format)
    """
    required_fields = ["name", "description", "repository", "stars", "last_updated"]

    for field in required_fields:
        if field not in skill:
            raise ValueError(f"Missing required field: {field}")

    # Type validation
    if not isinstance(skill["stars"], int) or skill["stars"] < 0:
        raise ValueError(f"Invalid stars value: {skill['stars']}")

    # Repository URL validation
    if not skill["repository"].startswith("https://github.com/"):
        raise ValueError(f"Invalid repository URL: {skill['repository']}")

    # Date format validation
    validate_date_format(skill["last_updated"])

    return True
```

---

#### 2. Database Integrity

```python
def validate_database_integrity(db_path: str) -> dict:
    """
    Returns ValidationReport with:
    - total_entries
    - valid_entries
    - invalid_entries
    - missing_fields_count
    - invalid_types_count
    - corrupted_urls_count
    """
    report = ValidationReport()

    with open(db_path) as f:
        data = json.load(f)

    report.total_entries = len(data["skills"])

    for skill in data["skills"]:
        try:
            validate_skill_data(skill)
            report.valid_entries += 1
        except ValueError as e:
            report.invalid_entries += 1
            report.add_issue(skill["name"], str(e))

    return report
```

**Output**:
```
⚠️ Data Validation Warnings:

- Missing 'last_updated' field in 5 skills (using 'unknown')
- Non-numeric 'stars' field in 2 skills (skipping)

✅ Validation passed with warnings
Processed: 31,760 / 31,767 skills (99.98%)
```

---

#### 3. API Response Validation

```python
def validate_github_api_response(response: dict) -> bool:
    """
    Validate GitHub API stargazer response
    """
    if not isinstance(response, list):
        raise ValueError("Expected list of stargazers")

    for stargazer in response:
        if "starred_at" not in stargazer:
            raise ValueError("Missing 'starred_at' field")

        # Validate ISO 8601 format
        try:
            datetime.fromisoformat(stargazer["starred_at"].replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid timestamp: {stargazer['starred_at']}")

    return True
```

---

## Layer 3: Temporal Validator

**File**: `scripts/validators/temporal_validator.py`

**Purpose**: Validate time-related consistency and logic

### Validation Rules

#### 1. Star History Consistency

```python
def validate_star_history(stargazers: list) -> bool:
    """
    Validate that star timestamps are in ascending order
    """
    timestamps = [s["starred_at"] for s in stargazers]

    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i-1]:
            raise ValueError(
                f"Star history out of order: "
                f"{timestamps[i-1]} followed by {timestamps[i]}"
            )

    return True
```

---

#### 2. Week-over-Week Calculation

```python
from datetime import datetime, timedelta

def validate_wow_calculation(
    this_week_count: int,
    last_week_count: int,
    week_start: datetime
) -> bool:
    """
    Validate WoW growth calculation inputs
    """
    # Week start must be a Monday
    if week_start.weekday() != 0:
        raise ValueError(f"Week start must be Monday, got {week_start.strftime('%A')}")

    # Star counts must be non-negative
    if this_week_count < 0 or last_week_count < 0:
        raise ValueError("Star counts cannot be negative")

    # Week start cannot be in the future
    if week_start > datetime.now():
        raise ValueError("Week start cannot be in the future")

    return True
```

---

#### 3. Cache Expiration Logic

```python
def validate_cache_expiration(
    cached_at: datetime,
    ttl_days: int,
    current_time: datetime = None
) -> bool:
    """
    Validate cache expiration logic
    """
    if current_time is None:
        current_time = datetime.now()

    expires_at = cached_at + timedelta(days=ttl_days)

    # Cache should not expire in the past (relative to cached_at)
    if expires_at < cached_at:
        raise ValueError("Cache expiration cannot be before cache creation")

    # Check if cache is stale
    is_stale = current_time > expires_at

    return not is_stale
```

---

#### 4. Update Recency

```python
def validate_update_recency(last_updated: str, max_age_days: int = 180) -> bool:
    """
    Validate that skill was updated within max_age_days
    Default: 180 days (6 months)
    """
    last_updated_date = datetime.strptime(last_updated, "%Y-%m-%d")
    age_days = (datetime.now() - last_updated_date).days

    if age_days > max_age_days:
        warnings.warn(
            f"Skill not updated in {age_days} days "
            f"(threshold: {max_age_days} days)"
        )
        return False

    return True
```

---

## Layer 4: Completeness Validator

**File**: `scripts/validators/completeness_validator.py`

**Purpose**: Validate that analysis results are complete and comprehensive

### Validation Rules

#### 1. Minimum Result Count

```python
def validate_result_count(
    results: list,
    min_count: int,
    analysis_type: str
) -> bool:
    """
    Ensure analysis returns sufficient results
    """
    if len(results) < min_count:
        warnings.warn(
            f"{analysis_type} returned only {len(results)} results "
            f"(expected >= {min_count}). "
            f"Consider adjusting filters or thresholds."
        )
        return False

    return True
```

**Example**:
```
⚠️ Growth rate analysis returned only 2 trending skills (expected >= 5)
Consider lowering growth_threshold from 5% to 3%
```

---

#### 2. Coverage Validation

```python
def validate_coverage(
    analyzed_skills: set,
    all_skills: set,
    min_coverage_percent: float = 80.0
) -> bool:
    """
    Ensure analysis covered sufficient portion of dataset
    """
    coverage = len(analyzed_skills) / len(all_skills) * 100

    if coverage < min_coverage_percent:
        warnings.warn(
            f"Analysis covered only {coverage:.1f}% of skills "
            f"(expected >= {min_coverage_percent}%)"
        )
        return False

    return True
```

---

#### 3. Quality Filter Validation

```python
def validate_quality_filters(
    filtered_count: int,
    total_count: int,
    filters: dict
) -> bool:
    """
    Ensure quality filters didn't remove too many skills
    """
    removal_rate = (total_count - filtered_count) / total_count * 100

    if removal_rate > 90:
        warnings.warn(
            f"Quality filters removed {removal_rate:.1f}% of skills. "
            f"Filters may be too strict: {filters}"
        )
        return False

    return True
```

**Example**:
```
⚠️ Quality filters removed 95.2% of skills
Filters may be too strict: {'min_stars': 500, 'max_age_days': 30}
Consider: {'min_stars': 50, 'max_age_days': 180}
```

---

#### 4. Missing Data Detection

```python
def validate_no_missing_data(results: list, required_fields: list) -> bool:
    """
    Ensure all results have required fields populated
    """
    missing_data = []

    for result in results:
        for field in required_fields:
            if field not in result or result[field] is None:
                missing_data.append((result.get("name", "unknown"), field))

    if missing_data:
        warnings.warn(
            f"Found {len(missing_data)} missing data points:\n" +
            "\n".join([f"  - {name}: missing {field}" for name, field in missing_data[:5]])
        )
        return False

    return True
```

---

## Validation Report

### Report Structure

```python
class ValidationReport:
    def __init__(self):
        self.total_entries = 0
        self.valid_entries = 0
        self.invalid_entries = 0
        self.warnings = []
        self.errors = []

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_error(self, message: str):
        self.errors.append(message)

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def to_markdown(self) -> str:
        """Generate Markdown report"""
        lines = ["# Validation Report", ""]
        lines.append(f"**Total Entries**: {self.total_entries}")
        lines.append(f"**Valid Entries**: {self.valid_entries}")
        lines.append(f"**Invalid Entries**: {self.invalid_entries}")
        lines.append("")

        if self.errors:
            lines.append("## ❌ Errors")
            for error in self.errors:
                lines.append(f"- {error}")
            lines.append("")

        if self.warnings:
            lines.append("## ⚠️ Warnings")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        if self.is_valid():
            lines.append("✅ **Validation Passed**")
        else:
            lines.append("❌ **Validation Failed**")

        return "\n".join(lines)
```

---

### Example Report

```markdown
# Validation Report

**Total Entries**: 31,767
**Valid Entries**: 31,760
**Invalid Entries**: 7

## ⚠️ Warnings

- Missing 'last_updated' field in 5 skills (using 'unknown')
- Non-numeric 'stars' field in 2 skills (skipping)
- Growth rate analysis returned only 3 trending skills (expected >= 5)
- Quality filters removed 85.2% of skills (consider adjusting)

✅ **Validation Passed**
```

---

## Usage in Scripts

### Comprehensive Validation

```python
from validators.parameter_validator import ParameterValidator
from validators.data_validator import DataValidator
from validators.temporal_validator import TemporalValidator
from validators.completeness_validator import CompletenessValidator

def run_analysis_with_validation(args):
    report = ValidationReport()

    # Layer 1: Parameters
    param_validator = ParameterValidator()
    try:
        param_validator.validate_all(
            similarity_threshold=args.similarity_threshold,
            growth_threshold=args.growth_threshold
        )
    except ValueError as e:
        report.add_error(f"Parameter validation failed: {e}")
        return report

    # Layer 2: Data
    data_validator = DataValidator()
    db_report = data_validator.validate_database_integrity(
        "~/.claude/skills/skill-manager/data/all_skills_with_cn.json"
    )
    report.merge(db_report)

    # Layer 3: Temporal
    temporal_validator = TemporalValidator()
    # ... validate time-related logic

    # Run analysis
    results = run_analysis(args)

    # Layer 4: Completeness
    completeness_validator = CompletenessValidator()
    if not completeness_validator.validate_result_count(results, min_count=5):
        report.add_warning("Insufficient results returned")

    return report
```

---

## Testing Validation

### Unit Tests

```bash
# Test parameter validation
pytest tests/test_parameter_validator.py

# Test data validation
pytest tests/test_data_validator.py

# Test temporal validation
pytest tests/test_temporal_validator.py

# Test completeness validation
pytest tests/test_completeness_validator.py
```

### Integration Tests

```bash
# Test with invalid parameters
python3 scripts/analyze_similarity.py --threshold 1.5
# Expected: ValueError with clear error message

# Test with corrupted database
echo "invalid json" > /tmp/corrupted_db.json
python3 scripts/analyze_new_skills.py --database /tmp/corrupted_db.json
# Expected: Graceful error handling with validation report

# Test with missing data
python3 scripts/analyze_growth_rates.py
# Expected: Warnings about missing star history, fallback to cached data
```

---

## Validation Best Practices

### 1. Fail Fast

Validate parameters **before** loading large datasets:

```python
# ✅ Good: Validate first
validate_parameters(args)
load_skill_manager_db()  # Expensive operation

# ❌ Bad: Load then validate
load_skill_manager_db()
validate_parameters(args)  # Wasted 3 seconds if invalid
```

---

### 2. Provide Actionable Error Messages

```python
# ❌ Bad
raise ValueError("Invalid threshold")

# ✅ Good
raise ValueError(
    f"Invalid threshold: {threshold}\n"
    f"Similarity threshold must be between 0.0 and 1.0\n"
    f"Example: --similarity-threshold 0.75"
)
```

---

### 3. Warnings vs Errors

- **Errors**: Block execution (invalid parameters, missing required data)
- **Warnings**: Log but continue (low result count, outdated data)

---

### 4. Validation Reports for Auditing

Save validation reports for debugging:

```python
report = run_analysis_with_validation(args)
report.save_to_file(f"meta/validation-reports/{datetime.now().isoformat()}.md")
```

---

**Last Updated**: 2026-02-03
**Skill Version**: 1.0.0
