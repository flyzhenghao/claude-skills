#!/usr/bin/env python3
"""
Comprehensive skill trending analysis orchestrator.
Combines all analysis modules to generate unified trending report.
"""

import argparse
import json
import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys
import re
from urllib.parse import urlparse

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from analyze_new_skills import analyze_new_skills
from analyze_growth_rates import analyze_growth_rates
from analyze_similarity import calculate_skill_similarity
from analyze_replacements import calculate_replacement_confidence
from evaluate_security import evaluate_skill_security
from fetch_skill_manager import fetch_all_skills, get_installed_skills
from parse_skill_manager import parse_skill_manager_response

logger = logging.getLogger(__name__)

_MD_ESCAPE_RE = re.compile(r'([\\`*_{}\[\]()#+\-!|>])')
_URL_UNSAFE_CHARS_RE = re.compile(r"[\x00-\x1f\x7f<>\[\]\(\)`\"']")


class _I18nFallbackDict(dict):
    """Fallback dictionary that returns a readable label for missing i18n keys."""

    def __missing__(self, key):
        return key.replace("_", " ")


def _escape_markdown(value: object) -> str:
    """Escape untrusted text before embedding into Markdown output."""
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return _MD_ESCAPE_RE.sub(r'\\\1', text)


def _format_safe_url(value: object) -> str:
    """Render a URL safely in Markdown; fallback to escaped text if invalid."""
    text = str(value or "").strip().replace("\r", "").replace("\n", "")
    if not text:
        return ""
    if _URL_UNSAFE_CHARS_RE.search(text):
        return _escape_markdown(text)
    parsed = urlparse(text)
    if (
        parsed.scheme in ("http", "https")
        and parsed.netloc
        and parsed.username is None
        and parsed.password is None
    ):
        return f"<{text}>"
    return _escape_markdown(text)


