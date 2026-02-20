#!/usr/bin/env python3
"""
Analyze GitHub star growth rates for trending skills identification.
Calculates week-over-week (WoW) growth and identifies fastest growing skills.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_github_stars import fetch_star_history, calculate_week_over_week_growth
from parse_github_stars import parse_star_history_response, aggregate_by_week
from utils.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


def analyze_growth_rates(
    skills_df: pd.DataFrame,
    github_token: str,
    min_growth_rate: float = 5.0,
    top_n: int = 10
) -> Tuple[pd.DataFrame, Dict]:
    """
    Identify fastest growing skills by week-over-week star growth.

    Args:
        skills_df: DataFrame with skills (must have 'github_url' column)
        github_token: GitHub API token for fetching star history
        min_growth_rate: Minimum WoW growth rate percentage (default: 5%)
        top_n: Number of top growing skills to return

    Returns:
        Tuple of (growing_skills_df, statistics):
        - growing_skills_df: DataFrame with top N fastest growing skills
        - statistics: Dict with analysis metadata

    Raises:
        ValueError: If no skills meet growth rate threshold
        KeyError: If skills_df missing required columns

    Example:
        >>> from parse_skill_manager import parse_skill_manager_response
        >>> skills_df = parse_skill_manager_response(skills)
        >>> growing, stats = analyze_growth_rates(skills_df, token, min_growth_rate=5.0)
        >>> print(f"Found {len(growing)} fast-growing skills")
        >>> print(f"Top growing: {growing.iloc[0]['name']} ({growing.iloc[0]['wow_growth_rate']:.1f}%)")
    """
    logger.info(f"Starting growth rate analysis (min_growth={min_growth_rate}%, top_n={top_n})")

    # Validate input DataFrame
    if 'github_url' not in skills_df.columns:
        raise KeyError("skills_df must have 'github_url' column")

    # Filter skills with GitHub URLs
    skills_with_github = skills_df[skills_df['github_url'].notna()].copy()
    logger.info(f"Found {len(skills_with_github)} skills with GitHub URLs")

    if len(skills_with_github) == 0:
        raise ValueError("No skills with GitHub URLs found")

    # Calculate growth rates for all skills
    growth_results = []

    for idx, skill in skills_with_github.iterrows():
        try:
            # Fetch star history from GitHub API
            logger.debug(f"Fetching star history for {skill['name']}...")
            star_history = fetch_star_history(
                skill['github_url'],
                github_token=github_token
            )

            if not star_history:
                logger.warning(f"No star history for {skill['name']}")
                continue

            # Calculate WoW growth
            growth = calculate_week_over_week_growth(star_history)

            # Add to results
            growth_results.append({
                'name': skill['name'],
                'github_url': skill['github_url'],
                'stars': skill.get('stars', 0),
                'current_week_stars': growth['current_week_stars'],
                'previous_week_stars': growth['previous_week_stars'],
                'wow_growth_rate': growth['wow_growth_rate'],
                'total_stars': growth['total_stars'],
                'current_week_start': growth['current_week_start'],
                'author': skill.get('author', ''),
                'description': skill.get('description', '')
            })

        except Exception as e:
            logger.error(f"Failed to analyze {skill['name']}: {e}")
            continue

    logger.info(f"Calculated growth rates for {len(growth_results)} skills")

    if len(growth_results) == 0:
        raise ValueError("Failed to calculate growth rates for any skills")

    # Convert to DataFrame
    growth_df = pd.DataFrame(growth_results)

    # Filter by minimum growth rate
    logger.info(f"Applying minimum growth filter: {min_growth_rate}%")
    fast_growing = growth_df[growth_df['wow_growth_rate'] >= min_growth_rate].copy()

    logger.info(f"Found {len(fast_growing)} skills with >= {min_growth_rate}% growth")

    if len(fast_growing) == 0:
        raise ValueError(f"No skills found with >= {min_growth_rate}% WoW growth")

    # Sort by growth rate descending
    fast_growing = fast_growing.sort_values('wow_growth_rate', ascending=False).reset_index(drop=True)

    # Return top N
    top_growing = fast_growing.head(top_n)

    # Generate statistics
    statistics = {
        'total_skills_analyzed': len(skills_with_github),
        'growth_calculated_for': len(growth_results),
        'above_threshold': len(fast_growing),
        'top_n_returned': len(top_growing),
        'filters': {
            'min_growth_rate': min_growth_rate,
            'top_n': top_n
        },
        'analyzed_at': datetime.now().isoformat(),
        'growth_range': {
            'min': float(top_growing['wow_growth_rate'].min()) if len(top_growing) > 0 else 0.0,
            'max': float(top_growing['wow_growth_rate'].max()) if len(top_growing) > 0 else 0.0,
            'median': float(top_growing['wow_growth_rate'].median()) if len(top_growing) > 0 else 0.0
        }
    }

    logger.info(f"Analysis complete. Returning top {len(top_growing)} fastest growing skills")

    return top_growing, statistics


def filter_by_growth_range(
    growth_df: pd.DataFrame,
    min_rate: float,
    max_rate: Optional[float] = None
) -> pd.DataFrame:
    """
    Filter growing skills by growth rate range.

    Args:
        growth_df: DataFrame from analyze_growth_rates()
        min_rate: Minimum growth rate percentage
        max_rate: Maximum growth rate percentage (None = no upper limit)

    Returns:
        Filtered DataFrame

    Example:
        >>> growing, _ = analyze_growth_rates(skills_df, token)
        >>> moderate = filter_by_growth_range(growing, min_rate=5.0, max_rate=20.0)
        >>> explosive = filter_by_growth_range(growing, min_rate=50.0)
    """
    if 'wow_growth_rate' not in growth_df.columns:
        logger.warning("No 'wow_growth_rate' column in DataFrame")
        return growth_df

    filtered = growth_df[growth_df['wow_growth_rate'] >= min_rate]

    if max_rate is not None:
        filtered = filtered[filtered['wow_growth_rate'] <= max_rate]

    logger.info(f"Filtered to {len(filtered)} skills with growth in [{min_rate}, {max_rate or 'inf'}]%")

    return filtered


def aggregate_growth_by_author(growth_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate growth rates by skill author.

    Args:
        growth_df: DataFrame from analyze_growth_rates()

    Returns:
        Aggregated DataFrame with author-level statistics:
        - author: str
        - skill_count: int
        - avg_growth_rate: float
        - total_stars: int

    Example:
        >>> growing, _ = analyze_growth_rates(skills_df, token)
        >>> author_stats = aggregate_growth_by_author(growing)
        >>> print(author_stats.sort_values('avg_growth_rate', ascending=False).head())
    """
    if 'author' not in growth_df.columns:
        logger.warning("No 'author' column for aggregation")
        return pd.DataFrame()

    agg = growth_df.groupby('author').agg(
        skill_count=('name', 'count'),
        avg_growth_rate=('wow_growth_rate', 'mean'),
        total_stars=('total_stars', 'sum')
    ).reset_index()

    agg['avg_growth_rate'] = agg['avg_growth_rate'].round(2)

    return agg.sort_values('avg_growth_rate', ascending=False)


