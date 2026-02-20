#!/usr/bin/env python3
"""
Temporal validators for skill-trending-monitor-cskill.
Checks temporal consistency and data age.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List
from .data_validator import ValidationResult, ValidationReport, ValidationLevel


def validate_temporal_consistency(df: pd.DataFrame) -> ValidationReport:
    """
    Check temporal consistency in data.

    Validations:
    - No future dates
    - Years in valid range
    - No suspicious gaps in time series
    - Data age is acceptable

    Args:
        df: DataFrame with 'year' column

    Returns:
        ValidationReport

    Example:
        >>> report = validate_temporal_consistency(df)
        >>> if report.has_critical_issues():
        ...     print(report.get_summary())
    """
    report = ValidationReport()
    current_year = datetime.now().year

    if 'year' not in df.columns:
        report.add(ValidationResult(
            check_name="has_year_column",
            level=ValidationLevel.CRITICAL,
            passed=False,
            message="Missing 'year' column"
        ))
        return report

    # Check 1: No future years
    max_year = df['year'].max()
    report.add(ValidationResult(
        check_name="no_future_years",
        level=ValidationLevel.CRITICAL,
        passed=max_year <= current_year,
        message=f"Max year: {max_year} ({'valid' if max_year <= current_year else 'FUTURE!'})"
    ))

    # Check 2: Years in reasonable range
    min_year = df['year'].min()
    is_reasonable = min_year >= 1900
    report.add(ValidationResult(
        check_name="reasonable_year_range",
        level=ValidationLevel.WARNING,
        passed=is_reasonable,
        message=f"Year range: {min_year}-{max_year}"
    ))

    # Check 3: Data age (is data recent enough?)
    data_age_years = current_year - max_year
    is_recent = data_age_years <= 2
    report.add(ValidationResult(
        check_name="data_freshness",
        level=ValidationLevel.WARNING,
        passed=is_recent,
        message=f"Data age: {data_age_years} years ({'recent' if is_recent else 'STALE'})"
    ))

    # Check 4: No suspicious gaps in time series
    if len(df['year'].unique()) > 2:
        years_sorted = sorted(df['year'].unique())
        gaps = [
            years_sorted[i+1] - years_sorted[i]
            for i in range(len(years_sorted)-1)
        ]
        max_gap = max(gaps) if gaps else 0
        has_large_gap = max_gap > 2

        report.add(ValidationResult(
            check_name="no_large_gaps",
            level=ValidationLevel.WARNING,
            passed=not has_large_gap,
            message=f"Max gap: {max_gap} years" + (" (suspicious)" if has_large_gap else "")
        ))

    return report


def validate_week_number(week: int, year: int) -> ValidationResult:
    """
    Validate week number is in valid range for year.

    Args:
        week: ISO week number (1-53)
        year: Year

    Returns:
        ValidationResult

    Example:
        >>> result = validate_week_number(6, 2026)
        >>> assert result.passed
    """
    # Most data types use weeks 1-53
    is_valid = 1 <= week <= 53

    return ValidationResult(
        check_name="valid_week",
        level=ValidationLevel.CRITICAL,
        passed=is_valid,
        message=f"Week {week} ({'valid' if is_valid else 'INVALID: must be 1-53'})"
    )


def validate_week_boundaries(
    week_start: datetime,
    week_end: datetime
) -> ValidationReport:
    """
    Validate ISO week boundaries.

    Checks:
    - week_start is Monday
    - week_end is Sunday
    - week_end is exactly 6 days after week_start
    - Both use UTC timezone

    Args:
        week_start: Week start datetime (should be Monday 00:00 UTC)
        week_end: Week end datetime (should be Sunday 23:59 UTC)

    Returns:
        ValidationReport

    Example:
        >>> from datetime import datetime, timezone
        >>> start = datetime(2026, 2, 2, 0, 0, 0, tzinfo=timezone.utc)  # Monday
        >>> end = datetime(2026, 2, 8, 23, 59, 59, tzinfo=timezone.utc)  # Sunday
        >>> report = validate_week_boundaries(start, end)
        >>> assert report.all_passed()
    """
    report = ValidationReport()

    # Check 1: week_start is Monday (weekday 0)
    is_monday = week_start.weekday() == 0
    if is_monday:
        monday_message = "Week start is Monday"
    else:
        day_name = week_start.strftime('%A')
        monday_message = f"Week start is INVALID ({day_name})"

    report.add(ValidationResult(
        check_name="start_is_monday",
        level=ValidationLevel.CRITICAL,
        passed=is_monday,
        message=monday_message
    ))

    # Check 2: week_end is Sunday (weekday 6)
    is_sunday = week_end.weekday() == 6
    if is_sunday:
        sunday_message = "Week end is Sunday"
    else:
        day_name = week_end.strftime('%A')
        sunday_message = f"Week end is INVALID ({day_name})"

    report.add(ValidationResult(
        check_name="end_is_sunday",
        level=ValidationLevel.CRITICAL,
        passed=is_sunday,
        message=sunday_message
    ))

    # Check 3: week_end is 6 days after week_start
    expected_end = week_start + timedelta(days=6)
    is_correct_span = week_end.date() == expected_end.date()
    report.add(ValidationResult(
        check_name="correct_week_span",
        level=ValidationLevel.CRITICAL,
        passed=is_correct_span,
        message=f"Week span: {(week_end - week_start).days} days ({'valid (6)' if is_correct_span else 'INVALID'})"
    ))

    # Check 4: Both use UTC timezone
    has_utc_start = week_start.tzinfo is not None and week_start.tzinfo.utcoffset(week_start) == timedelta(0)
    has_utc_end = week_end.tzinfo is not None and week_end.tzinfo.utcoffset(week_end) == timedelta(0)
    both_utc = has_utc_start and has_utc_end

    report.add(ValidationResult(
        check_name="uses_utc",
        level=ValidationLevel.WARNING,
        passed=both_utc,
        message="Both dates use UTC" if both_utc else "WARN: Not using UTC timezone"
    ))

    return report


def validate_data_freshness(
    max_date: datetime,
    threshold_days: int = 180
) -> ValidationResult:
    """
    Validate data is fresh enough.

    Args:
        max_date: Most recent date in dataset
        threshold_days: Maximum age in days (default 180 = 6 months)

    Returns:
        ValidationResult

    Example:
        >>> from datetime import datetime, timezone
        >>> recent = datetime.now(timezone.utc)
        >>> result = validate_data_freshness(recent, threshold_days=180)
        >>> assert result.passed
    """
    now = datetime.now(max_date.tzinfo or None)
    age_days = (now - max_date).days
    is_fresh = age_days <= threshold_days

    return ValidationResult(
        check_name="data_freshness",
        level=ValidationLevel.WARNING,
        passed=is_fresh,
        message=f"Data age: {age_days} days ({'fresh' if is_fresh else f'STALE (threshold: {threshold_days})'})"
    )


# Main for testing
if __name__ == "__main__":
    print("=== Temporal Validators Test ===\n")

    # Test 1: validate_temporal_consistency
    print("1. Testing validate_temporal_consistency():")

    # Sample DataFrame with years
    sample_df = pd.DataFrame([
        {'name': 'skill-a', 'year': 2024, 'stars': 100},
        {'name': 'skill-b', 'year': 2025, 'stars': 150},
        {'name': 'skill-c', 'year': 2026, 'stars': 200}
    ])

    report = validate_temporal_consistency(sample_df)
    print(f"   {report.get_summary()}")

    # Test with future years (should fail)
    future_df = pd.DataFrame([
        {'name': 'skill-x', 'year': 2030, 'stars': 100}
    ])
    report = validate_temporal_consistency(future_df)
    print(f"   Future year test: {report.get_summary()}")

    # Test 2: validate_week_number
    print("\n2. Testing validate_week_number():")
    result = validate_week_number(6, 2026)
    print(f"   Week 6: {result.message}")

    result = validate_week_number(0, 2026)  # Invalid
    print(f"   Week 0: {result.message}")

    # Test 3: validate_week_boundaries
    print("\n3. Testing validate_week_boundaries():")
    from datetime import timezone

    # Valid week boundaries (Monday to Sunday)
    monday = datetime(2026, 2, 2, 0, 0, 0, tzinfo=timezone.utc)  # Monday
    sunday = datetime(2026, 2, 8, 23, 59, 59, tzinfo=timezone.utc)  # Sunday

    report = validate_week_boundaries(monday, sunday)
    print(f"   {report.get_summary()}")

    # Invalid boundaries (Tuesday to Monday)
    tuesday = datetime(2026, 2, 3, 0, 0, 0, tzinfo=timezone.utc)  # Tuesday
    next_monday = datetime(2026, 2, 9, 23, 59, 59, tzinfo=timezone.utc)  # Monday

    report = validate_week_boundaries(tuesday, next_monday)
    print(f"   Invalid boundaries: {report.get_summary()}")

    # Test 4: validate_data_freshness
    print("\n4. Testing validate_data_freshness():")

    # Recent data
    recent = datetime.now(timezone.utc)
    result = validate_data_freshness(recent, threshold_days=180)
    print(f"   Recent data: {result.message}")

    # Stale data
    old = datetime.now(timezone.utc) - timedelta(days=200)
    result = validate_data_freshness(old, threshold_days=180)
    print(f"   Old data: {result.message}")
