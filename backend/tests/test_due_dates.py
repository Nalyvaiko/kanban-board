from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def _post_task(client, admin, **overrides):
    body = {
        "projectId": admin["project"]["id"],
        "boardId": admin["board"]["id"],
        "columnId": admin["columns"][0]["id"],
        "title": "Task",
        "assigneeId": admin["user"]["id"],
    }
    body.update(overrides)
    return client.post("/api/tasks", json=body, headers=admin["headers"])


def _midnight_utc(days_from_today: int) -> str:
    """What the date picker sends for a calendar day: midnight UTC of it."""
    day = datetime.now(UTC).date() + timedelta(days=days_from_today)
    return f"{day.isoformat()}T00:00:00.000Z"


@pytest.mark.parametrize("bad", ["tomorrow", "2026-13-01", "21/11/2026"])
def test_unparseable_due_dates_are_rejected(client, admin, bad):
    assert _post_task(client, admin, dueDate=bad).status_code == 400

    task = _post_task(client, admin).json()
    response = client.patch(f"/api/tasks/{task['id']}", json={"dueDate": bad}, headers=admin["headers"])
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("sent", "stored"),
    [
        ("2026-11-21", "2026-11-21T00:00:00Z"),
        ("2026-11-21T00:00:00.000Z", "2026-11-21T00:00:00Z"),
        ("2026-11-21T02:00:00+02:00", "2026-11-21T00:00:00Z"),
        ("2026-11-21T09:30:00", "2026-11-21T09:30:00Z"),
    ],
)
def test_due_dates_are_stored_in_canonical_utc_form(client, admin, sent, stored):
    assert _post_task(client, admin, dueDate=sent).json()["dueDate"] == stored


def test_task_due_today_is_not_overdue_until_the_day_has_passed(client, admin):
    yesterday = _post_task(client, admin, title="Yesterday", dueDate=_midnight_utc(-1)).json()
    _post_task(client, admin, title="Today", dueDate=_midnight_utc(0))
    _post_task(client, admin, title="Tomorrow", dueDate=_midnight_utc(1))
    _post_task(client, admin, title="No due date")

    dashboard = client.get("/api/dashboard", headers=admin["headers"]).json()
    assert len(dashboard["myTasks"]) == 4
    assert [t["id"] for t in dashboard["overdueTasks"]] == [yesterday["id"]]


def test_clearing_a_due_date_is_recorded(client, admin):
    task = _post_task(client, admin, dueDate="2026-11-21").json()

    response = client.patch(f"/api/tasks/{task['id']}", json={"dueDate": None}, headers=admin["headers"])
    assert response.status_code == 200
    assert response.json()["dueDate"] is None

    activity = client.get(f"/api/tasks/{task['id']}/activity", headers=admin["headers"]).json()
    assert any("removed the due date" in a["message"] for a in activity)
