# GitHub API Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-03

---

## Overview

This guide documents how to use the GitHub API v3 to fetch star history data for Claude Skills repositories.

**GitHub API v3 Base URL:**
```
https://api.github.com
```

**Integration Script:** `scripts/fetch_github_stars.py`

---

## Authentication Setup

### Why Authentication Is Required

**Unauthenticated Rate Limit:** 60 requests/hour
**Authenticated Rate Limit:** 5,000 requests/hour

For skill trending monitoring, authentication is **required** to avoid rate limit errors.

---

### Generate GitHub Personal Access Token

**Step 1: Navigate to GitHub Settings**
```
https://github.com/settings/tokens
```

**Step 2: Generate New Token**
- Click "Generate new token (classic)"
- Note: "Claude Skills Monitoring"
- Expiration: 90 days (recommended)
- Scopes: **public_repo** (read access to public repositories)

**Step 3: Copy Token**
```
<GITHUB_TOKEN>
```

⚠️ **Save immediately** - you won't see it again!

---

### Configure Environment

**Method 1: Export in Shell**
```bash
export GITHUB_TOKEN="<GITHUB_TOKEN>"
```

**Method 2: Add to Shell Profile**
```bash
# ~/.zshrc or ~/.bashrc
export GITHUB_TOKEN="<GITHUB_TOKEN>"

# Reload
source ~/.zshrc
```

**Method 3: Add to Skill Config**
```json
{
  "github_token": "<GITHUB_TOKEN>"
}
```

**Verify Token:**
```bash
echo $GITHUB_TOKEN | cut -c1-10
# Output: ghp_xxxxxx (shows first 10 chars)
```

---

## Star History Endpoint

### Endpoint Documentation

**URL Format:**
```
GET /repos/{owner}/{repo}/stargazers
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `owner` | string | ✅ | Repository owner |
| `repo` | string | ✅ | Repository name |
| `page` | integer | ❌ | Page number (default: 1) |
| `per_page` | integer | ❌ | Results per page (max: 100) |

**Headers:**

| Header | Value | Required | Description |
|--------|-------|----------|-------------|
| `Authorization` | `token {GITHUB_TOKEN}` | ✅ | Authentication |
| `Accept` | `application/vnd.github.v3.star+json` | ✅ | Star timestamp format |

---

### Request Format

**Example Request:**
```bash
curl -H "Authorization: token <GITHUB_TOKEN>" \
     -H "Accept: application/vnd.github.v3.star+json" \
     "https://api.github.com/repos/anthropics/claude-code-skills/stargazers?per_page=100"
```

**Python Example:**
```python
import requests

url = "https://api.github.com/repos/anthropics/claude-code-skills/stargazers"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.star+json"
}
params = {
    "per_page": 100,
    "page": 1
}

response = requests.get(url, headers=headers, params=params)
data = response.json()
```

---

### Response Format

**Structure:**
```json
[
  {
    "starred_at": "2025-11-15T10:00:00Z",
    "user": {
      "login": "username",
      "id": 123456
    }
  },
  {
    "starred_at": "2025-11-16T14:30:00Z",
    "user": {
      "login": "another_user",
      "id": 789012
    }
  }
]
```

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `starred_at` | string (ISO 8601) | Timestamp when user starred repo |
| `user.login` | string | GitHub username |
| `user.id` | integer | GitHub user ID |

---

## Rate Limiting

### Understanding Rate Limits

**Authenticated Limits:**
- **5,000 requests/hour** (resets every hour)
- **60-second window** for burst protection

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1704229200
X-RateLimit-Used: 1
```

---

### Check Rate Limit Status

**Using API:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/rate_limit
```

**Response:**
```json
{
  "resources": {
    "core": {
      "limit": 5000,
      "remaining": 4999,
      "reset": 1704229200,
      "used": 1
    }
  }
}
```

**Python Example:**
```python
import requests
from datetime import datetime

def check_rate_limit(token):
    """Check GitHub API rate limit status."""
    url = "https://api.github.com/rate_limit"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)
    data = response.json()

    core = data['resources']['core']
    reset_time = datetime.fromtimestamp(core['reset'])

    print(f"Limit: {core['limit']}")
    print(f"Remaining: {core['remaining']}")
    print(f"Used: {core['used']}")
    print(f"Resets at: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}")

    return core['remaining']
```

---

### Rate Limit Handling Strategies

**Strategy 1: Respect Headers**
```python
def fetch_with_rate_limit_check(url, headers):
    """Fetch data with rate limit awareness."""
    response = requests.get(url, headers=headers)

    # Check remaining requests
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))

    if remaining < 100:
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        wait_seconds = reset_time - time.time()
        print(f"⚠️ Low rate limit ({remaining} remaining)")
        print(f"   Resets in {wait_seconds/60:.1f} minutes")

    return response.json()
```

**Strategy 2: Exponential Backoff**
```python
import time

