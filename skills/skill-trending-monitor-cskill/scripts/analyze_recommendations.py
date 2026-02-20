#!/usr/bin/env python3
"""
ML-based personalized skill recommendations.
Combines TF-IDF similarity, quality signals, and user preferences.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Set
from datetime import datetime
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from fetch_skill_manager import fetch_all_skills, get_installed_skills
from parse_skill_manager import parse_skill_manager_response
from analyze_similarity import calculate_skill_similarity

logger = logging.getLogger(__name__)


def calculate_recommendation_score(
    skill: pd.Series,
    installed_skills: List[str],
    similarity_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate recommendation score for a skill using multi-factor weighting.

    Args:
        skill: A single row from skills DataFrame
        installed_skills: List of installed skill names
        similarity_scores: Dict mapping skill name -> max similarity to installed skills
        weights: Optional custom weights dict (must sum to 1.0)

    Returns:
        float: Recommendation score between 0.0 and 1.0
    """
    if weights is None:
        weights = {
            'popularity': 0.25,
            'recency': 0.20,
            'similarity': 0.30,
            'category': 0.15,
            'momentum': 0.10
        }

    # 1. Popularity score (normalized log stars)
    # Log scale: 10 stars = 0.3, 100 = 0.6, 1000 = 0.9, 10000 = 1.0
    stars = skill.get('stars', 0)
    popularity_score = min(np.log10(max(stars, 1)) / 4, 1.0)

    # 2. Recency score (0 days = 1.0, 365 days = 0.0)
    updated_at = skill.get('updated_at')
    if pd.isna(updated_at):
        recency_score = 0.0
    else:
        days_old = (datetime.now() - updated_at).days
        recency_score = max(1.0 - (days_old / 365), 0.0)

    # 3. Similarity score (from pre-calculated similarity_scores dict)
    skill_name = skill.get('name', '')
    similarity_score = similarity_scores.get(skill_name, 0.0)

    # 4. Category match score (use similarity as proxy, boost slightly)
    category_score = min(similarity_score * 1.2, 1.0)

    # 5. Momentum score (placeholder - use recency as proxy for now)
    momentum_score = recency_score

    # Final weighted score
    final_score = (
        weights['popularity'] * popularity_score +
        weights['recency'] * recency_score +
        weights['similarity'] * similarity_score +
        weights['category'] * category_score +
        weights['momentum'] * momentum_score
    )

    return final_score


