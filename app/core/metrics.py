from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

registry = CollectorRegistry()

REQUESTS_TOTAL = Counter(
    "sentinel_http_requests",
    "Total HTTP requests processed by Sentinel API.",
    labelnames=("method", "path", "status_code"),
    registry=registry,
)

REQUEST_LATENCY_SECONDS = Histogram(
    "sentinel_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=registry,
)

RATE_LIMIT_EVENTS_TOTAL = Counter(
    "sentinel_rate_limit_events",
    "Rate limit decisions for authenticated requests.",
    labelnames=("outcome",),
    registry=registry,
)

RATE_LIMIT_BACKEND_FAILURES_TOTAL = Counter(
    "sentinel_rate_limit_backend_failures",
    "Rate limit checks that failed open because Redis was unavailable.",
    registry=registry,
)


def record_request(
    *,
    method: str,
    path: str,
    status_code: int,
    latency_seconds: float,
) -> None:
    status = str(status_code)
    REQUESTS_TOTAL.labels(method=method, path=path, status_code=status).inc()
    REQUEST_LATENCY_SECONDS.labels(method=method, path=path).observe(latency_seconds)


def record_rate_limit(*, allowed: bool, backend_down: bool) -> None:
    outcome = "allowed" if allowed else "blocked"
    RATE_LIMIT_EVENTS_TOTAL.labels(outcome=outcome).inc()

    if backend_down:
        RATE_LIMIT_BACKEND_FAILURES_TOTAL.inc()


def render_prometheus_metrics() -> bytes:
    return generate_latest(registry)
