import pytest


@pytest.mark.anyio
async def test_notes_crud_flow(client, register_and_login):
    token = await register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/notes",
        json={"title": "Launch checklist", "body": "Write tests first."},
        headers=headers,
    )
    assert create_response.status_code == 201
    created_note = create_response.json()
    assert created_note["title"] == "Launch checklist"

    list_response = await client.get("/notes", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = await client.get(f"/notes/{created_note['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["body"] == "Write tests first."

    delete_response = await client.delete(
        f"/notes/{created_note['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/notes/{created_note['id']}", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_users_cannot_read_each_others_notes(client, register_and_login):
    owner_token = await register_and_login()
    other_token = await register_and_login(
        email="other@example.com",
        password="correct-password",
    )

    create_response = await client.post(
        "/notes",
        json={"title": "Private", "body": "Only mine."},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    note_id = create_response.json()["id"]

    response = await client.get(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
