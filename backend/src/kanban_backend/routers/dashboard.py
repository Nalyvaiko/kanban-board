from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends

from .. import auth
from ..models import DashboardData, Project, Task, User, parse_due_date
from ..store import store

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(user: User = Depends(auth.get_current_user)) -> DashboardData:
    project_ids = store.project_ids_for_user(user.id)
    projects = store.projects.where(Project.id.in_(project_ids))

    my_tasks = store.tasks.where(Task.projectId.in_(project_ids), Task.assigneeId == user.id)
    overdue_tasks = [t for t in my_tasks if _is_overdue(t.dueDate, datetime.now(UTC).date())]

    return DashboardData(projects=projects, myTasks=my_tasks, overdueTasks=overdue_tasks)


def _is_overdue(due_date: str | None, today: date) -> bool:
    """Overdue once the due *day* has passed, not from the first moment of
    it: due dates are calendar days stored as midnight UTC, so comparing the
    raw timestamp to "now" flagged every task as overdue on its own due day.
    The server has no viewer timezone, so "today" is the UTC date."""
    if due_date is None:
        return False
    parsed = parse_due_date(due_date)
    return parsed is not None and parsed.date() < today