def fetch_with_retry(url, headers, max_retries=3):
    """Fetch with exponential backoff on rate limit."""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 403:
            # Rate limit exceeded
            wait_time = 2 ** attempt * 60  # 1min, 2min, 4min
            print(f"Rate limit hit, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()

    raise Exception("Max retries exceeded")
```

**Strategy 3: Batch with Delays**
```python
import time

def fetch_multiple_repos(repo_urls, headers, delay=1):
    """Fetch multiple repos with rate limit protection."""
    results = []

    for i, url in enumerate(repo_urls, 1):
        print(f"Fetching {i}/{len(repo_urls)}: {url}")

        response = requests.get(url, headers=headers)
        results.append(response.json())

        # Check rate limit every 10 requests
        if i % 10 == 0:
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            print(f"   Rate limit: {remaining} remaining")

        # Delay between requests
        time.sleep(delay)

    return results
```

---

## Error Handling

### Common Errors

**Error 1: Invalid Token (401)**
```json
{
  "message": "Bad credentials",
  "documentation_url": "https://docs.github.com/rest"
}
```

**Solution:**
```python
if response.status_code == 401:
    raise ValueError(
        "Invalid GitHub token. Check:\n"
        "1. Token is correct\n"
        "2. Token hasn't expired\n"
        "3. GITHUB_TOKEN env variable is set"
    )
```

---

**Error 2: Rate Limit Exceeded (403)**
```json
{
  "message": "API rate limit exceeded",
  "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
}
```

**Solution:**
```python
if response.status_code == 403:
    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
    wait_seconds = reset_time - time.time()

    raise RateLimitError(
        f"Rate limit exceeded. Resets in {wait_seconds/60:.1f} minutes"
    )
```

---

**Error 3: Repository Not Found (404)**
```json
{
  "message": "Not Found",
  "documentation_url": "https://docs.github.com/rest/reference/repos#get-a-repository"
}
```

**Solution:**
```python
if response.status_code == 404:
    raise ValueError(
        f"Repository not found: {owner}/{repo}\n"
        "Check:\n"
        "1. Repository exists\n"
        "2. Repository is public\n"
        "3. Owner and repo names are correct"
    )
```

---

**Error 4: Network/Timeout Errors**
```python
import requests
from requests.exceptions import Timeout, ConnectionError

try:
    response = requests.get(url, headers=headers, timeout=10)
except Timeout:
    raise TimeoutError("Request timed out after 10 seconds")
except ConnectionError:
    raise ConnectionError("Network connection failed")
```

---

### Retry Logic

**Robust Fetch Function:**
```python
import time
import requests
from typing import List, Dict

def fetch_stargazers_robust(
    owner: str,
    repo: str,
    token: str,
    max_retries: int = 3,
    timeout: int = 10
) -> List[Dict]:
    """
    Fetch stargazers with comprehensive error handling.

    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds

    Returns:
        List of stargazer records

    Raises:
        ValueError: Invalid token or repository
        RateLimitError: Rate limit exceeded
        TimeoutError: Request timed out
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/stargazers"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.star+json"
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                headers=headers,
                params={"per_page": 100},
                timeout=timeout
            )

            # Success
            if response.status_code == 200:
                return response.json()

            # Handle specific errors
            if response.status_code == 401:
                raise ValueError("Invalid GitHub token")

            if response.status_code == 404:
                raise ValueError(f"Repository not found: {owner}/{repo}")

            if response.status_code == 403:
                # Rate limit - wait and retry
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_seconds = max(reset_time - time.time(), 60)

                if attempt < max_retries - 1:
                    print(f"Rate limit hit, waiting {wait_seconds/60:.1f} min...")
                    time.sleep(wait_seconds)
                    continue
                else:
                    raise RateLimitError("Rate limit exceeded")

            # Other errors
            response.raise_for_status()

        except (Timeout, ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise

    raise Exception("Max retries exceeded")
```

---

## Integration with fetch_github_stars.py

### Function: `fetch_star_history()`

**Signature:**
```python
def fetch_star_history(
    github_url: str,
    github_token: Optional[str] = None
) -> List[Dict]:
    """
    Fetch star history for a GitHub repository.

    Args:
        github_url: GitHub repository URL
        github_token: GitHub API token (reads from env if None)

    Returns:
        List of star records with timestamps:
        [
            {"starred_at": "2025-11-15T10:00:00Z", "user": {...}},
            ...
        ]

    Raises:
        ValueError: Invalid GitHub URL or token
        RateLimitError: Rate limit exceeded

    Example:
        >>> history = fetch_star_history(
        ...     "https://github.com/anthropics/claude-code-skills"
        ... )
        >>> len(history)
        1250
    """
```

**Example Usage:**
```python
from fetch_github_stars import fetch_star_history

# Example 1: Basic usage (token from env)
history = fetch_star_history(
    "https://github.com/anthropics/claude-code-skills"
)

print(f"Total stars: {len(history)}")
print(f"First star: {history[0]['starred_at']}")
print(f"Latest star: {history[-1]['starred_at']}")

# Example 2: Explicit token
history = fetch_star_history(
    "https://github.com/daymade/claude-code-skills",
    github_token="<GITHUB_TOKEN>"
)

# Example 3: Error handling
try:
    history = fetch_star_history("https://github.com/invalid/repo")
except ValueError as e:
    print(f"Error: {e}")
```

---

### Function: `calculate_week_over_week_growth()`

**Signature:**
```python
def calculate_week_over_week_growth(
    star_history: List[Dict]
) -> Dict:
    """
    Calculate week-over-week star growth.

    Args:
        star_history: List of star records from fetch_star_history()

    Returns:
        Dict with growth metrics:
        {
            "total_stars": int,
            "current_week_stars": int,
            "previous_week_stars": int,
            "wow_growth_rate": float,
            "current_week_start": str
        }

    Example:
        >>> growth = calculate_week_over_week_growth(history)
        >>> print(f"WoW growth: {growth['wow_growth_rate']:.1f}%")
        WoW growth: 12.5%
    """
```

**Example Usage:**
```python
from fetch_github_stars import fetch_star_history, calculate_week_over_week_growth

# Fetch star history
history = fetch_star_history(
    "https://github.com/anthropics/claude-code-skills"
)

# Calculate growth
growth = calculate_week_over_week_growth(history)

print(f"Total stars: {growth['total_stars']:,}")
print(f"Current week: {growth['current_week_stars']} new stars")
print(f"Previous week: {growth['previous_week_stars']} stars")
print(f"WoW growth: {growth['wow_growth_rate']:.1f}%")
print(f"Week starts: {growth['current_week_start']}")
```

---

## Performance Considerations

### Optimization Strategies

**Strategy 1: Cache Star History**
```python
from utils.cache_manager import CacheManager

cache = CacheManager(cache_dir=Path('.cache'))

# Try cache first
cache_key = f"stars_{owner}_{repo}"
history = cache.get(cache_key, category='github')

if history is None:
    # Cache miss: fetch and cache
    history = fetch_star_history(github_url, github_token)
    cache.set(cache_key, history, category='github', ttl=3600)  # 1 hour
```

**Strategy 2: Batch Requests with Rate Limit Awareness**
```python
def fetch_multiple_skills(skills, token, delay=1):
    """Fetch star history for multiple skills."""
    results = []

    for i, skill in enumerate(skills, 1):
        print(f"Fetching {i}/{len(skills)}: {skill['name']}")

        try:
            history = fetch_star_history(skill['github_url'], token)
            results.append({
                'name': skill['name'],
                'history': history,
                'total_stars': len(history)
            })
        except Exception as e:
            print(f"   Error: {e}")
            results.append({
                'name': skill['name'],
                'error': str(e)
            })

        # Rate limit check every 10 requests
        if i % 10 == 0:
            remaining = check_rate_limit(token)
            print(f"   Rate limit: {remaining} remaining")

        # Delay between requests
        time.sleep(delay)

    return results
```

**Strategy 3: Parallel Requests (Advanced)**
```python
import concurrent.futures

def fetch_parallel(urls, token, max_workers=5):
    """Fetch star history in parallel (use with caution)."""

    def fetch_one(url):
        try:
            return fetch_star_history(url, token)
        except Exception as e:
            return {"error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(fetch_one, urls))

    return results
```

⚠️ **Caution:** Parallel requests can quickly exhaust rate limit. Use conservatively.

---

## Testing Examples

### Test 1: Validate Token

```python
import os
import requests

def test_github_token():
    """Test if GitHub token is valid."""
    token = os.getenv('GITHUB_TOKEN')

    if not token:
        print("❌ GITHUB_TOKEN not set")
        return False

    url = "https://api.github.com/user"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user = response.json()
        print(f"✅ Token valid for user: {user['login']}")
        return True
    else:
        print(f"❌ Token invalid: {response.json()['message']}")
        return False
```

---

### Test 2: Check Rate Limit

```python
def test_rate_limit():
    """Check current rate limit status."""
    token = os.getenv('GITHUB_TOKEN')
    remaining = check_rate_limit(token)

    if remaining > 100:
        print(f"✅ Rate limit healthy: {remaining} requests remaining")
        return True
    else:
        print(f"⚠️ Low rate limit: {remaining} requests remaining")
        return False
```

---

### Test 3: Fetch Star History

```python
def test_fetch_star_history():
    """Test fetching star history for a known repository."""
    try:
        history = fetch_star_history(
            "https://github.com/anthropics/claude-code-skills"
        )

        print(f"✅ Fetched {len(history)} star records")
        print(f"   First star: {history[0]['starred_at']}")
        print(f"   Latest star: {history[-1]['starred_at']}")
        return True
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        return False
```

---

## Related Documentation

- **skill-manager API Guide**: `skill-manager-api-guide.md` (for skill database)
- **Analysis Methodologies**: `analysis-methodologies.md` (for growth calculations)
- **Troubleshooting**: `troubleshooting.md` (for common issues)

---

**End of Guide**
