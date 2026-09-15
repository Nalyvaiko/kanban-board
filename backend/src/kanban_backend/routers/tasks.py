from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import auth
from ..activity_log import log_activity
from ..errors import ApiError, not_found
from ..models import (
    CreateTaskInput,
    MoveTaskInput,
    Priority,
    Task,
    TaskType,
    UpdateTaskInput,
    User,
    utcnow_iso,
)
from ..store import new_id, store
from .boards import get_board_or_404, get_column_or_404
from .projects import get_project_or_404

router = APIRouter(tags=["Tasks"])


def get_task_or_404(task_id: str) -> Task:
    task = store.tasks.get(task_id)
    if task is None:
        raise not_found("Task not found")
    return task


@router.get("/projects/{projectId}/tasks", response_model=list[Task])
def list_tasks(
    projectId: str,
    user: User = Depends(auth.get_current_user),
    search: str | None = Query(default=None),
    columnId: str | None = Query(default=None),
    assigneeId: str | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    type: TaskType | None = Query(default=None),
    labelId: str | None = Query(default=None),
) -> list[Task]:
    get_project_or_404(projectId)
    auth.require_member(projectId, user)

    tasks = store.list_tasks_for_project(projectId)
    if search:
        needle = search.lower()
        tasks = [
            t
            for t in tasks
            if needle in t.title.lower() or needle in t.key.lower() or needle in t.description.lower()
        ]
    if columnId:
        tasks = [t for t in tasks if t.columnId == columnId]
    if assigneeId:
        if assigneeId == "unassigned":
            tasks = [t for t in tasks if t.assigneeId is None]
        else:
            tasks = [t for t in tasks if t.assigneeId == assigneeId]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if type:
        tasks = [t for t in tasks if t.type == type]
    if labelId:
        tasks = [t for t in tasks if labelId in t.labelIds]
    return tasks


@router.post("/tasks", status_code=201, response_model=Task)
def create_task(input: CreateTaskInput, user: User = Depends(auth.get_current_user)) -> Task:
    project = get_project_or_404(input.projectId)
    auth.require_contributor(project.id, user)
    get_board_or_404(input.boardId)
    column = get_column_or_404(input.columnId)

    title = input.title.strip()
    if not title:
        raise ApiError(400, "Task title is required")

    now = utcnow_iso()
    task = Task(
        id=new_id("task"),
        key=f"{project.key}-{store.next_task_number(project.id)}",
        projectId=project.id,
        boardId=input.boardId,
        columnId=input.columnId,
        title=title,
        description=input.description or "",
        type=input.type,
        priority=input.priority,
        assigneeId=input.assigneeId,
        labelIds=input.labelIds,
        dueDate=input.dueDate,
        position=len(store.list_tasks_for_column(column.id)),
        createdBy=user.id,
        createdAt=now,
        updatedAt=now,
    )
    store.tasks[task.id] = task
    log_activity(project.id, f"{user.name} created {task.key}", user.id, task.id)
    return task


@router.get("/tasks/{taskId}", response_model=Task)
def get_task(taskId: str, user: User = Depends(auth.get_current_user)) -> Task:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    return task


def _describe_changes(task: Task, input: UpdateTaskInput) -> list[str]:
    changes = []
    if input.title is not None and input.title != task.title:
        changes.append("updated the title")
    if input.priority is not None and input.priority != task.priority:
        changes.append(f"changed priority from {task.priority.value} to {input.priority.value}")
    if input.type is not None and input.type != task.type:
        changes.append(f"changed type from {task.type.value} to {input.type.value}")
    if "assigneeId" in input.model_fields_set and input.assigneeId != task.assigneeId:
        changes.append("changed the assignee")
    if input.dueDate is not None and input.dueDate != task.dueDate:
        changes.append("changed the due date")
    if input.labelIds is not None and set(input.labelIds) != set(task.labelIds):
        changes.append("updated labels")
    if input.description is not None and input.description != task.description:
        changes.append("updated the description")
    return changes


@router.patch("/tasks/{taskId}", response_model=Task)
def update_task(taskId: str, input: UpdateTaskInput, user: User = Depends(auth.get_current_user)) -> Task:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)

    if input.columnId is not None and input.columnId != task.columnId:
        column = get_column_or_404(input.columnId)
        if column.boardId != task.boardId:
            raise ApiError(400, "Column does not belong to this task's board")

    changes = _describe_changes(task, input)

    if input.title is not None:
        task.title = input.title
    if input.description is not None:
        task.description = input.description
    if input.type is not None:
        task.type = input.type
    if input.priority is not None:
        task.priority = input.priority
    if "assigneeId" in input.model_fields_set:
        task.assigneeId = input.assigneeId
    if input.labelIds is not None:
        task.labelIds = input.labelIds
    if input.dueDate is not None or "dueDate" in input.model_fields_set:
        task.dueDate = input.dueDate
    if input.columnId is not None:
        task.columnId = input.columnId

    task.updatedAt = utcnow_iso()

    for change in changes:
        log_activity(task.projectId, f"{user.name} {change} on {task.key}", user.id, task.id)

    return task


@router.delete("/tasks/{taskId}", status_code=204)
def delete_task(taskId: str, user: User = Depends(auth.get_current_user)) -> None:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)
    store.delete_task_cascade(taskId)


@router.post("/tasks/{taskId}/move", response_model=Task)
def move_task(taskId: str, input: MoveTaskInput, user: User = Depends(auth.get_current_user)) -> Task:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)
    destination = get_column_or_404(input.columnId)
    if destination.boardId != task.boardId:
        raise ApiError(400, "Column does not belong to this task's board")

    origin_column = store.columns.get(task.columnId)
    same_column = task.columnId == input.columnId

    if same_column:
        siblings = [t for t in store.list_tasks_for_column(task.columnId) if t.id != taskId]
    else:
        siblings = store.list_tasks_for_column(input.columnId)

    target_position = len(siblings) if input.position is None else max(0, min(input.position, len(siblings)))
    siblings.insert(target_position, task)
    for index, t in enumerate(siblings):
        t.position = index
    task.columnId = input.columnId
    task.updatedAt = utcnow_iso()

    if not same_column and origin_column is not None:
        # Close the gap left behind in the source column.
        for index, t in enumerate(store.list_tasks_for_column(origin_column.id)):
            t.position = index
        log_activity(
            task.projectId,
            f"{user.name} moved {task.key} from {origin_column.name} to {destination.name}",
            user.id,
            task.id,
        )

    return task
