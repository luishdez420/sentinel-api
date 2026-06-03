from __future__ import annotations

import logging
import time

import redis

from app.core.config import settings

logger = logging.getLogger("sentinel")

RATE_LIMIT = settings.rate_limit_per_minute
WINDOW_SECONDS = 60


class MemoryRateLimitStore:
    backend_name = "memory"

    def __init__(self) -> None:
        self._values: dict[str, tuple[int, float | None]] = {}

    def _prune(self, key: str) -> None:
        value = self._values.get(key)
        if value is None:
            return

        _, expires_at = value
        if expires_at is not None and expires_at <= time.monotonic():
            self._values.pop(key, None)

    def incr(self, key: str) -> int:
        self._prune(key)
        count, expires_at = self._values.get(key, (0, None))
        count += 1
        self._values[key] = (count, expires_at)
        return count

    def expire(self, key: str, seconds: int) -> None:
        self._prune(key)
        count, _ = self._values.get(key, (0, None))
        self._values[key] = (count, time.monotonic() + seconds)

    def ttl(self, key: str) -> int:
        self._prune(key)
        value = self._values.get(key)
        if value is None:
            return -2

        _, expires_at = value
        if expires_at is None:
            return -1
        return max(int(expires_at - time.monotonic()), 0)

    def flushdb(self) -> None:
        self._values.clear()

    def ping(self) -> bool:
        return True


def _build_rate_limit_store():
    if settings.redis_url == "memory://":
        return MemoryRateLimitStore()

    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    client.backend_name = "redis"
    return client


redis_client = _build_rate_limit_store()
rate_limit_backend = getattr(redis_client, "backend_name", "redis")


def check_rate_limit(user_id: int) -> tuple[bool, int, int | None, bool]:
    """
    Returns: (allowed, remaining, retry_after_seconds, backend_down)
    """
    key = f"rl:{user_id}"
    backend_down = False

    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, WINDOW_SECONDS)

        remaining = max(RATE_LIMIT - count, 0)

        if count > RATE_LIMIT:
            ttl = redis_client.ttl(key)
            retry_after = ttl if ttl and ttl > 0 else WINDOW_SECONDS
            return (False, 0, retry_after, backend_down)

        return (True, remaining, None, backend_down)

    except Exception:
        # FAIL-OPEN: if Redis is down, allow the request but log it
        backend_down = True
        logger.warning(
            "rate_limit_backend_down", extra={"event": "rate_limit", "user_id": user_id}
        )
        return (True, RATE_LIMIT, None, backend_down)
