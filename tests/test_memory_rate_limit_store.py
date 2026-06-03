from app.core.rate_limit import MemoryRateLimitStore


def test_memory_rate_limit_store_supports_redis_like_operations():
    store = MemoryRateLimitStore()

    assert store.ping() is True
    assert store.incr("rl:1") == 1
    store.expire("rl:1", 60)
    assert store.incr("rl:1") == 2
    assert store.ttl("rl:1") > 0

    store.flushdb()
    assert store.ttl("rl:1") == -2
