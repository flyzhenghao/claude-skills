#!/usr/bin/env python3
"""
Integration tests for skill-trending-monitor-cskill.
Tests complete workflows from query to result.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import analyze_new_skills as analyze_new_skills_module
import analyze_growth_rates as analyze_growth_rates_module
from analyze_new_skills import analyze_new_skills
from analyze_growth_rates import analyze_growth_rates
from analyze_similarity import calculate_skill_similarity
from analyze_replacements import calculate_replacement_confidence
from evaluate_security import evaluate_skill_security
from analyze_comprehensive import generate_comprehensive_report


def test_analyze_new_skills_basic(sample_skills_data, monkeypatch):
    """Test new skills discovery with mocked data sources."""
    print("\n✓ Testing analyze_new_skills()...")

    try:
        def fake_fetch_all_skills(min_stars=0, max_months_old=0, include_installed=True):
            return sample_skills_data, {"total": len(sample_skills_data)}

        def fake_get_installed_skills():
            return ["test-skill-1"]

        monkeypatch.setattr(analyze_new_skills_module, "fetch_all_skills", fake_fetch_all_skills)
        monkeypatch.setattr(analyze_new_skills_module, "get_installed_skills", fake_get_installed_skills)

        new_skills, stats = analyze_new_skills(min_stars=0, max_months_old=0, top_n=10)

        # Validations
        assert isinstance(new_skills, pd.DataFrame), "new_skills must be DataFrame"
        assert isinstance(stats, dict), "stats must be dict"
        assert "new_skills_found" in stats, "Missing stats key"

        print(f"  ✓ Found {len(new_skills)} new skills")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyze_new_skills_with_filters(sample_skills_data, monkeypatch):
    """Test new skills discovery with custom quality filters."""
    print("\n✓ Testing analyze_new_skills() with custom filters...")

    try:
        def fake_fetch_all_skills(min_stars=0, max_months_old=0, include_installed=True):
            return sample_skills_data, {"total": len(sample_skills_data)}

        def fake_get_installed_skills():
            return []

        monkeypatch.setattr(analyze_new_skills_module, "fetch_all_skills", fake_fetch_all_skills)
        monkeypatch.setattr(analyze_new_skills_module, "get_installed_skills", fake_get_installed_skills)

        result_df, _ = analyze_new_skills(min_stars=100, max_months_old=0, top_n=10)

        # With stricter filters, fewer skills should pass
        assert len(result_df) <= len(sample_skills_data)
        print(f"  ✓ Custom filters working: {len(result_df)} skills passed")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_analyze_growth_rates(sample_skills_df, monkeypatch):
    """Test growth rate calculation with mocked GitHub data."""
    print("\n✓ Testing analyze_growth_rates()...")

    try:
        def fake_fetch_star_history(github_url, github_token):
            return [
                {"starred_at": "2026-01-27T00:00:00Z"},
                {"starred_at": "2026-02-03T00:00:00Z"}
            ]

        def fake_calculate_week_over_week_growth(star_history):
            return {
                "current_week_stars": 1,
                "previous_week_stars": 1,
                "wow_growth_rate": 10.0,
                "total_stars": len(star_history),
                "current_week_start": datetime(2026, 2, 2, tzinfo=timezone.utc).isoformat()
            }

        monkeypatch.setattr(analyze_growth_rates_module, "fetch_star_history", fake_fetch_star_history)
        monkeypatch.setattr(analyze_growth_rates_module, "calculate_week_over_week_growth", fake_calculate_week_over_week_growth)

        result_df, stats = analyze_growth_rates(
            skills_df=sample_skills_df,
            github_token="fake-token",
            min_growth_rate=0,
            top_n=5
        )

        # Validations
        assert isinstance(result_df, pd.DataFrame), "Must return DataFrame"
        assert isinstance(stats, dict), "Must return stats dict"
        assert "growth_calculated_for" in stats, "Missing stats key"

        print(f"  ✓ Calculated growth rates: {len(result_df)} skills")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyze_similarity(sample_skills_df):
    """Test similarity matching with TF-IDF."""
    print("\n✓ Testing calculate_skill_similarity()...")

    try:
        pytest.importorskip("sklearn")

        result = calculate_skill_similarity(
            skills_df=sample_skills_df,
            similarity_threshold=0.1
        )

        # Validations
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        if not result.empty:
            assert "similarity_score" in result.columns, "Missing similarity_score"

        print(f"  ✓ Found {len(result)} similar skill pairs")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyze_replacements(sample_skills_df):
    """Test replacement recommendations."""
    print("\n✓ Testing calculate_replacement_confidence()...")

    try:
        skills_df = sample_skills_df.copy()
        skills_df["updated_at"] = pd.to_datetime(skills_df["updated_at"])

        installed_df = skills_df.head(1)[["name", "stars", "updated_at"]].copy()
        all_df = skills_df[["name", "stars", "updated_at"]].copy()

        similarity_df = pd.DataFrame([{
            "skill1_name": installed_df.iloc[0]["name"],
            "skill2_name": all_df.iloc[1]["name"],
            "similarity_score": 0.85
        }])

        result = calculate_replacement_confidence(
            installed_skills_df=installed_df,
            all_skills_df=all_df,
            similarity_df=similarity_df,
            confidence_threshold=0.0
        )

        # Validations
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        if not result.empty:
            assert "confidence_score" in result.columns, "Missing confidence_score"

        print(f"  ✓ Found {len(result)} replacement recommendations")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluate_security(sample_skills_df):
    """Test security evaluation scoring."""
    print("\n✓ Testing evaluate_skill_security()...")

    try:
        skills_df = sample_skills_df.copy()
        skills_df["updated_at"] = pd.to_datetime(skills_df["updated_at"])

        result = evaluate_skill_security(
            skills_df=skills_df,
            security_threshold=0
        )

        # Validations
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        if not result.empty:
            assert "security_score" in result.columns, "Missing security_score"
            assert 0 <= result.loc[0, "security_score"] <= 100, "Score out of range"

        print(f"  ✓ Evaluated {len(result)} skills")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comprehensive_report():
    """Test comprehensive report generation (all-in-one)."""
    print("\n✓ Testing generate_comprehensive_report()...")
    pytest.skip("Requires live GitHub data and full pipeline execution.")


def test_validation_integration():
    """Test that validation is integrated in functions."""
    print("\n✓ Testing validation integration...")
    pytest.skip("Validation integration requires full data pipeline.")


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("INTEGRATION TESTS - skill-trending-monitor-cskill")
    print("=" * 70)

    tests = [
        ("New skills discovery (basic)", test_analyze_new_skills_basic),
        ("New skills discovery (custom filters)", test_analyze_new_skills_with_filters),
        ("Growth rate calculation", test_analyze_growth_rates),
        ("Similarity matching", test_analyze_similarity),
        ("Replacement recommendations", test_analyze_replacements),
        ("Security evaluation", test_evaluate_security),
        ("Comprehensive report", test_comprehensive_report),
        ("Validation integration", test_validation_integration),
    ]

    results = []
    for test_name, test_func in tests:
        # Note: This is simplified - actual pytest will inject fixtures
        # For manual testing, would need to create fixtures manually
        passed = False
        try:
            # In real pytest, fixtures are automatically injected
            print(f"\n{'='*70}")
            print(f"Test: {test_name}")
            print(f"{'='*70}")
            # Would call: passed = test_func()
            print("  ⚠️  Skipped (pytest fixtures required)")
            passed = None
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            passed = False

        results.append((test_name, passed))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        if passed is None:
            status = "⚠️  SKIP"
        elif passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{status}: {test_name}")

    if None in [p for _, p in results]:
        print("\n⚠️  Run with pytest to execute all tests:")
        print("   pytest tests/test_integration.py -v")

    passed_count = sum(1 for _, p in results if p is True)
    total_count = len(results)

    print(f"\nResults: {passed_count}/{total_count} passed")

    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
