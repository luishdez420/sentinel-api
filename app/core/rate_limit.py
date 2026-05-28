from __future__ import annotations

import logging

import redis

from app.core.config import settings

logger = logging.getLogger("sentinel")

RATE_LIMIT = settings.rate_limit_per_minute
WINDOW_SECONDS = 60

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


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
