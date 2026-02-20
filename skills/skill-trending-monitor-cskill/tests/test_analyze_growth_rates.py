#!/usr/bin/env python3
"""Tests for analyze_growth_rates module."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import analyze_growth_rates as analyze_growth_rates_module
from analyze_growth_rates import (
    analyze_growth_rates,
    filter_by_growth_range,
    aggregate_growth_by_author,
    format_growth_report,
    export_growth_report,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def skills_with_github():
    """Sample skills DataFrame with GitHub URLs."""
    return pd.DataFrame([
        {
            "name": "skill-a",
            "github_url": "https://github.com/test/skill-a",
            "stars": 120,
            "author": "author-a",
            "description": "Test skill A description",
        },
        {
            "name": "skill-b",
            "github_url": "https://github.com/test/skill-b",
            "stars": 80,
            "author": "author-b",
            "description": "Test skill B description",
        },
        {
            "name": "skill-c",
            "github_url": "https://github.com/test/skill-c",
            "stars": 200,
            "author": "author-a",
            "description": "Test skill C description",
        },
    ])


# ============================================================
# analyze_growth_rates
# ============================================================

def test_analyze_growth_rates_success(skills_with_github, monkeypatch):
    """Test analyze_growth_rates with mocked GitHub data."""
    growth_by_repo = {
        "https://github.com/test/skill-a": {
            "current_week_stars": 10,
            "previous_week_stars": 5,
            "wow_growth_rate": 100.0,
            "total_stars": 300,
            "current_week_start": "2026-02-03T00:00:00+00:00",
            "previous_week_start": "2026-01-27T00:00:00+00:00",
        },
        "https://github.com/test/skill-b": {
            "current_week_stars": 3,
            "previous_week_stars": 4,
            "wow_growth_rate": -25.0,
            "total_stars": 120,
            "current_week_start": "2026-02-03T00:00:00+00:00",
            "previous_week_start": "2026-01-27T00:00:00+00:00",
        },
        "https://github.com/test/skill-c": {
            "current_week_stars": 8,
            "previous_week_stars": 4,
            "wow_growth_rate": 100.0,
            "total_stars": 500,
            "current_week_start": "2026-02-03T00:00:00+00:00",
            "previous_week_start": "2026-01-27T00:00:00+00:00",
        },
    }

    def fake_fetch_star_history(repo_url, github_token=None):
        return [{"repo": repo_url}]

    def fake_calculate_week_over_week_growth(star_history):
        repo_url = star_history[0]["repo"]
        return growth_by_repo[repo_url]

    monkeypatch.setattr(analyze_growth_rates_module, "fetch_star_history", fake_fetch_star_history)
    monkeypatch.setattr(
        analyze_growth_rates_module,
        "calculate_week_over_week_growth",
        fake_calculate_week_over_week_growth,
    )

    top_growing, stats = analyze_growth_rates(
        skills_with_github,
        github_token="test-token",
        min_growth_rate=0.0,
        top_n=2,
    )

    assert len(top_growing) == 2
    assert top_growing.iloc[0]["wow_growth_rate"] == pytest.approx(100.0)
    assert stats["total_skills_analyzed"] == 3
    assert stats["growth_calculated_for"] == 3
    assert stats["above_threshold"] == 2
    assert stats["top_n_returned"] == 2


def test_analyze_growth_rates_missing_github_url():
    """Missing github_url column should raise KeyError."""
    df = pd.DataFrame([{"name": "skill-a"}])
    with pytest.raises(KeyError):
        analyze_growth_rates(df, github_token="token")


def test_analyze_growth_rates_no_github_urls():
    """No GitHub URLs should raise ValueError."""
    df = pd.DataFrame([
        {"name": "skill-a", "github_url": None},
        {"name": "skill-b", "github_url": None},
    ])
    with pytest.raises(ValueError):
        analyze_growth_rates(df, github_token="token")


def test_analyze_growth_rates_no_growth_results(monkeypatch):
    """Empty star history for all skills should raise ValueError."""
    df = pd.DataFrame([{"name": "skill-a", "github_url": "https://github.com/test/skill-a"}])

    def fake_fetch_star_history(repo_url, github_token=None):
        return []

    monkeypatch.setattr(analyze_growth_rates_module, "fetch_star_history", fake_fetch_star_history)

    with pytest.raises(ValueError):
        analyze_growth_rates(df, github_token="token")


def test_analyze_growth_rates_below_threshold(skills_with_github, monkeypatch):
    """All skills below threshold should raise ValueError."""
    def fake_fetch_star_history(repo_url, github_token=None):
        return [{"repo": repo_url}]

    def fake_calculate_week_over_week_growth(star_history):
        return {
            "current_week_stars": 1,
            "previous_week_stars": 1,
            "wow_growth_rate": 0.0,
            "total_stars": 10,
            "current_week_start": "2026-02-03T00:00:00+00:00",
            "previous_week_start": "2026-01-27T00:00:00+00:00",
        }

    monkeypatch.setattr(analyze_growth_rates_module, "fetch_star_history", fake_fetch_star_history)
    monkeypatch.setattr(
        analyze_growth_rates_module,
        "calculate_week_over_week_growth",
        fake_calculate_week_over_week_growth,
    )

    with pytest.raises(ValueError):
        analyze_growth_rates(skills_with_github, github_token="token", min_growth_rate=5.0)


# ============================================================
# filter_by_growth_range
# ============================================================

def test_filter_by_growth_range_missing_column():
    """Missing wow_growth_rate column returns input DataFrame."""
    df = pd.DataFrame([{"name": "skill-a"}])
    result = filter_by_growth_range(df, min_rate=5.0)
    pd.testing.assert_frame_equal(result, df)


def test_filter_by_growth_range_min_max():
    """Filter by min and max growth rate."""
    df = pd.DataFrame({
        "name": ["a", "b", "c", "d"],
        "wow_growth_rate": [1.0, 5.0, 10.0, 20.0],
    })

    result = filter_by_growth_range(df, min_rate=5.0, max_rate=15.0)
    assert list(result["name"]) == ["b", "c"]


# ============================================================
# aggregate_growth_by_author
# ============================================================

def test_aggregate_growth_by_author_missing_author():
    """Missing author column should return empty DataFrame."""
    df = pd.DataFrame([{"name": "skill-a", "wow_growth_rate": 10.0}])
    result = aggregate_growth_by_author(df)
    assert result.empty


def test_aggregate_growth_by_author():
    """Aggregation should compute counts and averages."""
    df = pd.DataFrame([
        {"name": "skill-a", "author": "author-a", "wow_growth_rate": 10.0, "total_stars": 100},
        {"name": "skill-b", "author": "author-a", "wow_growth_rate": 20.0, "total_stars": 200},
        {"name": "skill-c", "author": "author-b", "wow_growth_rate": 5.0, "total_stars": 50},
    ])

    result = aggregate_growth_by_author(df)

    assert list(result.columns) == ["author", "skill_count", "avg_growth_rate", "total_stars"]
    assert result.iloc[0]["author"] == "author-a"
    assert result.iloc[0]["skill_count"] == 2
    assert result.iloc[0]["avg_growth_rate"] == pytest.approx(15.0)
    assert result.iloc[0]["total_stars"] == 300


# ============================================================
# format_growth_report / export_growth_report
# ============================================================

def test_format_growth_report_empty():
    """Empty growth DataFrame should return a simple message."""
    report = format_growth_report(pd.DataFrame(), statistics={})
    assert report == "No fast-growing skills found"


def test_format_growth_report_contents():
    """Report should include summary and skill details."""
    growth_df = pd.DataFrame([{
        "name": "skill-a",
        "wow_growth_rate": 12.34,
        "total_stars": 500,
        "current_week_stars": 10,
        "previous_week_stars": 8,
        "author": "author-a",
        "description": "A" * 50,
        "github_url": "https://github.com/test/skill-a",
    }])

    stats = {
        "total_skills_analyzed": 10,
        "growth_calculated_for": 9,
        "above_threshold": 3,
        "top_n_returned": 1,
        "filters": {"min_growth_rate": 5.0, "top_n": 1},
        "analyzed_at": "2026-02-04T10:00:00",
        "growth_range": {"min": 12.34, "max": 12.34, "median": 12.34},
    }

    report = format_growth_report(growth_df, stats, top_n=1)
    assert "Fastest Growing Skills" in report
    assert "skill-a" in report
    assert "Total Skills Analyzed" in report
    assert "WoW Growth Rate" in report


def test_export_growth_report(tmp_path):
    """Export should write report to file and return path."""
    growth_df = pd.DataFrame([{
        "name": "skill-a",
        "wow_growth_rate": 12.34,
        "total_stars": 500,
        "current_week_stars": 10,
        "previous_week_stars": 8,
        "author": "",
        "description": "",
        "github_url": "https://github.com/test/skill-a",
    }])

    stats = {
        "total_skills_analyzed": 1,
        "growth_calculated_for": 1,
        "above_threshold": 1,
        "top_n_returned": 1,
        "filters": {"min_growth_rate": 5.0, "top_n": 1},
        "analyzed_at": "2026-02-04T10:00:00",
        "growth_range": {"min": 12.34, "max": 12.34, "median": 12.34},
    }

    output_path = tmp_path / "growth-report.md"
    result_path = export_growth_report(growth_df, stats, output_path=output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert "Fastest Growing Skills" in output_path.read_text(encoding="utf-8")
