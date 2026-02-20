# Error Handling

This skill implements comprehensive error handling with graceful degradation.

## GitHub API Errors

### Error: Rate limit exceeded (HTTP 429)

**Handling:**
1. Parse `Retry-After` header (seconds until quota reset)
2. Implement exponential backoff: `wait_time = min(2^retry × 60, 3600)` seconds
3. Log rate limit status to user
4. Fallback: Use cached star data if available (even if expired)
5. Skip WoW growth analysis if API unavailable

**User Message:**
```
⚠️ GitHub API rate limit reached. Using cached data.
Next quota reset: 45 minutes
WoW growth analysis skipped (requires fresh API data)
```

---

### Error: Invalid repository URL or 404

**Handling:**
1. Mark skill as "unavailable" in results
2. Log warning to console
3. Continue processing other skills
4. Report unavailable skills in summary

**User Message:**
```
⚠️ 3 skills unavailable (repository not found):
- skill-x (repository deleted?)
- skill-y (invalid URL)
```

---

## skill-manager Database Errors

### Error: Database file not found

**Handling:**
1. Check if skill-manager is installed: `ls ~/.claude/skills/skill-manager`
2. If not installed, recommend installation
3. If installed but database missing, suggest re-installation
4. Abort analyses requiring database (1-4)

**User Message:**
```
❌ skill-manager database not found.

Please install skill-manager first:
/plugin marketplace add skill-manager

Or if already installed, reinstall to rebuild database.
```

---

### Error: Database schema mismatch or corrupted JSON

**Handling:**
1. Validate JSON syntax with try/catch
2. Check required fields: `name`, `description`, `repository`, `stars`
3. Log parse errors with line numbers
4. Skip corrupted entries, continue with valid entries
5. Report count of skipped entries

**User Message:**
```
⚠️ Database parsing issues:
- 12 entries skipped (missing required fields)
- 31,755 entries successfully parsed (99.96% success rate)
```

---

## Security Evaluation Errors

### Error: Security evaluation skill not installed

**Handling:**
1. Detect absence of security evaluation skill
2. Warn user that security scores will be unavailable
3. Continue analyses without security filtering
4. Mark all recommendations as "unevaluated"

**User Message:**
```
⚠️ Security evaluation skipped (skill not installed)
All recommendations marked as "unevaluated"

To enable security evaluation:
/plugin marketplace add skill-security-auditor
```

---

### Error: Security evaluation fails for specific skill

**Handling:**
1. Catch evaluation errors (exit code != 0)
2. Log error details to console
3. Mark skill as "unevaluated" (not blocked)
4. Continue evaluating other skills
5. Let user decide whether to trust unevaluated skills

**User Message:**
```
⚠️ Security evaluation failed for `problematic-skill`
Error: Timeout after 30 seconds
Status: Unevaluated (not blocked)
```

---

## Validation Errors

### Error: Invalid user parameters

**Handling:**
1. Use `parameter_validator.py` to validate inputs
2. Provide clear error message with valid ranges
3. Suggest correct usage with example
4. Abort analysis gracefully

**User Message:**
```
❌ Invalid threshold: 1.5

Similarity threshold must be between 0.0 and 1.0
Example: --similarity-threshold 0.75
```

**Example (threshold out of range):**
```bash
# Invalid
python3 scripts/analyze_similarity.py --threshold 1.5

# Valid
python3 scripts/analyze_similarity.py --threshold 0.75
```

---

### Error: Data validation failures

**Handling:**
1. Use `data_validator.py` to validate all data
2. Generate `ValidationReport` with detailed issues
3. If critical issues found: Abort with error report
4. If warnings only: Continue with warnings logged
5. Provide actionable next steps

**User Message:**
```
⚠️ Data Validation Warnings:

- Missing 'last_updated' field in 5 skills (using 'unknown')
- Non-numeric 'stars' field in 2 skills (skipping)

✅ Validation passed with warnings
Processed: 31,760 / 31,767 skills (99.98%)
```

---

## Network Errors

### Error: Connection timeout

**Handling:**
1. Retry with exponential backoff (max 3 attempts)
2. Log retry attempts to console
3. If all retries fail, skip the skill
4. Report skipped skills in summary

**User Message:**
```
⚠️ Connection timeout for `skill-x` (3 retries failed)
Skipping this skill. Other skills processed normally.
```

---

### Error: DNS resolution failure

**Handling:**
1. Check internet connectivity
2. Suggest checking network settings
3. Fallback to cached data if available
4. Skip network-dependent analyses

**User Message:**
```
❌ Network connectivity issue detected

Please check:
1. Internet connection is active
2. DNS servers are accessible
3. Firewall is not blocking GitHub API

Using cached data where available.
```

---

## File System Errors

### Error: Permission denied when writing cache

**Handling:**
1. Check write permissions for cache directory
2. Suggest fixing permissions with chmod
3. Continue without caching (performance degraded)
4. Warn user about performance impact

**User Message:**
```
⚠️ Cannot write to cache directory (permission denied)

Fix with:
chmod 755 ~/.claude/skills/skill-trending-monitor-cskill/data/cache/

Running without cache (slower performance).
```

---

### Error: Disk space full

**Handling:**
1. Detect disk space error when writing reports
2. Calculate required space vs. available space
3. Suggest cleaning up disk space
4. Abort gracefully without partial files

**User Message:**
```
❌ Insufficient disk space to save report

Required: 2 MB
Available: 100 KB

Please free up disk space and try again.
```

---

## Graceful Degradation Strategy

When errors occur, the skill follows this priority:

1. **Best:** Full analysis with fresh data
2. **Good:** Partial analysis with cached data
3. **Acceptable:** Skip failed component, complete other analyses
4. **Fallback:** Inform user of limitation, suggest manual steps

**Never:** Silent failure or incorrect results

---

## Error Recovery Checklist

When an error occurs:

- [ ] Log detailed error information
- [ ] Inform user with clear, actionable message
- [ ] Attempt graceful degradation
- [ ] Preserve partial results if possible
- [ ] Suggest next steps for user
- [ ] Do not corrupt cached data

---

## Testing Error Scenarios

To test error handling:

```bash
# Test rate limit handling
export GITHUB_TOKEN=""  # Force unauthenticated (60/hour limit)
python3 scripts/analyze_growth_rates.py

# Test missing database
mv ~/.claude/skills/skill-manager/data/all_skills_with_cn.json /tmp/
python3 scripts/analyze_new_skills.py
mv /tmp/all_skills_with_cn.json ~/.claude/skills/skill-manager/data/

# Test invalid threshold
python3 scripts/analyze_similarity.py --threshold 2.0

# Test corrupted cache
echo "invalid json" > data/cache/skill-metadata.json
python3 scripts/analyze_new_skills.py
```
