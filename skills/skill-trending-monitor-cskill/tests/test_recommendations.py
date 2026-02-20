#!/usr/bin/env python3
"""Tests for ML-based recommendations."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analyze_recommendations import (
    calculate_recommendation_score,
    get_personalized_recommendations,
    format_recommendations_report
)


# ============================================================
# Test Fixtures (local to this file)
# ============================================================

@pytest.fixture
def sample_skill():
    """Sample skill data as pd.Series."""
    return pd.Series({
        'name': 'test-skill',
        'stars': 100,
        'author': 'test-author',
        'description': 'A test skill for testing',
        'updated_at': datetime.now() - timedelta(days=30)
    })


@pytest.fixture
def sample_skills_df():
    """Sample skills DataFrame with 5 skills."""
    return pd.DataFrame([
        {
            'name': 'skill-a',
            'stars': 500,
            'author': 'author-a',
            'description': 'Code review and linting tool for Python',
            'updated_at': datetime.now() - timedelta(days=10)
        },
        {
            'name': 'skill-b',
            'stars': 200,
            'author': 'author-b',
            'description': 'Testing framework helper for Jest',
            'updated_at': datetime.now() - timedelta(days=60)
        },
        {
            'name': 'skill-c',
            'stars': 1000,
            'author': 'author-c',
            'description': 'Documentation generator for APIs',
            'updated_at': datetime.now() - timedelta(days=5)
        },
        {
            'name': 'installed-skill-1',
            'stars': 300,
            'author': 'author-d',
            'description': 'Code review tool for JavaScript',
            'updated_at': datetime.now() - timedelta(days=20)
        },
        {
            'name': 'installed-skill-2',
            'stars': 150,
            'author': 'author-e',
            'description': 'Testing utilities for Python pytest',
            'updated_at': datetime.now() - timedelta(days=40)
        }
    ])


@pytest.fixture(autouse=True)
def _force_lite_tfidf_backend(monkeypatch):
    """Force lightweight TF-IDF backend for tests to avoid slow sklearn import."""
    monkeypatch.setenv("PDT_TFIDF_BACKEND", "lite")


# ============================================================
# Tests for calculate_recommendation_score
# ============================================================

def test_calculate_recommendation_score_basic(sample_skill):
    """Test basic recommendation score calculation."""
    score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.5}
    )

    assert 0.0 <= score <= 1.0, "Score must be between 0 and 1"
    assert isinstance(score, float), "Score must be float"


def test_calculate_recommendation_score_high_similarity(sample_skill):
    """Test that high similarity increases score."""
    low_sim_score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.1}
    )

    high_sim_score = calculate_recommendation_score(
        sample_skill,
        installed_skills=['other-skill'],
        similarity_scores={'test-skill': 0.9}
    )

    assert high_sim_score > low_sim_score, "Higher similarity should increase score"


def test_calculate_recommendation_score_high_stars():
    """Test that high stars increases score."""
    low_star_skill = pd.Series({
        'name': 'low-star-skill',
        'stars': 10,
        'updated_at': datetime.now()
    })

    high_star_skill = pd.Series({
        'name': 'high-star-skill',
        'stars': 1000,
        'updated_at': datetime.now()
    })

    low_score = calculate_recommendation_score(
        low_star_skill,
        installed_skills=[],
        similarity_scores={}
    )

    high_score = calculate_recommendation_score(
        high_star_skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert high_score > low_score, "Higher stars should increase score"


def test_calculate_recommendation_score_recent_update():
    """Test that recent updates increase score."""
    old_skill = pd.Series({
        'name': 'old-skill',
        'stars': 100,
        'updated_at': datetime.now() - timedelta(days=300)
    })

    new_skill = pd.Series({
        'name': 'new-skill',
        'stars': 100,
        'updated_at': datetime.now() - timedelta(days=7)
    })

    old_score = calculate_recommendation_score(
        old_skill,
        installed_skills=[],
        similarity_scores={}
    )

    new_score = calculate_recommendation_score(
        new_skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert new_score > old_score, "More recent update should increase score"


def test_calculate_recommendation_score_custom_weights(sample_skill):
    """Test custom weights."""
    # All weight on popularity
    score = calculate_recommendation_score(
        sample_skill,
        installed_skills=[],
        similarity_scores={},
        weights={
            'popularity': 1.0,
            'recency': 0.0,
            'similarity': 0.0,
            'category': 0.0,
            'momentum': 0.0
        }
    )

    assert 0.0 <= score <= 1.0, "Score with custom weights must be in range"


def test_calculate_recommendation_score_missing_updated_at():
    """Test handling of missing updated_at."""
    skill = pd.Series({
        'name': 'skill-no-date',
        'stars': 100,
        'updated_at': None  # Missing date
    })

    score = calculate_recommendation_score(
        skill,
        installed_skills=[],
        similarity_scores={}
    )

    assert 0.0 <= score <= 1.0, "Should handle missing updated_at gracefully"


# ============================================================
# Tests for get_personalized_recommendations
# ============================================================

def test_get_personalized_recommendations_returns_dataframe(sample_skills_df):
    """Test that function returns a DataFrame."""
    # Mock installed skills
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1', 'installed-skill-2'],
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    assert isinstance(result, pd.DataFrame), "Must return DataFrame"


def test_get_personalized_recommendations_excludes_installed(sample_skills_df):
    """Test that installed skills are excluded."""
    installed = ['installed-skill-1', 'installed-skill-2']

    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=installed,
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    # Check no installed skills in results
    for name in installed:
        assert name not in result['name'].values, f"Installed skill {name} should be excluded"


def test_get_personalized_recommendations_respects_max_results(sample_skills_df):
    """Test that max_results is respected."""
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=50,
        max_results=2  # Only want 2 results
    )

    assert len(result) <= 2, "Should respect max_results"


def test_get_personalized_recommendations_sorted_by_score(sample_skills_df):
    """Test that results are sorted by recommendation_score descending."""
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=50,
        max_results=10
    )

    if len(result) > 1:
        scores = result['recommendation_score'].tolist()
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"


def test_get_personalized_recommendations_empty_candidates(sample_skills_df):
    """Test handling when no candidates pass filters."""
    # Use very high min_stars to filter out everything
    result = get_personalized_recommendations(
        sample_skills_df,
        installed_skills=['installed-skill-1'],
        exclude_installed=True,
        min_stars=10000,  # Very high threshold
        max_results=10
    )

    assert isinstance(result, pd.DataFrame), "Should return empty DataFrame, not None"
    assert len(result) == 0, "Should have no results"


# ============================================================
# Tests for format_recommendations_report
# ============================================================

def test_format_recommendations_report_basic():
    """Test report formatting with valid data."""
    recommendations = pd.DataFrame([
        {
            'name': 'skill-a',
            'recommendation_score': 0.85,
            'stars': 500,
            'author': 'author-a',
            'description': 'Test description',
            'similarity_to_installed': 0.7,
            'reason': 'Similar to installed'
        }
    ])

    report = format_recommendations_report(recommendations)

    assert 'Personalized Skill Recommendations' in report
    assert 'skill-a' in report
    assert '0.85' in report or '.850' in report  # Score formatting may vary
    assert '500' in report  # Stars


def test_format_recommendations_report_empty():
    """Test empty recommendations handling."""
    report = format_recommendations_report(pd.DataFrame())

    assert 'No personalized recommendations' in report


def test_format_recommendations_report_respects_top_n():
    """Test that top_n parameter is respected."""
    recommendations = pd.DataFrame([
        {'name': f'skill-{i}', 'recommendation_score': 0.9 - i*0.1,
         'stars': 100, 'author': 'author', 'description': 'desc',
         'similarity_to_installed': 0.5, 'reason': 'test'}
        for i in range(5)
    ])

    report = format_recommendations_report(recommendations, top_n=2)

    assert 'skill-0' in report
    assert 'skill-1' in report
    # skill-2, skill-3, skill-4 should NOT be in report
    assert 'skill-4' not in report


def test_format_recommendations_report_contains_scoring_table():
    """Test that report contains scoring formula table."""
    recommendations = pd.DataFrame([
        {'name': 'skill-a', 'recommendation_score': 0.85,
         'stars': 500, 'author': 'author', 'description': 'desc',
         'similarity_to_installed': 0.7, 'reason': 'test'}
    ])

    report = format_recommendations_report(recommendations)

    assert 'Scoring Formula' in report
    assert 'Similarity' in report
    assert '30%' in report
    assert 'Popularity' in report
    assert '25%' in report
