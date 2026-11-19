from __future__ import annotations

import logging

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
from ..telemetry import task_creation_failures, tasks_created
from .boards import get_board_or_404, get_column_or_404
from .projects import get_project_or_404

router = APIRouter(tags=["Tasks"])
logger = logging.getLogger("kanban_backend.tasks")


def get_task_or_404(task_id: str) -> Task:
    task = store.tasks.get(task_id)
    if task is None:
        raise not_found("Task not found")
    return task


def _validate_task_references(
    project_id: str, assignee_id: str | None, label_ids: list[str] | None
) -> None:
    """Rejects an assignee or labels that don't belong to the task's project.

    Without this, a task could point at a user who can't even see the
    project, or carry a label id from some other project (which would then
    leak that label's name/color into this project's board).
    """
    if assignee_id is not None and store.get_member(project_id, assignee_id) is None:
        raise ApiError(400, "Assignee must be a member of this project")
    for label_id in label_ids or []:
        label = store.labels.get(label_id)
        if label is None or label.projectId != project_id:
            raise ApiError(400, "Label does not belong to this project")


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
    # Counts every failed attempt to create a task - permission/404s from
    # the lookups below included, since those are still a caller trying
    # and failing to create a task, not just this endpoint's own
    # validation - not just the request-title-is-blank case.
    try:
        project = get_project_or_404(input.projectId)
        auth.require_contributor(project.id, user)
        board = get_board_or_404(input.boardId)
        column = get_column_or_404(input.columnId)
        if board.projectId != project.id:
            raise ApiError(400, "Board does not belong to this project")
        if column.boardId != board.id:
            raise ApiError(400, "Column does not belong to this board")

        title = input.title.strip()
        if not title:
            raise ApiError(400, "Task title is required")
        _validate_task_references(project.id, input.assigneeId, input.labelIds)

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
            labelIds=list(dict.fromkeys(input.labelIds)),
            dueDate=input.dueDate,
            position=len(store.list_tasks_for_column(column.id)),
            createdBy=user.id,
            createdAt=now,
            updatedAt=now,
        )
        store.tasks[task.id] = task
    except Exception as exc:
        task_creation_failures.add(1)
        # IDs/metadata only - never the title/description, which is
        # arbitrary user content, not something to send to telemetry.
        logger.warning(
            "task creation failed",
            extra={
                "project_id": input.projectId,
                "board_id": input.boardId,
                "column_id": input.columnId,
                "user_id": user.id,
                "error_type": type(exc).__name__,
            },
        )
        raise

    tasks_created.add(1)
    logger.info(
        "task created",
        extra={
            "task_id": task.id,
            "task_key": task.key,
            "project_id": project.id,
            "board_id": task.boardId,
            "column_id": task.columnId,
            "user_id": user.id,
        },
    )
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

    if input.title is not None:
        input.title = input.title.strip()
        if not input.title:
            raise ApiError(400, "Task title is required")

    origin_column_id = task.columnId
    column_changed = input.columnId is not None and input.columnId != origin_column_id
    if column_changed:
        column = get_column_or_404(input.columnId)
        if column.boardId != task.boardId:
            raise ApiError(400, "Column does not belong to this task's board")

    _validate_task_references(
        task.projectId,
        input.assigneeId if "assigneeId" in input.model_fields_set else None,
        input.labelIds,
    )
    if input.labelIds is not None:
        input.labelIds = list(dict.fromkeys(input.labelIds))

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
    if column_changed:
        # Same bookkeeping as /move: append to the destination column and
        # close the gap left behind, so positions stay 0..n-1 in both.
        task.position = len(store.list_tasks_for_column(input.columnId))
        task.columnId = input.columnId
        remaining = [t for t in store.list_tasks_for_column(origin_column_id) if t.id != task.id]
        for index, t in enumerate(remaining):
            t.position = index

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