def format_growth_report(
    growth_df: pd.DataFrame,
    statistics: Dict,
    top_n: int = 10
) -> str:
    """
    Format growth rate analysis as human-readable report.

    Args:
        growth_df: DataFrame from analyze_growth_rates()
        statistics: Statistics dict from analyze_growth_rates()
        top_n: Number of skills to include in report

    Returns:
        Formatted string report

    Example:
        >>> growing, stats = analyze_growth_rates(skills_df, token)
        >>> report = format_growth_report(growing, stats)
        >>> print(report)
    """
    if growth_df.empty:
        return "No fast-growing skills found"

    lines = [
        f"## 🔥 Fastest Growing Skills\n",
        f"**Analysis Date:** {statistics['analyzed_at']}\n",
        "### Summary\n",
        f"- **Total Skills Analyzed:** {statistics['total_skills_analyzed']:,}",
        f"- **Growth Calculated For:** {statistics['growth_calculated_for']:,}",
        f"- **Above Threshold:** {statistics['above_threshold']:,}",
        f"- **Top Recommendations:** {statistics['top_n_returned']}\n",
        "### Filter Criteria\n",
        f"- **Minimum Growth Rate:** {statistics['filters']['min_growth_rate']}%",
        f"- **Top N:** {statistics['filters']['top_n']}\n",
        "### Growth Rate Range (Top Skills)\n",
        f"- **Minimum:** {statistics['growth_range']['min']:.2f}%",
        f"- **Maximum:** {statistics['growth_range']['max']:.2f}%",
        f"- **Median:** {statistics['growth_range']['median']:.2f}%\n",
        f"### Top {min(top_n, len(growth_df))} Fastest Growing Skills\n"
    ]

    # Add top N skills
    top_skills = growth_df.head(top_n)

    for idx, skill in top_skills.iterrows():
        lines.append(f"#### {idx + 1}. {skill['name']}\n")
        lines.append(f"- **WoW Growth Rate:** {skill['wow_growth_rate']:.2f}% 📈")
        lines.append(f"- **Total Stars:** {skill['total_stars']:,} ⭐")
        lines.append(f"- **Current Week:** {skill['current_week_stars']} new stars")
        lines.append(f"- **Previous Week:** {skill['previous_week_stars']} stars")

        if skill.get('author'):
            lines.append(f"- **Author:** {skill['author']}")

        if skill.get('description'):
            desc = skill['description'][:200]
            if len(skill['description']) > 200:
                desc += "..."
            lines.append(f"- **Description:** {desc}")

        if skill.get('github_url'):
            lines.append(f"- **GitHub:** {skill['github_url']}")

        lines.append("")

    return "\n".join(lines)


