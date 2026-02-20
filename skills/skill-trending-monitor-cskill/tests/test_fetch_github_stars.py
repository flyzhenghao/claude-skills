#!/usr/bin/env python3
"""
Tests for fetch_github_stars.py.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from fetch_github_stars import (
    extract_repo_info,
    fetch_star_history,
    calculate_week_over_week_growth,
    fetch_multiple_repos_stars,
)


class DummyRateLimiter:
    def __init__(self):
        self.wait_calls = 0
        self.update_calls = 0

    def wait_if_needed(self):
        self.wait_calls += 1
        return 0.0

    def update_from_headers(self, headers):
        self.update_calls += 1


class DummyCache:
    def __init__(self, initial=None):
        self.initial = initial
        self.get_calls = []
        self.set_calls = []

    def get(self, key, cache_type='metadata'):
        self.get_calls.append((key, cache_type))
        return self.initial

    def set(self, key, value, cache_type='metadata'):
        self.set_calls.append((key, value, cache_type))


def make_star_event(ts):
    return {"starred_at": ts, "user": {"login": "tester"}}


def test_extract_repo_info_valid_urls():
    assert extract_repo_info("https://github.com/owner/repo") == ("owner", "repo")
    assert extract_repo_info("https://github.com/owner/repo.git") == ("owner", "repo")
    assert extract_repo_info("https://github.com/owner/repo/") == ("owner", "repo")


def test_extract_repo_info_invalid_url():
    with pytest.raises(ValueError):
        extract_repo_info("git@github.com:owner/repo.git")


def test_fetch_star_history_requires_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ValueError):
        fetch_star_history(
            "https://github.com/owner/repo",
            github_token=None,
            rate_limiter=DummyRateLimiter(),
            cache=DummyCache(),
        )


def test_fetch_star_history_uses_cache():
    cached = [make_star_event("2026-01-01T00:00:00Z")]
    cache = DummyCache(initial=cached)

    with patch("fetch_github_stars.requests.get") as mock_get:
        result = fetch_star_history(
            "https://github.com/owner/repo",
            github_token="token-123",
            rate_limiter=DummyRateLimiter(),
            cache=cache,
        )

    assert result == cached
    mock_get.assert_not_called()
    assert cache.set_calls == []


def test_fetch_star_history_success_single_page():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    response = Mock()
    response.headers = {"X-RateLimit-Remaining": "4999"}
    response.raise_for_status.return_value = None
    response.json.return_value = [make_star_event("2026-01-01T00:00:00Z")]

    with patch("fetch_github_stars.requests.get", return_value=response) as mock_get:
        result = fetch_star_history(
            "https://github.com/owner/repo",
            github_token="token-123",
            rate_limiter=rate_limiter,
            cache=cache,
        )

    assert len(result) == 1
    assert rate_limiter.wait_calls == 1
    assert rate_limiter.update_calls == 1
    assert len(cache.set_calls) == 1

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "token token-123"
    assert kwargs["params"] == {"page": 1, "per_page": 100}
    assert kwargs["timeout"] == 30


def test_fetch_star_history_pagination():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    response_page_1 = Mock()
    response_page_1.headers = {}
    response_page_1.raise_for_status.return_value = None
    response_page_1.json.return_value = [make_star_event("2026-01-01T00:00:00Z")] * 100

    response_page_2 = Mock()
    response_page_2.headers = {}
    response_page_2.raise_for_status.return_value = None
    response_page_2.json.return_value = [make_star_event("2026-01-02T00:00:00Z")] * 50

    with patch(
        "fetch_github_stars.requests.get",
        side_effect=[response_page_1, response_page_2],
    ) as mock_get:
        result = fetch_star_history(
            "https://github.com/owner/repo",
            github_token="token-123",
            rate_limiter=rate_limiter,
            cache=cache,
        )

    assert len(result) == 150
    assert mock_get.call_count == 2
    assert rate_limiter.wait_calls == 2

    pages = [call.kwargs["params"]["page"] for call in mock_get.call_args_list]
    assert pages == [1, 2]


def test_fetch_star_history_404_returns_empty():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    response = Mock()
    response.headers = {}
    response.status_code = 404
    response.raise_for_status.side_effect = requests.HTTPError(response=response)

    with patch("fetch_github_stars.requests.get", return_value=response):
        result = fetch_star_history(
            "https://github.com/owner/repo",
            github_token="token-123",
            rate_limiter=rate_limiter,
            cache=cache,
        )

    assert result == []


def test_fetch_star_history_403_with_reset_retries():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    response_403 = Mock()
    response_403.headers = {"X-RateLimit-Reset": "101"}
    response_403.status_code = 403
    response_403.raise_for_status.side_effect = requests.HTTPError(response=response_403)

    response_ok = Mock()
    response_ok.headers = {}
    response_ok.raise_for_status.return_value = None
    response_ok.json.return_value = []

    with patch(
        "fetch_github_stars.requests.get",
        side_effect=[response_403, response_ok],
    ) as mock_get, patch("fetch_github_stars.time.sleep") as mock_sleep, patch(
        "fetch_github_stars.time.time",
        return_value=100,
    ):
        result = fetch_star_history(
            "https://github.com/owner/repo",
            github_token="token-123",
            rate_limiter=rate_limiter,
            cache=cache,
        )

    assert result == []
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(2)


def test_fetch_star_history_403_without_reset_raises():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    response = Mock()
    response.headers = {}
    response.status_code = 403
    response.raise_for_status.side_effect = requests.HTTPError(response=response)

    with patch("fetch_github_stars.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            fetch_star_history(
                "https://github.com/owner/repo",
                github_token="token-123",
                rate_limiter=rate_limiter,
                cache=cache,
            )


def test_fetch_star_history_network_error_propagates():
    rate_limiter = DummyRateLimiter()
    cache = DummyCache()

    with patch(
        "fetch_github_stars.requests.get",
        side_effect=requests.RequestException("Network error"),
    ):
        with pytest.raises(requests.RequestException):
            fetch_star_history(
                "https://github.com/owner/repo",
                github_token="token-123",
                rate_limiter=rate_limiter,
                cache=cache,
            )


def test_calculate_week_over_week_growth_basic():
    current_week_start = datetime(2026, 2, 2, tzinfo=timezone.utc)

    star_history = [
        make_star_event("2026-01-27T12:00:00Z"),
        make_star_event("2026-02-03T12:00:00Z"),
        make_star_event("2026-02-04T12:00:00Z"),
    ]

    result = calculate_week_over_week_growth(
        star_history,
        current_week_start=current_week_start,
    )

    assert result["previous_week_stars"] == 1
    assert result["current_week_stars"] == 2
    assert result["wow_growth_rate"] == 100.0
    assert result["total_stars"] == 3


def test_calculate_week_over_week_growth_no_previous():
    current_week_start = datetime(2026, 2, 2, tzinfo=timezone.utc)

    star_history = [
        make_star_event("2026-02-03T00:00:00Z"),
    ]

    result = calculate_week_over_week_growth(
        star_history,
        current_week_start=current_week_start,
    )

    assert result["previous_week_stars"] == 0
    assert result["current_week_stars"] == 1
    assert result["wow_growth_rate"] == float("inf")


def test_fetch_multiple_repos_stars_success_and_error(monkeypatch):
    def fake_fetch(repo_url, github_token=None, rate_limiter=None, cache=None):
        if "good" in repo_url:
            return [make_star_event("2026-02-03T00:00:00Z")]
        raise RuntimeError("boom")

    monkeypatch.setattr("fetch_github_stars.fetch_star_history", fake_fetch)

    results = fetch_multiple_repos_stars(
        [
            "https://github.com/good/repo",
            "https://github.com/bad/repo",
        ],
        github_token="token-123",
        rate_limiter=DummyRateLimiter(),
        cache=DummyCache(),
    )

    assert "star_history" in results["https://github.com/good/repo"]
    assert "growth" in results["https://github.com/good/repo"]
    assert results["https://github.com/bad/repo"]["error"] == "boom"