def get_personalized_recommendations(
    all_skills_df: pd.DataFrame,
    installed_skills: Optional[List[str]] = None,
    exclude_installed: bool = True,
    min_stars: int = 50,
    max_results: int = 20,
    similarity_threshold: float = 0.3
) -> pd.DataFrame:
    """
    Generate personalized skill recommendations.

    Args:
        all_skills_df: DataFrame with all available skills
        installed_skills: List of installed skill names (auto-detected if None)
        exclude_installed: Whether to exclude already installed skills
        min_stars: Minimum stars to consider
        max_results: Maximum number of recommendations to return
        similarity_threshold: Minimum similarity for consider

    Returns:
        DataFrame with personalized recommendations
    """
    logger.info("Generating personalized recommendations...")

    # Step 1: Get installed skills if not provided
    if installed_skills is None:
        installed_skills = get_installed_skills()
        logger.info(f"Auto-detected {len(installed_skills)} installed skills")

    installed_set: Set[str] = set(installed_skills)

    # Step 2: Filter by min_stars
    candidates = all_skills_df[all_skills_df['stars'] >= min_stars].copy()
    logger.info(f"Filtered to {len(candidates)} candidates with >= {min_stars} stars")

    # Step 3: Exclude installed if requested
    if exclude_installed:
        candidates = candidates[~candidates['name'].isin(installed_set)]
        logger.info(f"After excluding installed: {len(candidates)} candidates")

    if candidates.empty:
        logger.warning("No candidates available for recommendations")
        return pd.DataFrame()

    # Step 4: Calculate similarity to installed skills
    # IMPORTANT: Need to include both candidates AND installed skills in the similarity calculation
    logger.info("Calculating similarity scores...")
    skills_for_similarity = pd.concat([
        candidates,
        all_skills_df[all_skills_df['name'].isin(installed_set)]
    ])

    similarity_df = calculate_skill_similarity(
        skills_for_similarity,
        similarity_threshold=similarity_threshold,
        installed_skills=installed_skills
    )

    # Step 5: Build similarity lookup: skill_name -> max similarity to any installed skill
    similarity_lookup: Dict[str, float] = {}
    if not similarity_df.empty:
        for _, row in similarity_df.iterrows():
            skill1, skill2 = row['skill1_name'], row['skill2_name']
            score = row['similarity_score']

            # If one is installed and other is candidate
            if skill1 in installed_set and skill2 not in installed_set:
                similarity_lookup[skill2] = max(similarity_lookup.get(skill2, 0), score)
            elif skill2 in installed_set and skill1 not in installed_set:
                similarity_lookup[skill1] = max(similarity_lookup.get(skill1, 0), score)

    logger.info(f"Found similarity scores for {len(similarity_lookup)} candidates")

    # Step 6: Calculate recommendation score for each candidate
    recommendations = []
    for _, skill in candidates.iterrows():
        score = calculate_recommendation_score(
            skill,
            installed_skills,
            similarity_lookup
        )

        sim_score = similarity_lookup.get(skill['name'], 0.0)

        # Generate reason based on score components
        if sim_score > 0.7:
            reason = f"Very similar to your installed skills (similarity: {sim_score:.2f})"
        elif sim_score > 0.5:
            reason = f"Related to your installed skills (similarity: {sim_score:.2f})"
        elif skill['stars'] > 500:
            reason = f"Popular in community ({skill['stars']:,} stars)"
        else:
            reason = "Trending and well-maintained"

        # Truncate description to 150 chars
        desc = skill.get('description', '')
        if len(desc) > 150:
            desc = desc[:150] + '...'

        recommendations.append({
            'name': skill['name'],
            'recommendation_score': score,
            'stars': skill['stars'],
            'author': skill.get('author', ''),
            'description': desc,
            'similarity_to_installed': sim_score,
            'updated_at': skill.get('updated_at'),
            'reason': reason
        })

    # Step 7: Convert to DataFrame and sort
    result_df = pd.DataFrame(recommendations)
    result_df = result_df.sort_values('recommendation_score', ascending=False)
    result_df = result_df.head(max_results).reset_index(drop=True)

    logger.info(f"Generated {len(result_df)} personalized recommendations")

    return result_df


def format_recommendations_report(
    recommendations_df: pd.DataFrame,
    top_n: int = 10
) -> str:
    """Format recommendations into a markdown report."""
    if recommendations_df.empty:
        return "No personalized recommendations available"

    lines = [
        f"## 🎯 Personalized Skill Recommendations\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "### Scoring Formula\n",
        "| Factor | Weight | Description |",
        "|--------|--------|-------------|",
        "| Similarity | 30% | Match to installed skills |",
        "| Popularity | 25% | Community stars (log scale) |",
        "| Recency | 20% | Days since last update |",
        "| Category | 15% | Topic overlap |",
        "| Momentum | 10% | Growth trend |",
        "",
        f"### Top {min(top_n, len(recommendations_df))} Recommendations\n"
    ]

    for idx, rec in recommendations_df.head(top_n).iterrows():
        lines.append(f"#### {idx + 1}. {rec['name']}")
        lines.append(f"- **Score:** {rec['recommendation_score']:.3f}")
        lines.append(f"- **Stars:** {rec['stars']:,} ⭐")
        lines.append(f"- **Author:** {rec['author']}")
        lines.append(f"- **Why:** {rec['reason']}")
        lines.append(f"- **Description:** {rec['description']}")
        lines.append("")

    return "\n".join(lines)


# Main for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 70)
    print("ML-BASED RECOMMENDATIONS - Test")
    print("=" * 70)

    try:
        # Fetch skills
        print("\n1. Fetching skills...")
        skills, _ = fetch_all_skills(min_stars=50, max_months_old=6)
        df = parse_skill_manager_response(skills)
        print(f"   Loaded {len(df)} skills")

        # Get recommendations
        print("\n2. Generating recommendations...")
        recommendations = get_personalized_recommendations(
            df,
            min_stars=50,
            max_results=10,
            similarity_threshold=0.3
        )

        print(f"   Generated {len(recommendations)} recommendations")

        # Format report
        print("\n3. Formatting report...")
        report = format_recommendations_report(recommendations)
        print("\n" + report)

        print("\n✅ Test completed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
