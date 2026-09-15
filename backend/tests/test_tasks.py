from __future__ import annotations

from .conftest import register


def _create_task(client, admin, **overrides):
    body = {
        "projectId": admin["project"]["id"],
        "boardId": admin["board"]["id"],
        "columnId": admin["columns"][0]["id"],
        "title": "Untitled task",
    }
    body.update(overrides)
    response = client.post("/api/tasks", json=body, headers=admin["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task_requires_title(client, admin):
    response = client.post(
        "/api/tasks",
        json={
            "projectId": admin["project"]["id"],
            "boardId": admin["board"]["id"],
            "columnId": admin["columns"][0]["id"],
            "title": "   ",
        },
        headers=admin["headers"],
    )
    assert response.status_code == 400


def test_task_key_is_prefixed_with_project_key_and_increments(client, admin):
    first = _create_task(client, admin, title="First")
    second = _create_task(client, admin, title="Second")
    assert first["key"] == "DEMO-1"
    assert second["key"] == "DEMO-2"


def test_list_tasks_filters(client, admin):
    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )

    unassigned = _create_task(client, admin, title="Fix payment bug", type="bug", priority="high")
    assigned = _create_task(
        client, admin, title="Write docs", assigneeId=bob["user"]["id"], priority="low"
    )

    by_search = client.get(
        f"/api/projects/{admin['project']['id']}/tasks",
        params={"search": "payment"},
        headers=admin["headers"],
    ).json()
    assert [t["id"] for t in by_search] == [unassigned["id"]]

    by_priority = client.get(
        f"/api/projects/{admin['project']['id']}/tasks",
        params={"priority": "high"},
        headers=admin["headers"],
    ).json()
    assert [t["id"] for t in by_priority] == [unassigned["id"]]

    by_unassigned = client.get(
        f"/api/projects/{admin['project']['id']}/tasks",
        params={"assigneeId": "unassigned"},
        headers=admin["headers"],
    ).json()
    assert [t["id"] for t in by_unassigned] == [unassigned["id"]]

    by_assignee = client.get(
        f"/api/projects/{admin['project']['id']}/tasks",
        params={"assigneeId": bob["user"]["id"]},
        headers=admin["headers"],
    ).json()
    assert [t["id"] for t in by_assignee] == [assigned["id"]]


def test_update_task_records_activity(client, admin):
    task = _create_task(client, admin, title="Needs triage", priority="low")

    response = client.patch(
        f"/api/tasks/{task['id']}", json={"priority": "urgent"}, headers=admin["headers"]
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"

    activity = client.get(f"/api/tasks/{task['id']}/activity", headers=admin["headers"]).json()
    messages = [a["message"] for a in activity]
    assert any("created" in m for m in messages)
    assert any("priority" in m for m in messages)


def test_move_task_reorders_columns(client, admin):
    todo_id = admin["columns"][0]["id"]
    in_progress_id = admin["columns"][1]["id"]

    t1 = _create_task(client, admin, title="One")
    t2 = _create_task(client, admin, title="Two")

    response = client.post(
        f"/api/tasks/{t1['id']}/move",
        json={"columnId": in_progress_id, "position": 0},
        headers=admin["headers"],
    )
    assert response.status_code == 200
    assert response.json()["columnId"] == in_progress_id
    assert response.json()["position"] == 0

    board_data = client.get(f"/api/boards/{admin['board']['id']}/data", headers=admin["headers"]).json()
    remaining_in_todo = [t for t in board_data["tasks"] if t["columnId"] == todo_id]
    assert [t["id"] for t in remaining_in_todo] == [t2["id"]]
    assert remaining_in_todo[0]["position"] == 0


def test_delete_task_cascades_comments_and_relations(client, admin):
    t1 = _create_task(client, admin, title="Primary")
    t2 = _create_task(client, admin, title="Related")

    client.post(f"/api/tasks/{t1['id']}/comments", json={"body": "hello"}, headers=admin["headers"])
    client.post(
        f"/api/tasks/{t1['id']}/relations",
        json={"relatedTaskId": t2["id"], "type": "blocks"},
        headers=admin["headers"],
    )

    response = client.delete(f"/api/tasks/{t1['id']}", headers=admin["headers"])
    assert response.status_code == 204

    assert client.get(f"/api/tasks/{t1['id']}", headers=admin["headers"]).status_code == 404
    # The inverse relation on the *other* task must be gone too.
    remaining_relations = client.get(f"/api/tasks/{t2['id']}/relations", headers=admin["headers"]).json()
    assert remaining_relations == []
