from __future__ import annotations


def _create_label(client, admin, name):
    response = client.post(
        f"/api/projects/{admin['project']['id']}/labels",
        json={"name": name},
        headers=admin["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_rename_label_rejects_blank_name(client, admin):
    label = _create_label(client, admin, "frontend")
    response = client.patch(
        f"/api/labels/{label['id']}", json={"name": "   "}, headers=admin["headers"]
    )
    assert response.status_code == 400


def test_rename_label_rejects_duplicate_name(client, admin):
    _create_label(client, admin, "frontend")
    backend = _create_label(client, admin, "backend")
    response = client.patch(
        f"/api/labels/{backend['id']}", json={"name": " Frontend "}, headers=admin["headers"]
    )
    assert response.status_code == 409


def test_rename_label_to_its_own_name_is_allowed(client, admin):
    label = _create_label(client, admin, "frontend")
    response = client.patch(
        f"/api/labels/{label['id']}", json={"name": "FRONTEND"}, headers=admin["headers"]
    )
    assert response.status_code == 200
    assert response.json()["name"] == "frontend"
