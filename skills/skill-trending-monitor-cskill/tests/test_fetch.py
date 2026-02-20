#!/usr/bin/env python3
"""
Tests for API fetch functions.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from fetch_skills import fetch_skill_manager_data, fetch_github_stars


def test_fetch_skill_manager_basic():
    """Test fetching skill-manager database."""
    print("\n✓ Testing fetch_skill_manager_data()...")

    # Test with mock database path
    mock_data = [
        {"name": "test-skill", "stars": 100, "description": "Test"}
    ]

    with patch('builtins.open', create=True) as mock_open:
        import json
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_data)

        result = fetch_skill_manager_data("mock_path.json")

        assert isinstance(result, list), "Result must be list"
        assert len(result) == 1, "Expected 1 skill"
        assert result[0]['name'] == 'test-skill', "Name mismatch"

    print("  ✓ Fetch successful")


def test_fetch_github_stars_with_cache(tmp_path, mock_github_api, github_success_response):
    """Test GitHub API fetch with caching."""
    print("\n✓ Testing fetch_github_stars() with cache...")

    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()

    mock_github_api.return_value = Mock(
        status_code=200,
        json=Mock(return_value=github_success_response)
    )

    # First call - should hit API
    result1 = fetch_github_stars(
        "test/repo",
        cache_dir=str(cache_dir),
        cache_ttl=3600
    )

    # Second call - should use cache
    result2 = fetch_github_stars(
        "test/repo",
        cache_dir=str(cache_dir),
        cache_ttl=3600
    )

    # Verify results
    assert result1['stargazers_count'] == 150
    assert result2['stargazers_count'] == 150

    # API should only be called once (second uses cache)
    assert mock_github_api.call_count == 1, "Cache not working"

    print("  ✓ Cache working correctly")


def test_fetch_with_rate_limiting(mock_github_api, github_rate_limit_response):
    """Test rate limiting on GitHub API."""
    print("\n✓ Testing rate limiting...")

    # Simulate rate limit exceeded
    mock_github_api.return_value = github_rate_limit_response

    result = fetch_github_stars("test/repo", max_retries=0)

    # Should return error or None
    assert result is None or 'error' in result

    print("  ✓ Rate limit handling working")


def test_fetch_error_handling(mock_github_api):
    """Test error handling for network failures."""
    print("\n✓ Testing error handling...")

    # Simulate network error
    mock_github_api.side_effect = ConnectionError("Network error")

    result = fetch_github_stars("test/repo", max_retries=0)

    # Should handle gracefully
    assert result is None or 'error' in result

    print("  ✓ Error handling working")


def test_fetch_with_authentication(mock_github_api, make_github_response):
    """Test GitHub API with authentication token."""
    print("\n✓ Testing authentication...")

    mock_github_api.return_value = make_github_response(stars=200)

    result = fetch_github_stars(
        "test/repo",
        github_token="test_token_123"
    )

    # Verify token was used in headers
    call_args = mock_github_api.call_args
    headers = call_args[1]['headers']
    assert 'Authorization' in headers, "Token not in headers"
    assert headers['Authorization'] == 'token test_token_123'

    print("  ✓ Authentication working")


def main():
    """Run fetch tests."""
    print("=" * 70)
    print("FETCH TESTS")
    print("=" * 70)

    tests = [
        test_fetch_skill_manager_basic,
        test_fetch_github_stars_with_cache,
        test_fetch_with_rate_limiting,
        test_fetch_error_handling,
        test_fetch_with_authentication,
    ]

    passed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
        else:
            passed += 1
    print(f"\nResults: {passed}/{len(tests)} passed")

    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
