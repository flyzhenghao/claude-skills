#!/usr/bin/env python3
"""
Tests for temporal helpers and utility functions.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from utils.helpers import (
    get_current_week,
    get_week_number,
    get_week_with_fallback,
    should_try_previous_week,
    format_week_message,
    get_week_date_range,
    format_iso_week,
    parse_iso_week
)


def test_get_current_week():
    """Test current week boundaries and week number."""
    print("\n✓ Testing get_current_week()...")

    try:
        week_start, week_end = get_current_week()
        week_num = get_week_number()

        assert week_start.weekday() == 0, "Week should start on Monday"
        assert week_end.weekday() == 6, "Week should end on Sunday"
        assert week_start <= week_end, "Week start must be before week end"
        assert 1 <= week_num <= 53, "Week number out of range"

        print(f"  ✓ Current week: {week_num}")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_week_with_fallback():
    """Test week fallback logic."""
    print("\n✓ Testing get_week_with_fallback()...")

    try:
        # Test with explicit week
        primary, fallback = get_week_with_fallback(10)

        assert primary == 10, "Primary should be 10"
        assert fallback == 9, "Fallback should be 9"
        assert primary - fallback == 1, "Fallback should be previous week"

        print(f"  ✓ Fallback: {primary} → {fallback}")

        # Test with None (current week)
        current_week = get_week_number()
        primary_none, fallback_none = get_week_with_fallback(None)
        expected_fallback = primary_none - 1 if primary_none > 1 else 53

        assert primary_none == current_week, "Should use current week when None"
        assert fallback_none == expected_fallback, "Fallback should be previous week"

        print(f"  ✓ Auto-detect: {primary_none} → {fallback_none}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_should_try_previous_week():
    """Test logic for determining if previous week should be tried."""
    print("\n✓ Testing should_try_previous_week()...")

    try:
        current_week = get_week_number()
        week_start, _ = get_current_week()
        days_into_week = (datetime.now(timezone.utc) - week_start).days

        expected = days_into_week < 3
        should_try = should_try_previous_week(current_week, data_availability_threshold_days=3)
        assert should_try == expected, "Current week fallback logic mismatch"
        print(f"  ✓ Current week logic: should_try={should_try}")

        # Non-current week should not fallback
        other_week = current_week - 1 if current_week > 1 else 53
        should_try_other = should_try_previous_week(other_week)
        assert should_try_other is False, "Non-current week should not fallback"
        print(f"  ✓ Non-current week: should_try={should_try_other}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_format_week_message():
    """Test week message formatting."""
    print("\n✓ Testing format_week_message()...")

    try:
        # Requested week matches used week
        msg1 = format_week_message(5, 5, False)
        assert 'Week 5' in msg1, "Must mention week"
        print(f"  ✓ Same week: {msg1}")

        # Requested week differs from used week (fallback)
        msg2 = format_week_message(4, 5, True)
        assert 'Week 4' in msg2, "Must mention week used"
        assert 'Week 5' in msg2, "Must mention week requested"
        print(f"  ✓ Fallback: {msg2}")

        # Auto-detected week
        msg3 = format_week_message(6, None, False)
        assert 'Week 6' in msg3, "Must mention week used"
        assert 'current' in msg3.lower(), "Must indicate current week"
        print(f"  ✓ Auto-detect: {msg3}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_cache_key_generation():
    """Test cache key generation for consistent caching."""
    print("\n✓ Testing cache key generation...")

    try:
        from utils.cache_manager import generate_cache_key

        # Test identical inputs produce same key
        key1 = generate_cache_key("test-skill", 2024, "github")
        key2 = generate_cache_key("test-skill", 2024, "github")
        assert key1 == key2, "Same inputs should produce same key"
        print(f"  ✓ Consistent: {key1}")

        # Test different inputs produce different keys
        key3 = generate_cache_key("test-skill", 2023, "github")
        assert key1 != key3, "Different inputs should produce different keys"
        print(f"  ✓ Unique: {key1} ≠ {key3}")

        # Test key format
        assert isinstance(key1, str), "Key must be string"
        assert len(key1) > 0, "Key must not be empty"
        print(f"  ✓ Valid format: {len(key1)} chars")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_rate_limiter():
    """Test rate limiter utility for GitHub API."""
    print("\n✓ Testing rate limiter...")

    try:
        from utils.rate_limiter import RateLimiter

        # Create rate limiter with test limits
        limiter = RateLimiter(max_requests=5, time_window=1)  # 5 requests per second

        # Test acquiring tokens
        for i in range(5):
            acquired = limiter.acquire()
            assert acquired is True, f"Should acquire token {i+1}/5"

        print(f"  ✓ Acquired 5 tokens successfully")

        # Test exceeding limit
        acquired_over = limiter.acquire(wait=False)
        assert acquired_over is False, "Should fail to acquire token after limit"
        print(f"  ✓ Correctly enforced rate limit")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_iso_week_parsing():
    """Test ISO week parsing utilities."""
    print("\n✓ Testing ISO week parsing...")

    try:
        # Test ISO week formatting/parsing
        iso_week = format_iso_week(6, 2026)
        year, week = parse_iso_week(iso_week)
        assert year == 2026, "Year should be 2026"
        assert week == 6, "Week should be 6"
        print(f"  ✓ ISO week: {iso_week}")

        # Test week date range
        week_start, week_end = get_week_date_range(1, 2026)
        assert week_start.weekday() == 0, "Week start should be Monday"
        assert week_end.weekday() == 6, "Week end should be Sunday"
        print(f"  ✓ Week range: {week_start.date()} → {week_end.date()}")

        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run helper tests."""
    print("=" * 70)
    print("HELPER TESTS")
    print("=" * 70)

    tests = [
        test_get_current_week,
        test_week_with_fallback,
        test_should_try_previous_week,
        test_format_week_message,
        test_cache_key_generation,
        test_rate_limiter,
        test_iso_week_parsing,
    ]

    passed = sum(1 for test in tests if test())
    print(f"\nResults: {passed}/{len(tests)} passed")

    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
