# app/core/metrics.py
from __future__ import annotations

import math
import threading
from collections import deque

_lock = threading.Lock()

_requests_total = 0
_errors_total = 0          # 5xx only
_client_errors_total = 0   # 4xx (optional but great)
_rate_limited_total = 0    # 429 only

_latencies_ms = deque(maxlen=2000)


def record_request(*, status_code: int, latency_ms: int) -> None:
    global _requests_total, _errors_total, _client_errors_total, _rate_limited_total

    with _lock:
        _requests_total += 1
        _latencies_ms.append(int(latency_ms))

        if 500 <= status_code:
            _errors_total += 1
        elif 400 <= status_code:
            _client_errors_total += 1

        if status_code == 429:
            _rate_limited_total += 1


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    values.sort()
    k = (len(values) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return int(round(d0 + d1))


def get_metrics() -> dict:
    with _lock:
        vals = list(_latencies_ms)
        p50 = _percentile(vals, 0.50)
        p95 = _percentile(vals, 0.95)
        mx = max(vals) if vals else 0

        return {
            "requests_total": _requests_total,
            "errors_total": _errors_total,  # 5xx only
            "client_errors_total": _client_errors_total,  # 4xx
            "rate_limited_total": _rate_limited_total,  # 429
            "latency_ms": {"p50": p50, "p95": p95, "max": mx},
        }