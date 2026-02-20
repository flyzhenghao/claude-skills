#!/usr/bin/env python3
"""
Data validators for skill-trending-monitor-cskill.
Validates API responses and analysis outputs.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Severity levels for validation results."""
    CRITICAL = "critical"  # Must fix
    WARNING = "warning"    # Should review
    INFO = "info"          # FYI


@dataclass
class ValidationResult:
    """Single validation check result."""
    check_name: str
    level: ValidationLevel
    passed: bool
    message: str
    details: Optional[Dict] = None


class ValidationReport:
    """Collection of validation results with aggregation methods."""

    def __init__(self):
        self.results: List[ValidationResult] = []

    def add(self, result: ValidationResult):
        """Add validation result."""
        self.results.append(result)

    def has_critical_issues(self) -> bool:
        """Check if any critical issues found."""
        return any(
            r.level == ValidationLevel.CRITICAL and not r.passed
            for r in self.results
        )

    def all_passed(self) -> bool:
        """Check if all validations passed."""
        return all(r.passed for r in self.results)

    def get_warnings(self) -> List[str]:
        """Get all warning messages."""
        return [
            r.message for r in self.results
            if r.level == ValidationLevel.WARNING and not r.passed
        ]

    def get_summary(self) -> str:
        """Get summary of validation results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        critical = sum(
            1 for r in self.results
            if r.level == ValidationLevel.CRITICAL and not r.passed
        )

        return (
            f"Validation: {passed}/{total} passed "
            f"({critical} critical issues)"
        )


class DataValidator:
    """Validates API responses and DataFrames."""

    def validate_response(self, data: Any) -> ValidationReport:
        """
        Validate raw API response.

        Args:
            data: Raw API response

        Returns:
            ValidationReport with results

        Example:
            >>> validator = DataValidator()
            >>> report = validator.validate_response(api_data)
            >>> if report.has_critical_issues():
            ...     print(report.get_summary())
        """
        report = ValidationReport()

        # Check 1: Not empty
        report.add(ValidationResult(
            check_name="not_empty",
            level=ValidationLevel.CRITICAL,
            passed=bool(data),
            message="Data is empty" if not data else "Data present"
        ))

        # Check 2: Correct type
        expected_type = (list, dict)
        is_correct_type = isinstance(data, expected_type)
        report.add(ValidationResult(
            check_name="correct_type",
            level=ValidationLevel.CRITICAL,
            passed=is_correct_type,
            message=f"Expected {expected_type}, got {type(data)}"
        ))

        # Check 3: Has expected structure (for skill-manager data)
        if isinstance(data, dict):
            # skill-manager database has skills as top-level keys
            has_skills = len(data) > 0
            report.add(ValidationResult(
                check_name="has_skills",
                level=ValidationLevel.WARNING,
                passed=has_skills,
                message=f"Found {len(data)} skills" if has_skills else "No skills found"
            ))

        elif isinstance(data, list):
            # GitHub API returns list of stargazers
            has_data = len(data) > 0
            report.add(ValidationResult(
                check_name="has_data",
                level=ValidationLevel.WARNING,
                passed=has_data,
                message=f"Found {len(data)} items" if has_data else "No items found"
            ))

        return report

    def validate_dataframe(self, df: pd.DataFrame, data_type: str) -> ValidationReport:
        """
        Validate parsed DataFrame.

        Args:
            df: Parsed DataFrame
            data_type: Type of data (for type-specific checks)

        Returns:
            ValidationReport

        Example:
            >>> validator = DataValidator()
            >>> report = validator.validate_dataframe(df, 'skills')
            >>> print(report.get_summary())
        """
        report = ValidationReport()

        # Check 1: Not empty
        report.add(ValidationResult(
            check_name="not_empty",
            level=ValidationLevel.CRITICAL,
            passed=len(df) > 0,
            message=f"DataFrame has {len(df)} rows"
        ))

        # Check 2: Required columns (data type specific)
        required_cols = self._get_required_columns(data_type)
        missing = set(required_cols) - set(df.columns)
        report.add(ValidationResult(
            check_name="required_columns",
            level=ValidationLevel.CRITICAL,
            passed=len(missing) == 0,
            message=f"Missing columns: {missing}" if missing else "All required columns present"
        ))

        # Check 3: No excessive NaN values
        if len(df) > 0:
            nan_pct = (df.isna().sum() / len(df) * 100).max()
            report.add(ValidationResult(
                check_name="nan_threshold",
                level=ValidationLevel.WARNING,
                passed=nan_pct < 30,
                message=f"Max NaN: {nan_pct:.1f}% ({'OK' if nan_pct < 30 else 'HIGH'})"
            ))

        # Check 4: Data types correct (type specific)
        if data_type == 'skills' and 'stars' in df.columns:
            is_numeric = pd.api.types.is_numeric_dtype(df['stars'])
            report.add(ValidationResult(
                check_name="stars_numeric",
                level=ValidationLevel.CRITICAL,
                passed=is_numeric,
                message="'stars' is numeric" if is_numeric else "'stars' is not numeric"
            ))

        if 'updated_at' in df.columns:
            # Check if datetime or string (both acceptable)
            is_temporal = (
                pd.api.types.is_datetime64_any_dtype(df['updated_at']) or
                pd.api.types.is_string_dtype(df['updated_at'])
            )
            report.add(ValidationResult(
                check_name="updated_at_temporal",
                level=ValidationLevel.WARNING,
                passed=is_temporal,
                message="'updated_at' has temporal type" if is_temporal else "'updated_at' type unexpected"
            ))

        return report

    def _get_required_columns(self, data_type: str) -> List[str]:
        """Get required columns for data type."""
        requirements = {
            'skills': ['name', 'description', 'stars'],
            'growth': ['name', 'week', 'stars'],
            'similarity': ['name', 'description'],
            'security': ['name', 'security_score']
        }
        return requirements.get(data_type, [])


def validate_skill_output(result: Dict) -> ValidationReport:
    """
    Validate analysis output for skills.

    Args:
        result: Analysis result dict

    Returns:
        ValidationReport

    Example:
        >>> report = validate_skill_output({'skills': [], 'week': 6})
        >>> if not report.all_passed():
        ...     print(report.get_warnings())
    """
    report = ValidationReport()

    # Check required keys
    required_keys = ['week', 'week_info']
    for key in required_keys:
        report.add(ValidationResult(
            check_name=f"has_{key}",
            level=ValidationLevel.CRITICAL,
            passed=key in result,
            message=f"'{key}' present" if key in result else f"Missing '{key}'"
        ))

    # Check data quality
    if 'skills' in result:
        skills_count = len(result['skills'])
        report.add(ValidationResult(
            check_name="has_skills",
            level=ValidationLevel.INFO,
            passed=skills_count > 0,
            message=f"Found {skills_count} skills"
        ))

    return report


def validate_growth_output(result: Dict) -> ValidationReport:
    """
    Validate growth analysis output.

    Args:
        result: Growth analysis result dict

    Returns:
        ValidationReport

    Example:
        >>> report = validate_growth_output({'growth_rate': 0.05, 'week': 6})
        >>> print(report.get_summary())
    """
    report = ValidationReport()

    # Check required keys
    required_keys = ['week', 'growth_rate']
    for key in required_keys:
        report.add(ValidationResult(
            check_name=f"has_{key}",
            level=ValidationLevel.CRITICAL,
            passed=key in result,
            message=f"'{key}' present" if key in result else f"Missing '{key}'"
        ))

    # Check growth rate is numeric
    if 'growth_rate' in result:
        is_numeric = isinstance(result['growth_rate'], (int, float))
        report.add(ValidationResult(
            check_name="growth_rate_numeric",
            level=ValidationLevel.CRITICAL,
            passed=is_numeric,
            message="Growth rate is numeric" if is_numeric else "Growth rate is not numeric"
        ))

        # Check growth rate is reasonable
        if is_numeric:
            is_reasonable = -1.0 <= result['growth_rate'] <= 10.0
            report.add(ValidationResult(
                check_name="growth_rate_reasonable",
                level=ValidationLevel.WARNING,
                passed=is_reasonable,
                message=f"Growth rate: {result['growth_rate']*100:.1f}%"
            ))

    return report


# Main for testing
if __name__ == "__main__":
    print("=== Data Validators Test ===\n")

    # Test 1: DataValidator - response validation
    print("1. Testing DataValidator.validate_response():")
    validator = DataValidator()

    sample_data = [{'name': 'skill-a', 'stars': 100}]
    report = validator.validate_response(sample_data)
    print(f"   {report.get_summary()}")

    # Test with empty data
    report = validator.validate_response([])
    print(f"   Empty data: {report.get_summary()}")

    # Test 2: DataValidator - DataFrame validation
    print("\n2. Testing DataValidator.validate_dataframe():")
    sample_df = pd.DataFrame([
        {'name': 'skill-a', 'stars': 100, 'description': 'Test skill A'},
        {'name': 'skill-b', 'stars': 200, 'description': 'Test skill B'}
    ])

    report = validator.validate_dataframe(sample_df, 'skills')
    print(f"   {report.get_summary()}")

    # Test 3: validate_skill_output
    print("\n3. Testing validate_skill_output():")
    sample_output = {
        'week': 6,
        'week_info': 'Using current week (Week 6)',
        'skills': [{'name': 'skill-a'}]
    }

    report = validate_skill_output(sample_output)
    print(f"   {report.get_summary()}")

    # Test 4: validate_growth_output
    print("\n4. Testing validate_growth_output():")
    sample_growth = {
        'week': 6,
        'growth_rate': 0.05
    }

    report = validate_growth_output(sample_growth)
    print(f"   {report.get_summary()}")
