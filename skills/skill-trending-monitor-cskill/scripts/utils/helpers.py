#!/usr/bin/env python3
"""
Temporal helper functions for skill-trending-monitor-cskill.
Provides week-based temporal context and date handling utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def get_current_week() -> Tuple[datetime, datetime]:
    """
    Get current week boundaries (Monday 00:00 - Sunday 23:59 UTC).

    Returns:
        Tuple[datetime, datetime]: (week_start, week_end) in UTC

    Example:
        >>> start, end = get_current_week()
        >>> start.weekday()  # Monday = 0
        0
        >>> end.weekday()    # Sunday = 6
        6
    """
    now = datetime.now(timezone.utc)

    # Find Monday of current week (weekday 0)
    days_since_monday = now.weekday()
    week_start = (now - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Find Sunday of current week (weekday 6)
    days_until_sunday = 6 - now.weekday()
    week_end = (now + timedelta(days=days_until_sunday)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    return week_start, week_end


def get_week_number(date: Optional[datetime] = None) -> int:
    """
    Get ISO week number for a given date.

    Args:
        date: Date to get week number for (defaults to now)

    Returns:
        int: ISO week number (1-53)

    Example:
        >>> get_week_number(datetime(2026, 2, 3))  # First week of Feb 2026
        6
    """
    if date is None:
        date = datetime.now(timezone.utc)

    return date.isocalendar()[1]


def get_week_with_fallback(week: Optional[int] = None) -> Tuple[int, int]:
    """
    Auto-detect current week or use provided, with previous week fallback.

    This function implements temporal context fallback logic:
    - If week=None: use current week, fallback to previous if needed
    - If week specified: use that week, fallback to week-1 if needed

    Args:
        week: Requested week number (None for auto-detect)

    Returns:
        Tuple[int, int]: (primary_week, fallback_week)

    Example:
        >>> primary, fallback = get_week_with_fallback()
        >>> primary == get_week_number()
        True
        >>> fallback == primary - 1
        True
    """
    if week is None:
        primary_week = get_week_number()
    else:
        primary_week = week

    # Fallback is always previous week
    fallback_week = primary_week - 1 if primary_week > 1 else 53

    return primary_week, fallback_week


def should_try_previous_week(
    week: int,
    data_availability_threshold_days: int = 3
) -> bool:
    """
    Determine if previous week should be tried for data availability.

    Logic: If current week is less than N days old, data might be incomplete.

    Args:
        week: Week number to check
        data_availability_threshold_days: Days to wait for complete data

    Returns:
        bool: True if should try previous week

    Example:
        >>> # If today is Monday (week just started)
        >>> should_try_previous_week(get_week_number(), threshold_days=3)
        True  # Week less than 3 days old, use previous week
    """
    current_week = get_week_number()

    if week != current_week:
        # Requested week is not current week, use as-is
        return False

    # Check how many days into current week we are
    week_start, _ = get_current_week()
    now = datetime.now(timezone.utc)
    days_into_week = (now - week_start).days

    # If less than threshold days into week, suggest previous week
    return days_into_week < data_availability_threshold_days


def format_week_message(
    week_used: int,
    week_requested: Optional[int],
    fallback_occurred: bool = False
) -> str:
    """
    Generate user-friendly message about which week was used.

    This provides transparency about temporal context decisions.

    Args:
        week_used: The week number that was actually used
        week_requested: The week number that was requested (None if auto)
        fallback_occurred: Whether fallback to previous week occurred

    Returns:
        str: Human-readable message

    Example:
        >>> format_week_message(5, None, False)
        'Using current week (Week 5)'

        >>> format_week_message(4, 5, True)
        'Week 5 data incomplete, using Week 4 instead'
    """
    if week_requested is None:
        # Auto-detected week
        if fallback_occurred:
            return f"Current week data incomplete, using previous week (Week {week_used})"
        else:
            return f"Using current week (Week {week_used})"
    else:
        # Explicitly requested week
        if fallback_occurred:
            return f"Week {week_requested} data incomplete, using Week {week_used} instead"
        else:
            if week_used == get_week_number():
                return f"Using requested week (Week {week_used}, current week)"
            else:
                return f"Using requested week (Week {week_used})"


def get_week_date_range(week: int, year: Optional[int] = None) -> Tuple[datetime, datetime]:
    """
    Get date range for a specific ISO week number.

    Args:
        week: ISO week number (1-53)
        year: Year (defaults to current year)

    Returns:
        Tuple[datetime, datetime]: (week_start, week_end) in UTC

    Example:
        >>> start, end = get_week_date_range(1, 2026)
        >>> start.strftime('%Y-%m-%d')
        '2025-12-29'  # Monday of ISO week 1, 2026
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    # ISO week 1 is the week with the first Thursday of the year
    jan_4 = datetime(year, 1, 4, tzinfo=timezone.utc)
    week_1_start = jan_4 - timedelta(days=jan_4.weekday())

    # Calculate target week start
    week_start = week_1_start + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return week_start, week_end


