# Troubleshooting Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-03

---

## Overview

This guide provides solutions to common issues encountered when using skill-trending-monitor-cskill. Consult this guide when:

- Installation or setup fails
- API calls return errors
- Data quality issues occur
- Similarity calculations produce unexpected results
- Performance problems arise

For detailed technical background, see:
- `skill-manager-api-guide.md` - Data source issues
- `github-api-guide.md` - API rate limiting and authentication
- `analysis-methodologies.md` - Analysis logic
- `similarity-algorithms.md` - Similarity calculation details

---

## 1. Installation Issues

### Issue: marketplace.json Not Found

**Error:**
```
Failed to install plugin: marketplace.json not found
```

**Cause:** Missing `.claude-plugin/marketplace.json` file

**Solution:**
```bash
# Verify file exists
ls -la skill-trending-monitor-cskill/.claude-plugin/marketplace.json

# If missing, reinstall or check git
git status
```

---

### Issue: Invalid JSON Syntax

**Error:**
```
JSON parse error: Unexpected token at line X
```

**Cause:** Syntax error in marketplace.json

**Solution:**
```bash
# Validate JSON
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"

# Check for:
# - Missing commas
# - Trailing commas
# - Unquoted strings
# - Unclosed brackets
```

---

### Issue: Python Dependencies Missing

**Error:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Cause:** Required Python packages not installed

**Solution:**
```bash
# Install all dependencies
pip install pandas scikit-learn requests

# Or use requirements.txt if provided
pip install -r requirements.txt

# Verify installation
python3 -c "import pandas, sklearn, requests; print('✅ All dependencies installed')"
```

---

## 2. API Rate Limiting

### Issue: GitHub API Rate Limit Exceeded

**Error:**
```
GitHub API rate limit exceeded: 0 remaining
Reset at: 2026-02-03 14:30:00 UTC
```

**Cause:** Exceeded 5,000 requests/hour (authenticated) or 60 requests/hour (unauthenticated)

**Solutions:**

**Option 1: Wait for Reset**
```bash
# Check rate limit status
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit

# Wait until reset time, then retry
```

**Option 2: Use Authentication**
```bash
# Set GitHub token (increases limit to 5,000/hour)
export GITHUB_TOKEN="your_personal_access_token"

# Verify token works
python3 scripts/fetch_github_stars.py --test
```

**Option 3: Batch and Cache**
```python
# Use cache_manager to avoid redundant API calls
from utils.cache_manager import CacheManager

cache = CacheManager(cache_dir=Path('.cache'))
cached_stars = cache.get('github_stars_repo_name', category='github')

if cached_stars is None:
    stars = fetch_github_stars(repo_name)
    cache.set('github_stars_repo_name', stars, category='github', ttl=86400)
```

---

### Issue: Authentication Failed

**Error:**
```
GitHub API authentication failed: 401 Unauthorized
```

**Cause:** Invalid or expired GitHub token

**Solution:**
```bash
# Verify token is set
echo $GITHUB_TOKEN

# Test token
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# If invalid, generate new token at:
# https://github.com/settings/tokens
# Required scopes: public_repo (read-only)
```

---

## 3. Data Quality Problems

### Issue: Empty skill-manager Database

**Error:**
```
ValueError: skills_df cannot be empty
```

**Cause:** skill-manager database file missing or corrupted

**Solution:**
```bash
# Verify database exists
ls -lh ~/.claude/skills/skill-manager/data/all_skills_with_cn.json

# Check file size (should be ~30 MB)
du -h ~/.claude/skills/skill-manager/data/all_skills_with_cn.json

# If missing or corrupted, reinstall skill-manager
npx skills-installer install skill-manager

# Verify installation
python3 -c "from scripts.fetch_skill_manager import fetch_all_skills; skills, meta = fetch_all_skills(); print(f'✅ {len(skills)} skills loaded')"
```

---

### Issue: Missing Required Columns

**Error:**
```
KeyError: Missing required columns: {'stars', 'updated_at'}
```

**Cause:** skill-manager database schema mismatch

