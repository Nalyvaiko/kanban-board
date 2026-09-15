"""Tiny helper for appending to the project activity feed. Kept separate
from `store.py` so routers can log activity without pulling in every store
detail, and separate from `viewmodels.py` since it writes rather than reads.
"""

from __future__ import annotations

from .models import Activity, utcnow_iso
from .store import Store, new_id, store


def log_activity(
    project_id: str, message: str, actor_id: str, task_id: str | None = None, db: Store = store
) -> Activity:
    activity = Activity(
        id=new_id("act"),
        projectId=project_id,
        taskId=task_id,
        actorId=actor_id,
        message=message,
        createdAt=utcnow_iso(),
    )
    db.activities[activity.id] = activity
    return activity
