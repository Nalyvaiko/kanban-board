from __future__ import annotations

from .conftest import auth_header, register


def _create_task(client, admin, title="Task"):
    body = {
        "projectId": admin["project"]["id"],
        "boardId": admin["board"]["id"],
        "columnId": admin["columns"][0]["id"],
        "title": title,
    }
    return client.post("/api/tasks", json=body, headers=admin["headers"]).json()


def test_only_author_can_edit_or_delete_their_comment(client, admin):
    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )
    bob_headers = auth_header(bob["token"])

    task = _create_task(client, admin)
    comment = client.post(
        f"/api/tasks/{task['id']}/comments", json={"body": "Alice's comment"}, headers=admin["headers"]
    ).json()

    denied_edit = client.patch(
        f"/api/comments/{comment['id']}", json={"body": "hijacked"}, headers=bob_headers
    )
    assert denied_edit.status_code == 403

    denied_delete = client.delete(f"/api/comments/{comment['id']}", headers=bob_headers)
    assert denied_delete.status_code == 403

    allowed_edit = client.patch(
        f"/api/comments/{comment['id']}", json={"body": "edited"}, headers=admin["headers"]
    )
    assert allowed_edit.status_code == 200
    assert allowed_edit.json()["body"] == "edited"


def test_project_admin_can_delete_others_comments(client, admin):
    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )
    task = _create_task(client, admin)
    comment = client.post(
        f"/api/tasks/{task['id']}/comments", json={"body": "Bob's comment"}, headers=auth_header(bob["token"])
    ).json()

    response = client.delete(f"/api/comments/{comment['id']}", headers=admin["headers"])
    assert response.status_code == 204


def test_empty_comment_is_rejected(client, admin):
    task = _create_task(client, admin)
    response = client.post(
        f"/api/tasks/{task['id']}/comments", json={"body": "   "}, headers=admin["headers"]
    )
    assert response.status_code == 400


def test_relation_creates_inverse_and_rejects_self_link(client, admin):
    a = _create_task(client, admin, title="A")
    b = _create_task(client, admin, title="B")

    self_link = client.post(
        f"/api/tasks/{a['id']}/relations",
        json={"relatedTaskId": a["id"], "type": "blocks"},
        headers=admin["headers"],
    )
    assert self_link.status_code == 400

    created = client.post(
        f"/api/tasks/{a['id']}/relations",
        json={"relatedTaskId": b["id"], "type": "blocks"},
        headers=admin["headers"],
    )
    assert created.status_code == 201
    assert created.json()["type"] == "blocks"
    assert created.json()["relatedTask"]["id"] == b["id"]

    b_relations = client.get(f"/api/tasks/{b['id']}/relations", headers=admin["headers"]).json()
    assert len(b_relations) == 1
    assert b_relations[0]["type"] == "blocked_by"
    assert b_relations[0]["relatedTask"]["id"] == a["id"]

    duplicate = client.post(
        f"/api/tasks/{a['id']}/relations",
        json={"relatedTaskId": b["id"], "type": "blocks"},
        headers=admin["headers"],
    )
    assert duplicate.status_code == 409


def test_deleting_relation_removes_both_directions(client, admin):
    a = _create_task(client, admin, title="A")
    b = _create_task(client, admin, title="B")
    relation = client.post(
        f"/api/tasks/{a['id']}/relations",
        json={"relatedTaskId": b["id"], "type": "relates_to"},
        headers=admin["headers"],
    ).json()

    response = client.delete(f"/api/relations/{relation['id']}", headers=admin["headers"])
    assert response.status_code == 204
    assert client.get(f"/api/tasks/{a['id']}/relations", headers=admin["headers"]).json() == []
    assert client.get(f"/api/tasks/{b['id']}/relations", headers=admin["headers"]).json() == []


def test_labels_require_admin_and_reject_duplicates(client, admin):
    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )

    denied = client.post(
        f"/api/projects/{admin['project']['id']}/labels",
        json={"name": "backend"},
        headers=auth_header(bob["token"]),
    )
    assert denied.status_code == 403

    created = client.post(
        f"/api/projects/{admin['project']['id']}/labels", json={"name": "Backend"}, headers=admin["headers"]
    )
    assert created.status_code == 201
    assert created.json()["name"] == "backend"  # stored lowercase

    duplicate = client.post(
        f"/api/projects/{admin['project']['id']}/labels", json={"name": "backend"}, headers=admin["headers"]
    )
    assert duplicate.status_code == 409


def test_deleting_label_removes_it_from_tasks(client, admin):
    label = client.post(
        f"/api/projects/{admin['project']['id']}/labels", json={"name": "urgent"}, headers=admin["headers"]
    ).json()
    task = _create_task(client, admin)
    client.patch(f"/api/tasks/{task['id']}", json={"labelIds": [label["id"]]}, headers=admin["headers"])

    response = client.delete(f"/api/labels/{label['id']}", headers=admin["headers"])
    assert response.status_code == 204

    updated_task = client.get(f"/api/tasks/{task['id']}", headers=admin["headers"]).json()
    assert updated_task["labelIds"] == []
