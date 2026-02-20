#!/usr/bin/env python3
"""
Identify skill replacement recommendations with multi-factor confidence scoring.
Combines star ratio, recency, and text similarity for confident recommendations.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


def calculate_replacement_confidence(
    installed_skills_df: pd.DataFrame,
    all_skills_df: pd.DataFrame,
    similarity_df: pd.DataFrame,
    confidence_threshold: float = 0.70
) -> pd.DataFrame:
    """
    Calculate replacement confidence scores using multi-factor weighting.

    Confidence formula:
    - Star ratio: 40% weight (candidate_stars / installed_stars)
    - Recency factor: 30% weight (days since update, normalized)
    - Text similarity: 30% weight (from similarity_df)

    Args:
        installed_skills_df: DataFrame with installed skills
        all_skills_df: DataFrame with all available skills
        similarity_df: DataFrame from analyze_similarity.py
        confidence_threshold: Minimum confidence (0.0-1.0, default: 0.70)

    Returns:
        DataFrame with replacement recommendations:
        - installed_skill: str
        - replacement_candidate: str
        - confidence_score: float
        - star_ratio: float
        - recency_factor: float
        - similarity_score: float
        - installed_stars: int
        - candidate_stars: int
        - installed_updated: datetime
        - candidate_updated: datetime

    Raises:
        ValueError: If DataFrames are empty or missing required columns

    Example:
        >>> replacements = calculate_replacement_confidence(
        ...     installed_df, all_df, similarity_df, confidence_threshold=0.70
        ... )
        >>> print(f"Found {len(replacements)} replacement recommendations")
    """
    logger.info(f"Calculating replacement confidence (threshold={confidence_threshold})")

    # Validate inputs
    if installed_skills_df.empty:
        raise ValueError("installed_skills_df cannot be empty")
    if all_skills_df.empty:
        raise ValueError("all_skills_df cannot be empty")
    if similarity_df.empty:
        logger.warning("similarity_df is empty, no replacements can be calculated")
        return pd.DataFrame()

    # Check required columns
    required_installed = ['name', 'stars', 'updated_at']
    required_all = ['name', 'stars', 'updated_at']
    required_similarity = ['skill1_name', 'skill2_name', 'similarity_score']

    for col in required_installed:
        if col not in installed_skills_df.columns:
            raise ValueError(f"installed_skills_df missing column: {col}")

    for col in required_all:
        if col not in all_skills_df.columns:
            raise ValueError(f"all_skills_df missing column: {col}")

    for col in required_similarity:
        if col not in similarity_df.columns:
            raise ValueError(f"similarity_df missing column: {col}")

    logger.info(f"Analyzing {len(installed_skills_df)} installed skills")

    # Calculate replacements
    replacements = []
    current_date = datetime.now()

    for _, installed_skill in installed_skills_df.iterrows():
        installed_name = installed_skill['name']
        installed_stars = installed_skill['stars']
        installed_updated = installed_skill['updated_at']

        # Find similar skills from similarity_df
        similar = similarity_df[
            (similarity_df['skill1_name'] == installed_name) |
            (similarity_df['skill2_name'] == installed_name)
        ]

        if similar.empty:
            logger.debug(f"No similar skills found for {installed_name}")
            continue

        # For each similar skill, calculate confidence
        for _, sim_row in similar.iterrows():
            # Determine candidate skill
            if sim_row['skill1_name'] == installed_name:
                candidate_name = sim_row['skill2_name']
            else:
                candidate_name = sim_row['skill1_name']

            # Get candidate skill details
            candidate = all_skills_df[all_skills_df['name'] == candidate_name]

            if candidate.empty:
                logger.warning(f"Candidate skill {candidate_name} not found in all_skills_df")
                continue

            candidate = candidate.iloc[0]
            candidate_stars = candidate['stars']
            candidate_updated = candidate['updated_at']
            similarity_score = sim_row['similarity_score']

            # Calculate factors

            # 1. Star ratio (40% weight) - capped at 1.0
            star_ratio = min(candidate_stars / max(installed_stars, 1), 1.0)

            # 2. Recency factor (30% weight)
            # More recent = higher score
            # Normalize: 0 days = 1.0, 365 days = 0.0
            if pd.isna(candidate_updated):
                recency_factor = 0.0
            else:
                days_since_update = (current_date - candidate_updated).days
                recency_factor = max(1.0 - (days_since_update / 365), 0.0)

            # 3. Similarity score (30% weight) - already 0.0-1.0
            # Already normalized from analyze_similarity.py

            # Calculate weighted confidence score
            confidence_score = (
                0.4 * star_ratio +
                0.3 * recency_factor +
                0.3 * similarity_score
            )

            # Only include if above threshold
            if confidence_score >= confidence_threshold:
                replacements.append({
                    'installed_skill': installed_name,
                    'replacement_candidate': candidate_name,
                    'confidence_score': confidence_score,
                    'star_ratio': star_ratio,
                    'recency_factor': recency_factor,
                    'similarity_score': similarity_score,
                    'installed_stars': installed_stars,
                    'candidate_stars': candidate_stars,
                    'installed_updated': installed_updated,
                    'candidate_updated': candidate_updated
                })

    logger.info(f"Found {len(replacements)} replacements above threshold")

    if not replacements:
        return pd.DataFrame()

    # Convert to DataFrame
    result_df = pd.DataFrame(replacements)

    # Sort by confidence score descending
    result_df = result_df.sort_values('confidence_score', ascending=False).reset_index(drop=True)

    return result_df


def filter_by_confidence_range(
    replacements_df: pd.DataFrame,
    min_confidence: float,
    max_confidence: Optional[float] = None
) -> pd.DataFrame:
    """
    Filter replacement recommendations by confidence score range.

    Args:
        replacements_df: DataFrame from calculate_replacement_confidence()
        min_confidence: Minimum confidence score
        max_confidence: Maximum confidence score (None = no upper limit)

    Returns:
        Filtered DataFrame

    Example:
        >>> high_confidence = filter_by_confidence_range(replacements, 0.85)
        >>> moderate = filter_by_confidence_range(replacements, 0.70, 0.85)
    """
    if 'confidence_score' not in replacements_df.columns:
        logger.warning("No 'confidence_score' column in DataFrame")
        return replacements_df

    filtered = replacements_df[replacements_df['confidence_score'] >= min_confidence]

    if max_confidence is not None:
        filtered = filtered[filtered['confidence_score'] <= max_confidence]

    logger.info(f"Filtered to {len(filtered)} replacements in [{min_confidence}, {max_confidence or 'inf'}]")

    return filtered


def format_replacement_report(
    replacements_df: pd.DataFrame,
    top_n: int = 10
) -> str:
    """
    Format replacement recommendations as human-readable report.

    Args:
        replacements_df: DataFrame from calculate_replacement_confidence()
        top_n: Number of recommendations to include

    Returns:
        Formatted string report

    Example:
        >>> report = format_replacement_report(replacements)
        >>> print(report)
    """
    if replacements_df.empty:
        return "No replacement recommendations found"

    lines = [
        f"## 🔄 Skill Replacement Recommendations\n",
        f"**Analysis Date:** {datetime.now().isoformat()}\n",
        "### Summary\n",
        f"- **Total Recommendations:** {len(replacements_df)}\n",
        f"### Confidence Scoring Formula\n",
        "- **Star Ratio:** 40% weight (candidate_stars / installed_stars, capped at 1.0)",
        "- **Recency Factor:** 30% weight (days since update, normalized 0-365 days)",
        "- **Text Similarity:** 30% weight (TF-IDF + cosine similarity)\n",
        f"### Top {min(top_n, len(replacements_df))} Recommendations\n"
    ]

    # Add top N recommendations
    top_replacements = replacements_df.head(top_n)

    for idx, rec in top_replacements.iterrows():
        lines.append(f"#### {idx + 1}. Replace: {rec['installed_skill']} → {rec['replacement_candidate']}\n")
        lines.append(f"- **Confidence Score:** {rec['confidence_score']:.3f} (Threshold: 0.70)")
        lines.append(f"- **Star Ratio:** {rec['star_ratio']:.3f} ({rec['candidate_stars']:,} vs {rec['installed_stars']:,})")
        lines.append(f"- **Recency Factor:** {rec['recency_factor']:.3f}")
        lines.append(f"- **Similarity Score:** {rec['similarity_score']:.3f}")

        if pd.notna(rec.get('candidate_updated')):
            if isinstance(rec['candidate_updated'], datetime):
                updated = rec['candidate_updated'].strftime('%Y-%m-%d')
            else:
                updated = str(rec['candidate_updated'])[:10]
            lines.append(f"- **Candidate Last Updated:** {updated}")

        lines.append("")

    return "\n".join(lines)


def export_replacement_report(
    replacements_df: pd.DataFrame,
    output_path: Optional[Path] = None
) -> Path:
    """
    Export replacement recommendations report to file.

    Args:
        replacements_df: DataFrame from calculate_replacement_confidence()
        output_path: Optional custom output path

    Returns:
        Path to exported report

    Example:
        >>> report_path = export_replacement_report(replacements)
        >>> print(f"Report exported to: {report_path}")
    """
    if output_path is None:
        # Default: meta/reports/YYYY-MM-DD-skill-replacements.md
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_path = Path(__file__).parent.parent / 'meta' / 'reports' / f'{date_str}-skill-replacements.md'

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate report
    report = format_replacement_report(replacements_df)

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
    print("ANALYZE REPLACEMENTS - Test")
    print("=" * 70)

    # Test: Calculate replacement confidence
    print("\n1. Testing calculate_replacement_confidence():")
    try:
        from fetch_skill_manager import fetch_all_skills, get_installed_skills
        from parse_skill_manager import parse_skill_manager_response
        from analyze_similarity import calculate_skill_similarity

        print("   Fetching skills from skill-manager...")
        skills, _ = fetch_all_skills(min_stars=100, max_months_old=6)
        df = parse_skill_manager_response(skills)

        print("   Getting installed skills...")
        installed_names = get_installed_skills()[:10]  # Limit to 10 for testing
        installed_df = df[df['name'].isin(installed_names)]

        print(f"   Testing with {len(installed_df)} installed skills...")

        # Calculate similarity first
        print("   Calculating similarity (this may take a moment)...")
        similarity_df = calculate_skill_similarity(
            df,
            similarity_threshold=0.70,
            installed_skills=installed_names
        )

        if similarity_df.empty:
            print("   ⚠️ No similar pairs found - lowering threshold")
            similarity_df = calculate_skill_similarity(
                df,
                similarity_threshold=0.60,
                installed_skills=installed_names
            )

        print(f"   Found {len(similarity_df)} similar pairs")

        # Calculate replacement confidence
        replacements = calculate_replacement_confidence(
            installed_df,
            df,
            similarity_df,
            confidence_threshold=0.70
        )

        print(f"   ✓ Found {len(replacements)} replacement recommendations")

        if len(replacements) > 0:
            print(f"\n   Top 3 recommendations:")
            for idx, rec in replacements.head(3).iterrows():
                print(f"     {idx + 1}. {rec['installed_skill']} → {rec['replacement_candidate']}")
                print(f"        Confidence: {rec['confidence_score']:.3f}")
                print(f"        Star ratio: {rec['star_ratio']:.3f}, Recency: {rec['recency_factor']:.3f}, Similarity: {rec['similarity_score']:.3f}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Filter by confidence range
    print("\n2. Testing filter_by_confidence_range():")
    if len(replacements) > 0:
        high_confidence = filter_by_confidence_range(replacements, 0.85)
        print(f"   ✓ High confidence (≥0.85): {len(high_confidence)} recommendations")

        moderate = filter_by_confidence_range(replacements, 0.70, 0.85)
        print(f"   ✓ Moderate confidence (0.70-0.85): {len(moderate)} recommendations")

    # Test 3: Format report
    print("\n3. Testing format_replacement_report():")
    report = format_replacement_report(replacements, top_n=5)
    print("   ✓ Report generated:")
    print("\n" + "\n".join(["     " + line for line in report.split("\n")[:20]]))
    print("     ...")

    # Test 4: Export report
    print("\n4. Testing export_replacement_report():")
    try:
        report_path = export_replacement_report(replacements)
        print(f"   ✓ Report exported to: {report_path}")
        print(f"   ✓ File exists: {report_path.exists()}")
    except Exception as e:
        print(f"   ✗ Export error: {e}")

    print("\n✅ All tests completed")
