"""A request is all or nothing: anything a handler wrote is rolled back if
the request ends in an error response, not only on an unhandled exception.

No production endpoint is known to write and then fail today, so these use
throwaway routes that do exactly that, registered on the real app (so they
go through the real session middleware) and removed afterwards.
"""

from __future__ import annotations

import pytest

from kanban_backend.errors import ApiError
from kanban_backend.main import app
from kanban_backend.models import Label
from kanban_backend.store import store


@pytest.fixture()
def route(client):
    added = []

    def add(path, endpoint, methods=("POST",)):
        app.router.add_api_route(path, endpoint, methods=list(methods))
        added.append(app.router.routes[-1])

    yield add
    for r in added:
        app.router.routes.remove(r)


def _write_label(project_id: str, name: str) -> None:
    store.labels[f"label_{name}"] = Label(id=f"label_{name}", projectId=project_id, name=name, color="#000000")


def _label_names(client, admin):
    labels = client.get(f"/api/projects/{admin['project']['id']}/labels", headers=admin["headers"]).json()
    return sorted(label["name"] for label in labels)


@pytest.mark.parametrize("status", [400, 403, 404, 409])
def test_writes_are_rolled_back_when_the_request_fails(client, admin, route, status):
    project_id = admin["project"]["id"]

    def write_then_fail():
        _write_label(project_id, "half-applied")
        raise ApiError(status, "Failed after writing")

    route("/api/_test/write-then-fail", write_then_fail)

    response = client.post("/api/_test/write-then-fail")
    assert response.status_code == status
    assert response.json() == {"message": "Failed after writing", "status": status}
    assert _label_names(client, admin) == []


def test_writes_are_committed_when_the_request_succeeds(client, admin, route):
    project_id = admin["project"]["id"]

    def write_and_succeed():
        _write_label(project_id, "kept")
        return {"ok": True}

    route("/api/_test/write-and-succeed", write_and_succeed)

    assert client.post("/api/_test/write-and-succeed").status_code == 200
    assert _label_names(client, admin) == ["kept"]


def test_unhandled_exceptions_still_roll_back(admin, route):
    from fastapi.testclient import TestClient

    project_id = admin["project"]["id"]

    def write_then_crash():
        _write_label(project_id, "crashed")
        raise RuntimeError("boom")

    route("/api/_test/write-then-crash", write_then_crash)

    with TestClient(app, raise_server_exceptions=False) as crash_client:
        assert crash_client.post("/api/_test/write-then-crash").status_code == 500
        labels = crash_client.get(f"/api/projects/{project_id}/labels", headers=admin["headers"]).json()
    assert labels == []
