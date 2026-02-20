#!/usr/bin/env python3
"""Tests for config_loader module."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from config_loader import deep_merge, load_config, get_config_value


def test_deep_merge_simple():
    """Test basic deep merge."""
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}

    result = deep_merge(base, override)

    assert result == {"a": 1, "b": 3, "c": 4}
    # Original unchanged
    assert base == {"a": 1, "b": 2}


def test_deep_merge_nested():
    """Test nested dict merge."""
    base = {"github": {"token": "default", "timeout": 30}}
    override = {"github": {"token": "override"}}

    result = deep_merge(base, override)

    assert result["github"]["token"] == "override"
    assert result["github"]["timeout"] == 30  # Preserved


def test_deep_merge_list_replace():
    """Test that lists are replaced, not merged."""
    base = {"tags": ["a", "b"]}
    override = {"tags": ["c"]}

    result = deep_merge(base, override)

    assert result["tags"] == ["c"]


def test_load_config_base_only(tmp_path):
    """Test loading with only base config."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')

    result = load_config(config_path=config_file, local_path=tmp_path / "nonexistent.json")

    assert result == {"key": "value"}


def test_load_config_with_local(tmp_path):
    """Test loading with local override."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"a": 1, "b": 2}')

    local_file = tmp_path / "config.local.json"
    local_file.write_text('{"b": 3}')

    result = load_config(config_path=config_file, local_path=local_file)

    assert result == {"a": 1, "b": 3}


def test_get_config_value():
    """Test dot-path value getter."""
    config = {
        "github": {
            "rate_limit": {
                "max_requests": 5000
            }
        }
    }

    assert get_config_value(config, "github.rate_limit.max_requests") == 5000
    assert get_config_value(config, "missing.key", "default") == "default"


def test_load_config_missing_base(tmp_path):
    """Test error when base config missing."""
    with pytest.raises(FileNotFoundError):
        load_config(config_path=tmp_path / "nonexistent.json")
