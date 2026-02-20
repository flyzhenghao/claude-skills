# Codex Task M1: Mock GitHub API in Tests

## Priority
Medium

## Objective
Enhance existing tests to use comprehensive GitHub API mocking with pytest fixtures.

## Context
- Tests exist in `tests/test_fetch.py` and already use `unittest.mock`
- Current mocking is inline per test function
- Need centralized, reusable fixtures in `tests/conftest.py`

## Requirements

### 1. Add GitHub API Fixtures to `tests/conftest.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

@pytest.fixture
def mock_github_api():
    """Centralized GitHub API mock fixture."""
    with patch('requests.get') as mock_get:
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
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1704067200',
        'Retry-After': '60'
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
```

### 2. Add Response Factory Fixture

```python
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
```

### 3. Update `tests/test_fetch.py` to Use Fixtures

Refactor existing tests to use the new fixtures:

```python
def test_fetch_github_stars_success(mock_github_api, github_success_response):
    """Test successful GitHub API fetch using fixtures."""
    mock_github_api.return_value = Mock(
        status_code=200,
        json=Mock(return_value=github_success_response)
    )

    result = fetch_github_stars("test/repo")

    assert result['stargazers_count'] == 150
    assert mock_github_api.called

def test_fetch_rate_limited(mock_github_api, github_rate_limit_response):
    """Test rate limit handling using fixtures."""
    mock_github_api.return_value = github_rate_limit_response

    result = fetch_github_stars("test/repo", max_retries=0)

    assert result is None or 'error' in result
```

## Files to Modify

1. `tests/conftest.py` - Add all fixtures
2. `tests/test_fetch.py` - Refactor to use fixtures (keep existing tests working)

## Testing

```bash
cd skill-trending-monitor-cskill
python3 -m pytest tests/test_fetch.py -v
```

## Acceptance Criteria

- [ ] All fixtures added to `conftest.py`
- [ ] Existing tests still pass
- [ ] At least 2 tests refactored to use fixtures
- [ ] `pytest tests/test_fetch.py -v` passes

## Dependencies

None - standalone task

## Notes

- Keep backward compatibility with existing tests
- Use `Mock` from `unittest.mock` (already imported in test files)
- pytest fixtures auto-inject by parameter name
