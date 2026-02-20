#!/usr/bin/env python3
"""
Configuration loader with local override support.

Usage:
    from config_loader import load_config
    config = load_config()  # Auto-merges config.json + config.local.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

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
