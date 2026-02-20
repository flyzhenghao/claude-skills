#!/usr/bin/env python3
"""
Parse skill-manager data into standardized format.
Normalizes varying schemas and validates data quality.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.validators.data_validator import DataValidator, ValidationReport

logger = logging.getLogger(__name__)


def parse_skill_manager_response(skills: List[Dict]) -> pd.DataFrame:
    """
    Parse skill-manager data into standardized DataFrame.

    Handles multiple schema formats:
    - Dict format: {skill_name: {metadata}}
    - List format: [{name: skill_name, ...}]
    - Field variations: description/desc, author/owner, etc.

    Args:
        skills: List of skill dictionaries from fetch_skill_manager.py

    Returns:
        DataFrame with standardized schema:
        - name: str
        - description: str
        - stars: int
        - forks: int
        - updated_at: datetime
        - author: str
        - github_url: str
        - tags: List[str]
        - category: str

    Raises:
        ValueError: If skills list is empty or invalid

    Example:
        >>> from fetch_skill_manager import fetch_all_skills
        >>> skills, stats = fetch_all_skills()
        >>> df = parse_skill_manager_response(skills)
        >>> print(df.shape)
        (150, 9)
    """
    if not skills:
        raise ValueError("Skills list cannot be empty")

    if not isinstance(skills, list):
        raise ValueError(f"Expected list, got {type(skills)}")

    logger.info(f"Parsing {len(skills)} skills from skill-manager")

    # Normalize each skill entry
    normalized_skills = []
    for skill in skills:
        normalized = _normalize_skill_entry(skill)
        if normalized:
            normalized_skills.append(normalized)

    logger.info(f"Normalized {len(normalized_skills)} skills")

    # Convert to DataFrame
    df = pd.DataFrame(normalized_skills)

    # Parse dates
    df = _parse_dates(df)

    # Ensure correct types
    df = _standardize_types(df)

    # Validate
    validator = DataValidator()
    report = validator.validate_dataframe(df, 'skill-manager')

    if report.has_critical_issues():
        logger.warning(f"Validation found issues: {report.get_summary()}")
        for warning in report.get_warnings():
            logger.warning(f"  - {warning}")

    logger.info(f"Parsed DataFrame shape: {df.shape}")

    return df


def _normalize_skill_entry(skill: Dict) -> Optional[Dict]:
    """
    Normalize a single skill entry to standardized schema.

    Handles field name variations and missing values.
    """
    try:
        normalized = {
            'name': skill.get('name', ''),
            'description': skill.get('description') or skill.get('desc') or '',
            'stars': skill.get('stars', 0),
            'forks': skill.get('forks', 0),
            'updated_at': skill.get('updated_at') or skill.get('updated'),
            'author': skill.get('author') or skill.get('owner') or '',
            'github_url': skill.get('github_url') or skill.get('url') or '',
            'tags': skill.get('tags') or skill.get('keywords') or [],
            'category': skill.get('category', ''),
        }

        # Skip if missing critical fields
        if not normalized['name']:
            logger.debug(f"Skipping skill with missing name: {skill}")
            return None

        # Ensure types
        normalized['stars'] = int(normalized['stars']) if normalized['stars'] else 0
        normalized['forks'] = int(normalized['forks']) if normalized['forks'] else 0
        normalized['tags'] = normalized['tags'] if isinstance(normalized['tags'], list) else []

        return normalized

    except Exception as e:
        logger.warning(f"Failed to normalize skill: {e}")
        return None


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse date strings to datetime objects.

    Handles multiple datetime formats:
    - ISO format with Z: "2024-01-15T10:30:00Z"
    - ISO format with timezone: "2024-01-15T10:30:00+00:00"
    - Unix timestamp: 1705315800
    """
    if 'updated_at' not in df.columns:
        return df

    def parse_date(date_value):
        if pd.isna(date_value):
            return None

        # Already datetime
        if isinstance(date_value, datetime):
            return date_value

        # Unix timestamp (number)
        if isinstance(date_value, (int, float)):
            try:
                return datetime.fromtimestamp(date_value)
            except Exception:
                return None

        # String format
        if isinstance(date_value, str):
            try:
                # Handle Z suffix
                date_str = date_value.replace('Z', '+00:00')
                return datetime.fromisoformat(date_str)
            except Exception:
                return None

        return None

    df['updated_at'] = df['updated_at'].apply(parse_date)

    return df


