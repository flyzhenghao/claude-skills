#!/usr/bin/env python3
"""
Parameter validators for skill-trending-monitor-cskill.
Validates user inputs before making API calls or processing data.
"""

from typing import Any, List, Optional
from datetime import datetime


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_skill_name(skill_name: str, valid_skills: Optional[List[str]] = None) -> str:
    """
    Validate skill name parameter.

    Args:
        skill_name: Skill name to validate
        valid_skills: List of valid skill names (None to skip check)

    Returns:
        str: Validated and normalized skill name

    Raises:
        ValidationError: If skill name is invalid

    Example:
        >>> validate_skill_name("Skill-Manager")
        "skill-manager"  # Normalized to lowercase

        >>> validate_skill_name("invalid", ["skill-a", "skill-b"])
        ValidationError: Invalid skill: invalid
    """
    if not skill_name:
        raise ValidationError("Skill name cannot be empty")

    if not isinstance(skill_name, str):
        raise ValidationError(f"Skill name must be string, got {type(skill_name)}")

    # Normalize: strip whitespace, convert to lowercase
    skill_name = skill_name.strip().lower()

    # Check if valid (if list provided)
    if valid_skills:
        valid_skills_lower = [s.lower() for s in valid_skills]
        if skill_name not in valid_skills_lower:
            # Generate suggestions
            suggestions = [s for s in valid_skills_lower if skill_name[:3] in s]
            error_msg = f"Invalid skill: {skill_name}\n"
            error_msg += f"Valid options: {', '.join(valid_skills[:10])}\n"
            if suggestions:
                error_msg += f"Did you mean: {', '.join(suggestions[:3])}?"
            raise ValidationError(error_msg)

    return skill_name


