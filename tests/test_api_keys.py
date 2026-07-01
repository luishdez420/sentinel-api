import pytest

from app.core.api_keys import verify_api_key
from app.db.models import ApiKey, AuditLog


@pytest.mark.anyio
async def test_user_can_create_list_and_revoke_api_key(client, register_and_login):
    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "ci-script"},
        headers=headers,
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["api_key"].startswith(f"sentinel_{created['prefix']}_")

    list_response = await client.get("/api/v1/api-keys", headers=headers)
    listed = list_response.json()["data"][0]

    assert list_response.status_code == 200
    assert listed["name"] == "ci-script"
    assert listed["prefix"] == created["prefix"]
    assert "api_key" not in listed

    revoke_response = await client.delete(
        f"/api/v1/api-keys/{created['id']}",
        headers=headers,
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["data"]["is_active"] is False
    assert revoke_response.json()["data"]["revoked_at"] is not None


@pytest.mark.anyio
async def test_api_key_is_hashed_and_can_authenticate_protected_routes(
    client, register_and_login, db_engine
):
    token = await register_and_login()

    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "integration"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_response.json()["data"]["api_key"]
    prefix = create_response.json()["data"]["prefix"]

    with db_engine.begin() as connection:
        row = (
            connection.execute(ApiKey.__table__.select().where(ApiKey.prefix == prefix))
            .mappings()
            .one()
        )

    assert row["key_hash"] != api_key
    assert verify_api_key(api_key, row["key_hash"])

    me_response = await client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})

    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "user@example.com"
    assert me_response.headers["X-RateLimit-Limit"] == "100"

    with db_engine.begin() as connection:
        used_row = (
            connection.execute(ApiKey.__table__.select().where(ApiKey.prefix == prefix))
            .mappings()
            .one()
        )

    assert used_row["last_used_at"] is not None


@pytest.mark.anyio
async def test_revoked_api_key_cannot_authenticate(client, register_and_login):
    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/api-keys", json={"name": "old-key"}, headers=headers
    )
    created = create_response.json()["data"]
    await client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers)

    response = await client.get(
        "/api/v1/auth/me", headers={"X-API-Key": created["api_key"]}
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid API key"


@pytest.mark.anyio
async def test_api_key_rate_limit_and_audit_logs(
    client, register_and_login, monkeypatch, db_engine
):
    from app.core import rate_limit

    monkeypatch.setattr(rate_limit, "API_KEY_RATE_LIMIT", 1)

    token = await register_and_login()
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "rate-limited-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_response.json()["data"]["api_key"]

    first_response = await client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
    second_response = await client.get(
        "/api/v1/auth/me", headers={"X-API-Key": api_key}
    )

    assert first_response.status_code == 200
    assert first_response.headers["X-RateLimit-Limit"] == "1"
    assert first_response.headers["X-RateLimit-Remaining"] == "0"
    assert second_response.status_code == 429
    assert second_response.headers["Retry-After"]

    with db_engine.begin() as connection:
        event_types = [
            row["event_type"]
            for row in connection.execute(AuditLog.__table__.select()).mappings().all()
        ]

    assert "api_key_created" in event_types
    assert "rate_limit_exceeded" in event_types


@pytest.mark.anyio
async def test_invalid_api_key_attempt_is_audited(client, db_engine):
    response = await client.get(
        "/api/v1/auth/me", headers={"X-API-Key": "sentinel_missing_invalid"}
    )

    assert response.status_code == 401

    with db_engine.begin() as connection:
        event_types = [
            row["event_type"]
            for row in connection.execute(AuditLog.__table__.select()).mappings().all()
        ]

    assert "api_key_auth_failed" in event_types


@pytest.mark.anyio
async def test_api_key_metrics_are_exposed(client, register_and_login):
    token = await register_and_login()
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "metrics-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_response.json()["data"]["api_key"]

    await client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
    await client.get("/api/v1/auth/me", headers={"X-API-Key": "sentinel_bad_value"})

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "api_key_auth_success_total" in response.text
    assert "api_key_auth_failed_total" in response.text
    assert "api_keys_created_total" in response.text
    assert "audit_logs_written_total" in response.text
