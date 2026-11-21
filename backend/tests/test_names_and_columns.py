from __future__ import annotations

import pytest


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_names_are_rejected(client, admin, blank):
    headers = admin["headers"]
    project_id = admin["project"]["id"]
    column_id = admin["columns"][0]["id"]

    assert client.patch("/api/auth/me", json={"name": blank}, headers=headers).status_code == 400
    assert (
        client.patch(f"/api/projects/{project_id}", json={"name": blank}, headers=headers).status_code
        == 400
    )
    assert (
        client.post(f"/api/projects/{project_id}/boards", json={"name": blank}, headers=headers).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/boards/{admin['board']['id']}/columns", json={"name": blank}, headers=headers
        ).status_code
        == 400
    )
    assert client.patch(f"/api/columns/{column_id}", json={"name": blank}, headers=headers).status_code == 400

    # Nothing was changed by the rejected requests.
    assert client.get("/api/auth/me", headers=headers).json()["name"] == "Alice Admin"
    assert client.get(f"/api/projects/{project_id}", headers=headers).json()["name"] == "Demo Project"
    assert len(client.get(f"/api/projects/{project_id}/boards", headers=headers).json()) == 1


def test_names_are_stored_trimmed(client, admin):
    headers = admin["headers"]
    project_id = admin["project"]["id"]

    assert client.patch("/api/auth/me", json={"name": "  Alice  "}, headers=headers).json()["name"] == "Alice"
    project = client.patch(f"/api/projects/{project_id}", json={"name": " Renamed "}, headers=headers).json()
    assert project["name"] == "Renamed"
    board = client.post(f"/api/projects/{project_id}/boards", json={"name": " Second "}, headers=headers).json()
    assert board["name"] == "Second"
    column = client.post(
        f"/api/boards/{admin['board']['id']}/columns", json={"name": " QA "}, headers=headers
    ).json()
    assert column["name"] == "QA"
    renamed = client.patch(f"/api/columns/{column['id']}", json={"name": " Testing "}, headers=headers).json()
    assert renamed["name"] == "Testing"


def test_delete_column_appends_its_tasks_without_position_gaps(client, admin):
    headers = admin["headers"]
    first, second = admin["columns"][0]["id"], admin["columns"][1]["id"]

    def create(title, column_id):
        response = client.post(
            "/api/tasks",
            json={
                "projectId": admin["project"]["id"],
                "boardId": admin["board"]["id"],
                "columnId": column_id,
                "title": title,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    kept = [create("Kept 1", first), create("Kept 2", first)]
    moved = [create("Moved 1", second), create("Moved 2", second), create("Moved 3", second)]

    assert client.delete(f"/api/columns/{second}", headers=headers).status_code == 204

    data = client.get(f"/api/boards/{admin['board']['id']}/data", headers=headers).json()
    in_first = [(t["id"], t["position"]) for t in data["tasks"] if t["columnId"] == first]
    assert in_first == [(task_id, index) for index, task_id in enumerate(kept + moved)]
