"""Guards against full-table scans creeping back into request handling.

The store used to load whole tables and filter in Python, so e.g. every
membership check read every membership in the database. These tests record
the SQL the main read/write paths actually run and fail on any row-returning
SELECT without a WHERE clause.
"""

from __future__ import annotations

import re
from contextlib import contextmanager

from sqlalchemy import event

from kanban_backend.db import engine

from .conftest import auth_header, register


@contextmanager
def _recorded_selects():
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def _unscoped(statements: list[str]) -> list[str]:
    """Row-returning SELECTs with no WHERE (aggregates like count(*) are fine)."""
    return [
        s
        for s in statements
        if " WHERE " not in s.upper() and not re.match(r"SELECT (count|max|min)\(", s, re.IGNORECASE)
    ]


def test_common_requests_never_scan_whole_tables(client, admin):
    headers = admin["headers"]
    project_id = admin["project"]["id"]
    board_id = admin["board"]["id"]
    first, second = admin["columns"][0]["id"], admin["columns"][1]["id"]

    bob = register(client, "Bob", "bob@example.com")
    client.post(f"/api/projects/{project_id}/members", json={"email": "bob@example.com", "role": "member"}, headers=headers)
    label = client.post(f"/api/projects/{project_id}/labels", json={"name": "ui"}, headers=headers).json()

    with _recorded_selects() as statements:
        task = client.post(
            "/api/tasks",
            json={
                "projectId": project_id,
                "boardId": board_id,
                "columnId": first,
                "title": "Scoped",
                "assigneeId": bob["user"]["id"],
                "labelIds": [label["id"]],
            },
            headers=headers,
        ).json()
        other = client.post(
            "/api/tasks",
            json={"projectId": project_id, "boardId": board_id, "columnId": first, "title": "Other"},
            headers=headers,
        ).json()
        client.post(f"/api/tasks/{task['id']}/move", json={"columnId": second, "position": 0}, headers=headers)
        client.post(f"/api/tasks/{task['id']}/comments", json={"body": "hi"}, headers=headers)
        client.post(
            f"/api/tasks/{task['id']}/relations",
            json={"relatedTaskId": other["id"], "type": "blocks"},
            headers=headers,
        )

        for path in [
            "/api/projects",
            f"/api/projects/{project_id}",
            f"/api/projects/{project_id}/my-role",
            f"/api/projects/{project_id}/tasks",
            f"/api/projects/{project_id}/boards",
            f"/api/projects/{project_id}/labels",
            f"/api/projects/{project_id}/members",
            f"/api/projects/{project_id}/activity",
            f"/api/boards/{board_id}/data",
            f"/api/tasks/{task['id']}/comments",
            f"/api/tasks/{task['id']}/relations",
            f"/api/tasks/{task['id']}/attachments",
            f"/api/tasks/{task['id']}/activity",
            "/api/dashboard",
            "/api/invitations/mine",
        ]:
            assert client.get(path, headers=headers).status_code == 200, path

        client.post("/api/auth/login", json={"email": "bob@example.com", "password": "password123"})
        client.delete(f"/api/projects/{project_id}/members/{bob['user']['id']}", headers=headers)
        client.delete(f"/api/labels/{label['id']}", headers=headers)
        client.delete(f"/api/tasks/{task['id']}", headers=headers)
        client.delete(f"/api/projects/{project_id}", headers=headers)

    assert statements, "no SQL was recorded - is the listener attached to the right engine?"
    assert _unscoped(statements) == []


def test_membership_lookup_is_a_single_scoped_query(client, admin):
    """The check behind nearly every endpoint: one query on the member's own
    (projectId, userId), however many other memberships exist."""
    for i in range(5):
        other = register(client, f"User {i}", f"user{i}@example.com")
        client.post("/api/projects", json={"name": f"P{i}", "key": f"P{i}X"}, headers=auth_header(other["token"]))

    with _recorded_selects() as statements:
        response = client.get(f"/api/projects/{admin['project']['id']}/my-role", headers=admin["headers"])
    assert response.status_code == 200

    membership_queries = [s for s in statements if "from project_member" in s.lower()]
    assert len(membership_queries) == 1
    # Both columns must be in the WHERE clause, not just in the selected
    # column list (which a full scan of the table would also have).
    _, _, where_clause = membership_queries[0].lower().partition(" where ")
    assert "projectid" in where_clause and "userid" in where_clause
