#!/usr/bin/env python3
"""
Analyze and identify new skills not locally installed.
Applies quality filters and recommends high-value skills for installation.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_skill_manager import fetch_all_skills, get_installed_skills
from parse_skill_manager import parse_skill_manager_response, filter_quality_skills

logger = logging.getLogger(__name__)


def analyze_new_skills(
    min_stars: int = 50,
    max_months_old: int = 6,
    top_n: int = 20
) -> Tuple[pd.DataFrame, Dict]:
    """
    Identify high-quality new skills not locally installed.

    Args:
        min_stars: Minimum GitHub stars required
        max_months_old: Maximum age in months (0 to disable)
        top_n: Number of top recommendations to return

    Returns:
        Tuple of (new_skills_df, statistics):
        - new_skills_df: DataFrame with top N new skills
        - statistics: Dict with analysis metadata

    Raises:
        ValueError: If no new skills found after filtering

    Example:
        >>> new_skills, stats = analyze_new_skills(min_stars=50, top_n=20)
        >>> print(f"Found {len(new_skills)} new skills")
        >>> print(f"Top skill: {new_skills.iloc[0]['name']}")
    """
    logger.info(f"Starting new skills analysis (min_stars={min_stars}, max_months_old={max_months_old})")

    # Step 1: Fetch all skills from skill-manager
    logger.info("Fetching skills from skill-manager database...")
    skills, fetch_stats = fetch_all_skills(
        min_stars=0,  # Don't filter yet, we'll filter later
        max_months_old=0,
        include_installed=True
    )

    logger.info(f"Fetched {len(skills)} skills from database")

    # Step 2: Parse into DataFrame
    logger.info("Parsing skills into DataFrame...")
    df = parse_skill_manager_response(skills)

    # Step 3: Get installed skills
    logger.info("Fetching locally installed skills...")
    installed = get_installed_skills()
    installed_set = set(installed)

    logger.info(f"Found {len(installed)} installed skills")

    # Step 4: Filter for quality
    logger.info("Applying quality filters...")
    quality_df = filter_quality_skills(df, min_stars=min_stars, max_months_old=max_months_old)

    logger.info(f"After quality filter: {len(quality_df)} skills")

    # Step 5: Exclude installed skills
    logger.info("Filtering out installed skills...")
    new_skills_df = quality_df[~quality_df['name'].isin(installed_set)].copy()

    logger.info(f"Found {len(new_skills_df)} new skills (not installed)")

    if len(new_skills_df) == 0:
        raise ValueError("No new skills found after filtering")

    # Step 6: Sort by stars descending
    new_skills_df = new_skills_df.sort_values('stars', ascending=False).reset_index(drop=True)

    # Step 7: Return top N
    top_new_skills = new_skills_df.head(top_n)

    # Generate statistics
    statistics = {
        'total_in_database': len(df),
        'after_quality_filter': len(quality_df),
        'installed_skills': len(installed),
        'new_skills_found': len(new_skills_df),
        'top_n_returned': len(top_new_skills),
        'filters': {
            'min_stars': min_stars,
            'max_months_old': max_months_old,
            'top_n': top_n
        },
        'analyzed_at': datetime.now().isoformat(),
        'star_range': {
            'min': int(top_new_skills['stars'].min()) if len(top_new_skills) > 0 else 0,
            'max': int(top_new_skills['stars'].max()) if len(top_new_skills) > 0 else 0,
            'median': int(top_new_skills['stars'].median()) if len(top_new_skills) > 0 else 0
        }
    }

    logger.info(f"Analysis complete. Returning top {len(top_new_skills)} new skills")

    return top_new_skills, statistics


def filter_by_category(
    new_skills_df: pd.DataFrame,
    category: str
) -> pd.DataFrame:
    """
    Filter new skills by category.

    Args:
        new_skills_df: DataFrame from analyze_new_skills()
        category: Category to filter by

    Returns:
        Filtered DataFrame

    Example:
        >>> new_skills, _ = analyze_new_skills()
        >>> dev_skills = filter_by_category(new_skills, 'development')
    """
    if 'category' not in new_skills_df.columns:
        logger.warning("No 'category' column in DataFrame")
        return new_skills_df

    filtered = new_skills_df[new_skills_df['category'] == category]

    logger.info(f"Filtered to {len(filtered)} skills in category '{category}'")

    return filtered


def filter_by_tags(
    new_skills_df: pd.DataFrame,
    tags: List[str],
    match_all: bool = False
) -> pd.DataFrame:
    """
    Filter new skills by tags.

    Args:
        new_skills_df: DataFrame from analyze_new_skills()
        tags: List of tags to filter by
        match_all: If True, skill must have ALL tags. If False, ANY tag matches.

    Returns:
        Filtered DataFrame

    Example:
        >>> new_skills, _ = analyze_new_skills()
        >>> python_skills = filter_by_tags(new_skills, ['python', 'automation'])
    """
    if 'tags' not in new_skills_df.columns:
        logger.warning("No 'tags' column in DataFrame")
        return new_skills_df

    def has_tags(skill_tags):
        if not isinstance(skill_tags, list):
            return False

        skill_tags_set = set(skill_tags)
        target_tags_set = set(tags)

        if match_all:
            return target_tags_set.issubset(skill_tags_set)
        else:
            return len(target_tags_set & skill_tags_set) > 0

    filtered = new_skills_df[new_skills_df['tags'].apply(has_tags)]

    match_type = "all" if match_all else "any"
    logger.info(f"Filtered to {len(filtered)} skills matching {match_type} of tags: {tags}")

    return filtered


def format_new_skills_report(
    new_skills_df: pd.DataFrame,
    statistics: Dict,
    top_n: int = 10
) -> str:
    """
    Format new skills analysis as human-readable report.

    Args:
        new_skills_df: DataFrame from analyze_new_skills()
        statistics: Statistics dict from analyze_new_skills()
        top_n: Number of skills to include in report

    Returns:
        Formatted string report

    Example:
        >>> new_skills, stats = analyze_new_skills()
        >>> report = format_new_skills_report(new_skills, stats)
        >>> print(report)
    """
    if new_skills_df.empty:
        return "No new skills found"

    lines = [
        f"## 🆕 New Skills Analysis\n",
        f"**Analysis Date:** {statistics['analyzed_at']}\n",
        "### Summary\n",
        f"- **Total in Database:** {statistics['total_in_database']:,}",
        f"- **After Quality Filter:** {statistics['after_quality_filter']:,}",
        f"- **Installed Locally:** {statistics['installed_skills']:,}",
        f"- **New Skills Found:** {statistics['new_skills_found']:,}",
        f"- **Top Recommendations:** {statistics['top_n_returned']}\n",
        "### Filter Criteria\n",
        f"- **Minimum Stars:** {statistics['filters']['min_stars']}",
        f"- **Maximum Age:** {statistics['filters']['max_months_old']} months",
        f"- **Top N:** {statistics['filters']['top_n']}\n",
        "### Star Range (Top Recommendations)\n",
        f"- **Minimum:** {statistics['star_range']['min']:,}",
        f"- **Maximum:** {statistics['star_range']['max']:,}",
        f"- **Median:** {statistics['star_range']['median']:,}\n",
        f"### Top {min(top_n, len(new_skills_df))} New Skills\n"
    ]

    # Add top N skills
    top_skills = new_skills_df.head(top_n)

    for idx, skill in top_skills.iterrows():
        lines.append(f"#### {idx + 1}. {skill['name']}\n")
        lines.append(f"- **Stars:** {skill['stars']:,} ⭐")
        lines.append(f"- **Forks:** {skill['forks']:,} 🔀")

        if pd.notna(skill.get('updated_at')):
            if isinstance(skill['updated_at'], datetime):
                updated = skill['updated_at'].strftime('%Y-%m-%d')
            else:
                updated = str(skill['updated_at'])[:10]
            lines.append(f"- **Last Updated:** {updated}")

        if skill.get('author'):
            lines.append(f"- **Author:** {skill['author']}")

        if skill.get('description'):
            desc = skill['description'][:200]
            if len(skill['description']) > 200:
                desc += "..."
            lines.append(f"- **Description:** {desc}")

        if skill.get('github_url'):
            lines.append(f"- **GitHub:** {skill['github_url']}")

        if skill.get('tags') and isinstance(skill['tags'], list) and len(skill['tags']) > 0:
            tags_str = ", ".join(skill['tags'][:5])
            lines.append(f"- **Tags:** {tags_str}")

        lines.append("")

    return "\n".join(lines)


def export_new_skills_report(
    new_skills_df: pd.DataFrame,
    statistics: Dict,
    output_path: Optional[Path] = None
) -> Path:
    """
    Export new skills analysis report to file.

    Args:
        new_skills_df: DataFrame from analyze_new_skills()
        statistics: Statistics dict from analyze_new_skills()
        output_path: Optional custom output path

    Returns:
        Path to exported report

    Example:
        >>> new_skills, stats = analyze_new_skills()
        >>> report_path = export_new_skills_report(new_skills, stats)
        >>> print(f"Report exported to: {report_path}")
    """
    if output_path is None:
        # Default: meta/reports/YYYY-MM-DD-new-skills-report.md
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_path = Path(__file__).parent.parent / 'meta' / 'reports' / f'{date_str}-new-skills-report.md'

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate report
    report = format_new_skills_report(new_skills_df, statistics)

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"Report exported to: {output_path}")

    return output_path


# Main for testing
if __name__ == "__main__":
    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 70)
    print("ANALYZE NEW SKILLS - Test")
    print("=" * 70)

    # Test 1: Basic analysis
    print("\n1. Testing analyze_new_skills():")
    try:
        new_skills, stats = analyze_new_skills(min_stars=50, max_months_old=6, top_n=20)
        print(f"   ✓ Found {len(new_skills)} new skills")
        print(f"   ✓ Statistics: {stats['total_in_database']} total, {stats['installed_skills']} installed")
        print(f"\n   Top 3 new skills:")
        for idx, skill in new_skills.head(3).iterrows():
            print(f"     {idx + 1}. {skill['name']} ({skill['stars']} ⭐)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Filter by tags
    print("\n2. Testing filter_by_tags():")
    tagged_skills = filter_by_tags(new_skills, ['python', 'automation'], match_all=False)
    print(f"   ✓ Found {len(tagged_skills)} skills with tags ['python', 'automation']")

    # Test 3: Format report
    print("\n3. Testing format_new_skills_report():")
    report = format_new_skills_report(new_skills, stats, top_n=5)
    print("   ✓ Report generated:")
    print("\n" + "\n".join(["     " + line for line in report.split("\n")[:15]]))
    print("     ...")

    # Test 4: Export report
    print("\n4. Testing export_new_skills_report():")
    try:
        report_path = export_new_skills_report(new_skills, stats)
        print(f"   ✓ Report exported to: {report_path}")
        print(f"   ✓ File exists: {report_path.exists()}")
    except Exception as e:
        print(f"   ✗ Export error: {e}")

    print("\n✅ All tests completed")
