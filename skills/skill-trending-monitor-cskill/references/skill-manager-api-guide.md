# skill-manager API Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-03

---

## Overview

This guide documents how to access and query the skill-manager local database, which contains **31,767+ Claude Skills** with comprehensive metadata.

**Database Location:**
```
~/.claude/skills/skill-manager/data/all_skills_with_cn.json
```

**Integration Script:** `scripts/fetch_skill_manager.py`

---

## Database Schema

### Root Structure

```json
{
  "skills": [
    {
      "name": "skill-name",
      "author": "author-name",
      "github_url": "https://github.com/owner/repo/path",
      "stars": 123,
      "forks": 45,
      "updated_at": "2025-12-15T10:30:00Z",
      "description": "English description",
      "description_cn": "中文描述",
      "tags": ["tag1", "tag2"],
      "category": "category-name"
    }
  ],
  "metadata": {
    "total_count": 31767,
    "last_updated": "2025-12-26T08:00:00Z",
    "version": "2.0.0"
  }
}
```

### Field Definitions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Unique skill identifier | `"macos-cleaner"` |
| `author` | string | GitHub owner/organization | `"daymade"` |
| `github_url` | string | Full GitHub path to skill | `"https://github.com/daymade/claude-code-skills/macos-cleaner"` |
| `stars` | integer | GitHub repository stars | `123` |
| `forks` | integer | GitHub repository forks | `45` |
| `updated_at` | string (ISO 8601) | Last update timestamp | `"2025-12-15T10:30:00Z"` |
| `description` | string | English description | `"Analyze and reclaim macOS disk space"` |
| `description_cn` | string | Chinese description | `"分析和回收 macOS 磁盘空间"` |
| `tags` | array[string] | Skill tags/categories | `["macos", "cleanup", "storage"]` |
| `category` | string | Primary category | `"system-tools"` |

**Key Characteristics:**
- **All skills have `name`, `author`, `github_url`** (required fields)
- **`stars` and `forks` may be 0** for newly added skills
- **`updated_at` is always present** (parsed from GitHub API)
- **`description_cn` covers 99.95% of skills** (31,752 of 31,767)
- **`tags` and `category` may be empty arrays/strings** for uncategorized skills

---

## Access Patterns

### Pattern 1: Fetch All Skills (Unfiltered)

**Use Case:** Get complete skill database for local processing

**Function:** `fetch_all_skills(min_stars=0, max_months_old=0)`

**Example:**
```python
from fetch_skill_manager import fetch_all_skills

# Fetch all 31,767 skills
skills, metadata = fetch_all_skills(min_stars=0, max_months_old=0)

print(f"Total skills: {len(skills)}")
print(f"Database version: {metadata['version']}")
print(f"Last updated: {metadata['last_updated']}")
```

**Output:**
```
Total skills: 31767
Database version: 2.0.0
Last updated: 2025-12-26T08:00:00Z
```

**Performance:** ~500ms (parsing 30MB JSON)

---

### Pattern 2: Quality Filtering (Stars + Recency)

**Use Case:** Filter for high-quality, actively maintained skills

**Function:** `fetch_all_skills(min_stars=50, max_months_old=6)`

**Example:**
```python
# Fetch skills with ≥50 stars, updated within 6 months
skills, metadata = fetch_all_skills(min_stars=50, max_months_old=6)

print(f"Filtered skills: {len(skills)}")
print(f"Filter: stars ≥ {metadata['filters']['min_stars']}")
print(f"Filter: updated within {metadata['filters']['max_months_old']} months")
```

**Output:**
```
Filtered skills: 1234
Filter: stars ≥ 50
Filter: updated within 6 months
```

**Filter Logic:**
```python
# Stars filter (exact match)
skill['stars'] >= min_stars

# Recency filter (months since update)
months_old = (now - updated_at).days / 30
months_old <= max_months_old
```

---

### Pattern 3: Check Installed Skills

**Use Case:** Identify which skills are already installed locally

**Function:** `get_installed_skills()`

