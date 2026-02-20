# Installation Guide - skill-trending-monitor-cskill

> Complete step-by-step tutorial for installing and configuring the skill-trending-monitor system

**Version:** 1.0.0
**Created:** 2026-02-03
**Difficulty:** Beginner-friendly

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Configuration Guide](#configuration-guide)
4. [First Run Tutorial](#first-run-tutorial)
5. [Verification](#verification)
6. [Automation Setup](#automation-setup)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

---

## Prerequisites

Before installing skill-trending-monitor-cskill, ensure you have:

### 1. Python Environment

**Required:** Python 3.8 or higher

```bash
# Check Python version
python3 --version
# Should output: Python 3.8.x or higher
```

**Why Python 3.8+:**
- Type hints with `from __future__ import annotations`
- Modern syntax (walrus operator, positional-only parameters)
- Long-term support (3.8 EOL October 2024)

### 2. skill-manager Database

**Required:** skill-manager installed with complete database

```bash
# Verify skill-manager database exists
ls -lh ~/.claude/skills/skill-manager/data/all_skills_with_cn.json
# Should show: ~30 MB file with 31,767 skills
```

**If missing:**
```bash
# Install skill-manager using Claude Code
/skill skill-manager
# Or use skill installer
npx skills-installer install skill-manager
```

### 3. GitHub Personal Access Token (Optional but Recommended)

**Optional but HIGHLY recommended for 5,000/hour rate limit vs 60/hour**

**Create token:**
1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: `skill-trending-monitor`
4. Scopes: **Only `public_repo`** (read public repositories)
5. Expiration: 90 days (or your preference)
6. Click "Generate token"
7. **Copy token immediately** (shown only once)

**Why recommended:**
- Unauthenticated: 60 requests/hour → can analyze ~15 skills
- Authenticated: 5,000 requests/hour → can analyze ~1,200 skills
- Growth rate analysis requires 1 API call per skill per week

### 4. Python Dependencies

**Required packages:**
- `pandas` (data manipulation)
- `scikit-learn` (TF-IDF, cosine similarity)
- `requests` (HTTP requests)

These will be installed in Step 2 below.

---

## Installation Steps

### Step 1: Clone or Download the Skill

```bash
# Navigate to your skills directory
cd ~/.claude/skills/

# If using Git
git clone <repository-url> skill-trending-monitor-cskill
cd skill-trending-monitor-cskill

# Or if downloaded as ZIP
unzip skill-trending-monitor-cskill.zip
cd skill-trending-monitor-cskill
```

### Step 2: Install Python Dependencies

```bash
# Install required packages
pip3 install pandas scikit-learn requests

# Verify installation
python3 -c "import pandas, sklearn, requests; print('✓ All dependencies installed')"
# Should output: ✓ All dependencies installed
```

**Troubleshooting dependency issues:**
```bash
# If pip3 not found
python3 -m pip install pandas scikit-learn requests

# If permission denied
pip3 install --user pandas scikit-learn requests
```

### Step 3: Verify skill-manager Database

```bash
# Run verification script
python3 scripts/fetch_skill_manager.py

# Expected output:
# Loading skill-manager database...
# ✓ Found database: ~/.claude/skills/skill-manager/data/all_skills_with_cn.json
# ✓ Loaded 31,767 skills
# ✓ Database verification successful
```

**If verification fails:**
- Check that skill-manager is installed
- Verify database file exists and is readable
- See [Troubleshooting](#troubleshooting) section

### Step 4: Configure GitHub Token (Recommended)

```bash
# Set GitHub token as environment variable
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Verify token is set
echo $GITHUB_TOKEN
# Should output your token

# Make permanent (add to shell profile)
# For bash:
echo 'export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc

# For zsh (macOS default):
echo 'export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

**Verify token works:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit | grep limit
# Should show: "limit": 5000 (authenticated)
```

### Step 5: Initial Configuration

The skill comes with sensible defaults in `assets/config.json`. **You can use it as-is** for the first run, or customize:

```bash
# View default configuration
cat assets/config.json

# Optional: Add your GitHub token to config (alternative to environment variable)
# Edit assets/config.json and replace "YOUR_GITHUB_TOKEN_HERE" with your token
```

**Note:** Environment variable `GITHUB_TOKEN` takes precedence over `config.json`.

---

## Configuration Guide

### Understanding Configuration Files

The skill uses two configuration files:

1. **`assets/config.json`** - Main configuration
2. **`assets/filters.json`** - Quality filter profiles

### 1. Main Configuration (`assets/config.json`)

**Default configuration (balanced profile):**

```json
{
  "github": {
    "token": "YOUR_GITHUB_TOKEN_HERE",
    "rate_limit": {
      "max_requests_per_hour": 5000
    }
  },
  "thresholds": {
    "quality": {
      "min_stars": 50,
      "max_months_old": 6
    },
    "similarity": {
      "threshold": 0.75,
      "max_features": 500
    },
    "replacement": {
      "confidence_threshold": 0.70
    },
    "security": {
      "threshold": 70
    }
  },
  "cache": {
    "enabled": true,
    "ttl": {
      "github": 86400,
      "skills": 604800,
      "analysis": 3600
    }
  },
  "output": {
    "report_dir": "meta/reports",
    "format": "markdown"
  }
}
```

**Key settings explained:**

- **`github.token`**: Your GitHub Personal Access Token (or use environment variable)
- **`thresholds.quality.min_stars`**: Minimum stars to consider a skill (default: 50)
- **`thresholds.quality.max_months_old`**: Maximum age in months (default: 6)
- **`thresholds.similarity.threshold`**: Cosine similarity threshold 0.0-1.0 (default: 0.75)
- **`thresholds.replacement.confidence_threshold`**: Replacement confidence 0.0-1.0 (default: 0.70)
- **`thresholds.security.threshold`**: Security score threshold 0-100 (default: 70)
- **`cache.ttl`**: Time-to-live in seconds (github: 24h, skills: 7d, analysis: 1h)

### 2. Filter Profiles (`assets/filters.json`)

Four preset configurations for different use cases:

| Profile | min_stars | max_months | similarity | Use When |
|---------|-----------|------------|------------|----------|
| **strict** | 100 | 3 | 0.80 | Production systems, high quality only |
| **balanced** | 50 | 6 | 0.75 | General use (default) |
| **permissive** | 10 | 12 | 0.65 | Discovery, willing to evaluate manually |
| **experimental** | 0 | 24 | 0.50 | Research, comprehensive coverage |

**To apply a profile:**

**Method 1: Manual copy (simplest)**
```bash
# Copy values from filters.json balanced profile to config.json
# Edit config.json manually
```

**Method 2: Command-line override (requires script modification)**
```bash
python3 scripts/analyze_comprehensive.py --profile strict
```

**Method 3: Environment variable (requires script modification)**
```bash
FILTER_PROFILE=strict python3 scripts/analyze_comprehensive.py
```

---

## First Run Tutorial

Let's run each analysis function to verify everything works.

### Test 1: Verify Database Access

```bash
cd skill-trending-monitor-cskill

# Test skill-manager database loading
python3 scripts/fetch_skill_manager.py

# Expected output:
# Loading skill-manager database...
# ✓ Found database: ~/.claude/skills/skill-manager/data/all_skills_with_cn.json
# ✓ Loaded 31,767 skills
# Database has following fields: name, author, github_url, stars, forks, updated_at, description
```

### Test 2: Discover New Skills

```bash
# Find high-quality skills not installed locally
python3 scripts/analyze_new_skills.py

# Expected output:
# Discovering new skills (min_stars=50, max_months_old=6)...
# ✓ Found 1,234 skills meeting quality thresholds
# ✓ Filtering out 12 already installed skills
# ✓ Top 10 new skills by stars:
#
# 1. advanced-code-reviewer (1,250 ⭐, updated 2026-01-15)
# 2. ai-commit-generator (890 ⭐, updated 2026-01-28)
# ...
#
# Report saved to: meta/reports/2026-02-03-new-skills-report.md
```

**If you see warnings:**
- "GitHub API rate limit approaching" → Token not configured or exhausted
- "No skills found" → Adjust quality thresholds in config.json

### Test 3: Calculate Growth Rates

```bash
# Calculate week-over-week growth
python3 scripts/analyze_growth_rates.py

# Expected output:
# Analyzing growth rates (time_window=7 days)...
# ✓ Using GitHub token (5,000/hour rate limit)
# ✓ Fetched star history for 50 skills (cached: 30, fresh: 20)
#
# Top 10 fastest growing skills:
# 1. ai-code-explainer: +45% WoW (150 → 218 stars)
# 2. skill-marketplace-search: +38% WoW (200 → 276 stars)
# ...
#
# Report saved to: meta/reports/2026-02-03-growth-rates-report.md
```

**Note:** First run will be slower as it fetches star history. Subsequent runs use cache (24h TTL).

### Test 4: Find Similar Skills

```bash
# Find functionally similar alternatives
python3 scripts/analyze_similarity.py

# Expected output:
# Finding similar skills (similarity_threshold=0.75)...
# ✓ Loaded 31,767 skills
# ✓ Vectorized 31,767 skill descriptions (TF-IDF, max_features=500)
# ✓ Calculated cosine similarity matrix (sparse: 10 MB vs 4 GB dense)
# ✓ Found 45 similar pairs
#
# Similar to "code-reviewer":
# 1. advanced-code-reviewer (similarity: 0.87, 1,250 ⭐)
# 2. pr-review-assistant (similarity: 0.82, 890 ⭐)
# ...
#
# Report saved to: meta/reports/2026-02-03-similarity-report.md
```

### Test 5: Evaluate Replacements

```bash
# Recommend better alternatives for installed skills
python3 scripts/analyze_replacements.py

# Expected output:
# Evaluating replacements (confidence_threshold=0.70)...
# ✓ Found 12 installed skills in ~/.claude/skills/
# ✓ Analyzed 31,767 potential replacements
# ✓ Found 5 high-confidence recommendations
#
# Recommended Replacements:
# 1. old-code-reviewer → advanced-code-reviewer
#    Confidence: 0.85 (star_ratio: 0.90, recency: 0.85, similarity: 0.87)
#    Stars: 500 → 1,250 (+150%)
# ...
#
# Report saved to: meta/reports/2026-02-03-replacements-report.md
```

### Test 6: Security Assessment

```bash
# Evaluate security and quality signals
python3 scripts/evaluate_security.py

# Expected output:
# Evaluating security (threshold=70)...
# ✓ Analyzed 1,234 skills
# ✓ 856 skills passed security threshold
#
# Top 10 Secure Skills:
# 1. advanced-code-reviewer (score: 92/100, EXCELLENT)
#    Stars: 95/100, Activity: 100/100, License: 100/100, Updates: 85/100
# ...
#
# Report saved to: meta/reports/2026-02-03-security-report.md
```

### Test 7: Generate Comprehensive Report

```bash
# Generate complete weekly trending report (combines all analyses)
python3 scripts/analyze_comprehensive.py

# Expected output:
# Generating comprehensive trending report...
#
# Phase 1: Discover new skills... ✓ 1,234 found
# Phase 2: Calculate growth rates... ✓ 45 with significant growth
# Phase 3: Find similar skills... ✓ 45 similar pairs
# Phase 4: Evaluate replacements... ✓ 5 recommendations
# Phase 5: Security assessments... ✓ 856 passed threshold
# Phase 6: Generate statistics... ✓
#
# Report saved to: meta/reports/2026-02-03-skill-trending-report.md
#
# Summary:
# - 🆕 New Skills: 1,234 (top 10 shown)
# - 📈 Fastest Growing: 10 skills
# - 🔄 Similar Alternatives: 45 pairs
# - 🔍 Replacement Recommendations: 5
# - 🛡️ Security Passed: 856 skills
```

---

## Verification

After first run, verify everything is working:

### 1. Check Generated Reports

```bash
# List generated reports
ls -lh meta/reports/2026-02-03-*.md

# Should see:
# 2026-02-03-new-skills-report.md
# 2026-02-03-growth-rates-report.md
# 2026-02-03-similarity-report.md
# 2026-02-03-replacements-report.md
# 2026-02-03-security-report.md
# 2026-02-03-skill-trending-report.md (comprehensive)
```

### 2. Check Cache Directory

```bash
# Verify cache is working
ls -lh .cache/

# Should see:
# github/  (GitHub API responses, 24h TTL)
# skills/  (skill-manager database, 7d TTL)
# analysis/ (analysis results, 1h TTL)
```

### 3. Verify GitHub API Usage

```bash
# Check remaining rate limit
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Should show:
# "limit": 5000
# "remaining": 4900+ (after first run using ~50-100 requests)
# "reset": <timestamp>
```

---

## Automation Setup

Set up weekly automated reports using your system's scheduler.

### macOS (launchd)

**1. Create launchd plist:**

```bash
# Create launch agent directory if needed
mkdir -p ~/Library/LaunchAgents

# Create plist file
cat > ~/Library/LaunchAgents/com.skill-trending-monitor.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.skill-trending-monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/.claude/skills/skill-trending-monitor-cskill/scripts/analyze_comprehensive.py</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>GITHUB_TOKEN</key>
        <string>YOUR_GITHUB_TOKEN_HERE</string>
    </dict>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>  <!-- Sunday -->
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/tmp/skill-trending-monitor.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/skill-trending-monitor.error.log</string>
</dict>
</plist>
EOF
```

**2. Update paths in plist:**

```bash
# Replace YOUR_USERNAME with your actual username
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.skill-trending-monitor.plist

# Replace YOUR_GITHUB_TOKEN_HERE with your actual token
sed -i '' "s/YOUR_GITHUB_TOKEN_HERE/$GITHUB_TOKEN/g" ~/Library/LaunchAgents/com.skill-trending-monitor.plist
```

**3. Load launch agent:**

```bash
# Load the agent
launchctl load ~/Library/LaunchAgents/com.skill-trending-monitor.plist

# Verify it's loaded
launchctl list | grep skill-trending-monitor
# Should show: com.skill-trending-monitor

# Check next run time
launchctl list com.skill-trending-monitor | grep NextInterval
```

**4. Test immediately (optional):**

```bash
# Run now for testing
launchctl start com.skill-trending-monitor

# Check logs
tail -f /tmp/skill-trending-monitor.log
```

### Linux (cron)

**1. Edit crontab:**

```bash
# Open crontab editor
crontab -e
```

**2. Add weekly job:**

```cron
# Run every Sunday at 9:00 AM
0 9 * * 0 cd /home/YOUR_USERNAME/.claude/skills/skill-trending-monitor-cskill && GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE" /usr/bin/python3 scripts/analyze_comprehensive.py >> /tmp/skill-trending-monitor.log 2>&1
```

**3. Save and verify:**

```bash
# List cron jobs
crontab -l

# Check cron logs
grep skill-trending /var/log/syslog
```

---

## Troubleshooting

### Problem 1: "GitHub API rate limit exceeded"

**Symptoms:**
```
Error: GitHub API rate limit exceeded (60/hour)
Remaining: 0, Reset in: 3600 seconds
```

**Cause:** Using unauthenticated requests (60/hour limit)

**Solution:**
1. Generate GitHub token: https://github.com/settings/tokens (public_repo scope)
2. Set environment variable: `export GITHUB_TOKEN="ghp_xxxxx"`
3. Or update `assets/config.json`: `"token": "ghp_xxxxx"`
4. Verify: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit`

---

### Problem 2: "skill-manager database not found"

**Symptoms:**
```
Error: Database file not found at ~/.claude/skills/skill-manager/data/all_skills_with_cn.json
```

**Cause:** Database file missing or wrong path

**Solution:**
```bash
# Verify path
ls -lh ~/.claude/skills/skill-manager/data/all_skills_with_cn.json

# If missing, install skill-manager
npx skills-installer install skill-manager

# Verify installation
python3 scripts/fetch_skill_manager.py
```

---

### Problem 3: "No similar pairs found"

**Symptoms:**
```
✓ Calculated cosine similarity matrix
✓ Found 0 similar pairs
```

**Cause:** Similarity threshold too high or insufficient skill descriptions

**Solutions:**

**1. Lower threshold in `assets/config.json`:**
```json
"similarity": {
  "threshold": 0.60,  // Lower from 0.75
  "max_features": 1000  // Increase from 500
}
```

**2. Use permissive profile:**
```bash
# Apply permissive profile settings (similarity: 0.65)
# Copy from assets/filters.json to assets/config.json
```

**3. Check data quality:**
```bash
# Verify skills have descriptions
python3 scripts/fetch_skill_manager.py | grep description
```

---

### Problem 4: "Analysis taking too long (> 5 minutes)"

**Symptoms:**
- Script runs for > 5 minutes
- High CPU usage
- Memory usage > 2 GB

**Cause:** Large skill database with quadratic similarity calculation

**Solutions:**

**1. Filter skills first (increase min_stars):**
```json
"quality": {
  "min_stars": 100,  // Increase from 50
  "max_months_old": 6
}
```

**2. Enable batch processing (future feature):**
```json
"performance": {
  "batch_size": 500,
  "parallel_processing": false
}
```

**3. Clear old cache:**
```bash
# Remove stale cache files
rm -rf .cache/
```

---

### Problem 5: "High memory usage (> 4 GB)"

**Symptoms:**
- Python process using > 4 GB RAM
- System slowdown
- Out of memory errors

**Cause:** Dense TF-IDF matrix or large similarity matrix

**Solutions:**

**1. Verify sparse matrices are used:**
```bash
# Check scripts use scipy.sparse (already implemented)
grep -n "scipy.sparse" scripts/analyze_similarity.py
```

**2. Reduce max_features:**
```json
"similarity": {
  "max_features": 300  // Reduce from 500
}
```

**3. Process in batches:**
```bash
# Split into batches (manual for now)
python3 scripts/analyze_similarity.py --batch-size 500
```

---

### Problem 6: "ModuleNotFoundError: No module named 'pandas'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Cause:** Dependencies not installed

**Solution:**
```bash
# Install dependencies
pip3 install pandas scikit-learn requests

# If permission denied
pip3 install --user pandas scikit-learn requests

# Verify installation
python3 -c "import pandas, sklearn, requests; print('✓ OK')"
```

---

## Next Steps

After successful installation and first run:

### 1. Customize Configuration

**Adjust quality thresholds:**
- Lower `min_stars` to discover more emerging skills
- Increase `min_stars` for stricter quality filtering
- Adjust `max_months_old` based on your freshness preference

**Try different filter profiles:**
- `strict` for production environments
- `permissive` for discovery mode
- `experimental` for comprehensive research

### 2. Set Up Weekly Automation

Follow the [Automation Setup](#automation-setup) section to schedule weekly reports.

### 3. Integrate with Your Workflow

**Review reports weekly:**
```bash
# Open latest comprehensive report
open meta/reports/$(ls -t meta/reports/*skill-trending-report.md | head -1)
```

**Install recommended skills:**
```bash
# From replacement recommendations section
npx skills-installer install <skill-name>
```

**Update your skills:**
```bash
# Based on security assessment and growth trends
```

### 4. Explore Advanced Features

**Custom similarity algorithms:**
- Modify `scripts/analyze_similarity.py`
- Experiment with different TF-IDF parameters
- Try different similarity metrics (Jaccard, Levenshtein)

**Add new analyses:**
- Skill dependency graphs
- Category-based trending
- Author/organization statistics

**Contribute improvements:**
- See `DECISIONS.md` for architectural rationale
- Submit issues/PRs to improve the skill

### 5. Monitor Performance

**Check cache effectiveness:**
```bash
# View cache hit rates (future feature)
python3 scripts/analyze_comprehensive.py --show-cache-stats
```

**Optimize GitHub API usage:**
- Review rate limit consumption
- Adjust analysis frequency
- Use caching strategically

---

## Getting Help

**Documentation:**
- **[README.md](README.md)** - Overview and quick start
- **[DECISIONS.md](DECISIONS.md)** - Architectural decisions and rationale
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and planned features
- **[references/](references/)** - Detailed technical guides

**Troubleshooting:**
- **[references/troubleshooting.md](references/troubleshooting.md)** - Common issues and solutions
- **[references/github-api-guide.md](references/github-api-guide.md)** - GitHub API setup and rate limiting
- **[references/skill-manager-api-guide.md](references/skill-manager-api-guide.md)** - Database access patterns

**Community:**
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share tips

---

**Installation Complete!** 🎉

You now have a fully functional skill-trending-monitor system that will help you:
- ✅ Discover high-quality new skills weekly
- ✅ Track skill growth trends
- ✅ Find better alternatives to installed skills
- ✅ Make informed decisions about skill adoption
- ✅ Maintain a secure and up-to-date skill ecosystem

**Happy skill monitoring!**

---

**Last Updated:** 2026-02-03
**Version:** 1.0.0
**Created by:** Agent-Skill-Creator
