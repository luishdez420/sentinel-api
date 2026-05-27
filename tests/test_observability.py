import json
import logging

import pytest

from app.core.logging import JsonFormatter


@pytest.mark.anyio
async def test_request_id_is_returned(client):
    response = await client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"


@pytest.mark.anyio
async def test_metrics_endpoint_exposes_prometheus_metrics(client):
    await client.get("/health")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    body = response.text
    assert "sentinel_http_requests_total" in body
    assert "sentinel_http_request_duration_seconds_bucket" in body


@pytest.mark.anyio
async def test_rate_limit_metrics_are_recorded(client, register_and_login, monkeypatch):
    from app.core import rate_limit

    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 1)

    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    await client.get("/auth/me", headers=headers)
    await client.get("/auth/me", headers=headers)
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert 'sentinel_rate_limit_events_total{outcome="allowed"}' in response.text
    assert 'sentinel_rate_limit_events_total{outcome="blocked"}' in response.text


def test_json_formatter_outputs_structured_log_line():
    record = logging.LogRecord(
        name="sentinel",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "http_request"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 200