**Solution:**
```python
# Debug: Inspect actual columns
import json
from pathlib import Path

db_path = Path.home() / '.claude/skills/skill-manager/data/all_skills_with_cn.json'
with open(db_path) as f:
    data = json.load(f)

print("Database version:", data['metadata']['version'])
print("Available columns:", list(data['skills'][0].keys()))

# If schema is outdated, update skill-manager
npx skills-installer update skill-manager
```

---

### Issue: Validation Failures

**Error:**
```
ValidationError: 'year' must be integer type
```

**Cause:** Data type mismatch in parsed data

**Solution:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run analysis to see detailed validation output
from scripts.analyze_new_skills import discover_new_skills
skills = discover_new_skills(min_stars=50, max_months_old=6)

# Check validation report in output
# Fix data type issues in parse scripts if needed
```

---

## 4. Similarity Calculation Issues

### Issue: No Similar Pairs Found

**Error:**
```
Found 0 similar pairs above threshold
```

**Cause:** Similarity threshold too high or insufficient skill descriptions

**Solutions:**

**Option 1: Lower Threshold**
```python
# Default threshold: 0.75 (strict)
similar = calculate_skill_similarity(skills_df, similarity_threshold=0.75)

# Try lower threshold: 0.60 (more permissive)
similar = calculate_skill_similarity(skills_df, similarity_threshold=0.60)
```

**Option 2: Check Data Quality**
```python
# Verify skills have descriptions
skills_with_desc = skills_df[skills_df['description'].notna()]
print(f"Skills with descriptions: {len(skills_with_desc)} / {len(skills_df)}")

# Filter out empty descriptions
skills_df = skills_df[skills_df['description'].str.strip() != '']
```

**Option 3: Tune TF-IDF Parameters**
```python
# Increase max_features for more precision
vectorizer = TfidfVectorizer(
    max_features=1000,  # Default: 500
    ngram_range=(1, 3),  # Default: (1, 2) - add trigrams
    min_df=1,
    max_df=0.8
)
```

---

### Issue: Low Similarity Scores

**Problem:** All similarity scores < 0.5, even for obviously similar skills

**Cause:** Poor parameter tuning or stop words removing key terms

**Solutions:**

**Option 1: Reduce Stop Words**
```python
# Default uses English stop words
vectorizer = TfidfVectorizer(stop_words='english')

# Try custom stop words (preserve domain terms)
custom_stops = ['the', 'a', 'an', 'is', 'are']  # Minimal list
vectorizer = TfidfVectorizer(stop_words=custom_stops)

# Or remove stop words entirely
vectorizer = TfidfVectorizer(stop_words=None)
```

**Option 2: Adjust IDF Weighting**
```python
# Default: IDF weighting enabled
vectorizer = TfidfVectorizer(use_idf=True)

# Try disabling IDF (pure TF)
vectorizer = TfidfVectorizer(use_idf=False)

# Compare results
```

**Option 3: Increase Context Window**
```python
# Default: bigrams (1, 2)
vectorizer = TfidfVectorizer(ngram_range=(1, 2))

# Try larger context: unigrams to trigrams
vectorizer = TfidfVectorizer(ngram_range=(1, 3))
```

---

## 5. Performance Optimization

### Issue: Slow Analysis (> 5 minutes)

**Cause:** Large skill database (31,767+ skills) with quadratic similarity calculation

**Solutions:**

**Option 1: Filter Skills First**
```python
# Apply quality filters before similarity
skills_df = skills_df[skills_df['stars'] >= 50]
skills_df = skills_df[skills_df['updated_at'] >= cutoff_date]

# Reduces from 31,767 to ~1,200 skills
# 26x faster similarity calculation
```

**Option 2: Parallel Processing**
```bash
# Set environment variable for parallel processing
export JOBLIB_N_JOBS=8  # Use 8 cores

# Run analysis (automatically uses parallel if available)
python3 scripts/analyze_comprehensive.py
```

**Option 3: Use Approximate Nearest Neighbors**
```python
# For very large datasets (100,000+), use LSH
# Add to scripts/analyze_similarity.py:

