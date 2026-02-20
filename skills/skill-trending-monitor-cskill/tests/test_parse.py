#!/usr/bin/env python3
"""
Tests for parsers.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from parse_skill_manager import parse_skill_manager_response
from parse_github_stars import parse_star_history_response


def test_parse_skill_manager():
    """Test skill-manager data parsing."""
    print("\n✓ Testing parse_skill_manager_response()...")

    sample_data = [
        {
            'name': 'test-skill-1',
            'author': 'test-author',
            'github_url': 'https://github.com/test/skill-1',
            'stars': 150,
            'forks': 25,
            'updated_at': '2026-01-15',
            'description': 'Test skill'
        }
    ]

    try:
        df = parse_skill_manager_response(sample_data)

        # Validations
        assert isinstance(df, pd.DataFrame), "Must return DataFrame"
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"
        assert 'name' in df.columns, "Missing 'name' column"
        assert 'stars' in df.columns, "Missing 'stars' column"
        assert df.loc[0, 'name'] == 'test-skill-1', "Name mismatch"

        print(f"  ✓ Parsed: {len(df)} records")
        print(f"  ✓ Columns: {list(df.columns)}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_parse_star_history():
    """Test GitHub star history parsing."""
    print("\n✓ Testing parse_star_history_response()...")

    sample_data = [
        {"starred_at": "2026-01-15T10:30:00Z", "user": {"login": "alice"}},
        {"starred_at": "2026-01-22T10:30:00Z", "user": {"login": "bob"}}
    ]

    try:
        result = parse_star_history_response(sample_data, "https://github.com/test/skill-1")

        # Validations
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        assert "repo_url" in result.columns, "Missing repo_url"
        assert "starred_at" in result.columns, "Missing starred_at"
        assert len(result) == 2, "Should parse all star events"

        print(f"  ✓ Parsed star history correctly")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_parse_empty_data():
    """Test parsing empty/invalid data."""
    print("\n✓ Testing empty data handling...")

    try:
        # Empty list
        try:
            parse_skill_manager_response([])
            print("  ✗ Should have raised error for empty list")
            return False
        except ValueError:
            print("  ✓ Empty list correctly raises ValueError")

        # Invalid structure
        try:
            parse_skill_manager_response(None)
            print("  ✗ Should have raised error for None")
            return False
        except (ValueError, TypeError):
            print("  ✓ Correctly handles None")

        # Empty star history
        try:
            parse_star_history_response([], "https://github.com/test/skill-1")
            print("  ✗ Should have raised error for empty star history")
            return False
        except ValueError:
            print("  ✓ Empty star history correctly raises ValueError")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_parse_schema_validation():
    """Test schema validation during parsing."""
    print("\n✓ Testing schema validation...")

    # Missing required field
    invalid_data = [{'name': 'test'}]  # Missing 'stars'

    try:
        df = parse_skill_manager_response(invalid_data)

        # Missing stars should default to 0
        assert 'stars' in df.columns, "Stars column missing"
        assert df.loc[0, 'stars'] == 0, "Stars default should be 0"
        print("  ✓ Missing fields handled with defaults")

        return True

    except ValueError as e:
        print(f"  ✓ Schema validation working: {e}")
        return True
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


def test_parse_data_transformations():
    """Test data type conversions and cleaning."""
    print("\n✓ Testing data transformations...")

    sample_data = [
        {
            'name': 'test-skill',
            'stars': '150',  # String instead of int
            'updated_at': '2026-01-15'
        }
    ]

    try:
        df = parse_skill_manager_response(sample_data)

        # Check type conversions
        assert pd.api.types.is_numeric_dtype(df['stars']), "Stars not converted to numeric"
        print("  ✓ Data types converted correctly")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run parser tests."""
    print("=" * 70)
    print("PARSER TESTS")
    print("=" * 70)

    tests = [
        test_parse_skill_manager,
        test_parse_star_history,
        test_parse_empty_data,
        test_parse_schema_validation,
        test_parse_data_transformations,
    ]

    passed = sum(1 for test in tests if test())
    print(f"\nResults: {passed}/{len(tests)} passed")

    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
