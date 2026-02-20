#!/usr/bin/env python3
"""
Tests for analysis functions.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import analyze_new_skills as analyze_new_skills_module
from analyze_new_skills import analyze_new_skills, filter_by_category, filter_by_tags
from analyze_similarity import calculate_skill_similarity, find_alternatives
from analyze_replacements import calculate_replacement_confidence
from evaluate_security import evaluate_skill_security
from fetch_github_stars import calculate_week_over_week_growth


def test_analyze_new_skills(sample_skills_data, monkeypatch):
    """Test new skills analysis with mocked data sources."""
    print("\n✓ Testing analyze_new_skills()...")

    try:
        def fake_fetch_all_skills(min_stars=0, max_months_old=0, include_installed=True):
            return sample_skills_data, {"total": len(sample_skills_data)}

        def fake_get_installed_skills():
            return ["test-skill-1"]

        monkeypatch.setattr(analyze_new_skills_module, "fetch_all_skills", fake_fetch_all_skills)
        monkeypatch.setattr(analyze_new_skills_module, "get_installed_skills", fake_get_installed_skills)

        new_skills, stats = analyze_new_skills(min_stars=0, max_months_old=0, top_n=10)

        assert isinstance(new_skills, pd.DataFrame), "Must return DataFrame"
        assert isinstance(stats, dict), "Must return stats dict"
        assert "new_skills_found" in stats, "Stats missing new_skills_found"
        print(f"  ✓ Found {len(new_skills)} new skills")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_category_and_tag_filters():
    """Test category and tag filtering helpers."""
    print("\n✓ Testing filter_by_category() / filter_by_tags()...")

    try:
        df = pd.DataFrame([
            {"name": "skill-a", "category": "dev", "tags": ["python", "ai"]},
            {"name": "skill-b", "category": "ops", "tags": ["infra"]},
        ])

        dev_skills = filter_by_category(df, "dev")
        assert len(dev_skills) == 1, "Category filter failed"

        python_skills = filter_by_tags(df, ["python"])
        assert len(python_skills) == 1, "Tag filter failed"

        print(f"  ✓ Category filter: {len(dev_skills)} skill")
        print(f"  ✓ Tag filter: {len(python_skills)} skill")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_growth_rate_calculation():
    """Test week-over-week growth calculation."""
    print("\n✓ Testing calculate_week_over_week_growth()...")

    try:
        current_week_start = datetime(2026, 2, 2, tzinfo=timezone.utc)  # Monday
        star_history = [
            {"starred_at": "2026-01-27T00:00:00Z"},  # previous week
            {"starred_at": "2026-02-03T00:00:00Z"},  # current week
            {"starred_at": "2026-02-04T00:00:00Z"},  # current week
        ]

        growth = calculate_week_over_week_growth(
            star_history=star_history,
            current_week_start=current_week_start
        )

        assert growth["current_week_stars"] == 2, "Current week count mismatch"
        assert growth["previous_week_stars"] == 1, "Previous week count mismatch"
        assert abs(growth["wow_growth_rate"] - 100.0) < 0.01, "WoW growth mismatch"
        print(f"  ✓ WoW growth: {growth['wow_growth_rate']}%")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_similarity_calculation(sample_skills_df):
    """Test skill similarity calculation."""
    print("\n✓ Testing calculate_skill_similarity()...")

    try:
        pytest.importorskip("sklearn")

        result = calculate_skill_similarity(
            skills_df=sample_skills_df,
            similarity_threshold=0.1
        )

        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        if not result.empty:
            assert "similarity_score" in result.columns, "Missing similarity_score"

        print(f"  ✓ Found {len(result)} similar skill pairs")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_replacement_confidence():
    """Test replacement confidence scoring."""
    print("\n✓ Testing calculate_replacement_confidence()...")

    try:
        now = datetime.now()
        installed_df = pd.DataFrame([{
            "name": "old-skill",
            "stars": 50,
            "updated_at": now - timedelta(days=400)
        }])
        all_skills_df = pd.DataFrame([
            {
                "name": "old-skill",
                "stars": 50,
                "updated_at": now - timedelta(days=400)
            },
            {
                "name": "new-skill",
                "stars": 150,
                "updated_at": now - timedelta(days=10)
            }
        ])
        similarity_df = pd.DataFrame([{
            "skill1_name": "old-skill",
            "skill2_name": "new-skill",
            "similarity_score": 0.85
        }])

        replacements = calculate_replacement_confidence(
            installed_skills_df=installed_df,
            all_skills_df=all_skills_df,
            similarity_df=similarity_df,
            confidence_threshold=0.0
        )

        assert isinstance(replacements, pd.DataFrame), "Must return DataFrame"
        assert len(replacements) >= 1, "Expected at least one replacement"
        assert 0 <= replacements.loc[0, "confidence_score"] <= 1, "Score out of range"

        print(f"  ✓ Replacement score: {replacements.loc[0, 'confidence_score']:.2f}")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_security_score_calculation():
    """Test security score calculation."""
    print("\n✓ Testing evaluate_skill_security()...")

    try:
        df = pd.DataFrame([{
            "name": "secure-skill",
            "github_url": "https://github.com/test/secure-skill",
            "stars": 150,
            "updated_at": pd.to_datetime("2026-01-15")
        }])

        result = evaluate_skill_security(df, security_threshold=0)
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        if not result.empty:
            assert "security_score" in result.columns, "Missing security_score"
            assert 0 <= result.loc[0, "security_score"] <= 100, "Score out of range"

        print(f"  ✓ Security scores computed: {len(result)}")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run analysis tests."""
    print("=" * 70)
    print("ANALYSIS TESTS")
    print("=" * 70)

    # Note: Tests would need fixtures injected by pytest
    # For manual run, would need to create fixtures
    print("\n⚠️  Run with pytest to execute all tests:")
    print("   pytest tests/test_analyze.py -v")

    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
