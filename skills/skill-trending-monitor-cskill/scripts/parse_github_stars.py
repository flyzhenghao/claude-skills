#!/usr/bin/env python3
"""
Parse GitHub star history into time-series format.
Converts stargazer events into analyzable DataFrames with week buckets.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.validators.temporal_validator import validate_temporal_consistency
from utils.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


def parse_star_history_response(
    star_history: List[Dict],
    repo_url: str
) -> pd.DataFrame:
    """
    Parse GitHub star history into time-series DataFrame.

    Args:
        star_history: List of star events from fetch_github_stars.py
        repo_url: Repository URL for identification

    Returns:
        DataFrame with schema:
        - repo_url: str
        - starred_at: datetime (UTC)
        - user: str
        - week_start: datetime (Monday 00:00 UTC)
        - cumulative_stars: int

    Raises:
        ValueError: If star_history is empty or invalid

    Example:
        >>> from fetch_github_stars import fetch_star_history
        >>> stars = fetch_star_history('https://github.com/user/repo', token)
        >>> df = parse_star_history_response(stars, 'https://github.com/user/repo')
        >>> print(df.shape)
        (150, 5)
    """
    if not star_history:
        raise ValueError("Star history cannot be empty")

    if not isinstance(star_history, list):
        raise ValueError(f"Expected list, got {type(star_history)}")

    logger.info(f"Parsing {len(star_history)} star events for {repo_url}")

    # Extract star events
    records = []
    for star in star_history:
        starred_at_str = star.get('starred_at')
        user = star.get('user', {}).get('login', 'unknown')

        if not starred_at_str:
            logger.debug(f"Skipping star event with missing timestamp: {star}")
            continue

        # Parse timestamp to datetime (UTC)
        try:
            starred_at = _parse_timestamp(starred_at_str)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{starred_at_str}': {e}")
            continue

        records.append({
            'repo_url': repo_url,
            'starred_at': starred_at,
            'user': user
        })

    if not records:
        raise ValueError("No valid star events after parsing")

    logger.info(f"Parsed {len(records)} valid star events")

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Sort by starred_at
    df = df.sort_values('starred_at').reset_index(drop=True)

    # Add week buckets
    df = _add_week_buckets(df)

    # Add cumulative star counts
    df = _add_cumulative_stars(df)

    # Validate temporal consistency
    _validate_temporal_data(df)

    logger.info(f"Final DataFrame shape: {df.shape}")

    return df


def parse_multiple_repos_stars(
    repos_stars: Dict[str, List[Dict]]
) -> pd.DataFrame:
    """
    Parse star history for multiple repositories.

    Args:
        repos_stars: Dict mapping repo_url to star_history list

    Returns:
        Combined DataFrame with all repositories

    Example:
        >>> repos = {
        ...     'https://github.com/user/repo1': stars1,
        ...     'https://github.com/user/repo2': stars2
        ... }
        >>> df = parse_multiple_repos_stars(repos)
        >>> print(df['repo_url'].nunique())
        2
    """
    dfs = []

    for repo_url, star_history in repos_stars.items():
        try:
            df = parse_star_history_response(star_history, repo_url)
            dfs.append(df)
        except Exception as e:
            logger.error(f"Failed to parse star history for {repo_url}: {e}")

    if not dfs:
        raise ValueError("No valid star histories parsed")

    # Combine all DataFrames
    combined = pd.concat(dfs, ignore_index=True)

    logger.info(f"Combined {len(dfs)} repositories, total {len(combined)} star events")

    return combined


def aggregate_by_week(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate star events by week.

    Args:
        df: Parsed star history DataFrame

    Returns:
        Aggregated DataFrame with weekly statistics:
        - repo_url: str
        - week_start: datetime
        - stars_this_week: int
        - cumulative_stars: int

    Example:
        >>> df = parse_star_history_response(stars, repo_url)
        >>> weekly = aggregate_by_week(df)
        >>> print(weekly.head())
    """
    if 'week_start' not in df.columns:
        df = _add_week_buckets(df)

    # Group by repo and week
    weekly = df.groupby(['repo_url', 'week_start']).agg(
        stars_this_week=('starred_at', 'count')
    ).reset_index()

    # Calculate cumulative stars per repo
    weekly = weekly.sort_values(['repo_url', 'week_start'])
    weekly['cumulative_stars'] = weekly.groupby('repo_url')['stars_this_week'].cumsum()

    return weekly


