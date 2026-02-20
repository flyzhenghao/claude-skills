#!/usr/bin/env python3
"""
Fetch skill data from local skill-manager database.
Loads and filters 31,767 skills from all_skills_with_cn.json.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def load_skill_manager_database(
    database_path: Optional[Path] = None
) -> List[Dict]:
    """
    Load skill-manager database from local JSON file.

    Args:
        database_path: Path to all_skills_with_cn.json (auto-detects if None)

    Returns:
        List of skill dictionaries

    Raises:
        FileNotFoundError: If database file not found
        json.JSONDecodeError: If JSON is invalid

    Example:
        >>> skills = load_skill_manager_database()
        >>> print(f"Loaded {len(skills)} skills")
    """
    if database_path is None:
        # Auto-detect: ~/.claude/skills/skill-manager/data/all_skills_with_cn.json
        database_path = Path.home() / '.claude' / 'skills' / 'skill-manager' / 'data' / 'all_skills_with_cn.json'

    if not database_path.exists():
        raise FileNotFoundError(
            f"skill-manager database not found: {database_path}\n"
            f"Please ensure skill-manager is installed via:\n"
            f"  /plugin marketplace add skill-manager"
        )

    logger.info(f"Loading skill-manager database: {database_path}")

    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both dict and list formats
        if isinstance(data, dict):
            # Extract skills from dict format (key = skill name, value = skill data)
            skills = []
            for name, skill_data in data.items():
                if isinstance(skill_data, dict):
                    skill_data['name'] = name  # Ensure name field exists
                    skills.append(skill_data)
        elif isinstance(data, list):
            skills = data
        else:
            raise ValueError(f"Unexpected data format: {type(data)}")

        logger.info(f"Loaded {len(skills)} skills from database")
        return skills

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in database file: {e}")
        raise


def filter_quality_skills(
    skills: List[Dict],
    min_stars: int = 50,
    max_months_old: int = 6
) -> List[Dict]:
    """
    Filter skills by quality thresholds.

    Args:
        skills: List of skill dictionaries
        min_stars: Minimum GitHub stars required
        max_months_old: Maximum age in months (0 to disable)

    Returns:
        Filtered list of skills

    Example:
        >>> all_skills = load_skill_manager_database()
        >>> quality_skills = filter_quality_skills(all_skills, min_stars=50)
        >>> print(f"Found {len(quality_skills)} quality skills")
    """
    cutoff_date = datetime.now() - timedelta(days=max_months_old * 30) if max_months_old > 0 else None

    filtered = []
    stats = {
        'total': len(skills),
        'filtered_by_stars': 0,
        'filtered_by_recency': 0,
        'filtered_by_missing_data': 0
    }

    for skill in skills:
        # Require basic fields
        if not skill.get('name'):
            stats['filtered_by_missing_data'] += 1
            continue

        # Filter by stars
        stars = skill.get('stars', 0)
        if stars < min_stars:
            stats['filtered_by_stars'] += 1
            continue

        # Filter by recency (if enabled)
        if cutoff_date:
            updated_at = skill.get('updated_at') or skill.get('updated')
            if updated_at:
                try:
                    # Handle multiple datetime formats
                    if isinstance(updated_at, str):
                        # ISO format with Z or timezone
                        updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    else:
                        updated_date = datetime.fromtimestamp(updated_at)

                    if updated_date < cutoff_date:
                        stats['filtered_by_recency'] += 1
                        continue
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Date parsing failed for {skill.get('name')}: {e}")
                    # Don't filter out if date parsing fails - give benefit of doubt

        filtered.append(skill)

    logger.info(
        f"Filtered {len(filtered)}/{stats['total']} skills "
        f"(>={min_stars} stars, updated within {max_months_old} months)\n"
        f"  - Filtered by stars: {stats['filtered_by_stars']}\n"
        f"  - Filtered by recency: {stats['filtered_by_recency']}\n"
        f"  - Filtered by missing data: {stats['filtered_by_missing_data']}"
    )

    return filtered


def get_installed_skills(
    skills_dir: Optional[Path] = None
) -> List[str]:
    """
    Get list of locally installed skill names.

    Args:
        skills_dir: Path to skills directory (auto-detects if None)

    Returns:
        List of installed skill names

    Example:
        >>> installed = get_installed_skills()
        >>> print(f"Found {len(installed)} installed skills")
    """
    if skills_dir is None:
        # Default: ~/.claude/skills/
        skills_dir = Path.home() / '.claude' / 'skills'

    if not skills_dir.exists():
        logger.warning(f"Skills directory not found: {skills_dir}")
        return []

    installed = []
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir() and (skill_path / 'SKILL.md').exists():
            installed.append(skill_path.name)

    logger.info(f"Found {len(installed)} installed skills")
    return installed


def filter_new_skills(
    all_skills: List[Dict],
    installed_skills: List[str]
) -> List[Dict]:
    """
    Filter skills to only those not locally installed.

    Args:
        all_skills: List of all skill dictionaries
        installed_skills: List of installed skill names

    Returns:
        List of skills not installed locally

    Example:
        >>> all_skills = load_skill_manager_database()
        >>> installed = get_installed_skills()
        >>> new_skills = filter_new_skills(all_skills, installed)
        >>> print(f"Found {len(new_skills)} new skills")
    """
    installed_set = set(installed_skills)
    new_skills = [s for s in all_skills if s.get('name') not in installed_set]

    logger.info(f"Found {len(new_skills)} new skills (not installed locally)")
    return new_skills


def extract_skill_metadata(skills: List[Dict]) -> List[Dict]:
    """
    Extract standardized metadata from skills.

    Args:
        skills: List of skill dictionaries (may have varying schemas)

    Returns:
        List of skills with standardized schema

    Example:
        >>> skills = load_skill_manager_database()
        >>> standardized = extract_skill_metadata(skills)
    """
    standardized = []

    for skill in skills:
        metadata = {
            'name': skill.get('name', ''),
            'description': skill.get('description', '') or skill.get('desc', ''),
            'stars': skill.get('stars', 0),
            'forks': skill.get('forks', 0),
            'updated_at': skill.get('updated_at') or skill.get('updated'),
            'author': skill.get('author', '') or skill.get('owner', ''),
            'github_url': skill.get('github_url', '') or skill.get('url', ''),
            'tags': skill.get('tags', []) or skill.get('keywords', []),
            'category': skill.get('category', ''),
        }

        # Ensure types
        metadata['stars'] = int(metadata['stars']) if metadata['stars'] else 0
        metadata['forks'] = int(metadata['forks']) if metadata['forks'] else 0
        metadata['tags'] = metadata['tags'] if isinstance(metadata['tags'], list) else []

        standardized.append(metadata)

    logger.debug(f"Standardized metadata for {len(standardized)} skills")
    return standardized


def fetch_all_skills(
    min_stars: int = 50,
    max_months_old: int = 6,
    include_installed: bool = True
) -> Tuple[List[Dict], Dict[str, any]]:
    """
    Fetch and filter all skills from skill-manager database.

    Args:
        min_stars: Minimum GitHub stars required
        max_months_old: Maximum age in months (0 to disable)
        include_installed: Include locally installed skills

    Returns:
        Tuple of (filtered_skills, statistics)

    Example:
        >>> skills, stats = fetch_all_skills(min_stars=50, max_months_old=6)
        >>> print(f"Fetched {len(skills)} skills")
        >>> print(f"Statistics: {stats}")
    """
    # Load database
    all_skills = load_skill_manager_database()

    # Filter by quality
    quality_skills = filter_quality_skills(all_skills, min_stars, max_months_old)

    # Get installed skills
    installed = get_installed_skills()

    # Filter new skills (if requested)
    if not include_installed:
        quality_skills = filter_new_skills(quality_skills, installed)

    # Standardize metadata
    standardized_skills = extract_skill_metadata(quality_skills)

    # Generate statistics
    statistics = {
        'total_in_database': len(all_skills),
        'after_quality_filter': len(quality_skills),
        'installed_skills': len(installed),
        'new_skills': len([s for s in quality_skills if s.get('name') not in installed]),
        'filters': {
            'min_stars': min_stars,
            'max_months_old': max_months_old,
            'include_installed': include_installed
        },
        'fetched_at': datetime.now().isoformat()
    }

    logger.info(f"Fetch complete: {len(standardized_skills)} skills returned")
    return standardized_skills, statistics


# Main for testing
if __name__ == "__main__":
    import sys

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== fetch_skill_manager.py Test ===\n")

    # Test 1: Load database
    print("1. Testing load_skill_manager_database():")
    try:
        all_skills = load_skill_manager_database()
        print(f"   ✓ Loaded {len(all_skills)} skills")
        print(f"   ✓ Sample skill: {all_skills[0].get('name', 'N/A')}")
    except FileNotFoundError as e:
        print(f"   ✗ Database not found: {e}")
        print("   ℹ Please install skill-manager first")
        sys.exit(1)

    # Test 2: Filter quality skills
    print("\n2. Testing filter_quality_skills():")
    quality_skills = filter_quality_skills(all_skills, min_stars=50, max_months_old=6)
    print(f"   ✓ Filtered to {len(quality_skills)} quality skills")

    # Test 3: Get installed skills
    print("\n3. Testing get_installed_skills():")
    installed = get_installed_skills()
    print(f"   ✓ Found {len(installed)} installed skills")
    if installed:
        print(f"   ✓ Sample: {installed[0]}")

    # Test 4: Filter new skills
    print("\n4. Testing filter_new_skills():")
    new_skills = filter_new_skills(quality_skills, installed)
    print(f"   ✓ Found {len(new_skills)} new skills")

    # Test 5: Extract metadata
    print("\n5. Testing extract_skill_metadata():")
    standardized = extract_skill_metadata(quality_skills[:10])
    print(f"   ✓ Standardized {len(standardized)} skills")
    print(f"   ✓ Sample schema: {list(standardized[0].keys())}")

    # Test 6: Fetch all (main function)
    print("\n6. Testing fetch_all_skills():")
    skills, stats = fetch_all_skills(min_stars=50, max_months_old=6)
    print(f"   ✓ Fetched {len(skills)} skills")
    print(f"   ✓ Statistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"      {key}:")
            for k, v in value.items():
                print(f"        {k}: {v}")
        else:
            print(f"      {key}: {value}")

    print("\n✅ All tests completed")
