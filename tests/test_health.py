import pytest


@pytest.mark.anyio
async def test_health_reports_ready_dependencies(client):
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db": "ok",
        "rate_limit_backend": "redis",
        "rate_limit": "ok",
    }


@pytest.mark.anyio
async def test_liveness_does_not_require_dependencies(client):
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
