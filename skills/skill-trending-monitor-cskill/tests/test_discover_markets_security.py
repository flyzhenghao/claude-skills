#!/usr/bin/env python3
"""Security-focused tests for discover_markets helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import discover_markets as dm


def test_safe_markdown_url_allows_valid_github_https():
    url = "https://github.com/example/repo"
    assert dm._safe_markdown_url(url) == f"<{url}>"


def test_safe_markdown_url_escapes_unsafe_chars():
    rendered = dm._safe_markdown_url("https://github.com/example/repo>oops")
    assert rendered == "https://github.com/example/repo\\>oops"


def test_is_allowed_market_url_rejects_userinfo_and_controls():
    assert not dm._is_allowed_market_url("https://user@github.com/example/repo")
    assert not dm._is_allowed_market_url("https://github.com/example/repo\nbad")
