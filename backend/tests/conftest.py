from __future__ import annotations

import os

# Must be set before `kanban_backend.db` is imported (by any import below),
# since it reads DATABASE_URL once at import time. An in-memory DB keeps
# tests fast and isolated from whatever the dev server has on disk.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from kanban_backend.main import app
from kanban_backend.store import store


@pytest.fixture()
def client():
    """A TestClient backed by a blank store.

    The app's module-level store is seeded with demo data at import time
    (see `main.py`), which is handy for running the server by hand but
    would make tests depend on that seed's exact contents. Each test gets
    a clean slate instead and builds whatever data it needs through the
    API itself.
    """
    store.reset()
    with TestClient(app) as test_client:
        yield test_client
    store.reset()


def register(client: TestClient, name: str, email: str, password: str = "password123") -> dict:
    """Registers a user and returns {"token": ..., "user": {...}}."""
    response = client.post(
        "/api/auth/register", json={"name": name, "email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin(client: TestClient) -> dict:
    """A signed-up user with a project it administers, plus the project's
    default board and columns."""
    session = register(client, "Alice Admin", "alice@example.com")
    headers = auth_header(session["token"])
    project = client.post(
        "/api/projects", json={"name": "Demo Project", "key": "DEMO"}, headers=headers
    ).json()
    board = client.get("/api/projects/" + project["id"] + "/boards", headers=headers).json()[0]
    columns = client.get(f"/api/boards/{board['id']}/data", headers=headers).json()["columns"]
    return {
        "user": session["user"],
        "headers": headers,
        "project": project,
        "board": board,
        "columns": columns,
    }
