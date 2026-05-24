import pytest


@pytest.mark.anyio
async def test_register_login_and_get_current_user(client, register_and_login):
    token = await register_and_login()

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


@pytest.mark.anyio
async def test_register_rejects_short_password(client):
    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_duplicate_registration_is_rejected(client, register_and_login):
    await register_and_login()

    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "correct-password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
