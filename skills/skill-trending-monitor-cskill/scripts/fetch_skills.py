#!/usr/bin/env python3
"""
Fetch skill-manager data and GitHub repo metadata.

Lightweight wrappers used by tests:
- fetch_skill_manager_data: load JSON from disk
- fetch_github_stars: fetch repo metadata with optional caching and retries
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def fetch_skill_manager_data(database_path: str) -> Any:
    """
    Load skill-manager database JSON from disk.

    Args:
        database_path: Path to JSON file

    Returns:
        Parsed JSON content
    """
    with open(database_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_repo(repo: str) -> str:
    """Normalize repo input to owner/repo."""
    if "github.com/" in repo:
        parts = repo.split("github.com/")[-1].strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return repo.strip().strip("/")


def _cache_file_path(cache_dir: Path, repo: str) -> Path:
    sanitized = repo.replace("/", "_").replace(":", "_")
    return cache_dir / f"{sanitized}.json"


def _is_cache_valid(cache_file: Path, cache_ttl: int) -> bool:
    if not cache_file.exists():
        return False
    if cache_ttl <= 0:
        return False
    age_seconds = time.time() - cache_file.stat().st_mtime
    return age_seconds <= cache_ttl


def fetch_github_stars(
    repo: str,
    github_token: Optional[str] = None,
    cache_dir: Optional[str] = None,
    cache_ttl: int = 3600,
    max_retries: int = 3,
    timeout: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Fetch GitHub repo metadata (includes stargazers_count).

    Args:
        repo: "owner/repo" or GitHub URL
        github_token: Optional GitHub token
        cache_dir: Directory to cache JSON responses
        cache_ttl: Cache TTL in seconds
        max_retries: Max retry attempts for transient failures
        timeout: Request timeout in seconds

    Returns:
        Response JSON dict on success, or error dict/None on failure
    """
    repo_slug = _normalize_repo(repo)
    api_url = f"https://api.github.com/repos/{repo_slug}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "skill-trending-monitor-cskill"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    cache_path = None
    if cache_dir:
        cache_dir_path = Path(cache_dir)
        cache_dir_path.mkdir(parents=True, exist_ok=True)
        cache_path = _cache_file_path(cache_dir_path, repo_slug)

        if _is_cache_valid(cache_path, cache_ttl):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Cache read failed for {repo_slug}: {e}")

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(api_url, headers=headers, timeout=timeout)
        except Exception as e:
            if attempt < max_retries:
                continue
            return {"error": str(e)}

        if response.status_code == 200:
            data = response.json()
            if cache_path:
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except OSError as e:
                    logger.debug(f"Cache write failed for {repo_slug}: {e}")
            return data

        if response.status_code == 429:
            return {"error": "rate_limited"}

        if response.status_code in (401, 404):
            try:
                message = response.json().get("message", "HTTP error")
            except Exception:
                message = "HTTP error"
            return {"error": message}

        if attempt >= max_retries:
            return {"error": f"HTTP {response.status_code}"}

    return None