**Example:**
```python
from fetch_skill_manager import get_installed_skills

installed = get_installed_skills()
print(f"Installed skills: {len(installed)}")
print(f"Examples: {installed[:5]}")
```

**Output:**
```
Installed skills: 12
Examples: ['orchestrator-agent', 'work-agent', 'life-agent', 'family-agent', 'learning-agent']
```

**Detection Logic:**
1. Scan `~/.claude/skills/` directory
2. Identify valid skill directories (containing SKILL.md)
3. Extract skill names from directory names
4. Return list of installed skill names

**Use in Filtering:**
```python
# Get all skills
all_skills, _ = fetch_all_skills()

# Get installed skill names
installed_names = get_installed_skills()

# Filter for new (uninstalled) skills
new_skills = [s for s in all_skills if s['name'] not in installed_names]
```

---

## Query Patterns

### Query 1: Find Skills by Author

```python
skills, _ = fetch_all_skills()

# Find all skills by specific author
anthropic_skills = [s for s in skills if s['author'] == 'anthropics']
print(f"Anthropic skills: {len(anthropic_skills)}")
```

### Query 2: Find Skills by Tags

```python
skills, _ = fetch_all_skills()

# Find skills with specific tag
ai_skills = [s for s in skills if 'ai' in s.get('tags', [])]
print(f"AI-related skills: {len(ai_skills)}")
```

### Query 3: Find Skills by Name Pattern

```python
skills, _ = fetch_all_skills()

# Find skills matching name pattern
agent_skills = [s for s in skills if 'agent' in s['name'].lower()]
print(f"Agent skills: {len(agent_skills)}")
```

### Query 4: Top Skills by Stars

```python
skills, _ = fetch_all_skills(min_stars=10)

# Sort by stars descending
top_skills = sorted(skills, key=lambda s: s['stars'], reverse=True)[:20]

for idx, skill in enumerate(top_skills, 1):
    print(f"{idx}. {skill['name']} - {skill['stars']} ⭐")
```

### Query 5: Recently Updated Skills

```python
from datetime import datetime, timedelta

skills, _ = fetch_all_skills()
one_week_ago = datetime.now() - timedelta(days=7)

# Find skills updated within last week
recent = [
    s for s in skills
    if datetime.fromisoformat(s['updated_at'].replace('Z', '+00:00')) > one_week_ago
]

print(f"Updated in last 7 days: {len(recent)}")
```

---

## Integration with fetch_skill_manager.py

### Function: `fetch_all_skills()`

**Signature:**
```python
def fetch_all_skills(
    min_stars: int = 0,
    max_months_old: int = 0,
    skill_manager_path: Optional[Path] = None
) -> Tuple[List[Dict], Dict]:
```

**Parameters:**
- `min_stars`: Minimum GitHub stars (0 = no filter)
- `max_months_old`: Maximum age in months (0 = no filter)
- `skill_manager_path`: Custom database path (None = auto-detect)

**Returns:**
- `Tuple[List[Dict], Dict]`:
  - `List[Dict]`: Filtered skill list
  - `Dict`: Metadata with filters applied

**Raises:**
- `FileNotFoundError`: Database file not found
- `json.JSONDecodeError`: Invalid JSON format
- `KeyError`: Required fields missing

**Example with Error Handling:**
```python
from fetch_skill_manager import fetch_all_skills

try:
    skills, metadata = fetch_all_skills(min_stars=50, max_months_old=6)
    print(f"✓ Fetched {len(skills)} skills")
except FileNotFoundError:
    print("✗ skill-manager database not found")
    print("  Install: npx skills-installer install skill-manager")
except json.JSONDecodeError:
    print("✗ Database corrupted")
    print("  Reinstall skill-manager to fix")
```

---

### Function: `get_installed_skills()`

**Signature:**
```python
def get_installed_skills(
    skills_dir: Optional[Path] = None
) -> List[str]:
```

**Parameters:**
- `skills_dir`: Custom skills directory (None = `~/.claude/skills/`)

**Returns:**
- `List[str]`: List of installed skill names

