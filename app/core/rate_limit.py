from __future__ import annotations

import logging
import time

import redis

from app.core.config import settings

logger = logging.getLogger("sentinel")

RATE_LIMIT = settings.rate_limit_per_minute
API_KEY_RATE_LIMIT = settings.api_key_rate_limit_per_minute
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


def check_rate_limit(
    subject_id: object,
    *,
    subject_type: str = "user",
    limit: int | None = None,
) -> tuple[bool, int, int | None, bool, int]:
    """
    Returns: (allowed, remaining, retry_after_seconds, backend_down, limit)
    """
    active_limit = limit or RATE_LIMIT
    now = int(time.time())
    bucket = now // WINDOW_SECONDS
    window_reset_at = (bucket + 1) * WINDOW_SECONDS
    ttl_seconds = max(window_reset_at - now, 1)
    key = f"rl:{subject_type}:{subject_id}:{bucket}"
    backend_down = False

    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, ttl_seconds)

        remaining = max(active_limit - count, 0)

        if count > active_limit:
            ttl = redis_client.ttl(key)
            retry_after = ttl if ttl and ttl > 0 else ttl_seconds
            return (False, 0, retry_after, backend_down, active_limit)

        return (True, remaining, None, backend_down, active_limit)

    except Exception:
        # FAIL-OPEN: if Redis is down, allow the request but log it
        backend_down = True
        logger.warning(
            "rate_limit_backend_down",
            extra={
                "event": "rate_limit",
                "subject_type": subject_type,
                "subject_id": str(subject_id),
            },
        )
        return (True, active_limit, None, backend_down, active_limit)
