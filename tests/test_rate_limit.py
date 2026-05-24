import pytest


@pytest.mark.anyio
async def test_authenticated_requests_are_rate_limited(
    client, register_and_login, monkeypatch
):
    from app.core import rate_limit

    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 2)

    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    first_response = await client.get("/auth/me", headers=headers)
    second_response = await client.get("/auth/me", headers=headers)
    third_response = await client.get("/auth/me", headers=headers)

    assert first_response.status_code == 200
    assert first_response.headers["X-RateLimit-Remaining"] == "1"
    assert second_response.status_code == 200
    assert second_response.headers["X-RateLimit-Remaining"] == "0"
    assert third_response.status_code == 429
    assert third_response.headers["Retry-After"]
