#!/usr/bin/env python3
"""
Skill Market 自发现脚本
月度扫描 GitHub 寻找新的 Claude Code Skill 市场/列表
读取 skill-markets.json，搜索新市场，评估质量，自动或推荐添加
"""

import argparse
import json
import os
import sys
import time
import re
import requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse


SKILL_DIR = Path(__file__).resolve().parent.parent
MARKETS_FILE = SKILL_DIR / "assets" / "skill-markets.json"
REPORTS_DIR = SKILL_DIR / "meta" / "reports"

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = None
ALLOWED_GITHUB_API_HOST = "api.github.com"
ALLOWED_MARKET_HOSTS = {"github.com", "www.github.com"}
MARKET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
MD_ESCAPE_RE = re.compile(r'([\\`*_{}\[\]()#+\-!|>])')
URL_UNSAFE_CHARS_RE = re.compile(r"[\x00-\x1f\x7f<>\[\]\(\)`\"']")


def _escape_markdown(value):
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return MD_ESCAPE_RE.sub(r'\\\1', text)


def _safe_markdown_url(url):
    text = str(url or "").strip().replace("\r", "").replace("\n", "")
    if URL_UNSAFE_CHARS_RE.search(text):
        return _escape_markdown(text)
    parsed = urlparse(text)
    if (
        parsed.scheme == "https"
        and parsed.netloc in ALLOWED_MARKET_HOSTS
        and parsed.username is None
        and parsed.password is None
    ):
        return f"<{text}>"
    return _escape_markdown(text)


def _is_allowed_market_url(url):
    parsed = urlparse(str(url or "").strip())
    if URL_UNSAFE_CHARS_RE.search(str(url or "")):
        return False
    if parsed.scheme != "https" or parsed.netloc not in ALLOWED_MARKET_HOSTS:
        return False
    # Require at least /owner/repo path form.
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2


def _build_market_id(name):
    raw = str(name or "").lower().replace("/", "-")
    market_id = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
    market_id = re.sub(r"-{2,}", "-", market_id)[:100]
    return market_id


