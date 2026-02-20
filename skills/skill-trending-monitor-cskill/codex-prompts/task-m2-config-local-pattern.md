# Codex Task M2: Add config.local.json Pattern

## Priority
Medium

## Objective
Implement local configuration override pattern so users can customize settings without modifying the tracked `config.json`.

## Context
- Main config: `assets/config.json` (tracked in git, contains defaults)
- Local config: `assets/config.local.json` (git-ignored, user overrides)
- Deep merge: local settings override defaults recursively

## Requirements

### 1. Create `scripts/config_loader.py`

```python
#!/usr/bin/env python3
"""
Configuration loader with local override support.

Usage:
    from config_loader import load_config
    config = load_config()  # Auto-merges config.json + config.local.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Default paths relative to project root
CONFIG_DIR = Path(__file__).parent.parent / 'assets'
DEFAULT_CONFIG = CONFIG_DIR / 'config.json'
LOCAL_CONFIG = CONFIG_DIR / 'config.local.json'


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    - override values replace base values
    - nested dicts are merged recursively
    - lists are replaced (not merged)

    Args:
        base: Base configuration dictionary
        override: Override values to merge in

    Returns:
        Merged dictionary (new object, does not mutate inputs)
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Override value (including lists)
            result[key] = value

    return result


def load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """
    Load JSON file, return None if not found.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON as dict, or None if file doesn't exist

    Raises:
        json.JSONDecodeError: If file exists but is invalid JSON
    """
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_config(
    config_path: Optional[Path] = None,
    local_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load configuration with local override support.

    Priority (highest to lowest):
    1. config.local.json (user overrides)
    2. config.json (defaults)

    Args:
        config_path: Path to base config (default: assets/config.json)
        local_path: Path to local config (default: assets/config.local.json)

    Returns:
        Merged configuration dictionary

    Raises:
        FileNotFoundError: If base config doesn't exist
        json.JSONDecodeError: If any config file is invalid JSON
    """
    config_path = config_path or DEFAULT_CONFIG
    local_path = local_path or LOCAL_CONFIG

    # Load base config (required)
    base_config = load_json_file(config_path)
    if base_config is None:
        raise FileNotFoundError(f"Base configuration not found: {config_path}")

    logger.debug(f"Loaded base config from {config_path}")

    # Load local config (optional)
    local_config = load_json_file(local_path)
    if local_config:
        logger.info(f"Applying local overrides from {local_path}")
        return deep_merge(base_config, local_config)

    return base_config


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get nested config value by dot-separated path.

    Example:
        get_config_value(config, "github.rate_limit.max_requests_per_hour")

    Args:
        config: Configuration dictionary
        key_path: Dot-separated path (e.g., "github.token")
        default: Default value if path not found

    Returns:
        Value at path, or default if not found
    """
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


# Convenience: load config on module import
_cached_config: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    """Get cached config (loads once, reuses)."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config


if __name__ == '__main__':
    # CLI test
    import sys
    config = load_config()

    if len(sys.argv) > 1:
        # Print specific key
        key = sys.argv[1]
        value = get_config_value(config, key)
        print(f"{key} = {json.dumps(value, indent=2)}")
    else:
        # Print full merged config
        print(json.dumps(config, indent=2))
```

### 2. Create Example Local Config

Create `assets/config.local.json.example`:

```json
{
  "_comment": "Copy this to config.local.json and customize. This file is git-ignored.",

  "github": {
    "token": "YOUR_GITHUB_TOKEN_HERE"
  },

  "thresholds": {
    "quality": {
      "min_stars": 100
    }
  },

  "logging": {
    "level": "DEBUG"
  }
}
```

### 3. Update `.gitignore`

Add to `.gitignore`:

```
# Local config (contains secrets)
assets/config.local.json
```

### 4. Add Tests

Create `tests/test_config_loader.py`:

```python
#!/usr/bin/env python3
"""Tests for config_loader module."""

import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from config_loader import deep_merge, load_config, get_config_value


def test_deep_merge_simple():
    """Test basic deep merge."""
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}

    result = deep_merge(base, override)

    assert result == {"a": 1, "b": 3, "c": 4}
    # Original unchanged
    assert base == {"a": 1, "b": 2}


def test_deep_merge_nested():
    """Test nested dict merge."""
    base = {"github": {"token": "default", "timeout": 30}}
    override = {"github": {"token": "override"}}

    result = deep_merge(base, override)

    assert result["github"]["token"] == "override"
    assert result["github"]["timeout"] == 30  # Preserved


def test_deep_merge_list_replace():
    """Test that lists are replaced, not merged."""
    base = {"tags": ["a", "b"]}
    override = {"tags": ["c"]}

    result = deep_merge(base, override)

    assert result["tags"] == ["c"]


def test_load_config_base_only(tmp_path):
    """Test loading with only base config."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')

    result = load_config(config_path=config_file, local_path=tmp_path / "nonexistent.json")

    assert result == {"key": "value"}


def test_load_config_with_local(tmp_path):
    """Test loading with local override."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"a": 1, "b": 2}')

    local_file = tmp_path / "config.local.json"
    local_file.write_text('{"b": 3}')

    result = load_config(config_path=config_file, local_path=local_file)

    assert result == {"a": 1, "b": 3}


def test_get_config_value():
    """Test dot-path value getter."""
    config = {
        "github": {
            "rate_limit": {
                "max_requests": 5000
            }
        }
    }

    assert get_config_value(config, "github.rate_limit.max_requests") == 5000
    assert get_config_value(config, "missing.key", "default") == "default"


def test_load_config_missing_base(tmp_path):
    """Test error when base config missing."""
    with pytest.raises(FileNotFoundError):
        load_config(config_path=tmp_path / "nonexistent.json")
```

## Files to Create/Modify

1. `scripts/config_loader.py` - New file (main implementation)
2. `assets/config.local.json.example` - New file (example for users)
3. `.gitignore` - Add `assets/config.local.json`
4. `tests/test_config_loader.py` - New file (tests)

## Testing

```bash
cd skill-trending-monitor-cskill

# Run tests
python3 -m pytest tests/test_config_loader.py -v

# Test CLI
python3 scripts/config_loader.py
python3 scripts/config_loader.py github.token
```

## Acceptance Criteria

- [ ] `config_loader.py` created with all functions
- [ ] `config.local.json.example` created
- [ ] `.gitignore` updated
- [ ] All tests pass
- [ ] CLI test works: `python3 scripts/config_loader.py github.token`

## Dependencies

None - standalone task

## Notes

- Do NOT modify existing code that reads config.json yet (future task)
- Focus on creating the loader module only
- Keep `_comment` fields (they're documentation)
