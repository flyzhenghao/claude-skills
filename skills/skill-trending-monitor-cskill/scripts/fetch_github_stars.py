#!/usr/bin/env python3
"""
Fetch star history from GitHub API for growth rate calculation.
Uses rate limiting and caching for efficient API usage.
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import sys
import os
import time

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.rate_limiter import RateLimiter
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


def extract_repo_info(github_url: str) -> Tuple[str, str]:
    """
    Extract owner and repo name from GitHub URL.

    Args:
        github_url: GitHub repository URL

    Returns:
        Tuple of (owner, repo)

    Raises:
        ValueError: If URL format is invalid

    Example:
        >>> owner, repo = extract_repo_info('https://github.com/user/repo')
        >>> print(f"{owner}/{repo}")
        user/repo
    """
    # Remove trailing slash and .git
    url = github_url.rstrip('/').replace('.git', '')

    # Extract from various URL formats
    if 'github.com/' in url:
        parts = url.split('github.com/')[-1].split('/')
        if len(parts) >= 2:
            return parts[0], parts[1]

    raise ValueError(f"Invalid GitHub URL format: {github_url}")


def fetch_star_history(
    repo_url: str,
    github_token: Optional[str] = None,
    rate_limiter: Optional[RateLimiter] = None,
    cache: Optional[CacheManager] = None
) -> List[Dict]:
    """
    Fetch complete star history for a GitHub repository.

    Uses GitHub's Stargazers API with Accept: application/vnd.github.v3.star+json
    to get timestamps for each star.

    Args:
        repo_url: GitHub repository URL
        github_token: GitHub API token (required for 5,000/hour limit)
        rate_limiter: RateLimiter instance (created if None)
        cache: CacheManager instance (created if None)

    Returns:
        List of star events with timestamps:
        [
            {
                'starred_at': '2024-01-15T10:30:00Z',
                'user': 'username'
            },
            ...
        ]

    Raises:
        requests.HTTPError: If API request fails
        ValueError: If GitHub token is not provided

    Example:
        >>> token = os.getenv('GITHUB_TOKEN')
        >>> stars = fetch_star_history('https://github.com/user/repo', token)
        >>> print(f"Total stars: {len(stars)}")
    """
    # Validate token
    if not github_token:
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN environment variable or pass github_token parameter.\n"
                "Get token at: https://github.com/settings/tokens (requires 'public_repo' scope)"
            )

    # Initialize components
    if rate_limiter is None:
        rate_limiter = RateLimiter(requests_per_hour=5000)

    if cache is None:
        cache = CacheManager()

    # Extract repo info
    owner, repo = extract_repo_info(repo_url)
    cache_key = f"{owner}/{repo}"

    # Check cache (24-hour TTL for star history)
    cached = cache.get(cache_key, cache_type='metadata')
    if cached:
        logger.info(f"Using cached star history for {cache_key}")
        return cached

    logger.info(f"Fetching star history for {cache_key} from GitHub API")

    # GitHub API configuration
    api_url = f"https://api.github.com/repos/{owner}/{repo}/stargazers"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3.star+json',  # Required for timestamps
        'User-Agent': 'skill-trending-monitor-cskill'
    }

    all_stars = []
    page = 1
    per_page = 100  # Max allowed by GitHub

    while True:
        # Wait for rate limit if needed
        rate_limiter.wait_if_needed()

        # Make API request
        params = {'page': page, 'per_page': per_page}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)

            # Update rate limiter from response headers
            rate_limiter.update_from_headers(response.headers)

            # Check for errors
            response.raise_for_status()

            # Parse response
            page_stars = response.json()

            if not page_stars:
                # No more pages
                break

            all_stars.extend(page_stars)

            logger.debug(f"Fetched page {page}: {len(page_stars)} stars")

            # Check if we've reached the end
            if len(page_stars) < per_page:
                break

            page += 1

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Repository not found: {cache_key}")
                return []
            elif e.response.status_code == 403:
                # Rate limit exceeded
                reset_time = int(e.response.headers.get('X-RateLimit-Reset', 0))
                if reset_time:
                    wait_seconds = reset_time - int(time.time())
                    logger.warning(f"Rate limit exceeded. Waiting {wait_seconds}s until reset.")
                    time.sleep(wait_seconds + 1)
                    continue
                else:
                    raise
            else:
                logger.error(f"GitHub API error: {e}")
                raise

    logger.info(f"Fetched {len(all_stars)} total stars for {cache_key}")

    # Cache results
    cache.set(cache_key, all_stars, cache_type='metadata')

    return all_stars


def calculate_week_over_week_growth(
    star_history: List[Dict],
    current_week_start: Optional[datetime] = None
) -> Dict:
    """
    Calculate week-over-week growth rate from star history.

    Args:
        star_history: List of star events with 'starred_at' timestamps
        current_week_start: Start of current week (defaults to this Monday 00:00 UTC)

    Returns:
        Dict with growth statistics:
        {
            'current_week_stars': int,
            'previous_week_stars': int,
            'wow_growth_rate': float (percentage, -100 to +inf),
            'total_stars': int,
            'current_week_start': str (ISO),
            'previous_week_start': str (ISO)
        }

    Example:
        >>> stars = fetch_star_history('https://github.com/user/repo', token)
        >>> growth = calculate_week_over_week_growth(stars)
        >>> print(f"WoW growth: {growth['wow_growth_rate']:.1f}%")
    """
    # Default to current week (Monday 00:00 UTC)
    if current_week_start is None:
        now = datetime.now(timezone.utc)
        days_since_monday = now.weekday()
        current_week_start = now - timedelta(days=days_since_monday)
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate week boundaries
    previous_week_start = current_week_start - timedelta(days=7)
    current_week_end = current_week_start + timedelta(days=7)

    # Convert timestamps and count stars per week
    current_week_count = 0
    previous_week_count = 0

    for star in star_history:
        starred_at_str = star.get('starred_at')
        if not starred_at_str:
            continue

        # Parse timestamp
        starred_at = datetime.fromisoformat(starred_at_str.replace('Z', '+00:00'))

        # Count by week
        if previous_week_start <= starred_at < current_week_start:
            previous_week_count += 1
        elif current_week_start <= starred_at < current_week_end:
            current_week_count += 1

    # Calculate growth rate
    if previous_week_count > 0:
        wow_growth_rate = ((current_week_count - previous_week_count) / previous_week_count) * 100
    else:
        # No previous week data - can't calculate meaningful growth
        wow_growth_rate = 0.0 if current_week_count == 0 else float('inf')

    return {
        'current_week_stars': current_week_count,
        'previous_week_stars': previous_week_count,
        'wow_growth_rate': wow_growth_rate,
        'total_stars': len(star_history),
        'current_week_start': current_week_start.isoformat(),
        'previous_week_start': previous_week_start.isoformat()
    }


def fetch_multiple_repos_stars(
    repo_urls: List[str],
    github_token: Optional[str] = None,
    rate_limiter: Optional[RateLimiter] = None,
    cache: Optional[CacheManager] = None
) -> Dict[str, Dict]:
    """
    Fetch star history and growth rates for multiple repositories.

    Args:
        repo_urls: List of GitHub repository URLs
        github_token: GitHub API token
        rate_limiter: RateLimiter instance (created if None)
        cache: CacheManager instance (created if None)

    Returns:
        Dict mapping repo URL to growth statistics:
        {
            'https://github.com/user/repo': {
                'star_history': [...],
                'growth': {...}
            },
            ...
        }

    Example:
        >>> urls = ['https://github.com/user/repo1', 'https://github.com/user/repo2']
        >>> results = fetch_multiple_repos_stars(urls, token)
        >>> for url, data in results.items():
        ...     print(f"{url}: {data['growth']['wow_growth_rate']:.1f}%")
    """
    # Initialize shared components
    if rate_limiter is None:
        rate_limiter = RateLimiter(requests_per_hour=5000)

    if cache is None:
        cache = CacheManager()

    results = {}

    for repo_url in repo_urls:
        try:
            # Fetch star history
            star_history = fetch_star_history(
                repo_url,
                github_token=github_token,
                rate_limiter=rate_limiter,
                cache=cache
            )

            # Calculate growth
            growth = calculate_week_over_week_growth(star_history)

            results[repo_url] = {
                'star_history': star_history,
                'growth': growth
            }

        except Exception as e:
            logger.error(f"Error fetching stars for {repo_url}: {e}")
            results[repo_url] = {
                'error': str(e)
            }

    return results


# Main for testing
if __name__ == "__main__":
    import sys

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== fetch_github_stars.py Test ===\n")

    # Check for GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Get token at: https://github.com/settings/tokens")
        print("   Required scope: public_repo")
        sys.exit(1)

    print(f"✓ GitHub token found: {github_token[:8]}...")

    # Test 1: Extract repo info
    print("\n1. Testing extract_repo_info():")
    test_urls = [
        'https://github.com/anthropics/skills',
        'https://github.com/user/repo.git',
        'github.com/owner/project/'
    ]
    for url in test_urls:
        try:
            owner, repo = extract_repo_info(url)
            print(f"   ✓ {url} → {owner}/{repo}")
        except ValueError as e:
            print(f"   ✗ {url} → {e}")

    # Test 2: Fetch star history (small repo for testing)
    print("\n2. Testing fetch_star_history():")
    test_repo = 'https://github.com/anthropics/skills'  # Official Anthropic skills repo

    try:
        stars = fetch_star_history(test_repo, github_token)
        print(f"   ✓ Fetched {len(stars)} stars")
        if stars:
            print(f"   ✓ First star: {stars[0].get('starred_at')}")
            print(f"   ✓ Last star: {stars[-1].get('starred_at')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Calculate growth
    print("\n3. Testing calculate_week_over_week_growth():")
    if stars:
        growth = calculate_week_over_week_growth(stars)
        print(f"   ✓ Current week stars: {growth['current_week_stars']}")
        print(f"   ✓ Previous week stars: {growth['previous_week_stars']}")
        print(f"   ✓ WoW growth rate: {growth['wow_growth_rate']:.2f}%")
        print(f"   ✓ Total stars: {growth['total_stars']}")

    # Test 4: Rate limiter status
    print("\n4. Testing rate limiter integration:")
    limiter = RateLimiter(requests_per_hour=5000)
    status = limiter.get_status()
    print(f"   ✓ Tokens remaining: {status['tokens']:.0f}/{status['tokens_max']}")

    # Test 5: Cache verification
    print("\n5. Testing cache:")
    cache = CacheManager()
    owner, repo = extract_repo_info(test_repo)
    cache_key = f"{owner}/{repo}"
    cached = cache.get(cache_key, cache_type='metadata')
    if cached:
        print(f"   ✓ Cached data found: {len(cached)} stars")
    else:
        print("   ℹ No cached data (expected on first run)")

    print("\n✅ All tests completed")