from sklearn.neighbors import LSHForest

# Build LSH index (fast approximate search)
lshf = LSHForest(n_estimators=20, n_candidates=200)
lshf.fit(tfidf_matrix)

# Find approximate nearest neighbors
distances, indices = lshf.kneighbors(tfidf_matrix[0:1], n_neighbors=10)
```

---

### Issue: High Memory Usage (> 4 GB)

**Cause:** Dense TF-IDF matrix or large similarity matrix

**Solutions:**

**Option 1: Use Sparse Matrices** (Already Default)
```python
# Verify sparse matrix is being used
from scipy.sparse import issparse

tfidf_matrix = vectorizer.fit_transform(descriptions)
print(f"Sparse: {issparse(tfidf_matrix)}")  # Should be True

# Memory usage
print(f"Memory: {tfidf_matrix.data.nbytes / 1024 / 1024:.1f} MB")
```

**Option 2: Batch Processing**
```python
# Process in batches of 1,000 skills
batch_size = 1000
for i in range(0, len(skills_df), batch_size):
    batch = skills_df.iloc[i:i+batch_size]
    process_batch(batch)
```

**Option 3: Store Only High Similarities**
```python
# Don't store full N×N matrix (4 GB for 31,767 skills)
# Only store pairs above threshold (10 MB)

high_sim_pairs = []
for i in range(len(similarity_matrix)):
    for j in range(i+1, len(similarity_matrix)):
        if similarity_matrix[i, j] >= 0.75:
            high_sim_pairs.append((i, j, similarity_matrix[i, j]))
```

---

## 6. Common Error Messages

### Error: "File not found: .cache/github_stars.json"

**Solution:** Cache directory doesn't exist
```bash
mkdir -p .cache
chmod 755 .cache
```

---

### Error: "ConnectionError: Max retries exceeded"

**Solution:** Network timeout or API down
```bash
# Check network
ping api.github.com

# Verify API status
curl https://www.githubstatus.com/api/v2/status.json

# Increase timeout in scripts/fetch_github_stars.py:
response = requests.get(url, headers=headers, timeout=30)  # Default: 10
```

---

### Error: "UnicodeDecodeError: 'utf-8' codec can't decode"

**Solution:** Non-UTF-8 characters in skill descriptions
```python
# In parse scripts, force UTF-8 encoding
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
```

---

## 7. Debug Strategies

### Enable Debug Logging

```python
import logging

# Enable debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run analysis
from scripts.analyze_comprehensive import generate_comprehensive_report
generate_comprehensive_report()
```

---

### Test Individual Components

```bash
# Test fetch_skill_manager.py
python3 scripts/fetch_skill_manager.py

# Test fetch_github_stars.py
python3 scripts/fetch_github_stars.py --repo anthropics/skills

# Test parse_skill_manager.py
python3 scripts/parse_skill_manager.py

# Test analyze_new_skills.py
python3 scripts/analyze_new_skills.py
```

---

### Validate Data at Each Step

```python
# After fetching
print(f"Fetched: {len(skills)} skills")
print(f"Sample: {skills[0]}")

# After parsing
print(f"Parsed: {len(df)} rows")
print(f"Columns: {list(df.columns)}")
print(f"Types: {df.dtypes}")

# After validation
report = validator.validate_dataframe(df, 'skills')
print(report.get_summary())
```

---

## 8. Related Documentation

- **skill-manager-api-guide.md** - Database access issues
- **github-api-guide.md** - API authentication and rate limiting
- **analysis-methodologies.md** - Analysis logic and formulas
- **similarity-algorithms.md** - TF-IDF and cosine similarity tuning

---

## 9. Getting Help

If issues persist after consulting this guide:

1. **Check logs:** `logs/` directory for detailed error traces
2. **Run tests:** `python3 tests/test_integration.py` to verify installation
3. **Verify dependencies:** `pip list | grep -E "pandas|scikit|requests"`
4. **Review configuration:** Check `assets/config.json` for correct settings
5. **Consult documentation:** Read related guides for deeper technical details

---

**End of Troubleshooting Guide**
