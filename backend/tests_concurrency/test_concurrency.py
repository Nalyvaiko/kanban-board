"""Regression test for the SQLite concurrent-write bug fixed in a885e7f
(BEGIN IMMEDIATE + a longer busy_timeout - see db.py's own comment on
`_sqlite_begin`).

Deliberately outside backend/tests/: that suite's conftest.py hardcodes
DATABASE_URL to sqlite:///:memory: before any import, which binds a
different engine (StaticPool, no BEGIN IMMEDIATE event listener - see
db.py's own gating on `_is_sqlite_memory`) that cannot exercise this bug
at all. This test needs DATABASE_URL already pointed at a real file
*before* kanban_backend.db is ever imported in this process - pytest
never discovers tests/conftest.py for a file outside tests/, so running
this via `make test-concurrency` (which sets DATABASE_URL first) is
what makes that true.

Run via `make test-concurrency` - not part of `make test` / `make test-backend`.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

_database_url = os.environ.get("DATABASE_URL", "")
if ":memory:" in _database_url or not _database_url.startswith("sqlite"):
    pytest.skip(
        "Needs DATABASE_URL pointed at a real sqlite file before import - "
        "run via `make test-concurrency`, not `pytest` directly.",
        allow_module_level=True,
    )

from fastapi.testclient import TestClient  # noqa: E402

from kanban_backend.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def test_concurrent_task_creation_does_not_hit_database_locked() -> None:
    """Reproduces a885e7f's exact scenario: several requests each read
    (project/membership/board/column lookups) before writing, then race
    to write at the same moment - the specific SQLite lock-escalation
    conflict that a plain `BEGIN` cannot recover from even with a long
    busy_timeout (see db.py's comment for why)."""
    register = client.post(
        "/api/auth/register",
        json={"name": "Concurrency Test", "email": "concurrency@example.com", "password": "password123"},
    )
    assert register.status_code == 201, register.text
    token = register.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post("/api/projects", json={"name": "Concurrency", "key": "CNC"}, headers=headers)
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    board_id = client.get(f"/api/projects/{project_id}/boards", headers=headers).json()[0]["id"]
    column_id = client.get(f"/api/boards/{board_id}/data", headers=headers).json()["columns"][0]["id"]

    def create_task(i: int):
        return client.post(
            "/api/tasks",
            json={
                "projectId": project_id,
                "boardId": board_id,
                "columnId": column_id,
                "title": f"Concurrent task {i}",
                "type": "task",
                "priority": "medium",
                "labelIds": [],
            },
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(create_task, i) for i in range(8)]
        results = [future.result() for future in as_completed(futures)]

    statuses = [r.status_code for r in results]
    failures = [r.text[:300] for r in results if r.status_code != 201]
    assert statuses == [201] * 8, f"expected 8/8 to succeed, got {statuses}; failures: {failures}"

    tasks = client.get(f"/api/projects/{project_id}/tasks", headers=headers).json()
    keys = [t["key"] for t in tasks]
    assert len(keys) == len(set(keys)), f"duplicate task keys (the other historical race): {keys}"
