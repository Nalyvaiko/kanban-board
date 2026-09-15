from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..models import DashboardData, User, utcnow_iso
from ..store import store

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(user: User = Depends(auth.get_current_user)) -> DashboardData:
    project_ids = {m.projectId for m in store.members.values() if m.userId == user.id}
    projects = [p for p in store.projects.values() if p.id in project_ids]

    my_tasks = [t for t in store.tasks.values() if t.projectId in project_ids and t.assigneeId == user.id]
    now = utcnow_iso()
    overdue_tasks = [t for t in my_tasks if t.dueDate is not None and t.dueDate < now]

    return DashboardData(projects=projects, myTasks=my_tasks, overdueTasks=overdue_tasks)
