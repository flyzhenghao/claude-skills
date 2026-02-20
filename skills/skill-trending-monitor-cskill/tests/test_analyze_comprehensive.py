#!/usr/bin/env python3
"""Tests for analyze_comprehensive module."""

import json
from datetime import datetime as real_datetime
from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import analyze_comprehensive as ac
from analyze_comprehensive import (
    _apply_profile,
    _build_output_path,
    _deep_merge,
    _format_comprehensive_report,
    _format_safe_url,
    _read_json,
    _strip_metadata,
    generate_comprehensive_report,
    load_config,
    load_profile,
)


def test_read_json_success(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"a": 1, "b": {"c": 2}}', encoding="utf-8")

    assert _read_json(path) == {"a": 1, "b": {"c": 2}}


def test_read_json_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        _read_json(tmp_path / "missing.json")


def test_read_json_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{bad", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        _read_json(path)


def test_load_config_default_path_uses_assets():
    expected = Path(ac.__file__).parent.parent / "assets" / "config.json"
    with patch.object(ac, "_read_json", return_value={"ok": True}) as mock_read:
        result = load_config()

    mock_read.assert_called_once_with(expected)
    assert result == {"ok": True}


def test_load_config_custom_path(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}', encoding="utf-8")

    assert load_config(config_path=config_file) == {"key": "value"}


def test_load_config_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(config_path=tmp_path / "missing.json")


def test_strip_metadata_recursive():
    data = {
        "_private": 1,
        "keep": 2,
        "nested": {
            "_skip": 3,
            "value": 4,
        },
        "list": [{"_leave": 5}, 6],
    }

    assert _strip_metadata(data) == {
        "keep": 2,
        "nested": {"value": 4},
        "list": [{"_leave": 5}, 6],
    }


def test_deep_merge_simple():
    base = {"a": 1, "b": 2}
    overrides = {"b": 3, "c": 4}

    result = _deep_merge(base, overrides)

    assert result == {"a": 1, "b": 3, "c": 4}
    assert base == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested():
    base = {"quality": {"min_stars": 50, "max_months_old": 6}}
    overrides = {"quality": {"min_stars": 10}}

    result = _deep_merge(base, overrides)

    assert result["quality"]["min_stars"] == 10
    assert result["quality"]["max_months_old"] == 6


def test_deep_merge_list_replace():
    base = {"tags": ["a", "b"]}
    overrides = {"tags": ["c"]}

    result = _deep_merge(base, overrides)

    assert result["tags"] == ["c"]


def test_load_profile_found():
    with patch.object(
        ac, "_read_json", return_value={"profiles": {"strict": {"min_stars": 100}}}
    ):
        assert load_profile("strict") == {"min_stars": 100}


def test_load_profile_missing():
    with patch.object(ac, "_read_json", return_value={"profiles": {"balanced": {}}}):
        with pytest.raises(ValueError):
            load_profile("strict")


def test_apply_profile_merges_sections():
    config = {"thresholds": {"quality": {"min_stars": 10}, "similarity": {"threshold": 0.4}}}
    profile = {
        "quality": {"min_stars": 20, "_note": "ignore"},
        "security": {"threshold": 80},
    }

    result = _apply_profile(config, profile)

    assert result["thresholds"]["quality"] == {"min_stars": 20}
    assert result["thresholds"]["similarity"]["threshold"] == 0.4
    assert result["thresholds"]["security"]["threshold"] == 80


def test_apply_profile_handles_non_dict_existing():
    config = {"thresholds": {"security": "legacy"}}
    profile = {"security": {"threshold": 70}}

    result = _apply_profile(config, profile)

    assert result["thresholds"]["security"] == {"threshold": 70}


def test_apply_profile_empty_profile_no_change():
    config = {"thresholds": {"quality": {"min_stars": 10}}}

    assert _apply_profile(config, {}) == {"thresholds": {"quality": {"min_stars": 10}}}


def test_build_output_path_none():
    assert _build_output_path({}) is None
    assert _build_output_path({"output": {}}) is None


def test_build_output_path_with_pattern(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return real_datetime(2024, 1, 2, 3, 4, 5)

    monkeypatch.setattr(ac, "datetime", FixedDateTime)

    config = {
        "output": {
            "report_dir": "meta/reports",
            "filename_pattern": "{date}-custom.md",
        }
    }

    expected = Path(ac.__file__).parent.parent / "meta" / "reports" / "2024-01-02-custom.md"
    assert _build_output_path(config) == expected


def test_build_output_path_rejects_path_escape(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return real_datetime(2024, 1, 2, 3, 4, 5)

    monkeypatch.setattr(ac, "datetime", FixedDateTime)

    config = {
        "output": {
            "report_dir": "../../outside",
            "filename_pattern": "{date}-custom.md",
        }
    }

    with pytest.raises(ValueError, match="escapes skill directory"):
        _build_output_path(config)


def test_format_safe_url_accepts_https():
    assert _format_safe_url("https://example.com/path?a=1") == "<https://example.com/path?a=1>"


def test_format_safe_url_rejects_unsafe_chars():
    rendered = _format_safe_url("https://example.com/>pwn")
    assert rendered == "https://example.com/\\>pwn"


def test_format_safe_url_rejects_userinfo():
    rendered = _format_safe_url("https://user:pass@example.com/private")
    assert rendered == "https://user:pass@example.com/private"


def test_format_comprehensive_report_with_data():
    long_desc = "x" * 201
    new_skills = pd.DataFrame(
        [
            {
                "name": "Skill A",
                "stars": 1234,
                "forks": 12,
                "updated_at": real_datetime(2024, 1, 1),
                "author": "Alice",
                "description": long_desc,
                "github_url": "https://example.com/a",
            }
        ]
    )
    growing_skills = pd.DataFrame(
        [
            {
                "name": "Skill B",
                "wow_growth_rate": 12.34,
                "total_stars": 2000,
                "current_week_stars": 50,
                "previous_week_stars": 40,
                "author": "Bob",
                "description": "Fast growth",
                "github_url": "https://example.com/b",
            }
        ]
    )
    replaceable_skills = pd.DataFrame(
        [
            {
                "installed_skill": "old",
                "replacement_candidate": "new",
                "confidence_score": 0.8,
                "star_ratio": 1.0,
                "candidate_stars": 200,
                "installed_stars": 100,
                "recency_factor": 0.9,
                "similarity_score": 0.95,
                "candidate_updated": real_datetime(2024, 1, 3),
            }
        ]
    )
    secure_skills = pd.DataFrame(
        [
            {
                "name": "Secure Skill",
                "security_score": 95,
                "assessment": "EXCELLENT",
                "stars_score": 90,
                "activity_score": 88,
                "license_score": 100,
                "update_score": 85,
                "github_url": "https://example.com/secure",
            }
        ]
    )
    statistics = {
        "generated_at": "2024-01-04T00:00:00",
        "new_skills": {"total_found": 1, "top_recommended": 1, "new_skills_found": 1},
        "growing_skills": {"total_found": 1, "top_recommended": 1, "growth_calculated_for": 1},
        "replaceable_skills": {"total_found": 1, "top_recommended": 1},
        "secure_skills": {"total_found": 1, "top_recommended": 1},
        "filters": {
            "min_stars": 10,
            "max_months_old": 6,
            "min_growth_rate": 5.0,
            "similarity_threshold": 0.7,
            "confidence_threshold": 0.8,
            "security_threshold": 70,
        },
    }

    report = _format_comprehensive_report(
        new_skills, growing_skills, replaceable_skills, secure_skills, statistics
    )

    assert "Claude Skills Trending Report" in report
    assert "Skill A" in report
    assert "Skill B" in report
    assert "Replace: old" in report
    assert "Secure Skill" in report
    assert "EXCELLENT" in report
    assert "2024-01-01" in report
    assert "Description: " in report
    assert "..." in report


def test_generate_comprehensive_report_happy_path(tmp_path):
    output_path = tmp_path / "report.md"
    new_df = pd.DataFrame([{"name": "new"}])
    growing_df = pd.DataFrame([{"name": "grow"}])
    replaceable_df = pd.DataFrame([{"installed_skill": "old"}])
    secure_df = pd.DataFrame([{"name": "secure"}])
    base_df = pd.DataFrame([{"name": "installed", "stars": 10}, {"name": "other", "stars": 5}])

    with (
        patch.object(ac, "analyze_new_skills", return_value=(new_df, {"new_skills_found": 1})),
        patch.object(ac, "analyze_growth_rates", return_value=(growing_df, {"growth_calculated_for": 1})),
        patch.object(ac, "fetch_all_skills", return_value=([{"name": "installed"}], {})),
        patch.object(ac, "parse_skill_manager_response", return_value=base_df),
        patch.object(ac, "get_installed_skills", return_value=["installed"]),
        patch.object(ac, "calculate_skill_similarity", return_value=pd.DataFrame([{"dummy": 1}])),
        patch.object(ac, "calculate_replacement_confidence", return_value=replaceable_df),
        patch.object(ac, "evaluate_skill_security", return_value=secure_df),
        patch.object(ac, "_format_comprehensive_report", return_value="REPORT"),
    ):
        result = generate_comprehensive_report(
            github_token="token",
            min_stars=5,
            max_months_old=1,
            min_growth_rate=2.0,
            similarity_threshold=0.5,
            confidence_threshold=0.6,
            security_threshold=70,
            top_n_new=1,
            top_n_growing=1,
            top_n_replaceable=1,
            top_n_secure=1,
            output_path=output_path,
        )

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == "REPORT"
    assert result["report_path"] == output_path
    assert result["statistics"]["filters"]["min_stars"] == 5
