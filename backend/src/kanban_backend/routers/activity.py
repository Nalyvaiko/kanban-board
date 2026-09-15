from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..models import ActivityWithActor, User
from ..store import store
from ..viewmodels import activity_with_actor
from .projects import get_project_or_404
from .tasks import get_task_or_404

router = APIRouter(tags=["Activity"])


@router.get("/tasks/{taskId}/activity", response_model=list[ActivityWithActor])
def list_task_activity(taskId: str, user: User = Depends(auth.get_current_user)) -> list[ActivityWithActor]:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    activities = sorted(
        (a for a in store.activities.values() if a.taskId == taskId),
        key=lambda a: a.createdAt,
        reverse=True,
    )
    return [activity_with_actor(a) for a in activities]


@router.get("/projects/{projectId}/activity", response_model=list[ActivityWithActor])
def list_project_activity(
    projectId: str, user: User = Depends(auth.get_current_user)
) -> list[ActivityWithActor]:
    get_project_or_404(projectId)
    auth.require_member(projectId, user)
    activities = sorted(
        (a for a in store.activities.values() if a.projectId == projectId),
        key=lambda a: a.createdAt,
        reverse=True,
    )[:50]
    return [activity_with_actor(a) for a in activities]
