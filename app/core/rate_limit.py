from __future__ import annotations

import os
import time
import logging
import redis

logger = logging.getLogger("rlapi")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "20"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

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
        logger.warning("rate_limit_backend_down", extra={"event": "rate_limit", "user_id": user_id})
        return (True, RATE_LIMIT, None, backend_down)