def format_time_series_report(df: pd.DataFrame, repo_url: str) -> str:
    """
    Format star history as human-readable time series report.

    Args:
        df: Parsed star history DataFrame
        repo_url: Repository URL to report on

    Returns:
        Formatted string report

    Example:
        >>> report = format_time_series_report(df, repo_url)
        >>> print(report)
    """
    repo_df = df[df['repo_url'] == repo_url]

    if repo_df.empty:
        return f"No star history data for {repo_url}"

    lines = [
        f"## Star History: {repo_url}\n",
        f"**Total Stars:** {len(repo_df):,}",
        f"**First Star:** {repo_df['starred_at'].min().strftime('%Y-%m-%d')}",
        f"**Latest Star:** {repo_df['starred_at'].max().strftime('%Y-%m-%d')}",
        f"**Time Span:** {(repo_df['starred_at'].max() - repo_df['starred_at'].min()).days} days\n"
    ]

    # Recent activity (last 4 weeks)
    lines.append("### Recent Activity (Last 4 Weeks)\n")
    weekly = aggregate_by_week(repo_df)
    recent = weekly.tail(4)

    for _, week in recent.iterrows():
        lines.append(
            f"- Week of {week['week_start'].strftime('%Y-%m-%d')}: "
            f"{week['stars_this_week']} stars (total: {week['cumulative_stars']:,})"
        )

    return "\n".join(lines)


def _parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse GitHub timestamp string to datetime object (UTC).

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Datetime object in UTC

    Example:
        >>> dt = _parse_timestamp("2024-01-15T10:30:00Z")
        >>> print(dt.tzinfo)
        UTC
    """
    # Handle Z suffix (GitHub format)
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'

    # Parse to datetime
    dt = datetime.fromisoformat(timestamp_str)

    # Ensure UTC timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)

    return dt


def _add_week_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add week_start column (Monday 00:00 UTC) for each star event.

    Args:
        df: DataFrame with starred_at column

    Returns:
        DataFrame with week_start column added
    """
    def get_week_start(dt):
        """Get Monday 00:00 UTC for the week containing dt."""
        # Days since Monday (0 = Monday, 6 = Sunday)
        days_since_monday = dt.weekday()

        # Subtract to get to Monday
        week_start = dt - timedelta(days=days_since_monday)

        # Set to 00:00:00
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        return week_start

    df['week_start'] = df['starred_at'].apply(get_week_start)

    return df


def _add_cumulative_stars(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cumulative_stars column showing running total.

    Args:
        df: Sorted DataFrame with starred_at

    Returns:
        DataFrame with cumulative_stars column added
    """
    # Cumulative count per repo
    df['cumulative_stars'] = df.groupby('repo_url').cumcount() + 1

    return df


def _validate_temporal_data(df: pd.DataFrame) -> None:
    """
    Validate temporal consistency of star history data.

    Args:
        df: Parsed star history DataFrame

    Raises:
        ValueError: If critical temporal issues found
    """
    from utils.validators.temporal_validator import validate_temporal_consistency

    # Validate starred_at column
    report = validate_temporal_consistency(df[['starred_at']].rename(columns={'starred_at': 'year'}))

    if report.has_critical_issues():
        error_msg = f"Temporal validation failed: {report.get_summary()}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Log warnings if any
    for warning in report.get_warnings():
        logger.warning(f"Temporal validation warning: {warning}")


# Main for testing
if __name__ == "__main__":
    import sys
    from fetch_github_stars import fetch_star_history
    import os

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== parse_github_stars.py Test ===\n")

    # Check for GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Get token at: https://github.com/settings/tokens")
        print("   Required scope: public_repo")
        sys.exit(1)

    print(f"✓ GitHub token found: {github_token[:8]}...")

    # Test 1: Parse star history
    print("\n1. Testing parse_star_history_response():")
    test_repo = 'https://github.com/anthropics/skills'

    try:
        # Fetch stars
        stars = fetch_star_history(test_repo, github_token)
        print(f"   ✓ Fetched {len(stars)} stars")

        # Parse
        df = parse_star_history_response(stars, test_repo)
        print(f"   ✓ Parsed DataFrame: {df.shape}")
        print(f"   ✓ Columns: {list(df.columns)}")
        print(f"   ✓ Date range: {df['starred_at'].min()} to {df['starred_at'].max()}")
        print(f"\n   Sample:\n{df.head(3)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Aggregate by week
    print("\n2. Testing aggregate_by_week():")
    weekly = aggregate_by_week(df)
    print(f"   ✓ Weekly aggregation: {weekly.shape}")
    print(f"   ✓ Weeks: {len(weekly)}")
    print(f"\n   Last 4 weeks:\n{weekly.tail(4)}")

    # Test 3: Format report
    print("\n3. Testing format_time_series_report():")
    report = format_time_series_report(df, test_repo)
    print(report)

    # Test 4: Validate temporal data
    print("\n4. Testing temporal validation:")
    try:
        _validate_temporal_data(df)
        print("   ✓ Temporal validation passed")
    except Exception as e:
        print(f"   ✗ Validation error: {e}")

    # Test 5: Week bucket calculation
    print("\n5. Testing week bucket calculation:")
    print(f"   ✓ Unique weeks: {df['week_start'].nunique()}")
    print(f"   ✓ First week: {df['week_start'].min()}")
    print(f"   ✓ Last week: {df['week_start'].max()}")

    print("\n✅ All tests completed")
