#!/usr/bin/env python3
"""
Cache management for skill-trending-monitor-cskill.
Provides dual-cache system with different TTLs for metadata and security evaluations.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching for skill-trending-monitor.

    Two cache types:
    1. Metadata cache (30-day TTL) - skill-manager database data
    2. Security cache (7-day TTL) - security evaluation results

    Features:
    - Filesystem-based JSON caching
    - Automatic TTL enforcement
    - Cache invalidation
    - Cleanup of expired entries

    Example:
        >>> cache = CacheManager()
        >>> cache.set('skill-a', {'stars': 100}, cache_type='metadata')
        >>> data = cache.get('skill-a', cache_type='metadata')
        >>> cache.invalidate('skill-a', cache_type='metadata')
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Cache directory (defaults to data/cache/ relative to project root)

        Example:
            >>> cache = CacheManager()  # Uses default
            >>> cache = CacheManager(Path('/tmp/cache'))  # Custom location
        """
        if cache_dir is None:
            # Default: skill-trending-monitor-cskill/data/cache/
            base_dir = Path(__file__).parent.parent.parent
            cache_dir = base_dir / 'data' / 'cache'

        self.cache_dir = Path(cache_dir)
        self.metadata_cache_dir = self.cache_dir / 'metadata'
        self.security_cache_dir = self.cache_dir / 'security'

        # Create cache directories
        self.metadata_cache_dir.mkdir(parents=True, exist_ok=True)
        self.security_cache_dir.mkdir(parents=True, exist_ok=True)

        # TTLs
        self.metadata_ttl = timedelta(days=30)
        self.security_ttl = timedelta(days=7)

        logger.info(f"CacheManager initialized: {self.cache_dir}")

    def get(self, key: str, cache_type: str = 'metadata') -> Optional[Any]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key (usually skill name)
            cache_type: 'metadata' or 'security'

        Returns:
            Cached value if exists and not expired, None otherwise

        Example:
            >>> cache = CacheManager()
            >>> data = cache.get('skill-manager', cache_type='metadata')
            >>> if data is None:
            ...     print("Cache miss or expired")
        """
        cache_dir = self._get_cache_dir(cache_type)
        ttl = self._get_ttl(cache_type)
        cache_file = cache_dir / f"{self._sanitize_key(key)}.json"

        if not cache_file.exists():
            logger.debug(f"Cache miss: {key} (file not found)")
            return None

        # Check TTL
        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_mtime

        if age > ttl:
            logger.info(f"Cache expired: {key} (age: {age.days} days, TTL: {ttl.days} days)")
            cache_file.unlink()
            return None

        # Load and return
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Cache hit: {key} (age: {age.days} days)")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Cache read error for {key}: {e}")
            cache_file.unlink()  # Remove corrupted cache
            return None

    def set(self, key: str, value: Any, cache_type: str = 'metadata') -> None:
        """
        Set cached value.

        Args:
            key: Cache key (usually skill name)
            value: Value to cache (must be JSON-serializable)
            cache_type: 'metadata' or 'security'

        Example:
            >>> cache = CacheManager()
            >>> cache.set('skill-manager', {'stars': 1250, 'updated': '2026-02-03'})
        """
        cache_dir = self._get_cache_dir(cache_type)
        cache_file = cache_dir / f"{self._sanitize_key(key)}.json"

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
            logger.debug(f"Cache set: {key}")
        except (TypeError, IOError) as e:
            logger.error(f"Cache write error for {key}: {e}")

    def invalidate(self, key: str, cache_type: str = 'metadata') -> None:
        """
        Invalidate cached value.

        Args:
            key: Cache key to invalidate
            cache_type: 'metadata' or 'security'

        Example:
            >>> cache = CacheManager()
            >>> cache.invalidate('skill-manager', cache_type='metadata')
        """
        cache_dir = self._get_cache_dir(cache_type)
        cache_file = cache_dir / f"{self._sanitize_key(key)}.json"

        if cache_file.exists():
            cache_file.unlink()
            logger.info(f"Cache invalidated: {key}")
        else:
            logger.debug(f"Cache invalidation skipped (not found): {key}")

    def cleanup_expired(self, cache_type: Optional[str] = None) -> int:
        """
        Cleanup expired cache entries.

        Args:
            cache_type: 'metadata', 'security', or None for both

        Returns:
            Number of expired entries removed

        Example:
            >>> cache = CacheManager()
            >>> removed = cache.cleanup_expired()
            >>> print(f"Removed {removed} expired entries")
        """
        types = [cache_type] if cache_type else ['metadata', 'security']
        total_removed = 0

        for cache_type in types:
            cache_dir = self._get_cache_dir(cache_type)
            ttl = self._get_ttl(cache_type)

            for cache_file in cache_dir.glob('*.json'):
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = datetime.now() - file_mtime

                if age > ttl:
                    cache_file.unlink()
                    total_removed += 1
                    logger.debug(f"Removed expired cache: {cache_file.stem}")

        if total_removed > 0:
            logger.info(f"Cleanup completed: {total_removed} expired entries removed")

        return total_removed

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with cache counts by type

        Example:
            >>> cache = CacheManager()
            >>> stats = cache.get_stats()
            >>> print(f"Metadata cache: {stats['metadata']} entries")
        """
        metadata_count = len(list(self.metadata_cache_dir.glob('*.json')))
        security_count = len(list(self.security_cache_dir.glob('*.json')))

        return {
            'metadata': metadata_count,
            'security': security_count,
            'total': metadata_count + security_count
        }

    def clear(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache (remove all entries).

        Args:
            cache_type: 'metadata', 'security', or None for both

        Returns:
            Number of entries removed

        Example:
            >>> cache = CacheManager()
            >>> removed = cache.clear(cache_type='metadata')
            >>> print(f"Cleared {removed} metadata cache entries")
        """
        types = [cache_type] if cache_type else ['metadata', 'security']
        total_removed = 0

        for cache_type in types:
            cache_dir = self._get_cache_dir(cache_type)

            for cache_file in cache_dir.glob('*.json'):
                cache_file.unlink()
                total_removed += 1

        logger.info(f"Cache cleared: {total_removed} entries removed")
        return total_removed

    def _get_cache_dir(self, cache_type: str) -> Path:
        """Get cache directory for given type."""
        if cache_type == 'metadata':
            return self.metadata_cache_dir
        elif cache_type == 'security':
            return self.security_cache_dir
        else:
            raise ValueError(f"Invalid cache_type: {cache_type} (must be 'metadata' or 'security')")

    def _get_ttl(self, cache_type: str) -> timedelta:
        """Get TTL for given cache type."""
        if cache_type == 'metadata':
            return self.metadata_ttl
        elif cache_type == 'security':
            return self.security_ttl
        else:
            raise ValueError(f"Invalid cache_type: {cache_type}")

    def _sanitize_key(self, key: str) -> str:
        """
        Sanitize cache key for safe filename usage.

        Replaces filesystem-unsafe characters with underscores.
        """
        # Replace unsafe characters with underscore
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = key
        for char in unsafe_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized


# Main for testing
if __name__ == "__main__":
    import sys

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== CacheManager Test ===\n")

    # Test 1: Initialize cache
    print("1. Testing initialization:")
    cache = CacheManager()
    print(f"   ✓ Cache directory: {cache.cache_dir}")
    print(f"   ✓ Metadata TTL: {cache.metadata_ttl.days} days")
    print(f"   ✓ Security TTL: {cache.security_ttl.days} days")

    # Test 2: Set and get metadata cache
    print("\n2. Testing metadata cache:")
    cache.set('skill-manager', {
        'stars': 1250,
        'updated': '2026-02-03',
        'description': 'Test skill'
    }, cache_type='metadata')
    print("   ✓ Cache set: skill-manager")

    data = cache.get('skill-manager', cache_type='metadata')
    if data:
        print(f"   ✓ Cache hit: {data}")
    else:
        print("   ✗ Cache miss (unexpected)")

    # Test 3: Set and get security cache
    print("\n3. Testing security cache:")
    cache.set('skill-a', {
        'security_score': 85,
        'evaluated': '2026-02-03'
    }, cache_type='security')
    print("   ✓ Cache set: skill-a")

    data = cache.get('skill-a', cache_type='security')
    if data:
        print(f"   ✓ Cache hit: {data}")

    # Test 4: Cache stats
    print("\n4. Testing cache statistics:")
    stats = cache.get_stats()
    print(f"   ✓ Metadata cache: {stats['metadata']} entries")
    print(f"   ✓ Security cache: {stats['security']} entries")
    print(f"   ✓ Total: {stats['total']} entries")

    # Test 5: Cache invalidation
    print("\n5. Testing cache invalidation:")
    cache.invalidate('skill-manager', cache_type='metadata')
    data = cache.get('skill-manager', cache_type='metadata')
    if data is None:
        print("   ✓ Cache invalidated successfully")
    else:
        print("   ✗ Cache invalidation failed")

    # Test 6: Cleanup
    print("\n6. Testing cleanup:")
    removed = cache.cleanup_expired()
    print(f"   ✓ Cleanup completed: {removed} expired entries removed")

    # Test 7: Clear cache
    print("\n7. Testing cache clear:")
    removed = cache.clear()
    print(f"   ✓ Cache cleared: {removed} entries removed")

    stats = cache.get_stats()
    print(f"   ✓ Final cache size: {stats['total']} entries")

    print("\n✅ All tests completed")
