from __future__ import annotations

from .conftest import auth_header, register


def test_create_project_makes_caller_admin_with_default_board(client, admin):
    project = admin["project"]
    assert project["key"] == "DEMO"

    role_response = client.get(f"/api/projects/{project['id']}/my-role", headers=admin["headers"])
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "admin"

    assert len(admin["columns"]) == 4
    assert [c["name"] for c in admin["columns"]] == ["To Do", "In Progress", "Review", "Done"]


def test_duplicate_project_key_is_rejected(client):
    session = register(client, "Alice", "alice@example.com")
    headers = auth_header(session["token"])
    client.post("/api/projects", json={"name": "First", "key": "DUP"}, headers=headers)
    response = client.post("/api/projects", json={"name": "Second", "key": "DUP"}, headers=headers)
    assert response.status_code == 409


def test_project_key_falls_back_to_slug_of_name(client):
    session = register(client, "Alice", "alice@example.com")
    headers = auth_header(session["token"])
    response = client.post("/api/projects", json={"name": "Zeta One!!"}, headers=headers)
    assert response.status_code == 201
    # Non-alphanumerics are stripped and the key is capped to a short,
    # Jira-style prefix.
    assert response.json()["key"] == "ZETAON"


def test_non_member_cannot_read_project(client):
    session = register(client, "Alice", "alice@example.com")
    headers = auth_header(session["token"])
    project = client.post("/api/projects", json={"name": "Private", "key": "PRIV"}, headers=headers).json()

    other = register(client, "Mallory", "mallory@example.com")
    response = client.get(f"/api/projects/{project['id']}", headers=auth_header(other["token"]))
    assert response.status_code == 403


def test_only_admin_can_update_project(client):
    admin_session = register(client, "Alice", "alice@example.com")
    admin_headers = auth_header(admin_session["token"])
    project = client.post(
        "/api/projects", json={"name": "Team Project", "key": "TEAM"}, headers=admin_headers
    ).json()

    member_session = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{project['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin_headers,
    )
    member_headers = auth_header(member_session["token"])

    forbidden = client.patch(
        f"/api/projects/{project['id']}", json={"name": "Renamed"}, headers=member_headers
    )
    assert forbidden.status_code == 403

    allowed = client.patch(
        f"/api/projects/{project['id']}", json={"name": "Renamed"}, headers=admin_headers
    )
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "Renamed"


def test_viewer_cannot_create_task_but_member_can(client):
    admin_session = register(client, "Alice", "alice@example.com")
    admin_headers = auth_header(admin_session["token"])
    project = client.post(
        "/api/projects", json={"name": "Viewer Test", "key": "VIEW"}, headers=admin_headers
    ).json()
    board = client.get(f"/api/projects/{project['id']}/boards", headers=admin_headers).json()[0]
    column = client.get(f"/api/boards/{board['id']}/data", headers=admin_headers).json()["columns"][0]

    viewer_session = register(client, "Carol", "carol@example.com")
    client.post(
        f"/api/projects/{project['id']}/members",
        json={"email": "carol@example.com", "role": "viewer"},
        headers=admin_headers,
    )
    viewer_headers = auth_header(viewer_session["token"])

    task_body = {
        "projectId": project["id"],
        "boardId": board["id"],
        "columnId": column["id"],
        "title": "Should fail for viewer",
    }
    denied = client.post("/api/tasks", json=task_body, headers=viewer_headers)
    assert denied.status_code == 403

    allowed = client.post("/api/tasks", json=task_body, headers=admin_headers)
    assert allowed.status_code == 201


def test_delete_project_requires_admin_and_cascades(client):
    admin_session = register(client, "Alice", "alice@example.com")
    admin_headers = auth_header(admin_session["token"])
    project = client.post(
        "/api/projects", json={"name": "Doomed", "key": "DOOM"}, headers=admin_headers
    ).json()
    board = client.get(f"/api/projects/{project['id']}/boards", headers=admin_headers).json()[0]
    column = client.get(f"/api/boards/{board['id']}/data", headers=admin_headers).json()["columns"][0]
    client.post(
        "/api/tasks",
        json={
            "projectId": project["id"],
            "boardId": board["id"],
            "columnId": column["id"],
            "title": "A task in a doomed project",
        },
        headers=admin_headers,
    )

    member_session = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{project['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin_headers,
    )
    denied = client.delete(f"/api/projects/{project['id']}", headers=auth_header(member_session["token"]))
    assert denied.status_code == 403

    response = client.delete(f"/api/projects/{project['id']}", headers=admin_headers)
    assert response.status_code == 204
    assert client.get(f"/api/projects/{project['id']}", headers=admin_headers).status_code == 404
    assert client.get(f"/api/boards/{board['id']}/data", headers=admin_headers).status_code == 404