def export_growth_report(
    growth_df: pd.DataFrame,
    statistics: Dict,
    output_path: Optional[Path] = None
) -> Path:
    """
    Export growth rate analysis report to file.

    Args:
        growth_df: DataFrame from analyze_growth_rates()
        statistics: Statistics dict from analyze_growth_rates()
        output_path: Optional custom output path

    Returns:
        Path to exported report

    Example:
        >>> growing, stats = analyze_growth_rates(skills_df, token)
        >>> report_path = export_growth_report(growing, stats)
        >>> print(f"Report exported to: {report_path}")
    """
    if output_path is None:
        # Default: meta/reports/YYYY-MM-DD-growth-rates-report.md
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_path = Path(__file__).parent.parent / 'meta' / 'reports' / f'{date_str}-growth-rates-report.md'

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate report
    report = format_growth_report(growth_df, statistics)

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"Report exported to: {output_path}")

    return output_path


# Main for testing
if __name__ == "__main__":
    import os

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 70)
    print("ANALYZE GROWTH RATES - Test")
    print("=" * 70)

    # Check for GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Get token at: https://github.com/settings/tokens")
        print("   Required scope: public_repo")
        sys.exit(1)

    print(f"✓ GitHub token found: {github_token[:8]}...")

    # Test 1: Analyze growth rates (using small sample)
    print("\n1. Testing analyze_growth_rates():")
    try:
        # Create sample skills DataFrame
        from fetch_skill_manager import fetch_all_skills
        from parse_skill_manager import parse_skill_manager_response

        print("   Fetching skills from skill-manager...")
        skills, _ = fetch_all_skills(min_stars=100, max_months_old=3)
        df = parse_skill_manager_response(skills)

        # Limit to top 5 by stars for testing (avoid rate limits)
        test_df = df.nlargest(5, 'stars')

        print(f"   Testing with {len(test_df)} popular skills...")
        growing, stats = analyze_growth_rates(
            test_df,
            github_token,
            min_growth_rate=0.0,  # Low threshold for testing
            top_n=5
        )

        print(f"   ✓ Found {len(growing)} skills with growth data")
        print(f"   ✓ Statistics: {stats['growth_calculated_for']} analyzed")

        if len(growing) > 0:
            print(f"\n   Top 3 fastest growing:")
            for idx, skill in growing.head(3).iterrows():
                print(f"     {idx + 1}. {skill['name']} ({skill['wow_growth_rate']:.2f}% WoW)")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Filter by growth range
    print("\n2. Testing filter_by_growth_range():")
    moderate = filter_by_growth_range(growing, min_rate=5.0, max_rate=20.0)
    print(f"   ✓ Found {len(moderate)} skills with 5-20% growth")

    explosive = filter_by_growth_range(growing, min_rate=20.0)
    print(f"   ✓ Found {len(explosive)} skills with >20% growth")

    # Test 3: Aggregate by author
    print("\n3. Testing aggregate_growth_by_author():")
    author_stats = aggregate_growth_by_author(growing)
    print(f"   ✓ Author aggregation: {len(author_stats)} authors")
    if len(author_stats) > 0:
        print(f"\n   Top 3 authors by avg growth:")
        for _, author in author_stats.head(3).iterrows():
            print(f"     {author['author']}: {author['avg_growth_rate']:.2f}% avg ({author['skill_count']} skills)")

    # Test 4: Format report
    print("\n4. Testing format_growth_report():")
    report = format_growth_report(growing, stats, top_n=5)
    print("   ✓ Report generated:")
    print("\n" + "\n".join(["     " + line for line in report.split("\n")[:15]]))
    print("     ...")

    # Test 5: Export report
    print("\n5. Testing export_growth_report():")
    try:
        report_path = export_growth_report(growing, stats)
        print(f"   ✓ Report exported to: {report_path}")
        print(f"   ✓ File exists: {report_path.exists()}")
    except Exception as e:
        print(f"   ✗ Export error: {e}")

    print("\n✅ All tests completed")
