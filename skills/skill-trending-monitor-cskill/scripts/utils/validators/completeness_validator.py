#!/usr/bin/env python3
"""
Completeness validators for skill-trending-monitor-cskill.
Checks data completeness and coverage.
"""

import pandas as pd
from typing import List, Set, Optional
from .data_validator import ValidationResult, ValidationReport, ValidationLevel


def validate_completeness(
    df: pd.DataFrame,
    expected_entities: Optional[List[str]] = None,
    expected_periods: Optional[List[int]] = None
) -> ValidationReport:
    """
    Validate data completeness.

    Args:
        df: DataFrame to validate
        expected_entities: Expected skill names (None to skip)
        expected_periods: Expected week numbers or years (None to skip)

    Returns:
        ValidationReport

    Example:
        >>> expected_skills = ['skill-a', 'skill-b', 'skill-c']
        >>> expected_weeks = [1, 2, 3, 4, 5, 6]
        >>> report = validate_completeness(df, expected_skills, expected_weeks)
        >>> if not report.all_passed():
        ...     print(report.get_warnings())
    """
    report = ValidationReport()

    # Check 1: All expected entities present
    if expected_entities:
        actual_entities = set(df['name'].unique()) if 'name' in df.columns else set()
        expected_set = set(expected_entities)
        missing = expected_set - actual_entities

        report.add(ValidationResult(
            check_name="all_entities_present",
            level=ValidationLevel.WARNING,
            passed=len(missing) == 0,
            message=f"Missing entities: {missing}" if missing else "All entities present",
            details={'missing': list(missing)}
        ))

    # Check 2: All expected periods present
    if expected_periods:
        # Try 'week' column first, then 'year'
        period_col = None
        if 'week' in df.columns:
            period_col = 'week'
        elif 'year' in df.columns:
            period_col = 'year'

        if period_col:
            actual_periods = set(df[period_col].unique())
            expected_set = set(expected_periods)
            missing = expected_set - actual_periods

            report.add(ValidationResult(
                check_name="all_periods_present",
                level=ValidationLevel.WARNING,
                passed=len(missing) == 0,
                message=f"Missing {period_col}s: {missing}" if missing else f"All {period_col}s present"
            ))
        else:
            report.add(ValidationResult(
                check_name="has_period_column",
                level=ValidationLevel.WARNING,
                passed=False,
                message="No 'week' or 'year' column found for period validation"
            ))

    # Check 3: No excessive nulls in critical columns
    critical_columns = ['name', 'stars', 'description']
    for col in critical_columns:
        if col in df.columns:
            null_count = df[col].isna().sum()
            null_pct = (null_count / len(df) * 100) if len(df) > 0 else 0

            report.add(ValidationResult(
                check_name=f"{col}_no_nulls",
                level=ValidationLevel.CRITICAL if null_pct > 10 else ValidationLevel.WARNING,
                passed=null_count == 0,
                message=f"'{col}' has {null_count} nulls ({null_pct:.1f}%)"
            ))

    # Check 4: Coverage percentage
    if expected_entities and expected_periods:
        expected_total = len(expected_entities) * len(expected_periods)
        actual_total = len(df)
        coverage_pct = (actual_total / expected_total) * 100 if expected_total > 0 else 0

        report.add(ValidationResult(
            check_name="coverage_percentage",
            level=ValidationLevel.INFO,
            passed=coverage_pct >= 80,
            message=f"Coverage: {coverage_pct:.1f}% ({actual_total}/{expected_total})"
        ))

    return report


def check_required_columns(
    df: pd.DataFrame,
    required_cols: List[str],
    data_type: str = "dataset"
) -> ValidationReport:
    """
    Check if all required columns are present.

    Args:
        df: DataFrame to check
        required_cols: List of required column names
        data_type: Description of data type (for error messages)

    Returns:
        ValidationReport

    Example:
        >>> required = ['name', 'stars', 'description', 'week']
        >>> report = check_required_columns(df, required, "growth data")
        >>> assert report.all_passed()
    """
    report = ValidationReport()

    missing = set(required_cols) - set(df.columns)

    report.add(ValidationResult(
        check_name="required_columns",
        level=ValidationLevel.CRITICAL,
        passed=len(missing) == 0,
        message=f"Missing required columns in {data_type}: {missing}" if missing else f"All required columns present in {data_type}",
        details={'missing': list(missing), 'present': list(df.columns)}
    ))

    return report


def validate_entity_distribution(
    df: pd.DataFrame,
    entity_col: str = 'name',
    min_records_per_entity: int = 1
) -> ValidationReport:
    """
    Validate entity distribution in dataset.

    Checks:
    - Each entity has minimum number of records
    - Distribution is not heavily skewed

    Args:
        df: DataFrame to validate
        entity_col: Column name for entities
        min_records_per_entity: Minimum records required per entity

    Returns:
        ValidationReport

    Example:
        >>> report = validate_entity_distribution(df, 'name', min_records_per_entity=2)
        >>> if report.has_critical_issues():
        ...     print(report.get_summary())
    """
    report = ValidationReport()

    if entity_col not in df.columns:
        report.add(ValidationResult(
            check_name="entity_column_exists",
            level=ValidationLevel.CRITICAL,
            passed=False,
            message=f"Entity column '{entity_col}' not found"
        ))
        return report

    # Check 1: Each entity has minimum records
    entity_counts = df[entity_col].value_counts()
    under_threshold = entity_counts[entity_counts < min_records_per_entity]

    report.add(ValidationResult(
        check_name="min_records_per_entity",
        level=ValidationLevel.WARNING,
        passed=len(under_threshold) == 0,
        message=f"{len(under_threshold)} entities have < {min_records_per_entity} records" if len(under_threshold) > 0 else f"All entities have >= {min_records_per_entity} records",
        details={'under_threshold': under_threshold.to_dict()}
    ))

    # Check 2: Distribution skew
    if len(entity_counts) > 0:
        max_count = entity_counts.max()
        min_count = entity_counts.min()
        skew_ratio = max_count / min_count if min_count > 0 else float('inf')

        is_balanced = skew_ratio <= 10  # Max entity has <= 10x records of min entity

        report.add(ValidationResult(
            check_name="distribution_balance",
            level=ValidationLevel.INFO,
            passed=is_balanced,
            message=f"Distribution skew ratio: {skew_ratio:.1f}x ({'balanced' if is_balanced else 'SKEWED'})"
        ))

    return report


