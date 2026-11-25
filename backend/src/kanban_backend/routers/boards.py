from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..errors import ApiError, not_found, required_text
from ..models import (
    Board,
    BoardData,
    Column,
    CreateBoardInput,
    CreateColumnInput,
    RenameColumnInput,
    ReorderColumnInput,
    Task,
    User,
)
from ..seed import create_default_board
from ..store import new_id, store
from ..telemetry import boards_created
from .projects import get_project_or_404

router = APIRouter(tags=["Boards & Columns"])


def get_board_or_404(board_id: str) -> Board:
    board = store.boards.get(board_id)
    if board is None:
        raise not_found("Board not found")
    return board


def get_column_or_404(column_id: str) -> Column:
    column = store.columns.get(column_id)
    if column is None:
        raise not_found("Column not found")
    return column


@router.get("/projects/{projectId}/boards", response_model=list[Board])
def list_boards(projectId: str, user: User = Depends(auth.get_current_user)) -> list[Board]:
    get_project_or_404(projectId)
    auth.require_member(projectId, user)
    return store.list_boards(projectId)


@router.post("/projects/{projectId}/boards", status_code=201, response_model=Board)
def create_board(
    projectId: str, input: CreateBoardInput, user: User = Depends(auth.get_current_user)
) -> Board:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    name = required_text(input.name, "Board name is required")
    board = create_default_board(store, projectId, name)
    boards_created.add(1)
    return board


@router.delete("/boards/{boardId}", status_code=204)
def delete_board(boardId: str, user: User = Depends(auth.get_current_user)) -> None:
    board = get_board_or_404(boardId)
    auth.require_admin(board.projectId, user)
    if len(store.list_boards(board.projectId)) <= 1:
        raise ApiError(400, "A project needs at least one board")
    store.delete_board_cascade(boardId)


@router.get("/boards/{boardId}/data", response_model=BoardData)
def get_board_data(boardId: str, user: User = Depends(auth.get_current_user)) -> BoardData:
    board = get_board_or_404(boardId)
    auth.require_member(board.projectId, user)
    columns = store.list_columns(boardId)
    tasks = store.tasks.where(Task.boardId == boardId, order_by=(Task.columnId, Task.position, Task.id))
    return BoardData(board=board, columns=columns, tasks=tasks)


@router.post("/boards/{boardId}/columns", status_code=201, response_model=Column)
def create_column(
    boardId: str, input: CreateColumnInput, user: User = Depends(auth.get_current_user)
) -> Column:
    board = get_board_or_404(boardId)
    auth.require_admin(board.projectId, user)
    name = required_text(input.name, "Column name is required")
    position = len(store.list_columns(boardId))
    column = Column(id=new_id("col"), boardId=boardId, name=name, position=position)
    store.columns[column.id] = column
    return column


@router.patch("/columns/{columnId}", response_model=Column)
def rename_column(
    columnId: str, input: RenameColumnInput, user: User = Depends(auth.get_current_user)
) -> Column:
    column = get_column_or_404(columnId)
    board = get_board_or_404(column.boardId)
    auth.require_admin(board.projectId, user)
    column.name = required_text(input.name, "Column name is required")
    return column


@router.delete("/columns/{columnId}", status_code=204)
def delete_column(columnId: str, user: User = Depends(auth.get_current_user)) -> None:
    column = get_column_or_404(columnId)
    board = get_board_or_404(column.boardId)
    auth.require_admin(board.projectId, user)

    siblings = store.list_columns(column.boardId)
    if len(siblings) <= 1:
        raise ApiError(400, "A board needs at least one column")

    # Append the deleted column's tasks, in order, after the fallback
    # column's own. Count the fallback column once up front: re-counting it
    # inside the loop would also count the task being moved (the session
    # autoflushes its new columnId), shifting every moved task one slot too
    # far and leaving a gap after the fallback column's own tasks.
    fallback = next(c for c in siblings if c.id != columnId)
    base = len(store.list_tasks_for_column(fallback.id))
    for offset, task in enumerate(store.list_tasks_for_column(columnId)):
        task.columnId = fallback.id
        task.position = base + offset

    store.columns.pop(columnId, None)
    for position, c in enumerate(store.list_columns(column.boardId)):
        c.position = position


@router.post("/columns/{columnId}/reorder", response_model=list[Column])
def reorder_column(
    columnId: str, input: ReorderColumnInput, user: User = Depends(auth.get_current_user)
) -> list[Column]:
    column = get_column_or_404(columnId)
    board = get_board_or_404(column.boardId)
    auth.require_admin(board.projectId, user)

    columns = store.list_columns(column.boardId)
    columns.remove(column)
    position = max(0, min(input.position, len(columns)))
    columns.insert(position, column)
    for index, c in enumerate(columns):
        c.position = index
    return columns
