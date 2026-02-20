# Codex Task: Add --profile CLI Flag

## Context

Project: `skill-trending-monitor-cskill`
Location: `$HOME/Workspace/Personal-Digital-Twin/skill-trending-monitor-cskill`

The project has 4 filter profiles defined in `assets/filters.json`, but they can only be switched by modifying config files. Need to add CLI flag support.

## Task

Add `--profile` command-line argument to `analyze_comprehensive.py` to allow runtime profile switching.

## Requirements

### 1. Read Filter Profiles

First, read the existing profiles in `assets/filters.json`. Each profile has nested structure:

```json
{
  "profiles": {
    "strict": {
      "quality": { "min_stars": 100, "max_months_old": 3, ... },
      "similarity": { "threshold": 0.80, ... },
      "replacement": { "confidence_threshold": 0.75, ... },
      "security": { "threshold": 80, ... }
    },
    "balanced": { ... },
    "permissive": { ... },
    "experimental": { ... }
  }
}
```

Read the actual file for complete structure.

### 2. Modify `analyze_comprehensive.py`

Add argparse argument:

```python
parser.add_argument(
    '--profile',
    choices=['strict', 'balanced', 'permissive', 'experimental'],
    default='balanced',
    help='Filter profile to use (default: balanced). See assets/filters.json for details.'
)
```

### 3. Implementation Logic

1. Parse command-line arguments at the start of `main()`
2. Load profile from `assets/filters.json`
3. Deep merge profile settings into config thresholds:
   - `config['thresholds']['quality']` ← merge with `profile['quality']`
   - `config['thresholds']['similarity']` ← merge with `profile['similarity']`
   - `config['thresholds']['replacement']` ← merge with `profile['replacement']`
   - `config['thresholds']['security']` ← merge with `profile['security']`
4. Log which profile is being used: `logger.info(f"Using filter profile: {args.profile}")`
5. Create a helper function `load_profile(profile_name: str) -> dict` for clean code

### 4. Preserve Backward Compatibility

- If `--profile` is not provided, use "balanced" (current default behavior)
- Don't modify `config.json` file, only override in memory
- Existing tests should continue to pass

### 5. Add Help Text

When running `python scripts/analyze_comprehensive.py --help`, should show:

```
usage: analyze_comprehensive.py [-h] [--profile {strict,balanced,permissive,experimental}]

Comprehensive skill trending analysis

optional arguments:
  -h, --help            show this help message and exit
  --profile {strict,balanced,permissive,experimental}
                        Filter profile to use (default: balanced). See assets/filters.json for details.
```

### 6. Verification

```bash
cd $HOME/Workspace/Personal-Digital-Twin/skill-trending-monitor-cskill

# Test help
python scripts/analyze_comprehensive.py --help

# Test strict profile (should show "Using filter profile: strict" in logs)
python scripts/analyze_comprehensive.py --profile strict

# Test default (should use balanced)
python scripts/analyze_comprehensive.py
```

## Reference Files

- Main script: `scripts/analyze_comprehensive.py`
- Filter profiles: `assets/filters.json`
- Config: `assets/config.json`

## Expected Output

Modified `analyze_comprehensive.py` with working `--profile` flag.