def _standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all columns have correct data types.
    """
    # String columns
    for col in ['name', 'description', 'author', 'github_url', 'category']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # Integer columns
    for col in ['stars', 'forks']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # List columns (keep as-is, already validated in normalize)

    return df


def filter_quality_skills(
    df: pd.DataFrame,
    min_stars: int = 50,
    max_months_old: int = 6
) -> pd.DataFrame:
    """
    Filter DataFrame for quality skills.

    Args:
        df: Parsed skill DataFrame
        min_stars: Minimum GitHub stars required
        max_months_old: Maximum age in months (0 to disable)

    Returns:
        Filtered DataFrame

    Example:
        >>> df = parse_skill_manager_response(skills)
        >>> quality_df = filter_quality_skills(df, min_stars=50)
        >>> print(f"Filtered to {len(quality_df)} quality skills")
    """
    original_count = len(df)

    # Filter by stars
    df = df[df['stars'] >= min_stars]
    stars_filtered = original_count - len(df)

    # Filter by recency
    if max_months_old > 0 and 'updated_at' in df.columns:
        cutoff_date = datetime.now() - pd.Timedelta(days=max_months_old * 30)
        df = df[df['updated_at'] >= cutoff_date]
        recency_filtered = original_count - stars_filtered - len(df)
    else:
        recency_filtered = 0

    logger.info(
        f"Filtered {original_count} → {len(df)} skills "
        f"(stars: -{stars_filtered}, recency: -{recency_filtered})"
    )

    return df


def aggregate_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate skills by category.

    Args:
        df: Parsed skill DataFrame

    Returns:
        DataFrame with aggregated statistics per category:
        - category: str
        - count: int
        - avg_stars: float
        - total_stars: int

    Example:
        >>> agg = aggregate_by_category(df)
        >>> print(agg.sort_values('count', ascending=False).head())
    """
    if 'category' not in df.columns:
        logger.warning("No 'category' column found for aggregation")
        return pd.DataFrame()

    agg = df.groupby('category').agg(
        count=('name', 'count'),
        avg_stars=('stars', 'mean'),
        total_stars=('stars', 'sum')
    ).reset_index()

    agg['avg_stars'] = agg['avg_stars'].round(1)

    return agg.sort_values('count', ascending=False)


def format_skill_summary(df: pd.DataFrame, top_n: int = 10) -> str:
    """
    Format DataFrame as human-readable summary.

    Args:
        df: Parsed skill DataFrame
        top_n: Number of top skills to include

    Returns:
        Formatted string summary

    Example:
        >>> summary = format_skill_summary(df)
        >>> print(summary)
    """
    if df.empty:
        return "No skills found"

    lines = [
        f"## Skill-Manager Summary\n",
        f"**Total Skills:** {len(df)}",
        f"**Total Stars:** {df['stars'].sum():,}",
        f"**Average Stars:** {df['stars'].mean():.1f}\n",
    ]

    # Top skills by stars
    lines.append(f"### Top {top_n} Skills (by stars)\n")
    top_skills = df.nlargest(top_n, 'stars')

    for _, skill in top_skills.iterrows():
        lines.append(
            f"- **{skill['name']}** ({skill['stars']} ⭐) - {skill['description'][:80]}..."
        )

    # Category distribution
    if 'category' in df.columns:
        lines.append("\n### Category Distribution\n")
        category_counts = df['category'].value_counts().head(5)
        for category, count in category_counts.items():
            lines.append(f"- {category}: {count} skills")

    return "\n".join(lines)


# Main for testing
if __name__ == "__main__":
    import sys
    from fetch_skill_manager import fetch_all_skills

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== parse_skill_manager.py Test ===\n")

    # Test 1: Load and parse skills
    print("1. Testing parse_skill_manager_response():")
    try:
        skills, stats = fetch_all_skills(min_stars=50, max_months_old=6)
        print(f"   ✓ Fetched {len(skills)} skills")

        df = parse_skill_manager_response(skills)
        print(f"   ✓ Parsed DataFrame: {df.shape}")
        print(f"   ✓ Columns: {list(df.columns)}")
        print(f"   ✓ Sample:\n{df.head(3)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        sys.exit(1)

    # Test 2: Quality filtering
    print("\n2. Testing filter_quality_skills():")
    quality_df = filter_quality_skills(df, min_stars=100, max_months_old=3)
    print(f"   ✓ Filtered: {len(df)} → {len(quality_df)} skills")

    # Test 3: Category aggregation
    print("\n3. Testing aggregate_by_category():")
    agg = aggregate_by_category(df)
    print(f"   ✓ Categories: {len(agg)}")
    print(f"   ✓ Top 5:\n{agg.head()}")

    # Test 4: Format summary
    print("\n4. Testing format_skill_summary():")
    summary = format_skill_summary(df, top_n=5)
    print(summary)

    # Test 5: Data types
    print("\n5. Testing data types:")
    print(f"   ✓ name: {df['name'].dtype}")
    print(f"   ✓ stars: {df['stars'].dtype}")
    print(f"   ✓ updated_at: {df['updated_at'].dtype}")

    print("\n✅ All tests completed")
