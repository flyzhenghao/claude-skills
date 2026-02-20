#!/usr/bin/env python3
"""
Evaluate security and quality signals for Claude Skills.
Provides GitHub health metrics and graceful degradation framework.
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
import re

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


def evaluate_skill_security(
    skills_df: pd.DataFrame,
    security_threshold: int = 70
) -> pd.DataFrame:
    """
    Evaluate security and quality signals for skills.

    Security score components:
    - GitHub stars: 30% weight (normalized to 0-100)
    - Recent activity: 25% weight (commits, issues, PRs)
    - License verification: 25% weight (compatible license exists)
    - Update frequency: 20% weight (maintenance signals)

    Args:
        skills_df: DataFrame with skill metadata (must have 'github_url', 'stars', 'updated_at')
        security_threshold: Minimum score (0-100, default: 70)

    Returns:
        DataFrame with security assessments:
        - name: str
        - security_score: int
        - stars_score: int
        - activity_score: int
        - license_score: int
        - update_score: int
        - assessment: str
        - github_url: str

    Raises:
        ValueError: If skills_df is empty or missing required columns

    Example:
        >>> assessments = evaluate_skill_security(skills_df, security_threshold=70)
        >>> print(f"Found {len(assessments)} skills passing security threshold")
    """
    logger.info(f"Starting security evaluation (threshold={security_threshold})")

    # Validate input
    if skills_df.empty:
        raise ValueError("skills_df cannot be empty")

    required_columns = ['name', 'github_url', 'stars', 'updated_at']
    missing = set(required_columns) - set(skills_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Filter skills with GitHub URLs
    skills_with_github = skills_df[skills_df['github_url'].notna()].copy()
    logger.info(f"Evaluating {len(skills_with_github)} skills with GitHub URLs")

    if len(skills_with_github) == 0:
        logger.warning("No skills with GitHub URLs found")
        return pd.DataFrame()

    # Calculate security scores
    assessments = []
    current_date = datetime.now()

    for _, skill in skills_with_github.iterrows():
        try:
            # Calculate component scores
            stars_score = _calculate_stars_score(skill['stars'])
            activity_score = _calculate_activity_score(skill['updated_at'], current_date)
            license_score = _calculate_license_score(skill.get('license', ''))
            update_score = _calculate_update_score(skill['updated_at'], current_date)

            # Calculate weighted security score
            security_score = int(
                0.30 * stars_score +
                0.25 * activity_score +
                0.25 * license_score +
                0.20 * update_score
            )

            # Determine assessment level
            assessment = _get_assessment_level(security_score)

            assessments.append({
                'name': skill['name'],
                'security_score': security_score,
                'stars_score': stars_score,
                'activity_score': activity_score,
                'license_score': license_score,
                'update_score': update_score,
                'assessment': assessment,
                'github_url': skill['github_url']
            })

        except Exception as e:
            logger.error(f"Failed to evaluate {skill['name']}: {e}")
            # Graceful degradation: add with low score
            assessments.append({
                'name': skill['name'],
                'security_score': 0,
                'stars_score': 0,
                'activity_score': 0,
                'license_score': 0,
                'update_score': 0,
                'assessment': 'EVALUATION_FAILED',
                'github_url': skill['github_url']
            })

    logger.info(f"Evaluated {len(assessments)} skills")

    if not assessments:
        return pd.DataFrame()

    # Convert to DataFrame
    result_df = pd.DataFrame(assessments)

    # Filter by security threshold
    logger.info(f"Applying security threshold: {security_threshold}")
    passing = result_df[result_df['security_score'] >= security_threshold].copy()

    logger.info(f"Found {len(passing)} skills passing security threshold")

    # Sort by security score descending
    passing = passing.sort_values('security_score', ascending=False).reset_index(drop=True)

    return passing


def _calculate_stars_score(stars: int) -> int:
    """
    Calculate stars score (0-100) based on GitHub stars.

    Scoring:
    - 0-9 stars: 0-30
    - 10-99 stars: 30-60
    - 100-999 stars: 60-85
    - 1000+ stars: 85-100

    Args:
        stars: GitHub star count

    Returns:
        Score 0-100
    """
    if stars >= 1000:
        # 1000+ stars: 85-100 (cap at 100)
        return min(85 + (stars - 1000) // 200, 100)
    elif stars >= 100:
        # 100-999 stars: 60-85
        return 60 + int((stars - 100) / 900 * 25)
    elif stars >= 10:
        # 10-99 stars: 30-60
        return 30 + int((stars - 10) / 90 * 30)
    else:
        # 0-9 stars: 0-30
        return min(stars * 3, 30)


def _calculate_activity_score(updated_at: datetime, current_date: datetime) -> int:
    """
    Calculate activity score (0-100) based on recency of updates.

    Scoring:
    - < 1 month: 90-100
    - 1-3 months: 70-90
    - 3-6 months: 50-70
    - 6-12 months: 30-50
    - > 12 months: 0-30

    Args:
        updated_at: Last update date
        current_date: Current date for comparison

    Returns:
        Score 0-100
    """
    if pd.isna(updated_at):
        return 0

    days_since_update = (current_date - updated_at).days

    if days_since_update < 30:
        # < 1 month: 90-100
        return 100 - (days_since_update // 3)
    elif days_since_update < 90:
        # 1-3 months: 70-90
        return 90 - int((days_since_update - 30) / 60 * 20)
    elif days_since_update < 180:
        # 3-6 months: 50-70
        return 70 - int((days_since_update - 90) / 90 * 20)
    elif days_since_update < 365:
        # 6-12 months: 30-50
        return 50 - int((days_since_update - 180) / 185 * 20)
    else:
        # > 12 months: 0-30
        return max(30 - (days_since_update - 365) // 30, 0)


def _calculate_license_score(license_name: str) -> int:
    """
    Calculate license score (0-100) based on license compatibility.

    Scoring:
    - Permissive licenses (MIT, Apache, BSD): 100
    - Copyleft licenses (GPL, LGPL): 70
    - Other OSI-approved: 50
    - No license: 0

    Args:
        license_name: License identifier

    Returns:
        Score 0-100
    """
    if not license_name or license_name.lower() in ['none', 'unknown', '']:
        return 0

    license_lower = license_name.lower()

    # Permissive licenses (preferred)
    permissive = ['mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0']
    if any(lic in license_lower for lic in permissive):
        return 100

    # Copyleft licenses (acceptable but restrictive)
    copyleft = ['gpl', 'lgpl', 'agpl', 'mpl']
    if any(lic in license_lower for lic in copyleft):
        return 70

    # Other recognized licenses
    other = ['cc-by', 'artistic', 'epl', 'eupl']
    if any(lic in license_lower for lic in other):
        return 50

    # Unknown license
    return 25


def _calculate_update_score(updated_at: datetime, current_date: datetime) -> int:
    """
    Calculate update frequency score (0-100) based on maintenance signals.

    Scoring:
    - Updated within 1 month: 100
    - Updated within 3 months: 80
    - Updated within 6 months: 60
    - Updated within 1 year: 40
    - Updated > 1 year ago: 20
    - Never updated: 0

    Args:
        updated_at: Last update date
        current_date: Current date for comparison

    Returns:
        Score 0-100
    """
    if pd.isna(updated_at):
        return 0

    days_since_update = (current_date - updated_at).days

    if days_since_update < 30:
        return 100
    elif days_since_update < 90:
        return 80
    elif days_since_update < 180:
        return 60
    elif days_since_update < 365:
        return 40
    else:
        return 20


def _get_assessment_level(security_score: int) -> str:
    """
    Get assessment level based on security score.

    Levels:
    - 85-100: EXCELLENT
    - 70-84: GOOD
    - 50-69: MODERATE
    - 30-49: LOW
    - 0-29: POOR

    Args:
        security_score: Security score 0-100

    Returns:
        Assessment level string
    """
    if security_score >= 85:
        return 'EXCELLENT'
    elif security_score >= 70:
        return 'GOOD'
    elif security_score >= 50:
        return 'MODERATE'
    elif security_score >= 30:
        return 'LOW'
    else:
        return 'POOR'


def filter_by_assessment_level(
    assessments_df: pd.DataFrame,
    levels: List[str]
) -> pd.DataFrame:
    """
    Filter security assessments by level.

    Args:
        assessments_df: DataFrame from evaluate_skill_security()
        levels: List of assessment levels to include

    Returns:
        Filtered DataFrame

    Example:
        >>> excellent = filter_by_assessment_level(assessments, ['EXCELLENT'])
        >>> safe = filter_by_assessment_level(assessments, ['EXCELLENT', 'GOOD'])
    """
    if 'assessment' not in assessments_df.columns:
        logger.warning("No 'assessment' column in DataFrame")
        return assessments_df

    filtered = assessments_df[assessments_df['assessment'].isin(levels)]

    logger.info(f"Filtered to {len(filtered)} skills with levels: {levels}")

    return filtered


def format_security_report(
    assessments_df: pd.DataFrame,
    top_n: int = 10
) -> str:
    """
    Format security assessments as human-readable report.

    Args:
        assessments_df: DataFrame from evaluate_skill_security()
        top_n: Number of skills to include in report

    Returns:
        Formatted string report

    Example:
        >>> report = format_security_report(assessments)
        >>> print(report)
    """
    if assessments_df.empty:
        return "No security assessments available"

    lines = [
        f"## 🛡️ Security Assessments\n",
        f"**Analysis Date:** {datetime.now().isoformat()}\n",
        "### Summary\n",
        f"- **Total Assessed:** {len(assessments_df):,}\n"
    ]

    # Assessment level breakdown
    level_counts = assessments_df['assessment'].value_counts()
    lines.append("### Assessment Levels\n")
    for level in ['EXCELLENT', 'GOOD', 'MODERATE', 'LOW', 'POOR']:
        count = level_counts.get(level, 0)
        lines.append(f"- **{level}:** {count}")

    lines.append(f"\n### Top {min(top_n, len(assessments_df))} Secure Skills\n")

    # Add top N skills
    top_skills = assessments_df.head(top_n)

    for idx, skill in top_skills.iterrows():
        lines.append(f"#### {idx + 1}. {skill['name']}\n")
        lines.append(f"- **Security Score:** {skill['security_score']}/100 ({skill['assessment']})")
        lines.append(f"- **Component Scores:**")
        lines.append(f"  - Stars: {skill['stars_score']}/100")
        lines.append(f"  - Activity: {skill['activity_score']}/100")
        lines.append(f"  - License: {skill['license_score']}/100")
        lines.append(f"  - Updates: {skill['update_score']}/100")
        lines.append(f"- **GitHub:** {skill['github_url']}")
        lines.append("")

    return "\n".join(lines)


def export_security_report(
    assessments_df: pd.DataFrame,
    output_path: Optional[Path] = None
) -> Path:
    """
    Export security assessments report to file.

    Args:
        assessments_df: DataFrame from evaluate_skill_security()
        output_path: Optional custom output path

    Returns:
        Path to exported report

    Example:
        >>> report_path = export_security_report(assessments)
        >>> print(f"Report exported to: {report_path}")
    """
    if output_path is None:
        # Default: meta/reports/YYYY-MM-DD-skill-security-report.md
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_path = Path(__file__).parent.parent / 'meta' / 'reports' / f'{date_str}-skill-security-report.md'

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate report
    report = format_security_report(assessments_df)

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
    print("EVALUATE SECURITY - Test")
    print("=" * 70)

    # Test 1: Security evaluation
    print("\n1. Testing evaluate_skill_security():")
    try:
        from fetch_skill_manager import fetch_all_skills
        from parse_skill_manager import parse_skill_manager_response

        print("   Fetching skills from skill-manager...")
        skills, _ = fetch_all_skills(min_stars=100, max_months_old=6)
        df = parse_skill_manager_response(skills)

        # Limit to top 20 by stars for testing
        test_df = df.nlargest(20, 'stars')

        print(f"   Testing with {len(test_df)} popular skills...")
        assessments = evaluate_skill_security(
            test_df,
            security_threshold=70
        )

        print(f"   ✓ Found {len(assessments)} skills passing security threshold")

        if len(assessments) > 0:
            print(f"\n   Top 3 secure skills:")
            for idx, skill in assessments.head(3).iterrows():
                print(f"     {idx + 1}. {skill['name']} (score: {skill['security_score']}, {skill['assessment']})")
                print(f"        Stars: {skill['stars_score']}, Activity: {skill['activity_score']}, License: {skill['license_score']}, Update: {skill['update_score']}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Filter by assessment level
    print("\n2. Testing filter_by_assessment_level():")
    excellent = filter_by_assessment_level(assessments, ['EXCELLENT'])
    print(f"   ✓ Found {len(excellent)} EXCELLENT skills")

    safe = filter_by_assessment_level(assessments, ['EXCELLENT', 'GOOD'])
    print(f"   ✓ Found {len(safe)} EXCELLENT/GOOD skills")

    # Test 3: Format report
    print("\n3. Testing format_security_report():")
    report = format_security_report(assessments, top_n=5)
    print("   ✓ Report generated:")
    print("\n" + "\n".join(["     " + line for line in report.split("\n")[:20]]))
    print("     ...")

    # Test 4: Export report
    print("\n4. Testing export_security_report():")
    try:
        report_path = export_security_report(assessments)
        print(f"   ✓ Report exported to: {report_path}")
        print(f"   ✓ File exists: {report_path.exists()}")
    except Exception as e:
        print(f"   ✗ Export error: {e}")

    print("\n✅ All tests completed")