def validate_threshold(
    value: float,
    min_value: float,
    max_value: float,
    param_name: str = "threshold"
) -> float:
    """
    Validate threshold parameter is in valid range.

    Args:
        value: Threshold value to validate
        min_value: Minimum valid value (inclusive)
        max_value: Maximum valid value (inclusive)
        param_name: Parameter name for error messages

    Returns:
        float: Validated threshold value

    Raises:
        ValidationError: If threshold is out of range

    Example:
        >>> validate_threshold(0.75, 0.0, 1.0, "similarity_threshold")
        0.75

        >>> validate_threshold(1.5, 0.0, 1.0, "similarity_threshold")
        ValidationError: similarity_threshold must be between 0.0 and 1.0, got 1.5
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"{param_name} must be numeric, got {type(value)}"
        )

    if not min_value <= value <= max_value:
        raise ValidationError(
            f"{param_name} must be between {min_value} and {max_value}, got {value}"
        )

    return float(value)


def validate_week_number(
    week: int,
    year: Optional[int] = None,
    min_week: int = 1,
    max_week: int = 53
) -> int:
    """
    Validate week number is in valid range.

    Args:
        week: Week number to validate (ISO week, 1-53)
        year: Year (None for current year)
        min_week: Minimum valid week number
        max_week: Maximum valid week number

    Returns:
        int: Validated week number

    Raises:
        ValidationError: If week number is invalid

    Example:
        >>> validate_week_number(6)
        6

        >>> validate_week_number(0)
        ValidationError: Week number 0 out of range (must be 1-53)

        >>> validate_week_number(54)
        ValidationError: Week number 54 out of range (must be 1-53)
    """
    if not isinstance(week, int):
        raise ValidationError(f"Week number must be integer, got {type(week)}")

    if not min_week <= week <= max_week:
        raise ValidationError(
            f"Week number {week} out of range (must be {min_week}-{max_week})"
        )

    # Optional: Check if year has this many weeks
    # (Some years have only 52 weeks)
    if year is not None:
        from datetime import datetime, timedelta

        # Find last day of year
        last_day = datetime(year, 12, 31)
        # Get ISO calendar
        iso_year, last_week, _ = last_day.isocalendar()

        # If requested week > last week of this year
        if week > last_week and iso_year == year:
            raise ValidationError(
                f"Year {year} only has {last_week} weeks, requested week {week}"
            )

    return week


def validate_stars_threshold(stars: int) -> int:
    """
    Validate stars threshold for quality filtering.

    Args:
        stars: Minimum star count threshold

    Returns:
        int: Validated stars threshold

    Raises:
        ValidationError: If threshold is invalid

    Example:
        >>> validate_stars_threshold(50)
        50

        >>> validate_stars_threshold(-5)
        ValidationError: Stars threshold must be non-negative, got -5
    """
    if not isinstance(stars, int):
        raise ValidationError(f"Stars threshold must be integer, got {type(stars)}")

    if stars < 0:
        raise ValidationError(f"Stars threshold must be non-negative, got {stars}")

    return stars


def validate_months_ago(months: int) -> int:
    """
    Validate months ago parameter for recency filtering.

    Args:
        months: Number of months ago

    Returns:
        int: Validated months parameter

    Raises:
        ValidationError: If months is invalid

    Example:
        >>> validate_months_ago(6)
        6

        >>> validate_months_ago(-1)
        ValidationError: Months must be positive, got -1
    """
    if not isinstance(months, int):
        raise ValidationError(f"Months must be integer, got {type(months)}")

    if months <= 0:
        raise ValidationError(f"Months must be positive, got {months}")

    if months > 24:
        raise ValidationError(
            f"Months threshold too large ({months} months = {months/12:.1f} years). "
            "Consider using a smaller value (6-12 months recommended)"
        )

    return months


def validate_confidence_threshold(confidence: float) -> float:
    """
    Validate confidence threshold (0.0 to 1.0).

    Args:
        confidence: Confidence threshold value

    Returns:
        float: Validated confidence threshold

    Raises:
        ValidationError: If confidence is out of range

    Example:
        >>> validate_confidence_threshold(0.70)
        0.70

        >>> validate_confidence_threshold(1.5)
        ValidationError: Confidence threshold must be between 0.0 and 1.0, got 1.5
    """
    return validate_threshold(confidence, 0.0, 1.0, "confidence_threshold")


def validate_growth_rate_threshold(growth_rate: float) -> float:
    """
    Validate growth rate threshold (typically percentage as decimal).

    Args:
        growth_rate: Growth rate threshold (e.g., 0.05 for 5%)

    Returns:
        float: Validated growth rate threshold

    Raises:
        ValidationError: If growth rate is invalid

    Example:
        >>> validate_growth_rate_threshold(0.05)
        0.05  # 5% growth

        >>> validate_growth_rate_threshold(-0.1)
        # Valid - allows negative growth (decline)
    """
    if not isinstance(growth_rate, (int, float)):
        raise ValidationError(
            f"Growth rate must be numeric, got {type(growth_rate)}"
        )

    # Allow negative growth rates (decline)
    # But warn if extremely large
    if abs(growth_rate) > 10.0:
        raise ValidationError(
            f"Growth rate {growth_rate*100:.1f}% seems unrealistic. "
            "Did you mean {growth_rate/100:.3f} ({growth_rate:.1f}%)?"
        )

    return float(growth_rate)


def validate_security_threshold(security_score: int) -> int:
    """
    Validate security evaluation threshold (0-100).

    Args:
        security_score: Security score threshold

    Returns:
        int: Validated security threshold

    Raises:
        ValidationError: If security score is out of range

    Example:
        >>> validate_security_threshold(70)
        70

        >>> validate_security_threshold(150)
        ValidationError: Security score must be between 0 and 100, got 150
    """
    if not isinstance(security_score, int):
        raise ValidationError(
            f"Security score must be integer, got {type(security_score)}"
        )

    if not 0 <= security_score <= 100:
        raise ValidationError(
            f"Security score must be between 0 and 100, got {security_score}"
        )

    return security_score


# Main for testing
if __name__ == "__main__":
    print("=== Parameter Validators Test ===\n")

    # Test 1: Skill name validation
    print("1. Testing validate_skill_name():")
    try:
        skill = validate_skill_name("Skill-Manager")
        print(f"   ✓ Valid: {skill}")
    except ValidationError as e:
        print(f"   ✗ Error: {e}")

    try:
        validate_skill_name("invalid", ["skill-a", "skill-b"])
    except ValidationError as e:
        print(f"   ✓ Caught invalid skill: {str(e)[:50]}...")

    # Test 2: Threshold validation
    print("\n2. Testing validate_threshold():")
    threshold = validate_threshold(0.75, 0.0, 1.0, "similarity")
    print(f"   ✓ Valid: {threshold}")

    try:
        validate_threshold(1.5, 0.0, 1.0, "similarity")
    except ValidationError as e:
        print(f"   ✓ Caught out-of-range: {e}")

    # Test 3: Week number validation
    print("\n3. Testing validate_week_number():")
    week = validate_week_number(6)
    print(f"   ✓ Valid: Week {week}")

    try:
        validate_week_number(0)
    except ValidationError as e:
        print(f"   ✓ Caught invalid week: {e}")

    # Test 4: Stars threshold
    print("\n4. Testing validate_stars_threshold():")
    stars = validate_stars_threshold(50)
    print(f"   ✓ Valid: {stars} stars")

    # Test 5: Growth rate threshold
    print("\n5. Testing validate_growth_rate_threshold():")
    growth = validate_growth_rate_threshold(0.05)
    print(f"   ✓ Valid: {growth*100}% growth")

    # Test 6: Security threshold
    print("\n6. Testing validate_security_threshold():")
    security = validate_security_threshold(70)
    print(f"   ✓ Valid: {security}/100")
