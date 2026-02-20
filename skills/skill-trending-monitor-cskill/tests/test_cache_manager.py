#!/usr/bin/env python3
"""Tests for cache_manager module."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "utils"))

import cache_manager
from cache_manager import CacheManager


@pytest.fixture
def cache(tmp_path):
    """CacheManager with isolated temp directory."""
    return CacheManager(cache_dir=tmp_path / "cache")


def _set_mtime(path: Path, new_time: datetime) -> None:
    timestamp = new_time.timestamp()
    os.utime(path, (timestamp, timestamp))


def _freeze_time(mock_datetime, fixed_now: datetime) -> None:
    mock_datetime.now.return_value = fixed_now
    mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp


def test_init_default_creates_dirs(tmp_path, monkeypatch):
    fake_module_file = tmp_path / "scripts" / "utils" / "cache_manager.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("# placeholder")

    monkeypatch.setattr(cache_manager, "__file__", str(fake_module_file))

    cache_instance = CacheManager()

    assert cache_instance.cache_dir == tmp_path / "data" / "cache"
    assert cache_instance.metadata_cache_dir.exists()
    assert cache_instance.security_cache_dir.exists()
    assert cache_instance.metadata_ttl.days == 30
    assert cache_instance.security_ttl.days == 7


def test_init_custom_dir_creates_dirs(tmp_path):
    custom_dir = tmp_path / "custom_cache"

    cache_instance = CacheManager(cache_dir=custom_dir)

    assert cache_instance.cache_dir == custom_dir
    assert cache_instance.metadata_cache_dir.exists()
    assert cache_instance.security_cache_dir.exists()


def test_set_and_get_metadata(cache):
    value = {"stars": 123, "updated": "2026-02-03"}

    cache.set("skill-a", value, cache_type="metadata")
    result = cache.get("skill-a", cache_type="metadata")

    assert result == value

    cache_file = cache.metadata_cache_dir / "skill-a.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text(encoding="utf-8")) == value


def test_set_overwrites_existing(cache):
    cache.set("skill-a", {"stars": 10}, cache_type="metadata")
    cache.set("skill-a", {"stars": 20}, cache_type="metadata")

    assert cache.get("skill-a", cache_type="metadata") == {"stars": 20}


def test_set_security_cache(cache):
    value = {"score": 85}

    cache.set("skill-b", value, cache_type="security")

    security_file = cache.security_cache_dir / "skill-b.json"
    metadata_file = cache.metadata_cache_dir / "skill-b.json"
    assert security_file.exists()
    assert not metadata_file.exists()


def test_get_missing_returns_none(cache):
    assert cache.get("missing", cache_type="metadata") is None


def test_get_invalid_cache_type_raises(cache):
    with pytest.raises(ValueError):
        cache.get("skill-a", cache_type="invalid")


def test_get_corrupted_cache_removes_file(cache):
    cache_file = cache.metadata_cache_dir / "bad.json"
    cache_file.write_text("{not valid json", encoding="utf-8")

    result = cache.get("bad", cache_type="metadata")

    assert result is None
    assert not cache_file.exists()


def test_get_expired_cache_removes_file(cache):
    fixed_now = datetime(2026, 2, 4, 12, 0, 0)
    cache.set("expired", {"value": 1}, cache_type="metadata")

    cache_file = cache.metadata_cache_dir / "expired.json"
    expired_time = fixed_now - cache.metadata_ttl - timedelta(seconds=1)
    _set_mtime(cache_file, expired_time)

    with patch("cache_manager.datetime") as mock_datetime:
        _freeze_time(mock_datetime, fixed_now)
        result = cache.get("expired", cache_type="metadata")

    assert result is None
    assert not cache_file.exists()


def test_get_boundary_not_expired(cache):
    fixed_now = datetime(2026, 2, 4, 12, 0, 0)
    value = {"value": 1}
    cache.set("boundary", value, cache_type="metadata")

    cache_file = cache.metadata_cache_dir / "boundary.json"
    boundary_time = fixed_now - cache.metadata_ttl
    _set_mtime(cache_file, boundary_time)

    with patch("cache_manager.datetime") as mock_datetime:
        _freeze_time(mock_datetime, fixed_now)
        result = cache.get("boundary", cache_type="metadata")

    assert result == value


def test_security_ttl_expired(cache):
    fixed_now = datetime(2026, 2, 4, 12, 0, 0)
    cache.set("sec-old", {"score": 70}, cache_type="security")

    cache_file = cache.security_cache_dir / "sec-old.json"
    expired_time = fixed_now - cache.security_ttl - timedelta(seconds=1)
    _set_mtime(cache_file, expired_time)

    with patch("cache_manager.datetime") as mock_datetime:
        _freeze_time(mock_datetime, fixed_now)
        result = cache.get("sec-old", cache_type="security")

    assert result is None
    assert not cache_file.exists()


def test_invalidate_removes_existing(cache):
    cache.set("to-remove", {"value": 1}, cache_type="metadata")
    cache_file = cache.metadata_cache_dir / "to-remove.json"
    assert cache_file.exists()

    cache.invalidate("to-remove", cache_type="metadata")

    assert not cache_file.exists()


def test_invalidate_missing_no_error(cache):
    cache.invalidate("missing", cache_type="metadata")


def test_cleanup_expired_only_removes_expired(cache):
    fixed_now = datetime(2026, 2, 4, 12, 0, 0)
    cache.set("expired", {"value": 1}, cache_type="metadata")
    cache.set("fresh", {"value": 2}, cache_type="metadata")

    expired_file = cache.metadata_cache_dir / "expired.json"
    fresh_file = cache.metadata_cache_dir / "fresh.json"

    _set_mtime(expired_file, fixed_now - cache.metadata_ttl - timedelta(seconds=1))
    _set_mtime(fresh_file, fixed_now - cache.metadata_ttl + timedelta(seconds=1))

    with patch("cache_manager.datetime") as mock_datetime:
        _freeze_time(mock_datetime, fixed_now)
        removed = cache.cleanup_expired(cache_type="metadata")

    assert removed == 1
    assert not expired_file.exists()
    assert fresh_file.exists()


def test_cleanup_expired_both_types(cache):
    fixed_now = datetime(2026, 2, 4, 12, 0, 0)
    cache.set("meta-old", {"value": 1}, cache_type="metadata")
    cache.set("sec-old", {"value": 2}, cache_type="security")

    meta_file = cache.metadata_cache_dir / "meta-old.json"
    sec_file = cache.security_cache_dir / "sec-old.json"

    _set_mtime(meta_file, fixed_now - cache.metadata_ttl - timedelta(seconds=1))
    _set_mtime(sec_file, fixed_now - cache.security_ttl - timedelta(seconds=1))

    with patch("cache_manager.datetime") as mock_datetime:
        _freeze_time(mock_datetime, fixed_now)
        removed = cache.cleanup_expired()

    assert removed == 2
    assert not meta_file.exists()
    assert not sec_file.exists()


def test_clear_cache_returns_count(cache):
    cache.set("meta-a", {"value": 1}, cache_type="metadata")
    cache.set("sec-a", {"value": 2}, cache_type="security")

    removed_metadata = cache.clear(cache_type="metadata")
    assert removed_metadata == 1
    assert not (cache.metadata_cache_dir / "meta-a.json").exists()
    assert (cache.security_cache_dir / "sec-a.json").exists()

    removed_all = cache.clear()
    assert removed_all == 1
    assert not (cache.security_cache_dir / "sec-a.json").exists()


def test_clear_empty_returns_zero(cache):
    assert cache.clear(cache_type="metadata") == 0


def test_get_stats_counts_entries(cache):
    cache.set("meta-a", {"value": 1}, cache_type="metadata")
    cache.set("sec-a", {"value": 2}, cache_type="security")

    stats = cache.get_stats()

    assert stats["metadata"] == 1
    assert stats["security"] == 1
    assert stats["total"] == 2


def test_sanitize_key_replaces_unsafe_chars(cache):
    key = 'a/b:c*?"<>|\\'
    sanitized = cache._sanitize_key(key)

    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        assert char not in sanitized