def load_config():
    """Load GitHub token from environment only."""
    global GITHUB_TOKEN
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def github_request(url):
    """Make an authenticated GitHub API request."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ALLOWED_GITHUB_API_HOST:
        print(f"  [warn] Rejected non-GitHub API URL: {url}", file=sys.stderr)
        return None

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skill-trending-monitor",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"  [warn] GitHub API error: {e}", file=sys.stderr)
        return None


def load_markets():
    """Load current skill-markets.json."""
    if not MARKETS_FILE.exists():
        print(f"ERROR: {MARKETS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(MARKETS_FILE.read_text())


def save_markets(data):
    """Save updated skill-markets.json."""
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    MARKETS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  [info] Updated {MARKETS_FILE}")


def get_known_urls(markets_data):
    """Extract known market URLs for deduplication."""
    return {m["url"].rstrip("/").lower() for m in markets_data.get("markets", [])}


def search_github(query, known_urls):
    """Search GitHub for potential skill market repos."""
    query_string = urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 20,
    })
    url = f"{GITHUB_API}/search/repositories?{query_string}"
    result = github_request(url)
    if not result or "items" not in result:
        return []

    candidates = []
    for repo in result["items"]:
        repo_url = repo.get("html_url", "").rstrip("/").lower()
        if not _is_allowed_market_url(repo_url):
            continue
        if repo_url in known_urls:
            continue

        # Basic filters
        stars = repo.get("stargazers_count", 0)
        pushed_at = repo.get("pushed_at", "")
        archived = repo.get("archived", False)

        if archived:
            continue

        candidates.append({
            "name": repo.get("full_name", ""),
            "url": repo.get("html_url", ""),
            "description": repo.get("description", "") or "",
            "stars": stars,
            "pushed_at": pushed_at,
            "topics": repo.get("topics", []),
            "language": repo.get("language", ""),
        })

    return candidates


def evaluate_candidate(candidate, config):
    """Evaluate a candidate market and compute quality score."""
    min_stars = config.get("min_stars", 50)
    max_months = config.get("max_months_since_update", 6)

    stars = candidate.get("stars", 0)
    pushed_at = candidate.get("pushed_at", "")

    # Filter: minimum stars
    if stars < min_stars:
        return None

    # Filter: recency
    if pushed_at:
        try:
            pushed_date = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            months_ago = (datetime.now(timezone.utc) - pushed_date).days / 30.0
            if months_ago > max_months:
                return None
            recency_score = max(0, 1.0 - months_ago / max_months)
        except (ValueError, TypeError):
            recency_score = 0.3
    else:
        recency_score = 0.3

    # Compute quality score
    # Stars weight: normalize to 0-1 (cap at 1000)
    stars_score = min(stars / 1000.0, 1.0)

    # Description quality
    desc = candidate.get("description", "")
    desc_score = 0.5
    skill_keywords = ["claude", "skill", "agent", "awesome", "collection", "list", "registry", "marketplace"]
    matched = sum(1 for kw in skill_keywords if kw in desc.lower())
    desc_score = min(matched / 3.0, 1.0)

    quality_score = round(stars_score * 0.4 + recency_score * 0.3 + desc_score * 0.3, 2)

    # Determine type
    name_lower = candidate["name"].lower()
    desc_lower = desc.lower()
    if "awesome" in name_lower or "awesome" in desc_lower:
        market_type = "github_awesome_list"
    elif "marketplace" in desc_lower or "registry" in desc_lower:
        market_type = "marketplace"
    else:
        market_type = "github_repo"

    market_id = _build_market_id(candidate["name"])
    if not MARKET_ID_RE.fullmatch(market_id):
        return None

    return {
        "id": market_id,
        "name": candidate.get("description", candidate["name"])[:80],
        "url": candidate["url"],
        "type": market_type,
        "trust_level": "community",
        "quality_score": quality_score,
        "enabled": False,  # Disabled by default until reviewed
        "stars": stars,
        "pushed_at": candidate.get("pushed_at", ""),
        "recency_score": recency_score,
        "stars_score": stars_score,
        "desc_score": desc_score,
    }


def run_discovery(dry_run=False):
    """Main discovery logic."""
    load_config()
    markets_data = load_markets()
    discovery_config = markets_data.get("discovery_config", {})

    search_queries = discovery_config.get("search_queries", [
        "claude code skills marketplace",
        "awesome claude code skills",
    ])
    min_quality = discovery_config.get("min_quality_score", 0.4)
    auto_add_threshold = discovery_config.get("auto_add_threshold", 0.6)

    known_urls = get_known_urls(markets_data)
    all_candidates = []

    print("=" * 50)
    print("Skill Market Discovery")
    print(f"  Known markets: {len(known_urls)}")
    print(f"  Search queries: {len(search_queries)}")
    print(f"  Min quality: {min_quality}")
    print(f"  Auto-add threshold: {auto_add_threshold}")
    print(f"  Dry run: {dry_run}")
    print("=" * 50)

    for query in search_queries:
        print(f"\n🔍 Searching: '{query}'")
        candidates = search_github(query, known_urls)
        print(f"  Found {len(candidates)} new repos")

        for c in candidates:
            evaluated = evaluate_candidate(c, discovery_config)
            if evaluated:
                # Avoid duplicates across queries
                if not any(e["url"] == evaluated["url"] for e in all_candidates):
                    all_candidates.append(evaluated)
                    print(f"  ✓ {evaluated['id']} (score={evaluated['quality_score']}, stars={evaluated['stars']})")

        # Rate limiting
        time.sleep(1)

    # Sort by quality score
    all_candidates.sort(key=lambda x: x["quality_score"], reverse=True)

    # Split into auto-add and recommend
    auto_add = [c for c in all_candidates if c["quality_score"] >= auto_add_threshold]
    recommend = [c for c in all_candidates if min_quality <= c["quality_score"] < auto_add_threshold]
    filtered_out = [c for c in all_candidates if c["quality_score"] < min_quality]

    print(f"\n{'=' * 50}")
    print(f"Discovery Results")
    print(f"  Total evaluated: {len(all_candidates)}")
    print(f"  Auto-add (>= {auto_add_threshold}): {len(auto_add)}")
    print(f"  Recommend ({min_quality} - {auto_add_threshold}): {len(recommend)}")
    print(f"  Filtered out (< {min_quality}): {len(filtered_out)}")
    print(f"{'=' * 50}")

    # Auto-add high quality markets
    added = []
    if auto_add and not dry_run:
        for market in auto_add:
            entry = {
                "id": market["id"],
                "name": market["name"],
                "url": market["url"],
                "type": market["type"],
                "trust_level": market["trust_level"],
                "quality_score": market["quality_score"],
                "enabled": True,
            }
            if not MARKET_ID_RE.fullmatch(entry["id"]) or not _is_allowed_market_url(entry["url"]):
                print(f"  [warn] Skipping invalid market entry: {entry['id']}", file=sys.stderr)
                continue
            markets_data["markets"].append(entry)
            added.append(market["id"])
            print(f"  ➕ Auto-added: {market['id']} (score={market['quality_score']})")

        save_markets(markets_data)

    # Generate discovery report
    report = generate_report(auto_add, recommend, filtered_out, added, dry_run)
    report_date = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{report_date}-market-discovery.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"\n📄 Report: {report_path}")

    return {
        "auto_added": added,
        "recommended": [r["id"] for r in recommend],
        "total_found": len(all_candidates),
    }


def generate_report(auto_add, recommend, filtered, added, dry_run):
    """Generate a Markdown discovery report."""
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Skill Market Discovery Report ({date})",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Mode**: {'Dry Run' if dry_run else 'Live'}",
        "",
        "---",
        "",
    ]

    if auto_add:
        lines.append(f"## Auto-Added ({len(auto_add)})")
        lines.append("")
        for m in auto_add:
            status = "✅ Added" if m["id"] in (added if not dry_run else []) else "🔍 Would add"
            lines.append(f"### {_escape_markdown(m['id'])}")
            lines.append(f"- **URL**: {_safe_markdown_url(m['url'])}")
            lines.append(f"- **Stars**: {m['stars']}")
            lines.append(f"- **Score**: {m['quality_score']}")
            lines.append(f"- **Status**: {status}")
            lines.append("")

    if recommend:
        lines.append(f"## Recommended for Review ({len(recommend)})")
        lines.append("")
        for m in recommend:
            lines.append(f"### {_escape_markdown(m['id'])}")
            lines.append(f"- **URL**: {_safe_markdown_url(m['url'])}")
            lines.append(f"- **Stars**: {m['stars']}")
            lines.append(f"- **Score**: {m['quality_score']}")
            lines.append(f"- **Action**: Manual review needed")
            lines.append("")

    if filtered:
        lines.append(f"## Filtered Out ({len(filtered)})")
        lines.append("")
        for m in filtered:
            lines.append(f"- {_escape_markdown(m['id'])} (score={m['quality_score']}, stars={m['stars']})")
        lines.append("")

    if not auto_add and not recommend:
        lines.append("## No New Markets Found")
        lines.append("")
        lines.append("All discovered repos are either already known or below quality threshold.")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Discover new Skill Markets")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate but don't modify skill-markets.json",
    )
    args = parser.parse_args()

    result = run_discovery(dry_run=args.dry_run)
    print(f"\nDone. Auto-added: {len(result['auto_added'])}, Recommended: {len(result['recommended'])}")


if __name__ == "__main__":
    main()
