import pytest


@pytest.mark.anyio
async def test_notes_crud_flow(client, register_and_login):
    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/notes",
        json={"title": "Launch checklist", "body": "Write tests first."},
        headers=headers,
    )
    assert create_response.status_code == 201
    created_note = create_response.json()["data"]
    assert created_note["title"] == "Launch checklist"

    list_response = await client.get("/api/v1/notes", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1
    assert list_response.json()["meta"]["total"] == 1

    get_response = await client.get(
        f"/api/v1/notes/{created_note['id']}", headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["body"] == "Write tests first."

    delete_response = await client.delete(
        f"/api/v1/notes/{created_note['id']}", headers=headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True

    missing_response = await client.get(
        f"/api/v1/notes/{created_note['id']}", headers=headers
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "not_found"


@pytest.mark.anyio
async def test_users_cannot_read_each_others_notes(client, register_and_login):
    owner_token = await register_and_login()
    other_token = await register_and_login(
        email="other@example.com",
        password="correct-password",
    )

    create_response = await client.post(
        "/api/v1/notes",
        json={"title": "Private", "body": "Only mine."},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    note_id = create_response.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/notes/{note_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_notes_are_paginated(client, register_and_login):
    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    for index in range(3):
        response = await client.post(
            "/api/v1/notes",
            json={"title": f"Note {index}", "body": "Paged body"},
            headers=headers,
        )
        assert response.status_code == 201

    page_response = await client.get(
        "/api/v1/notes?limit=2&offset=0",
        headers=headers,
    )

    assert page_response.status_code == 200
    body = page_response.json()
    assert len(body["data"]) == 2
    assert body["meta"] == {
        "limit": 2,
        "offset": 0,
        "total": 3,
        "next_offset": 2,
    }


@pytest.mark.anyio
async def test_create_note_is_idempotent_with_idempotency_key(
    client, register_and_login
):
    token = await register_and_login()
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "create-launch-checklist",
    }

    first_response = await client.post(
        "/api/v1/notes",
        json={"title": "Launch checklist", "body": "Write tests first."},
        headers=headers,
    )
    second_response = await client.post(
        "/api/v1/notes",
        json={"title": "Different title", "body": "Should not duplicate."},
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.json()["data"]["id"] == first_response.json()["data"]["id"]

    list_response = await client.get("/api/v1/notes", headers=headers)
    assert list_response.json()["meta"]["total"] == 1
