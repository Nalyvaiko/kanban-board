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


def _other_project(client, admin):
    """A second project owned by the same admin, with its board and columns."""
    headers = admin["headers"]
    project = client.post(
        "/api/projects", json={"name": "Other Project", "key": "OTH"}, headers=headers
    ).json()
    board = client.get(f"/api/projects/{project['id']}/boards", headers=headers).json()[0]
    columns = client.get(f"/api/boards/{board['id']}/data", headers=headers).json()["columns"]
    return {"project": project, "board": board, "columns": columns}


def _post_task(client, admin, **overrides):
    body = {
        "projectId": admin["project"]["id"],
        "boardId": admin["board"]["id"],
        "columnId": admin["columns"][0]["id"],
        "title": "Untitled task",
    }
    body.update(overrides)
    return client.post("/api/tasks", json=body, headers=admin["headers"])


def test_create_task_rejects_board_from_another_project(client, admin):
    other = _other_project(client, admin)
    response = _post_task(
        client, admin, boardId=other["board"]["id"], columnId=other["columns"][0]["id"]
    )
    assert response.status_code == 400
    tasks = client.get(f"/api/projects/{admin['project']['id']}/tasks", headers=admin["headers"])
    assert tasks.json() == []


def test_create_task_rejects_column_from_another_board(client, admin):
    other = _other_project(client, admin)
    response = _post_task(client, admin, columnId=other["columns"][0]["id"])
    assert response.status_code == 400


def test_task_assignee_must_be_project_member(client, admin):
    outsider = register(client, "Mallory", "mallory@example.com")
    assert _post_task(client, admin, assigneeId=outsider["user"]["id"]).status_code == 400

    task = _create_task(client, admin)
    response = client.patch(
        f"/api/tasks/{task['id']}",
        json={"assigneeId": outsider["user"]["id"]},
        headers=admin["headers"],
    )
    assert response.status_code == 400

    # Clearing the assignee is still allowed.
    response = client.patch(
        f"/api/tasks/{task['id']}", json={"assigneeId": None}, headers=admin["headers"]
    )
    assert response.status_code == 200
    assert response.json()["assigneeId"] is None


def test_task_labels_must_belong_to_project(client, admin):
    other = _other_project(client, admin)
    foreign_label = client.post(
        f"/api/projects/{other['project']['id']}/labels",
        json={"name": "foreign"},
        headers=admin["headers"],
    ).json()
    own_label = client.post(
        f"/api/projects/{admin['project']['id']}/labels",
        json={"name": "own"},
        headers=admin["headers"],
    ).json()

    assert _post_task(client, admin, labelIds=[foreign_label["id"]]).status_code == 400

    # Duplicate ids collapse to one.
    task = _create_task(client, admin, labelIds=[own_label["id"], own_label["id"]])
    assert task["labelIds"] == [own_label["id"]]

    response = client.patch(
        f"/api/tasks/{task['id']}",
        json={"labelIds": ["label_does_not_exist"]},
        headers=admin["headers"],
    )
    assert response.status_code == 400


def test_update_task_rejects_blank_title_and_strips_whitespace(client, admin):
    task = _create_task(client, admin, title="Original")

    response = client.patch(
        f"/api/tasks/{task['id']}", json={"title": "   "}, headers=admin["headers"]
    )
    assert response.status_code == 400

    response = client.patch(
        f"/api/tasks/{task['id']}", json={"title": "  Renamed  "}, headers=admin["headers"]
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


def test_update_task_column_change_keeps_positions_contiguous(client, admin):
    todo, doing = admin["columns"][0]["id"], admin["columns"][1]["id"]
    a = _create_task(client, admin, title="A", columnId=todo)
    b = _create_task(client, admin, title="B", columnId=todo)
    c = _create_task(client, admin, title="C", columnId=todo)
    existing = _create_task(client, admin, title="Already there", columnId=doing)

    response = client.patch(
        f"/api/tasks/{a['id']}", json={"columnId": doing}, headers=admin["headers"]
    )
    assert response.status_code == 200

    data = client.get(f"/api/boards/{admin['board']['id']}/data", headers=admin["headers"]).json()
    by_column: dict[str, list[tuple[str, int]]] = {}
    for t in data["tasks"]:
        by_column.setdefault(t["columnId"], []).append((t["id"], t["position"]))

    assert by_column[todo] == [(b["id"], 0), (c["id"], 1)]
    assert by_column[doing] == [(existing["id"], 0), (a["id"], 1)]
