#!/usr/bin/env python3
"""
Rate limiting for skill-trending-monitor-cskill.
Implements token bucket algorithm for GitHub API rate limiting.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for GitHub API.

    Features:
    - Token bucket algorithm
    - Automatic retry with exponential backoff
    - Rate limit header parsing
    - 5,000 requests/hour limit for authenticated requests

    Example:
        >>> limiter = RateLimiter(requests_per_hour=5000)
        >>> limiter.wait_if_needed()
        >>> # Make API request
        >>> limiter.update_from_headers(response.headers)
    """

    def __init__(
        self,
        requests_per_hour: int = 5000,
        initial_tokens: Optional[int] = None
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_hour: Maximum requests per hour (default 5000 for GitHub authenticated)
            initial_tokens: Initial token count (defaults to requests_per_hour)

        Example:
            >>> limiter = RateLimiter()  # Uses default 5000/hour
            >>> limiter = RateLimiter(requests_per_hour=60)  # Custom 60/hour
        """
        self.requests_per_hour = requests_per_hour
        self.tokens = initial_tokens if initial_tokens is not None else requests_per_hour
        self.last_refill = datetime.now()

        # Token refill rate (tokens per second)
        self.refill_rate = requests_per_hour / 3600.0

        # Exponential backoff parameters
        self.max_retries = 5
        self.base_wait = 1.0  # seconds

        logger.info(f"RateLimiter initialized: {requests_per_hour} requests/hour")

    def wait_if_needed(self, tokens_needed: int = 1) -> float:
        """
        Wait if insufficient tokens available.

        Args:
            tokens_needed: Number of tokens needed for operation

        Returns:
            Wait time in seconds (0 if no wait needed)

        Example:
            >>> limiter = RateLimiter()
            >>> wait_time = limiter.wait_if_needed()
            >>> print(f"Waited {wait_time}s")
        """
        self._refill_tokens()

        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            logger.debug(f"Consumed {tokens_needed} tokens, {self.tokens:.1f} remaining")
            return 0.0

        # Calculate wait time
        tokens_deficit = tokens_needed - self.tokens
        wait_seconds = tokens_deficit / self.refill_rate

        logger.info(f"Rate limit: waiting {wait_seconds:.1f}s for {tokens_needed} tokens")
        time.sleep(wait_seconds)

        self._refill_tokens()
        self.tokens -= tokens_needed

        return wait_seconds

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit state from GitHub API response headers.

        Args:
            headers: Response headers containing X-RateLimit-* fields

        Example:
            >>> import requests
            >>> response = requests.get('https://api.github.com/...')
            >>> limiter.update_from_headers(response.headers)
        """
        if 'X-RateLimit-Remaining' in headers:
            remaining = int(headers['X-RateLimit-Remaining'])
            self.tokens = remaining
            logger.debug(f"Rate limit updated from headers: {remaining} tokens remaining")

        if 'X-RateLimit-Reset' in headers:
            reset_timestamp = int(headers['X-RateLimit-Reset'])
            reset_time = datetime.fromtimestamp(reset_timestamp)
            now = datetime.now()

            if reset_time > now:
                time_until_reset = (reset_time - now).total_seconds()
                logger.debug(f"Rate limit resets in {time_until_reset:.0f}s at {reset_time}")
            else:
                logger.debug(f"Rate limit reset time has passed: {reset_time}")

    def retry_with_backoff(
        self,
        func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            max_retries: Maximum retry attempts (defaults to self.max_retries)
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted

        Example:
            >>> limiter = RateLimiter()
            >>> def fetch_data():
            ...     response = requests.get('https://api.github.com/...')
            ...     limiter.update_from_headers(response.headers)
            ...     return response.json()
            >>> data = limiter.retry_with_backoff(fetch_data)
        """
        max_retries = max_retries or self.max_retries

        for attempt in range(max_retries):
            try:
                # Wait if needed before attempt
                self.wait_if_needed()

                # Execute function
                result = func(*args, **kwargs)

                return result

            except Exception as e:
                # Check if rate limit error
                is_rate_limit = self._is_rate_limit_error(e)

                if attempt == max_retries - 1:
                    # Final attempt failed
                    logger.error(f"All {max_retries} retry attempts exhausted")
                    raise

                # Calculate backoff time
                wait_time = self._calculate_backoff(attempt, is_rate_limit)

                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )

                time.sleep(wait_time)

    def get_status(self) -> Dict[str, any]:
        """
        Get current rate limiter status.

        Returns:
            Dict with current state

        Example:
            >>> limiter = RateLimiter()
            >>> status = limiter.get_status()
            >>> print(f"Tokens available: {status['tokens']}")
        """
        self._refill_tokens()

        return {
            'tokens': self.tokens,
            'requests_per_hour': self.requests_per_hour,
            'refill_rate': self.refill_rate,
            'last_refill': self.last_refill.isoformat(),
            'tokens_max': self.requests_per_hour
        }

    def reset(self) -> None:
        """
        Reset rate limiter to initial state.

        Example:
            >>> limiter = RateLimiter()
            >>> # ... use limiter ...
            >>> limiter.reset()  # Start fresh
        """
        self.tokens = self.requests_per_hour
        self.last_refill = datetime.now()
        logger.info("Rate limiter reset")

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()

        if elapsed > 0:
            tokens_to_add = elapsed * self.refill_rate
            old_tokens = self.tokens
            self.tokens = min(self.tokens + tokens_to_add, self.requests_per_hour)
            self.last_refill = now

            if tokens_to_add > 0:
                logger.debug(
                    f"Refilled {tokens_to_add:.2f} tokens "
                    f"({old_tokens:.1f} → {self.tokens:.1f})"
                )

    def _calculate_backoff(self, attempt: int, is_rate_limit: bool) -> float:
        """
        Calculate exponential backoff wait time.

        Args:
            attempt: Current attempt number (0-indexed)
            is_rate_limit: Whether error was rate limit specific

        Returns:
            Wait time in seconds
        """
        if is_rate_limit:
            # For rate limit errors, wait longer
            wait_time = self.base_wait * (3 ** attempt)
        else:
            # For other errors, standard exponential backoff
            wait_time = self.base_wait * (2 ** attempt)

        # Cap maximum wait time at 5 minutes
        return min(wait_time, 300.0)

    def _is_rate_limit_error(self, exception: Exception) -> bool:
        """
        Check if exception is a rate limit error.

        Args:
            exception: Exception to check

        Returns:
            True if rate limit error
        """
        error_str = str(exception).lower()
        rate_limit_indicators = [
            'rate limit',
            '429',
            'too many requests',
            'api rate limit exceeded'
        ]

        return any(indicator in error_str for indicator in rate_limit_indicators)


# Main for testing
if __name__ == "__main__":
    import sys

    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=== RateLimiter Test ===\n")

    # Test 1: Initialize rate limiter
    print("1. Testing initialization:")
    limiter = RateLimiter(requests_per_hour=60)  # 1 request per second for testing
    print(f"   ✓ Rate limiter initialized: {limiter.requests_per_hour} requests/hour")
    print(f"   ✓ Initial tokens: {limiter.tokens}")
    print(f"   ✓ Refill rate: {limiter.refill_rate:.4f} tokens/second")

    # Test 2: Wait if needed (no wait)
    print("\n2. Testing wait_if_needed (sufficient tokens):")
    wait_time = limiter.wait_if_needed(tokens_needed=1)
    print(f"   ✓ Wait time: {wait_time}s")
    print(f"   ✓ Tokens remaining: {limiter.tokens:.1f}")

    # Test 3: Consume many tokens (should wait)
    print("\n3. Testing wait_if_needed (insufficient tokens):")
    print("   Consuming 55 tokens (will need to wait)...")
    wait_time = limiter.wait_if_needed(tokens_needed=55)
    print(f"   ✓ Wait time: {wait_time:.1f}s")
    print(f"   ✓ Tokens remaining: {limiter.tokens:.1f}")

    # Test 4: Update from headers
    print("\n4. Testing update_from_headers:")
    mock_headers = {
        'X-RateLimit-Remaining': '4500',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp()))
    }
    limiter.update_from_headers(mock_headers)
    print(f"   ✓ Tokens updated: {limiter.tokens}")

    # Test 5: Get status
    print("\n5. Testing get_status:")
    status = limiter.get_status()
    print(f"   ✓ Status: {status['tokens']:.1f} tokens")
    print(f"   ✓ Max tokens: {status['tokens_max']}")
    print(f"   ✓ Refill rate: {status['refill_rate']:.4f} tokens/second")

    # Test 6: Retry with backoff
    print("\n6. Testing retry_with_backoff:")

    call_count = [0]

    def mock_api_call():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Simulated API error")
        return {"success": True}

    try:
        result = limiter.retry_with_backoff(mock_api_call, max_retries=5)
        print(f"   ✓ Function succeeded after {call_count[0]} attempts")
        print(f"   ✓ Result: {result}")
    except Exception as e:
        print(f"   ✗ Function failed: {e}")

    # Test 7: Reset
    print("\n7. Testing reset:")
    limiter.reset()
    status_after_reset = limiter.get_status()
    print(f"   ✓ Tokens after reset: {status_after_reset['tokens']:.1f}")

    print("\n✅ All tests completed")