**Raises:**
- `PermissionError`: Cannot read skills directory

**Example:**
```python
from fetch_skill_manager import get_installed_skills

installed = get_installed_skills()

if 'macos-cleaner' in installed:
    print("✓ macos-cleaner already installed")
else:
    print("✗ macos-cleaner not installed")
    print("  Install: npx skills-installer install macos-cleaner")
```

---

## Performance Considerations

### Database Size

| Metric | Value |
|--------|-------|
| File size | ~30 MB |
| Skill count | 31,767 |
| Parse time | ~500 ms |
| Memory usage | ~80 MB |

### Optimization Strategies

**1. Filter Early:**
```python
# ✓ Good: Filter during fetch
skills, _ = fetch_all_skills(min_stars=50)  # ~1,200 skills

# ✗ Bad: Fetch all, filter later
skills, _ = fetch_all_skills()  # 31,767 skills
filtered = [s for s in skills if s['stars'] >= 50]
```

**2. Cache Results:**
```python
from utils.cache_manager import CacheManager

cache = CacheManager(cache_dir=Path('.cache'))

# Try cache first
skills = cache.get('skills_50_stars', category='historical')

if skills is None:
    # Cache miss: fetch and cache
    skills, _ = fetch_all_skills(min_stars=50)
    cache.set('skills_50_stars', skills, category='historical')
```

**3. Limit Results:**
```python
# Fetch all, sort, limit
skills, _ = fetch_all_skills(min_stars=50)
top_20 = sorted(skills, key=lambda s: s['stars'], reverse=True)[:20]
```

---

## Common Pitfalls

### Pitfall 1: Assuming All Fields Present

**Problem:**
```python
# ✗ Crashes if 'category' missing
if skill['category'] == 'ai':
    print(skill['name'])
```

**Solution:**
```python
# ✓ Use .get() with default
if skill.get('category', '') == 'ai':
    print(skill['name'])
```

---

### Pitfall 2: String vs Integer Comparison

**Problem:**
```python
# ✗ May fail if stars is string
if skill['stars'] > 50:
    ...
```

**Solution:**
```python
# ✓ Ensure integer type
stars = int(skill.get('stars', 0))
if stars > 50:
    ...
```

---

### Pitfall 3: Timezone-Naive Datetime

**Problem:**
```python
# ✗ Naive datetime comparison
updated = datetime.fromisoformat(skill['updated_at'])
```

**Solution:**
```python
# ✓ Timezone-aware datetime
from datetime import timezone
updated = datetime.fromisoformat(skill['updated_at'].replace('Z', '+00:00'))
```

---

## Testing Examples

### Test 1: Database Availability

```python
from pathlib import Path

db_path = Path.home() / '.claude/skills/skill-manager/data/all_skills_with_cn.json'

if db_path.exists():
    print(f"✓ Database found: {db_path}")
    print(f"  Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
else:
    print("✗ Database not found")
```

### Test 2: Fetch Performance

```python
import time

start = time.time()
skills, _ = fetch_all_skills()
elapsed = time.time() - start

print(f"✓ Fetched {len(skills)} skills in {elapsed:.2f}s")
```

### Test 3: Filter Accuracy

```python
skills, metadata = fetch_all_skills(min_stars=50, max_months_old=6)

# Verify all skills meet criteria
for skill in skills:
    assert skill['stars'] >= 50, f"Star filter failed: {skill['name']}"

    updated = datetime.fromisoformat(skill['updated_at'].replace('Z', '+00:00'))
    months_old = (datetime.now(timezone.utc) - updated).days / 30
    assert months_old <= 6, f"Recency filter failed: {skill['name']}"

print(f"✓ All {len(skills)} skills pass filters")
```

---

## Related Documentation

- **GitHub API Guide**: `github-api-guide.md` (for GitHub star history)
- **Analysis Methodologies**: `analysis-methodologies.md` (for using skill data)
- **Troubleshooting**: `troubleshooting.md` (for common issues)

---

**End of Guide**