def format_iso_week(week: int, year: Optional[int] = None) -> str:
    """
    Format week number as ISO week string.

    Args:
        week: ISO week number
        year: Year (defaults to current)

    Returns:
        str: Formatted as "2026-W06"

    Example:
        >>> format_iso_week(6, 2026)
        '2026-W06'
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    return f"{year}-W{week:02d}"


def parse_iso_week(iso_week: str) -> Tuple[int, int]:
    """
    Parse ISO week string to year and week number.

    Args:
        iso_week: String in format "2026-W06"

    Returns:
        Tuple[int, int]: (year, week)

    Raises:
        ValueError: If format is invalid

    Example:
        >>> parse_iso_week("2026-W06")
        (2026, 6)
    """
    try:
        parts = iso_week.split('-W')
        if len(parts) != 2:
            raise ValueError(f"Invalid ISO week format: {iso_week}")

        year = int(parts[0])
        week = int(parts[1])

        if not 1 <= week <= 53:
            raise ValueError(f"Week number {week} out of range (1-53)")

        return year, week
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid ISO week format: {iso_week}") from e


def get_weeks_ago(weeks: int) -> int:
    """
    Get week number N weeks ago.

    Args:
        weeks: Number of weeks to go back

    Returns:
        int: Week number N weeks ago

    Example:
        >>> current = get_week_number()
        >>> two_weeks_ago = get_weeks_ago(2)
        >>> two_weeks_ago == current - 2 or two_weeks_ago > 50  # Handle year boundary
        True
    """
    current_week = get_week_number()
    target_week = current_week - weeks

    # Handle year boundary (simple approach, assumes same year)
    if target_week < 1:
        target_week = 53 + target_week

    return target_week


def main():
    """Test temporal helper functions."""
    print("=== Temporal Helpers Test ===\n")

    # Test 1: Current week
    print("1. Current Week:")
    start, end = get_current_week()
    print(f"   Start: {start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   End:   {end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Week:  {get_week_number()}")

    # Test 2: Week with fallback
    print("\n2. Week with Fallback:")
    primary, fallback = get_week_with_fallback()
    print(f"   Primary:  Week {primary}")
    print(f"   Fallback: Week {fallback}")

    # Test 3: Should try previous week?
    print("\n3. Should Try Previous Week:")
    should_fallback = should_try_previous_week(get_week_number())
    print(f"   Result: {should_fallback}")

    # Test 4: Format messages
    print("\n4. Week Messages:")
    msg1 = format_week_message(5, None, False)
    print(f"   Auto-detect: {msg1}")
    msg2 = format_week_message(4, 5, True)
    print(f"   Fallback:    {msg2}")

    # Test 5: ISO week formatting
    print("\n5. ISO Week Format:")
    iso = format_iso_week(6, 2026)
    print(f"   Formatted: {iso}")
    year, week = parse_iso_week(iso)
    print(f"   Parsed:    Year={year}, Week={week}")

    # Test 6: Weeks ago
    print("\n6. Weeks Ago:")
    current = get_week_number()
    two_weeks_ago = get_weeks_ago(2)
    print(f"   Current:       Week {current}")
    print(f"   2 weeks ago:   Week {two_weeks_ago}")


if __name__ == "__main__":
    main()
