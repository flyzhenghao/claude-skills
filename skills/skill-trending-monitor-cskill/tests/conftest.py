#!/usr/bin/env python3
"""
Shared pytest fixtures for skill-trending-monitor-cskill tests.

Provides:
- Sample skill data fixtures
- Mock API response fixtures
- Temporary directory fixtures
- Configuration fixtures
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


@pytest.fixture
def sample_skills_data():
    """Sample skill-manager data for testing."""
    return [
        {
            "name": "test-skill-1",
            "author": "test-author",
            "github_url": "https://github.com/test/skill-1",
            "stars": 150,
            "forks": 25,
            "updated_at": "2026-01-15",
            "description": "Test skill for code analysis and review"
        },
        {
            "name": "test-skill-2",
            "author": "another-author",
            "github_url": "https://github.com/test/skill-2",
            "stars": 85,
            "forks": 12,
            "updated_at": "2026-02-01",
            "description": "Test skill for data processing and analysis"
        },
        {
            "name": "test-skill-3",
            "author": "test-author",
            "github_url": "https://github.com/test/skill-3",
            "stars": 200,
            "forks": 40,
            "updated_at": "2025-12-20",
            "description": "Test skill for code analysis tools"
        },
        {
            "name": "test-skill-4",
            "author": "community",
            "github_url": "https://github.com/community/skill-4",
            "stars": 45,
            "forks": 8,
            "updated_at": "2026-01-28",
            "description": "Test skill for documentation generation"
        },
        {
            "name": "test-skill-5",
            "author": "test-author",
            "github_url": "https://github.com/test/skill-5",
            "stars": 10,
            "forks": 2,
            "updated_at": "2025-08-15",
            "description": "Test skill - outdated"
        }
    ]


@pytest.fixture
def sample_skills_df(sample_skills_data):
    """Sample skills DataFrame for testing."""
    return pd.DataFrame(sample_skills_data)


@pytest.fixture
def mock_github_api():
    """Centralized GitHub API mock fixture."""
    with patch("requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def github_success_response():
    """Standard successful GitHub API response."""
    return {
        "stargazers_count": 150,
        "forks_count": 25,
        "watchers_count": 150,
        "open_issues_count": 5,
        "updated_at": "2026-01-15T10:30:00Z",
        "pushed_at": "2026-01-14T08:00:00Z",
        "license": {"key": "mit", "name": "MIT License"},
        "topics": ["claude", "ai", "skills"]
    }


@pytest.fixture
def github_rate_limit_response():
    """Rate limit exceeded response."""
    mock = Mock()
    mock.status_code = 429
    mock.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1704067200",
        "Retry-After": "60"
    }
    mock.json.return_value = {
        "message": "API rate limit exceeded"
    }
    return mock


@pytest.fixture
def github_not_found_response():
    """Repository not found response."""
    mock = Mock()
    mock.status_code = 404
    mock.json.return_value = {
        "message": "Not Found",
        "documentation_url": "https://docs.github.com/rest"
    }
    return mock


@pytest.fixture
def github_auth_required_response():
    """Authentication required response."""
    mock = Mock()
    mock.status_code = 401
    mock.json.return_value = {
        "message": "Bad credentials"
    }
    return mock


@pytest.fixture
def make_github_response():
    """Factory to create custom GitHub responses."""
    def _make_response(
        status_code=200,
        stars=100,
        forks=10,
        updated_at="2026-01-15T10:30:00Z",
        license_key="mit"
    ):
        mock = Mock()
        mock.status_code = status_code
        mock.json.return_value = {
            "stargazers_count": stars,
            "forks_count": forks,
            "updated_at": updated_at,
            "license": {"key": license_key} if license_key else None
        }
        return mock
    return _make_response


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response for star counts."""
    return {
        "stargazers_count": 150,
        "forks_count": 25,
        "updated_at": "2026-01-15T10:30:00Z",
        "license": {"spdx_id": "MIT"},
        "pushed_at": "2026-01-15T10:30:00Z"
    }


@pytest.fixture
def mock_github_history():
    """Mock GitHub commit history for growth rate calculation."""
    base_date = datetime.now()
    return [
        {
            "commit": {
                "committer": {
                    "date": (base_date - timedelta(days=7)).isoformat() + "Z"
                }
            }
        },
        {
            "commit": {
                "committer": {
                    "date": (base_date - timedelta(days=14)).isoformat() + "Z"
                }
            }
        }
    ]


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary cache directory for testing."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "github": {
            "token": "test_token_123",
            "rate_limit": {
                "max_requests_per_hour": 5000
            }
        },
        "thresholds": {
            "quality": {
                "min_stars": 50,
                "max_months_old": 6
            },
            "similarity": {
                "threshold": 0.75,
                "max_features": 500
            },
            "replacement": {
                "confidence_threshold": 0.70,
                "star_weight": 0.4,
                "recency_weight": 0.3,
                "similarity_weight": 0.3
            },
            "security": {
                "threshold": 70,
                "stars_weight": 0.30,
                "activity_weight": 0.25,
                "license_weight": 0.25,
                "update_weight": 0.20
            }
        },
        "cache": {
            "enabled": True,
            "ttl": {
                "github": 86400,
                "skills": 604800,
                "analysis": 3600
            }
        }
    }


@pytest.fixture
def sample_installed_skills(tmp_path):
    """Sample installed skills directory for testing."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create sample skill directories
    for i in range(1, 4):
        skill_dir = skills_dir / f"installed-skill-{i}"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(f"# Installed Skill {i}\n\nTest skill {i} installed locally.")

    return skills_dir


@pytest.fixture
def sample_similarity_matrix():
    """Sample similarity matrix for testing."""
    import numpy as np
    from scipy.sparse import csr_matrix

    # 5 skills, 5x5 similarity matrix
    data = [
        [1.0, 0.85, 0.40, 0.20, 0.10],
        [0.85, 1.0, 0.50, 0.15, 0.05],
        [0.40, 0.50, 1.0, 0.30, 0.25],
        [0.20, 0.15, 0.30, 1.0, 0.60],
        [0.10, 0.05, 0.25, 0.60, 1.0]
    ]
    return csr_matrix(data)


@pytest.fixture
def mock_validation_report():
    """Mock validation report for testing."""
    from dataclasses import dataclass
    from enum import Enum

    class ValidationLevel(Enum):
        CRITICAL = "critical"
        WARNING = "warning"
        INFO = "info"

    @dataclass
    class ValidationResult:
        check_name: str
        level: ValidationLevel
        passed: bool
        message: str

    return [
        ValidationResult("not_empty", ValidationLevel.CRITICAL, True, "Data present"),
        ValidationResult("correct_type", ValidationLevel.CRITICAL, True, "Type correct"),
        ValidationResult("required_columns", ValidationLevel.CRITICAL, True, "All columns present")
    ]
