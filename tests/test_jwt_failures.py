import pytest


@pytest.mark.anyio
async def test_protected_route_rejects_missing_token(client):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Missing bearer token"


@pytest.mark.anyio
async def test_protected_route_rejects_invalid_token(client):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid token"
