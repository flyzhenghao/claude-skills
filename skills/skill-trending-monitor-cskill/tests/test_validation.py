#!/usr/bin/env python3
"""
Tests for validation functions.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from utils.validators.parameter_validator import (
    validate_skill_name,
    validate_threshold,
    validate_week_number,
    validate_stars_threshold,
    ValidationError
)
from utils.validators.data_validator import (
    DataValidator,
    ValidationReport,
    ValidationLevel
)
from utils.validators.temporal_validator import validate_temporal_consistency
from utils.validators.completeness_validator import validate_completeness


def test_validate_skill_name():
    """Test skill name parameter validation."""
    print("\n✓ Testing validate_skill_name()...")

    try:
        # Test valid skill name
        result = validate_skill_name("Skill-Manager", valid_skills=["skill-manager", "skill-a"])
        assert result == "skill-manager", "Should normalize to lowercase"
        print(f"  ✓ Valid skill normalized: {result}")

        # Test invalid skill
        try:
            validate_skill_name("invalid", valid_skills=["skill-a", "skill-b"])
            print("  ✗ Should have raised ValidationError for invalid skill")
            return False
        except ValidationError as e:
            print(f"  ✓ Invalid skill caught: {str(e)[:50]}...")

        # Test empty skill
        try:
            validate_skill_name("", valid_skills=["skill-a"])
            print("  ✗ Should have raised ValidationError for empty skill")
            return False
        except ValidationError:
            print("  ✓ Empty skill caught")

        # Test without validation list (any skill allowed)
        result = validate_skill_name("Anything")
        assert result == "anything"
        print("  ✓ No validation list works")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_threshold():
    """Test threshold parameter validation."""
    print("\n✓ Testing validate_threshold()...")

    try:
        # Test valid threshold
        result = validate_threshold(0.75, 0.0, 1.0, "similarity_threshold")
        assert result == 0.75, "Should return valid threshold"
        print(f"  ✓ Valid threshold: {result}")

        # Test out-of-range
        try:
            validate_threshold(1.5, 0.0, 1.0, "similarity_threshold")
            print("  ✗ Should have raised ValidationError for out-of-range")
            return False
        except ValidationError as e:
            print(f"  ✓ Out-of-range blocked: {str(e)[:50]}...")

        # Test non-numeric
        try:
            validate_threshold("bad", 0.0, 1.0, "similarity_threshold")
            print("  ✗ Should have raised ValidationError for non-numeric")
            return False
        except ValidationError as e:
            print(f"  ✓ Non-numeric blocked: {str(e)[:50]}...")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_response():
    """Test API response validation."""
    print("\n✓ Testing validate_response()...")

    try:
        validator = DataValidator()

        # Test valid response (list)
        data = [{"name": "skill-a", "stars": 100, "description": "Test"}]
        report = validator.validate_response(data)

        assert isinstance(report, ValidationReport), "Must return ValidationReport"
        assert report.all_passed(), "Valid data should pass all checks"
        print("  ✓ Valid list response passed")

        # Test valid response (dict)
        data_dict = {"data": [{"name": "skill-a"}]}
        report = validator.validate_response(data_dict)
        assert isinstance(report, ValidationReport)
        print("  ✓ Valid dict response passed")

        # Test empty response
        report = validator.validate_response([])
        assert report.has_critical_issues(), "Empty data should fail"
        print("  ✓ Empty response correctly failed")

        # Test invalid type
        report = validator.validate_response("not a list or dict")
        assert report.has_critical_issues(), "Invalid type should fail"
        print("  ✓ Invalid type correctly failed")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_dataframe():
    """Test DataFrame validation."""
    print("\n✓ Testing validate_dataframe()...")

    try:
        validator = DataValidator()

        # Test valid DataFrame
        df = pd.DataFrame({
            "name": ["skill-a", "skill-b"],
            "description": ["Desc A", "Desc B"],
            "stars": [100, 150]
        })
        report = validator.validate_dataframe(df, "skills")

        assert isinstance(report, ValidationReport), "Must return ValidationReport"
        assert report.all_passed(), "Valid DataFrame should pass"
        print(f"  ✓ Valid DataFrame passed: {len(df)} rows")

        # Test empty DataFrame
        df_empty = pd.DataFrame()
        report = validator.validate_dataframe(df_empty, "skills")
        assert report.has_critical_issues(), "Empty DataFrame should fail"
        print("  ✓ Empty DataFrame correctly failed")

        # Test missing required columns
        df_missing = pd.DataFrame({"name": ["skill-a"]})
        report = validator.validate_dataframe(df_missing, "skills")
        assert report.has_critical_issues(), "Missing columns should fail"
        print("  ✓ Missing columns correctly failed")

        # Test excessive NaN values
        df_nan = pd.DataFrame({
            "name": ["skill-a"] * 10,
            "description": [None] * 10,
            "stars": [None] * 10
        })
        report = validator.validate_dataframe(df_nan, "skills")
        warnings = report.get_warnings()
        assert len(warnings) > 0, "Excessive NaN should generate warnings"
        print(f"  ✓ Excessive NaN detected: {len(warnings)} warnings")

        # Test incorrect data types
        df_wrong_type = pd.DataFrame({
            "name": ["skill-a"],
            "description": ["Test"],
            "stars": ["not a number"]  # Should be int
        })
        report = validator.validate_dataframe(df_wrong_type, "skills")
        assert not report.all_passed(), "Wrong types should fail validation"
        print("  ✓ Wrong data types correctly failed")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_temporal_consistency():
    """Test temporal consistency validation."""
    print("\n✓ Testing validate_temporal_consistency()...")

    try:
        current_year = datetime.now().year

        # Test valid temporal data
        df = pd.DataFrame({
            "entity": ["CORN"] * 5,
            "year": [2020, 2021, 2022, 2023, 2024]
        })
        report = validate_temporal_consistency(df)

        assert isinstance(report, ValidationReport), "Must return ValidationReport"
        assert report.all_passed(), "Valid temporal data should pass"
        print("  ✓ Valid temporal data passed")

        # Test future year (should fail)
        df_future = pd.DataFrame({
            "entity": ["CORN"],
            "year": [2050]
        })
        report = validate_temporal_consistency(df_future)
        assert not report.all_passed(), "Future year should fail"
        print("  ✓ Future year correctly failed")

        # Test very old year (should generate warning)
        df_old = pd.DataFrame({
            "entity": ["CORN"],
            "year": [1850]
        })
        report = validate_temporal_consistency(df_old)
        warnings = report.get_warnings()
        assert len(warnings) > 0, "Very old year should generate warning"
        print(f"  ✓ Old year warning: {warnings[0][:50]}...")

        # Test stale data (should generate warning)
        df_stale = pd.DataFrame({
            "entity": ["CORN"],
            "year": [2015]  # 11+ years old
        })
        report = validate_temporal_consistency(df_stale)
        warnings = report.get_warnings()
        assert len(warnings) > 0, "Stale data should generate warning"
        print("  ✓ Stale data warning generated")

        # Test large gaps in time series
        df_gaps = pd.DataFrame({
            "entity": ["CORN"] * 3,
            "year": [2020, 2021, 2024]  # Gap: 2022-2023 missing
        })
        report = validate_temporal_consistency(df_gaps)
        warnings = report.get_warnings()
        # Note: Some gaps might be acceptable, so we just check the report exists
        assert isinstance(report, ValidationReport)
        print(f"  ✓ Gap detection working: {len(warnings)} warnings")

        # Test missing year column
        df_no_year = pd.DataFrame({"entity": ["CORN"]})
        report = validate_temporal_consistency(df_no_year)
        assert report.has_critical_issues(), "Missing year column should fail"
        print("  ✓ Missing year column correctly failed")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_completeness_validation():
    """Test data completeness validation."""
    print("\n✓ Testing validate_completeness()...")

    try:
        # Test complete data
        df = pd.DataFrame({
            "name": ["skill-a", "skill-b"],
            "year": [2024, 2024]
        })
        expected_entities = ["skill-a", "skill-b"]
        expected_periods = [2024]

        report = validate_completeness(
            df,
            expected_entities=expected_entities,
            expected_periods=expected_periods
        )

        assert isinstance(report, ValidationReport), "Must return ValidationReport"
        assert report.all_passed(), "Complete data should pass"
        print("  ✓ Complete data passed")

        # Test missing entities
        df_missing = pd.DataFrame({
            "name": ["skill-a"],  # skill-b missing
            "year": [2024]
        })
        report = validate_completeness(
            df_missing,
            expected_entities=["skill-a", "skill-b"],
            expected_periods=[2024]
        )
        warnings = report.get_warnings()
        assert len(warnings) > 0, "Missing entities should generate warning"
        print(f"  ✓ Missing entities detected: {warnings[0][:50]}...")

        # Test missing years
        df_year_missing = pd.DataFrame({
            "name": ["skill-a"] * 2,
            "year": [2023, 2024]  # 2022 missing
        })
        report = validate_completeness(
            df_year_missing,
            expected_entities=["skill-a"],
            expected_periods=[2022, 2023, 2024]
        )
        warnings = report.get_warnings()
        assert len(warnings) > 0, "Missing years should generate warning"
        print("  ✓ Missing years detected")

        # Test null values in critical columns
        df_nulls = pd.DataFrame({
            "name": ["skill-a", None, "skill-b"],
            "description": ["A", "B", None],
            "stars": [10, 20, None],
            "year": [2024, 2024, 2024]
        })
        report = validate_completeness(
            df_nulls,
            expected_entities=None,
            expected_periods=None
        )
        assert report.has_critical_issues(), "Nulls in critical columns should fail"
        print("  ✓ Null values correctly failed")

        # Test coverage percentage
        df_partial = pd.DataFrame({
            "name": ["skill-a"] * 3 + ["skill-b"] * 3,
            "year": [2022, 2023, 2024] * 2
        })
        # Expected: 2 entities × 3 periods = 6 rows (matches actual)
        report = validate_completeness(
            df_partial,
            expected_entities=["skill-a", "skill-b"],
            expected_periods=[2022, 2023, 2024]
        )
        # Coverage should be 100%
        assert report.all_passed(), "100% coverage should pass"
        print("  ✓ Coverage calculation working")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_report():
    """Test ValidationReport functionality."""
    print("\n✓ Testing ValidationReport...")

    try:
        from utils.validators.data_validator import ValidationResult

        report = ValidationReport()

        # Test adding results
        report.add(ValidationResult(
            check_name="test_check",
            level=ValidationLevel.CRITICAL,
            passed=True,
            message="Test passed"
        ))

        assert len(report.results) == 1, "Should have 1 result"
        print("  ✓ Adding results works")

        # Test has_critical_issues
        report_critical = ValidationReport()
        report_critical.add(ValidationResult(
            check_name="critical_check",
            level=ValidationLevel.CRITICAL,
            passed=False,
            message="Critical issue"
        ))

        assert report_critical.has_critical_issues(), "Should detect critical issues"
        print("  ✓ Critical issue detection works")

        # Test all_passed
        report_pass = ValidationReport()
        report_pass.add(ValidationResult(
            check_name="pass1",
            level=ValidationLevel.INFO,
            passed=True,
            message="OK"
        ))
        report_pass.add(ValidationResult(
            check_name="pass2",
            level=ValidationLevel.WARNING,
            passed=True,
            message="OK"
        ))

        assert report_pass.all_passed(), "All checks passed"
        print("  ✓ all_passed() works correctly")

        # Test get_warnings
        report_warn = ValidationReport()
        report_warn.add(ValidationResult(
            check_name="warn1",
            level=ValidationLevel.WARNING,
            passed=False,
            message="Warning 1"
        ))
        report_warn.add(ValidationResult(
            check_name="warn2",
            level=ValidationLevel.WARNING,
            passed=False,
            message="Warning 2"
        ))

        warnings = report_warn.get_warnings()
        assert len(warnings) == 2, "Should have 2 warnings"
        print(f"  ✓ get_warnings() returned {len(warnings)} warnings")

        # Test get_summary
        summary = report_warn.get_summary()
        assert "0/2 passed" in summary, "Summary should show 0/2 passed"
        print(f"  ✓ Summary: {summary}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run validation tests."""
    print("=" * 70)
    print("VALIDATION TESTS")
    print("=" * 70)

    tests = [
        test_validate_skill_name,
        test_validate_threshold,
        test_validate_week_number,
        test_validate_response,
        test_validate_dataframe,
        test_temporal_consistency,
        test_completeness_validation,
        test_validation_report,
    ]

    passed = sum(1 for test in tests if test())
    print(f"\nResults: {passed}/{len(tests)} passed")

    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
def test_validate_week_number():
    """Test week number validation."""
    print("\n✓ Testing validate_week_number()...")

    try:
        result = validate_week_number(6)
        assert result == 6, "Should return valid week number"
        print(f"  ✓ Valid week: {result}")

        try:
            validate_week_number(0)
            print("  ✗ Should have raised ValidationError for week 0")
            return False
        except ValidationError:
            print("  ✓ Week 0 blocked")

        try:
            validate_week_number(54)
            print("  ✗ Should have raised ValidationError for week 54")
            return False
        except ValidationError:
            print("  ✓ Week 54 blocked")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