def _read_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_i18n(language: str = 'zh') -> Dict[str, str]:
    """加载语言包"""
    i18n_path = Path(__file__).parent.parent / 'assets' / 'i18n.json'
    with open(i18n_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(language, data['zh'])


def load_action_history() -> Dict:
    """加载行动历史"""
    history_path = Path(__file__).parent.parent / 'meta' / 'action-history.json'
    if not history_path.exists():
        return {
            "last_updated": None,
            "actions": [],
            "recommendations": {},
            "metadata": {
                "description": "Skill Trending Action History",
                "purpose": "Track recommended, installed, and replaced skills over time",
                "version": "1.0.0"
            }
        }
    with open(history_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_action_history(history: Dict) -> None:
    """保存行动历史"""
    history_path = Path(__file__).parent.parent / 'meta' / 'action-history.json'
    history['last_updated'] = datetime.now().isoformat()
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_recommendations(skill_names: List[str], date: str = None) -> None:
    """记录本次推荐的 skills"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    history = load_action_history()
    history['recommendations'][date] = skill_names

    for name in skill_names:
        history['actions'].append({
            "date": date,
            "type": "recommend_install",
            "skill_name": name,
            "reason": "Weekly trending analysis",
            "status": "recommended"
        })

    save_action_history(history)


def load_config(config_path: Optional[Path] = None) -> Dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'assets' / 'config.json'
    return _read_json(config_path)


def _strip_metadata(value: Dict) -> Dict:
    cleaned: Dict = {}
    for key, val in value.items():
        if key.startswith('_'):
            continue
        if isinstance(val, dict):
            cleaned[key] = _strip_metadata(val)
        else:
            cleaned[key] = val
    return cleaned


def _deep_merge(base: Dict, overrides: Dict) -> Dict:
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def load_profile(profile_name: str) -> Dict:
    filters_path = Path(__file__).parent.parent / 'assets' / 'filters.json'
    data = _read_json(filters_path)
    profiles = data.get('profiles', {})
    if profile_name not in profiles:
        raise ValueError(f"Unknown profile: {profile_name}")
    return profiles[profile_name]


def _apply_profile(config: Dict, profile: Dict) -> Dict:
    thresholds = config.setdefault('thresholds', {})
    for section in ('quality', 'similarity', 'replacement', 'security'):
        if section not in profile:
            continue
        overrides = _strip_metadata(profile[section])
        existing = thresholds.get(section, {})
        if not isinstance(existing, dict):
            existing = {}
        thresholds[section] = _deep_merge(existing, overrides)
    return config


def _build_output_path(config: Dict) -> Optional[Path]:
    output_cfg = config.get('output', {})
    report_dir = output_cfg.get('report_dir')
    if not report_dir:
        return None
    filename_pattern = output_cfg.get('filename_pattern', '{date}-skill-trending-report.md')
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = filename_pattern.format(date=date_str)
    base_dir = Path(__file__).parent.parent.resolve()
    candidate = (base_dir / report_dir / filename).resolve()
    if not candidate.is_relative_to(base_dir):
        raise ValueError("Output path escapes skill directory")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comprehensive skill trending analysis"
    )
    parser.add_argument(
        '--profile',
        choices=['strict', 'balanced', 'permissive', 'experimental'],
        default='balanced',
        help='Filter profile to use (default: balanced). See assets/filters.json for details.'
    )
    parser.add_argument(
        '--language',
        choices=['zh', 'en'],
        default='zh',
        help='Report language (default: zh). Options: zh (Chinese), en (English).'
    )
    args = parser.parse_args()

    config = load_config()
    profile = load_profile(args.profile)
    _apply_profile(config, profile)

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger.info(f"Using filter profile: {args.profile}")

    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.error("GITHUB_TOKEN not set. Refusing to read token from config file.")
        return 1

    thresholds = config.get('thresholds', {})
    quality = thresholds.get('quality', {})
    similarity = thresholds.get('similarity', {})
    replacement = thresholds.get('replacement', {})
    security = thresholds.get('security', {})

    output_path = _build_output_path(config)
    output_cfg = config.get('output', {})
    top_n_cfg = output_cfg.get('top_n', {})

    generate_comprehensive_report(
        github_token=github_token,
        min_stars=quality.get('min_stars', 50),
        max_months_old=quality.get('max_months_old', 6),
        min_growth_rate=thresholds.get('min_growth_rate', 5.0),
        similarity_threshold=similarity.get('threshold', 0.75),
        confidence_threshold=replacement.get('confidence_threshold', 0.70),
        security_threshold=security.get('threshold', 70),
        top_n_new=top_n_cfg.get('new_skills', 20),
        top_n_growing=top_n_cfg.get('growth_rates', 10),
        top_n_replaceable=top_n_cfg.get('replacements', 10),
        top_n_secure=top_n_cfg.get('security_assessments', 10),
        output_path=output_path,
        language=args.language
    )

    return 0


def generate_comprehensive_report(
    github_token: str,
    min_stars: int = 50,
    max_months_old: int = 6,
    min_growth_rate: float = 5.0,
    similarity_threshold: float = 0.75,
    confidence_threshold: float = 0.70,
    security_threshold: int = 70,
    top_n_new: int = 20,
    top_n_growing: int = 10,
    top_n_replaceable: int = 10,
    top_n_secure: int = 10,
    output_path: Optional[Path] = None,
    language: str = 'zh'
) -> Dict:
    """
    Generate comprehensive skill trending report combining all analyses.

    This is the main orchestrator function that:
    1. Calls analyze_new_skills() for new skill recommendations
    2. Calls analyze_growth_rates() for fastest growing skills
    3. Calls calculate_skill_similarity() and calculate_replacement_confidence() for replacements
    4. Calls evaluate_skill_security() for security assessments
    5. Aggregates all results into unified report
    6. Exports to meta/reports/YYYY-MM-DD-skill-trending-report.md

    Args:
        github_token: GitHub API token for star history
        min_stars: Minimum stars for quality filtering
        max_months_old: Maximum age in months for recency filtering
        min_growth_rate: Minimum WoW growth rate percentage
        similarity_threshold: Minimum similarity score (0.0-1.0)
        confidence_threshold: Minimum replacement confidence (0.0-1.0)
        security_threshold: Minimum security score (0-100)
        top_n_new: Number of new skills to recommend
        top_n_growing: Number of growing skills to recommend
        top_n_replaceable: Number of replacement recommendations
        top_n_secure: Number of secure skills to highlight
        output_path: Optional custom output path

    Returns:
        Dict with comprehensive report data:
        {
            'new_skills': DataFrame,
            'growing_skills': DataFrame,
            'replaceable_skills': DataFrame,
            'secure_skills': DataFrame,
            'statistics': Dict,
            'report_path': Path
        }

    Raises:
        ValueError: If required parameters invalid
        RuntimeError: If analysis pipeline fails

    Example:
        >>> report = generate_comprehensive_report(
        ...     github_token="ghp_xxx",
        ...     min_stars=50,
        ...     max_months_old=6
        ... )
        >>> print(f"Report saved to: {report['report_path']}")
    """
    logger.info("Starting comprehensive skill trending analysis")

    # Phase 1: Analyze new skills
    logger.info("Phase 1/4: Analyzing new skills...")
    try:
        new_skills, new_stats = analyze_new_skills(
            min_stars=min_stars,
            max_months_old=max_months_old,
            top_n=top_n_new
        )
        logger.info(f"Found {len(new_skills)} new skills")
    except Exception as e:
        logger.error(f"Failed to analyze new skills: {e}")
        new_skills = pd.DataFrame()
        new_stats = {'new_skills_found': 0}

    # Phase 2: Analyze growth rates
    logger.info("Phase 2/4: Analyzing growth rates...")
    try:
        # Fetch skills for growth analysis
        skills, _ = fetch_all_skills(min_stars=min_stars, max_months_old=max_months_old)
        df = parse_skill_manager_response(skills)

        # Limit to top by stars for GitHub API rate limiting
        # (Growth analysis requires GitHub API calls)
        top_popular = df.nlargest(50, 'stars')

        growing_skills, growth_stats = analyze_growth_rates(
            top_popular,
            github_token,
            min_growth_rate=min_growth_rate,
            top_n=top_n_growing
        )
        logger.info(f"Found {len(growing_skills)} fast-growing skills")
    except Exception as e:
        logger.error(f"Failed to analyze growth rates: {e}")
        growing_skills = pd.DataFrame()
        growth_stats = {'growth_calculated_for': 0}

    # Phase 3: Analyze replacements
    logger.info("Phase 3/4: Analyzing replacement recommendations...")
    try:
        # Get installed skills
        installed_names = get_installed_skills()

        if len(installed_names) > 0:
            # Fetch all skills (using profile filters to reduce dataset size)
            skills, _ = fetch_all_skills(min_stars=min_stars, max_months_old=max_months_old)
            df = parse_skill_manager_response(skills)

            # Filter for installed skills
            installed_df = df[df['name'].isin(installed_names)]

            # Calculate similarity (only for installed skills)
            similarity_df = calculate_skill_similarity(
                df,
                similarity_threshold=similarity_threshold,
                installed_skills=installed_names
            )

            # Calculate replacement confidence
            if not similarity_df.empty:
                replaceable_skills = calculate_replacement_confidence(
                    installed_df,
                    df,
                    similarity_df,
                    confidence_threshold=confidence_threshold
                )
                logger.info(f"Found {len(replaceable_skills)} replacement recommendations")
            else:
                replaceable_skills = pd.DataFrame()
                logger.warning("No similar skills found for replacement analysis")
        else:
            replaceable_skills = pd.DataFrame()
            logger.warning("No installed skills found for replacement analysis")

    except Exception as e:
        logger.error(f"Failed to analyze replacements: {e}")
        replaceable_skills = pd.DataFrame()

    # Phase 4: Evaluate security
    logger.info("Phase 4/4: Evaluating security...")
    try:
        # Fetch skills for security evaluation
        skills, _ = fetch_all_skills(min_stars=min_stars, max_months_old=max_months_old)
        df = parse_skill_manager_response(skills)

        secure_skills = evaluate_skill_security(
            df,
            security_threshold=security_threshold
        )
        logger.info(f"Found {len(secure_skills)} skills passing security threshold")
    except Exception as e:
        logger.error(f"Failed to evaluate security: {e}")
        secure_skills = pd.DataFrame()

    # Aggregate statistics
    statistics = {
        'generated_at': datetime.now().isoformat(),
        'new_skills': {
            'total_found': len(new_skills),
            'top_recommended': top_n_new,
            **new_stats
        },
        'growing_skills': {
            'total_found': len(growing_skills),
            'top_recommended': top_n_growing,
            **growth_stats
        },
        'replaceable_skills': {
            'total_found': len(replaceable_skills),
            'top_recommended': top_n_replaceable
        },
        'secure_skills': {
            'total_found': len(secure_skills),
            'top_recommended': top_n_secure
        },
        'filters': {
            'min_stars': min_stars,
            'max_months_old': max_months_old,
            'min_growth_rate': min_growth_rate,
            'similarity_threshold': similarity_threshold,
            'confidence_threshold': confidence_threshold,
            'security_threshold': security_threshold
        }
    }

    # Record recommendations to action history
    current_recommendations = new_skills['name'].head(top_n_new).tolist() if not new_skills.empty else []
    if current_recommendations:
        logger.info(f"Recording {len(current_recommendations)} recommendations to action history")
        add_recommendations(current_recommendations)

    # Generate report
    logger.info(f"Generating Markdown report (language={language})...")
    report_content = _format_comprehensive_report(
        new_skills.head(top_n_new) if not new_skills.empty else pd.DataFrame(),
        growing_skills.head(top_n_growing) if not growing_skills.empty else pd.DataFrame(),
        replaceable_skills.head(top_n_replaceable) if not replaceable_skills.empty else pd.DataFrame(),
        secure_skills.head(top_n_secure) if not secure_skills.empty else pd.DataFrame(),
        statistics,
        language=language
    )

    # Export report
    if output_path is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_path = Path(__file__).parent.parent / 'meta' / 'reports' / f'{date_str}-skill-trending-report.md'

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logger.info(f"Report exported to: {output_path}")

    return {
        'new_skills': new_skills,
        'growing_skills': growing_skills,
        'replaceable_skills': replaceable_skills,
        'secure_skills': secure_skills,
        'statistics': statistics,
        'report_path': output_path
    }


def _format_action_summary(i18n: Dict[str, str], history: Dict, current_recommendations: List[str]) -> str:
    """
    Format action summary section showing what the system has done.

    Args:
        i18n: Translation dictionary
        history: Action history data
        current_recommendations: List of skill names recommended this week

    Returns:
        Formatted action summary as markdown string
    """
    action_summary_label = i18n.get('action_summary', 'Action Summary')
    this_week_label = i18n.get('this_week', 'This Week')
    trend_label = i18n.get('trend_comparison', 'Trend Comparison')
    no_history_label = i18n.get('no_historical_data', 'No historical data')

    lines = [f"## {action_summary_label}\n"]

    # Current week recommendations
    lines.append(f"### {this_week_label}\n")
    lines.append(f"- **{i18n['recommended_to_install']}:** {len(current_recommendations)} skills")

    if current_recommendations:
        lines.append("  - " + ", ".join(f"`{name}`" for name in current_recommendations[:5]))
        if len(current_recommendations) > 5:
            lines.append(f"  - ... and {len(current_recommendations) - 5} more\n")
    else:
        lines.append("")

    # Historical comparison (last 4 weeks)
    lines.append(f"\n### {trend_label}\n")

    if history.get('recommendations'):
        # Get last 4 weeks data
        from datetime import datetime, timedelta
        today = datetime.now()
        weeks_data = []

        for i in range(4):
            week_start = today - timedelta(days=7 * (i + 1))
            week_key = week_start.strftime('%Y-%m-%d')

            # Find closest date in history
            closest_date = None
            min_diff = float('inf')

            for date_str in history['recommendations'].keys():
                try:
                    hist_date = datetime.fromisoformat(date_str.split('T')[0])
                    diff = abs((hist_date - week_start).days)
                    if diff < min_diff and diff <= 7:
                        min_diff = diff
                        closest_date = date_str
                except (ValueError, TypeError):
                    continue

            if closest_date:
                count = len(history['recommendations'][closest_date])
                weeks_data.append((i + 1, count))

        if weeks_data:
            lines.append("| Week | Recommended Skills |")
            lines.append("|------|-------------------|")
            lines.append(f"| This Week | {len(current_recommendations)} |")
            for week_num, count in weeks_data:
                lines.append(f"| -{week_num} week(s) | {count} |")
            lines.append("")
    else:
        lines.append(f"*{no_history_label}*\n")

    lines.append("---\n")

    return "\n".join(lines)


def _format_comprehensive_report(
    new_skills: pd.DataFrame,
    growing_skills: pd.DataFrame,
    replaceable_skills: pd.DataFrame,
    secure_skills: pd.DataFrame,
    statistics: Dict,
    language: str = 'en'
) -> str:
    """
    Format comprehensive trending report as Markdown.

    Args:
        new_skills: DataFrame with new skill recommendations
        growing_skills: DataFrame with fastest growing skills
        replaceable_skills: DataFrame with replacement recommendations
        secure_skills: DataFrame with security assessments
        statistics: Statistics dictionary
        language: Language code ('zh' or 'en'), defaults to 'zh'

    Returns:
        Formatted Markdown report string
    """
    # Load translations and history
    i18n = _I18nFallbackDict(load_i18n(language))
    history = load_action_history()

    # Get current recommendations
    current_recommendations = new_skills['name'].tolist() if not new_skills.empty else []

    # Start building report
    lines = [
        f"# {i18n['report_title']}\n",
        f"**{i18n['generated_at']}:** {statistics['generated_at']}\n",
        "---\n"
    ]

    # Action Summary (NEW)
    lines.append(_format_action_summary(i18n, history, current_recommendations))

    # Executive Summary
    lines.append(f"## {i18n['executive_summary']}\n")

    # Summary statistics
    lines.append(f"### {i18n['overview']}\n")
    lines.append(f"- **{i18n['new_skills_discovered']}:** {statistics['new_skills']['total_found']}")
    lines.append(f"- **{i18n['fast_growing_skills']}:** {statistics['growing_skills']['total_found']}")
    lines.append(f"- **{i18n['replacement_opportunities']}:** {statistics['replaceable_skills']['total_found']}")
    secure_count_label = i18n.get('secure_skills_count', i18n.get('secure_skills', 'Secure Skills'))
    lines.append(f"- **{secure_count_label}:** {statistics['secure_skills']['total_found']}\n")

    # Filter criteria
    lines.append(f"### {i18n['filter_criteria']}\n")
    filters = statistics['filters']
    lines.append(f"- **{i18n['minimum_stars']}:** {filters['min_stars']}")
    lines.append(f"- **{i18n['maximum_age']}:** {filters['max_months_old']} {i18n['months']}")
    lines.append(f"- **{i18n['minimum_growth_rate']}:** {filters['min_growth_rate']}%")
    lines.append(f"- **{i18n['similarity_threshold']}:** {filters['similarity_threshold']}")
    lines.append(f"- **{i18n['confidence_threshold']}:** {filters['confidence_threshold']}")
    lines.append(f"- **{i18n['security_threshold']}:** {filters['security_threshold']}/100\n")

    lines.append("---\n")

    # Section 1: New Skills
    lines.append(f"## {i18n['new_skills']}\n")

    if not new_skills.empty:
        lines.append(f"**{i18n['found']} {len(new_skills)} {i18n['new_high_quality_skills']}**\n")

        for idx, skill in new_skills.iterrows():
            lines.append(f"### {idx + 1}. {_escape_markdown(skill['name'])}\n")
            lines.append(f"- **{i18n['stars']}:** {skill['stars']:,} ⭐")
            lines.append(f"- **{i18n['forks']}:** {skill['forks']:,} 🔀")

            if pd.notna(skill.get('updated_at')):
                if isinstance(skill['updated_at'], datetime):
                    updated = skill['updated_at'].strftime('%Y-%m-%d')
                else:
                    updated = str(skill['updated_at'])[:10]
                lines.append(f"- **{i18n['last_updated']}:** {updated}")

            if skill.get('author'):
                lines.append(f"- **{i18n['author']}:** {_escape_markdown(skill['author'])}")

            if skill.get('description'):
                desc = skill['description'][:200]
                if len(skill['description']) > 200:
                    desc += "..."
                lines.append(f"- {i18n['description']}: {_escape_markdown(desc)}")

            if skill.get('github_url'):
                lines.append(f"- **GitHub:** {_format_safe_url(skill['github_url'])}")

            lines.append("")
    else:
        lines.append(f"*{i18n['no_new_skills_found']}*\n")

    lines.append("---\n")

    # Section 2: Fastest Growing
    lines.append(f"## {i18n['fast_growing']}\n")

    if not growing_skills.empty:
        lines.append(f"**{i18n['found']} {len(growing_skills)} {i18n['significant_growth_skills']}**\n")

        for idx, skill in growing_skills.iterrows():
            lines.append(f"### {idx + 1}. {_escape_markdown(skill['name'])}\n")
            lines.append(f"- **{i18n['wow_growth_rate']}:** {skill['wow_growth_rate']:.2f}% 📈")
            lines.append(f"- **{i18n['total_stars']}:** {skill['total_stars']:,} ⭐")
            lines.append(f"- **{i18n['current_week']}:** {skill['current_week_stars']} {i18n['new_stars']}")
            lines.append(f"- **{i18n['previous_week']}:** {skill['previous_week_stars']} stars")

            if skill.get('author'):
                lines.append(f"- **{i18n['author']}:** {_escape_markdown(skill['author'])}")

            if skill.get('description'):
                desc = skill['description'][:200]
                if len(skill['description']) > 200:
                    desc += "..."
                lines.append(f"- {i18n['description']}: {_escape_markdown(desc)}")

            if skill.get('github_url'):
                lines.append(f"- **GitHub:** {_format_safe_url(skill['github_url'])}")

            lines.append("")
    else:
        lines.append(f"*{i18n['no_fast_growing_skills']}*\n")

    lines.append("---\n")

    # Section 3: Replacement Recommendations
    lines.append(f"## {i18n['replacement_recommendations']}\n")

    if not replaceable_skills.empty:
        lines.append(f"**{i18n['found']} {len(replaceable_skills)} {i18n['replacement_opportunities_desc']}**\n")
        lines.append(f"### {i18n['confidence_formula']}\n")
        lines.append(f"- **{i18n['star_ratio']}:** {i18n['star_ratio_desc']}")
        lines.append(f"- **{i18n['recency_factor']}:** {i18n['recency_factor_desc']}")
        lines.append(f"- **{i18n['text_similarity']}:** {i18n['text_similarity_desc']}\n")

        for idx, rec in replaceable_skills.iterrows():
            lines.append(
                f"### {idx + 1}. {i18n['replace']}: "
                f"{_escape_markdown(rec['installed_skill'])} → "
                f"{_escape_markdown(rec['replacement_candidate'])}\n"
            )
            lines.append(f"- **{i18n['confidence_score']}:** {rec['confidence_score']:.3f} ({i18n['threshold']}: 0.70)")
            lines.append(f"- **{i18n['star_ratio']}:** {rec['star_ratio']:.3f} ({rec['candidate_stars']:,} vs {rec['installed_stars']:,})")
            lines.append(f"- **{i18n['recency_factor']}:** {rec['recency_factor']:.3f}")
            lines.append(f"- **{i18n['similarity_score']}:** {rec['similarity_score']:.3f}")

            if pd.notna(rec.get('candidate_updated')):
                if isinstance(rec['candidate_updated'], datetime):
                    updated = rec['candidate_updated'].strftime('%Y-%m-%d')
                else:
                    updated = str(rec['candidate_updated'])[:10]
                lines.append(f"- **{i18n['candidate_last_updated']}:** {updated}")

            lines.append("")
    else:
        lines.append(f"*{i18n['no_replacement_found']}*\n")

    lines.append("---\n")

    # Section 4: Security Assessments
    lines.append(f"## {i18n['security_assessments']}\n")

    if not secure_skills.empty:
        lines.append(f"**{i18n['found']} {len(secure_skills)} {i18n['skills_passing_security']}**\n")
        lines.append(f"### {i18n['security_formula']}\n")
        lines.append(f"- **{i18n['github_stars']}:** {i18n['github_stars_weight']}")
        lines.append(f"- **{i18n['recent_activity']}:** {i18n['recent_activity_weight']}")
        lines.append(f"- **{i18n['license_verification']}:** {i18n['license_weight']}")
        lines.append(f"- **{i18n['update_frequency']}:** {i18n['update_frequency_weight']}\n")

        # Assessment level breakdown
        level_counts = secure_skills['assessment'].value_counts()
        lines.append(f"### {i18n['assessment_levels']}\n")
        for level in ['EXCELLENT', 'GOOD', 'MODERATE', 'LOW', 'POOR']:
            count = level_counts.get(level, 0)
            lines.append(f"- **{level}:** {count}")

        top_count = min(10, len(secure_skills))
        lines.append(f"\n### {i18n['top']} {top_count} {i18n['secure_skills']}\n")

        for idx, skill in secure_skills.head(10).iterrows():
            lines.append(f"#### {idx + 1}. {_escape_markdown(skill['name'])}\n")
            lines.append(f"- **{i18n['security_score']}:** {skill['security_score']}/100 ({skill['assessment']})")
            lines.append(f"- **{i18n['component_scores']}:**")
            lines.append(f"  - {i18n['stars']}: {skill['stars_score']}/100")
            lines.append(f"  - {i18n['activity']}: {skill['activity_score']}/100")
            lines.append(f"  - {i18n['license']}: {skill['license_score']}/100")
            lines.append(f"  - {i18n['updates']}: {skill['update_score']}/100")
            lines.append(f"- **GitHub:** {_format_safe_url(skill['github_url'])}")
            lines.append("")
    else:
        lines.append(f"*{i18n['no_secure_skills_found']}*\n")

    lines.append("---\n")

    # Footer
    lines.append("## 📝 Notes\n")
    lines.append("- **Data Sources:** skill-manager database (31,767 skills) + GitHub API")
    lines.append("- **Refresh Frequency:** Weekly (recommended)")
    lines.append("- **Installation:** Use `/skill-manager` to install recommended skills\n")

    lines.append("---\n")
    lines.append("*🤖 Generated by skill-trending-monitor-cskill*\n")

    return "\n".join(lines)


# Main for testing
if __name__ == "__main__":
    sys.exit(main())