def validate_coverage_gaps(
    df: pd.DataFrame,
    entity_col: str = 'name',
    period_col: str = 'week'
) -> ValidationReport:
    """
    Validate coverage gaps in entity-period matrix.

    Identifies entities with missing periods (gaps in time series).

    Args:
        df: DataFrame to validate
        entity_col: Column name for entities
        period_col: Column name for periods (week/year)

    Returns:
        ValidationReport

    Example:
        >>> report = validate_coverage_gaps(df, 'name', 'week')
        >>> print(report.get_summary())
    """
    report = ValidationReport()

    if entity_col not in df.columns:
        report.add(ValidationResult(
            check_name="entity_column_exists",
            level=ValidationLevel.CRITICAL,
            passed=False,
            message=f"Entity column '{entity_col}' not found"
        ))
        return report

    if period_col not in df.columns:
        report.add(ValidationResult(
            check_name="period_column_exists",
            level=ValidationLevel.CRITICAL,
            passed=False,
            message=f"Period column '{period_col}' not found"
        ))
        return report

    # Calculate expected vs actual coverage
    entities = df[entity_col].unique()
    periods = sorted(df[period_col].unique())

    if len(periods) > 1:
        # For each entity, check if all periods are present
        entities_with_gaps = []

        for entity in entities:
            entity_periods = set(df[df[entity_col] == entity][period_col].unique())
            all_periods = set(periods)
            missing_periods = all_periods - entity_periods

            if missing_periods:
                entities_with_gaps.append({
                    'entity': entity,
                    'missing_periods': len(missing_periods),
                    'coverage_pct': (len(entity_periods) / len(all_periods)) * 100
                })

        report.add(ValidationResult(
            check_name="no_coverage_gaps",
            level=ValidationLevel.WARNING,
            passed=len(entities_with_gaps) == 0,
            message=f"{len(entities_with_gaps)} entities have coverage gaps" if entities_with_gaps else "No coverage gaps detected",
            details={'entities_with_gaps': entities_with_gaps[:10]}  # Report top 10
        ))

    return report


# Main for testing
if __name__ == "__main__":
    print("=== Completeness Validators Test ===\n")

    # Test 1: validate_completeness
    print("1. Testing validate_completeness():")

    sample_df = pd.DataFrame([
        {'name': 'skill-a', 'week': 1, 'stars': 100, 'description': 'Test A'},
        {'name': 'skill-b', 'week': 1, 'stars': 150, 'description': 'Test B'},
        {'name': 'skill-a', 'week': 2, 'stars': 105, 'description': 'Test A'},
        {'name': 'skill-c', 'week': 2, 'stars': 200, 'description': 'Test C'}
    ])

    expected_skills = ['skill-a', 'skill-b', 'skill-c']
    expected_weeks = [1, 2]

    report = validate_completeness(sample_df, expected_skills, expected_weeks)
    print(f"   {report.get_summary()}")

    # Test with missing data
    incomplete_df = pd.DataFrame([
        {'name': 'skill-a', 'week': 1, 'stars': 100, 'description': 'Test A'}
    ])

    report = validate_completeness(incomplete_df, expected_skills, expected_weeks)
    print(f"   Incomplete data: {report.get_summary()}")
    print(f"   Warnings: {report.get_warnings()}")

    # Test 2: check_required_columns
    print("\n2. Testing check_required_columns():")

    required = ['name', 'stars', 'description', 'week']
    report = check_required_columns(sample_df, required, "test dataset")
    print(f"   {report.get_summary()}")

    # Test with missing columns
    incomplete_df2 = sample_df.drop(columns=['description'])
    report = check_required_columns(incomplete_df2, required, "incomplete dataset")
    print(f"   Missing columns: {report.get_summary()}")

    # Test 3: validate_entity_distribution
    print("\n3. Testing validate_entity_distribution():")

    report = validate_entity_distribution(sample_df, 'name', min_records_per_entity=1)
    print(f"   {report.get_summary()}")

    # Test 4: validate_coverage_gaps
    print("\n4. Testing validate_coverage_gaps():")

    report = validate_coverage_gaps(sample_df, 'name', 'week')
    print(f"   {report.get_summary()}")

    # Test with gaps
    gap_df = pd.DataFrame([
        {'name': 'skill-a', 'week': 1, 'stars': 100},
        {'name': 'skill-a', 'week': 3, 'stars': 110},  # Missing week 2
        {'name': 'skill-b', 'week': 1, 'stars': 150},
        {'name': 'skill-b', 'week': 2, 'stars': 155},
        {'name': 'skill-b', 'week': 3, 'stars': 160}
    ])

    report = validate_coverage_gaps(gap_df, 'name', 'week')
    print(f"   With gaps: {report.get_summary()}")
