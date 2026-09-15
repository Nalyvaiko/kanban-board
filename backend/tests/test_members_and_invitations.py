from __future__ import annotations

from .conftest import auth_header, register


def test_add_member_requires_existing_account(client, admin):
    response = client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "ghost@example.com", "role": "member"},
        headers=admin["headers"],
    )
    assert response.status_code == 404


def test_cannot_remove_the_last_admin(client, admin):
    response = client.delete(
        f"/api/projects/{admin['project']['id']}/members/{admin['user']['id']}",
        headers=admin["headers"],
    )
    assert response.status_code == 400


def test_cannot_demote_the_last_admin(client, admin):
    response = client.patch(
        f"/api/projects/{admin['project']['id']}/members/{admin['user']['id']}",
        json={"role": "member"},
        headers=admin["headers"],
    )
    assert response.status_code == 400


def test_removing_a_member_unassigns_their_tasks(client, admin):
    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )
    task = client.post(
        "/api/tasks",
        json={
            "projectId": admin["project"]["id"],
            "boardId": admin["board"]["id"],
            "columnId": admin["columns"][0]["id"],
            "title": "Assigned to Bob",
            "assigneeId": bob["user"]["id"],
        },
        headers=admin["headers"],
    ).json()

    response = client.delete(
        f"/api/projects/{admin['project']['id']}/members/{bob['user']['id']}", headers=admin["headers"]
    )
    assert response.status_code == 204

    updated_task = client.get(f"/api/tasks/{task['id']}", headers=admin["headers"]).json()
    assert updated_task["assigneeId"] is None


def test_invitation_flow(client, admin):
    dave = register(client, "Dave", "dave@example.com")

    invite = client.post(
        f"/api/projects/{admin['project']['id']}/invitations",
        json={"email": "dave@example.com", "role": "member"},
        headers=admin["headers"],
    )
    assert invite.status_code == 201
    invitation = invite.json()

    duplicate = client.post(
        f"/api/projects/{admin['project']['id']}/invitations",
        json={"email": "dave@example.com", "role": "member"},
        headers=admin["headers"],
    )
    assert duplicate.status_code == 409

    mine = client.get("/api/invitations/mine", headers=auth_header(dave["token"])).json()
    assert len(mine) == 1
    assert mine[0]["project"]["id"] == admin["project"]["id"]

    someone_elses = register(client, "Mallory", "mallory@example.com")
    wrong_account = client.post(
        f"/api/invitations/{invitation['id']}/accept", headers=auth_header(someone_elses["token"])
    )
    assert wrong_account.status_code == 403

    accepted = client.post(
        f"/api/invitations/{invitation['id']}/accept", headers=auth_header(dave["token"])
    )
    assert accepted.status_code == 204

    role = client.get(
        f"/api/projects/{admin['project']['id']}/my-role", headers=auth_header(dave["token"])
    ).json()
    assert role["role"] == "member"


def test_revoke_invitation_requires_admin(client, admin):
    invitation = client.post(
        f"/api/projects/{admin['project']['id']}/invitations",
        json={"email": "dave@example.com", "role": "viewer"},
        headers=admin["headers"],
    ).json()

    bob = register(client, "Bob", "bob@example.com")
    client.post(
        f"/api/projects/{admin['project']['id']}/members",
        json={"email": "bob@example.com", "role": "member"},
        headers=admin["headers"],
    )
    denied = client.delete(
        f"/api/invitations/{invitation['id']}", headers=auth_header(bob["token"])
    )
    assert denied.status_code == 403

    allowed = client.delete(f"/api/invitations/{invitation['id']}", headers=admin["headers"])
    assert allowed.status_code == 204
