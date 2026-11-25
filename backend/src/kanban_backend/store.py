"""A thin, dict-like facade over the database.

`Store` keeps the exact same public shape the original in-memory version
had (`store.boards.get(id)`, `store.tasks[id] = task`, `store.list_boards(...)`,
cascading-delete helpers, ...), so routers don't need to know or care that
reads and writes now go through a SQLAlchemy `Session` under the hood. Each
collection attribute (`.users`, `.boards`, ...) is a `_Collection` backed by
`SessionLocal`, a session scoped to the current request (see `db.py`).

Objects handed out by `.get()`/`.values()` are live, session-tracked rows:
mutating a field on one and letting the request finish (see the commit
middleware in `main.py`) is enough to persist it - the same "fetch it,
change a field, done" pattern the routers already use.
"""

from __future__ import annotations

import threading
from uuid import uuid4

from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, select

from .db import SessionLocal, engine
from .models import (
    Activity,
    Attachment,
    Board,
    Column,
    Comment,
    Credential,
    Invitation,
    Label,
    Project,
    ProjectMember,
    Role,
    Task,
    TaskCounter,
    TaskRelation,
    Token,
    User,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class _Collection:
    """Makes a table look like `dict[id, Model]`, backed by `SessionLocal`."""

    def __init__(self, model: type[SQLModel]) -> None:
        self._model = model

    def get(self, id: str, default=None):
        obj = SessionLocal.get(self._model, id)
        return obj if obj is not None else default

    def pop(self, id: str, default=None):
        obj = SessionLocal.get(self._model, id)
        if obj is None:
            return default
        SessionLocal.delete(obj)
        SessionLocal.flush()
        return obj

    def values(self) -> list:
        """Every row in the table. Prefer `where()` - this loads the whole
        table, so its cost grows with the entire database, not one project."""
        return list(SessionLocal.scalars(select(self._model)))

    def where(self, *conditions, order_by=None, limit: int | None = None) -> list:
        """Rows matching `conditions` (SQLAlchemy column expressions, e.g.
        `Task.projectId == pid`), filtered/sorted/limited in the database so
        the indexes on those columns are actually used. `order_by` is one
        column expression or a tuple of them."""
        stmt = select(self._model).where(*conditions)
        if order_by is not None:
            # Not `if order_by:` - a single SQL clause has no truth value.
            clauses = order_by if isinstance(order_by, tuple | list) else (order_by,)
            stmt = stmt.order_by(*clauses)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(SessionLocal.scalars(stmt))

    def first(self, *conditions):
        """The first row matching `conditions`, or None."""
        return SessionLocal.scalars(select(self._model).where(*conditions).limit(1)).first()

    def count(self, *conditions) -> int:
        stmt = select(func.count()).select_from(self._model).where(*conditions)
        return SessionLocal.execute(stmt).scalar_one()

    def delete_where(self, *conditions) -> None:
        """Delete every row matching `conditions` (through the session, so
        objects already loaded in this request see the delete)."""
        for obj in self.where(*conditions):
            SessionLocal.delete(obj)
        SessionLocal.flush()

    def keys(self) -> list[str]:
        return [obj.id for obj in self.values()]

    def any(self) -> bool:
        """Whether the table has any rows - `bool(store.users.values())`
        without pulling every row into memory just to check."""
        return SessionLocal.scalars(select(self._model).limit(1)).first() is not None

    def __setitem__(self, id: str, value) -> None:
        SessionLocal.add(value)
        SessionLocal.flush()

    def __getitem__(self, id: str):
        obj = SessionLocal.get(self._model, id)
        if obj is None:
            raise KeyError(id)
        return obj

    def __contains__(self, id: str) -> bool:
        return SessionLocal.get(self._model, id) is not None

    def __len__(self) -> int:
        return self.count()

    def __iter__(self):
        return (obj.id for obj in self.values())


class _ScalarCollection:
    """Adapts a two-column (key, value) table to look like `dict[key, value]`,
    for the handful of things that aren't full entities (password hashes,
    bearer tokens)."""

    def __init__(self, model: type[SQLModel], key_attr: str, value_attr: str) -> None:
        self._model = model
        self._key_attr = key_attr
        self._value_attr = value_attr

    def get(self, key: str, default=None):
        obj = SessionLocal.get(self._model, key)
        return getattr(obj, self._value_attr) if obj is not None else default

    def pop(self, key: str, default=None):
        obj = SessionLocal.get(self._model, key)
        if obj is None:
            return default
        value = getattr(obj, self._value_attr)
        SessionLocal.delete(obj)
        SessionLocal.flush()
        return value

    def __setitem__(self, key: str, value) -> None:
        obj = SessionLocal.get(self._model, key)
        if obj is None:
            obj = self._model(**{self._key_attr: key, self._value_attr: value})
            SessionLocal.add(obj)
        else:
            setattr(obj, self._value_attr, value)
        SessionLocal.flush()

    def __getitem__(self, key: str):
        obj = SessionLocal.get(self._model, key)
        if obj is None:
            raise KeyError(key)
        return getattr(obj, self._value_attr)

    def values(self) -> list:
        return [getattr(obj, self._value_attr) for obj in SessionLocal.scalars(select(self._model))]

    def __len__(self) -> int:
        return len(SessionLocal.scalars(select(self._model)).all())


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        self.users = _Collection(User)
        # userId -> "salt$hex_digest"; kept out of the User model on purpose.
        self.credentials = _ScalarCollection(Credential, "userId", "passwordHash")
        # bearer token -> userId
        self.tokens = _ScalarCollection(Token, "token", "userId")

        self.projects = _Collection(Project)
        self.members = _Collection(ProjectMember)
        self.boards = _Collection(Board)
        self.columns = _Collection(Column)
        self.labels = _Collection(Label)
        self.tasks = _Collection(Task)
        self.comments = _Collection(Comment)
        self.attachments = _Collection(Attachment)
        self.relations = _Collection(TaskRelation)
        self.activities = _Collection(Activity)
        self.invitations = _Collection(Invitation)

    def reset(self) -> None:
        """Wipes all data. Used between test cases to start from a blank slate."""
        SessionLocal.remove()
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        SessionLocal.remove()

    # -- generic helpers ----------------------------------------------------

    def next_task_number(self, project_id: str) -> int:
        with self._lock:
            counter = SessionLocal.get(TaskCounter, project_id)
            if counter is None:
                try:
                    # A SAVEPOINT (not the whole request's transaction) so
                    # a lost race below only unwinds this insert, not
                    # anything else already done earlier in the request.
                    with SessionLocal.begin_nested():
                        counter = TaskCounter(projectId=project_id, value=0)
                        SessionLocal.add(counter)
                        SessionLocal.flush()
                except IntegrityError:
                    # Another concurrent request for this project's very
                    # first task already inserted the counter row - for
                    # our own insert to have failed on the primary key,
                    # theirs must have committed, so it's safe to fetch it.
                    counter = SessionLocal.get(TaskCounter, project_id)
            # A plain `counter.value += 1` isn't atomic across requests: each
            # request has its own uncommitted transaction (see db.py), so a
            # second request's read wouldn't see a first request's increment
            # until it commits at the very end - the Lock above only
            # serializes this Python code, not the underlying reads, so two
            # concurrent requests could both read the same value and produce
            # duplicate task keys. An UPDATE instead takes a row lock that's
            # held for the rest of the transaction, so a second request
            # blocks here until the first commits, then correctly sees its
            # incremented value.
            SessionLocal.execute(
                update(TaskCounter)
                .where(TaskCounter.projectId == project_id)
                .values(value=TaskCounter.value + 1)
            )
            SessionLocal.refresh(counter)
            return counter.value

    # -- membership -----------------------------------------------------

    # Every helper below filters in SQL (see `_Collection.where`), so its
    # cost depends on the rows it actually needs - e.g. `get_member`, which
    # runs on nearly every request, is one indexed lookup instead of a scan
    # of every membership in the database.

    def get_member(self, project_id: str, user_id: str) -> ProjectMember | None:
        return self.members.first(ProjectMember.projectId == project_id, ProjectMember.userId == user_id)

    def list_members(self, project_id: str) -> list[ProjectMember]:
        return self.members.where(ProjectMember.projectId == project_id)

    def admin_count(self, project_id: str) -> int:
        return self.members.count(ProjectMember.projectId == project_id, ProjectMember.role == Role.admin)

    def project_ids_for_user(self, user_id: str) -> list[str]:
        return [m.projectId for m in self.members.where(ProjectMember.userId == user_id)]

    def find_user_by_email(self, email: str) -> User | None:
        """Case-insensitive, matching how emails were compared before."""
        return self.users.first(func.lower(User.email) == email.lower())

    # -- boards / columns -----------------------------------------------

    def list_boards(self, project_id: str) -> list[Board]:
        return self.boards.where(Board.projectId == project_id)

    def list_columns(self, board_id: str) -> list[Column]:
        return self.columns.where(Column.boardId == board_id, order_by=(Column.position, Column.id))

    # -- tasks ------------------------------------------------------------

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return self.tasks.where(Task.projectId == project_id)

    def list_tasks_for_column(self, column_id: str) -> list[Task]:
        return self.tasks.where(Task.columnId == column_id, order_by=(Task.position, Task.id))

    # -- cascading deletes ------------------------------------------------

    def delete_task_cascade(self, task_id: str) -> None:
        self.tasks.pop(task_id, None)
        self.comments.delete_where(Comment.taskId == task_id)
        self.attachments.delete_where(Attachment.taskId == task_id)
        self.relations.delete_where(
            or_(TaskRelation.taskId == task_id, TaskRelation.relatedTaskId == task_id)
        )
        self.activities.delete_where(Activity.taskId == task_id)

    def delete_column_cascade(self, column_id: str) -> None:
        for task in self.tasks.where(Task.columnId == column_id):
            self.delete_task_cascade(task.id)
        self.columns.pop(column_id, None)

    def delete_board_cascade(self, board_id: str) -> None:
        for column in self.columns.where(Column.boardId == board_id):
            self.delete_column_cascade(column.id)
        self.boards.pop(board_id, None)

    def delete_project_cascade(self, project_id: str) -> None:
        for board in self.boards.where(Board.projectId == project_id):
            self.delete_board_cascade(board.id)
        self.labels.delete_where(Label.projectId == project_id)
        self.members.delete_where(ProjectMember.projectId == project_id)
        self.invitations.delete_where(Invitation.projectId == project_id)
        self.activities.delete_where(Activity.projectId == project_id)
        self.projects.pop(project_id, None)

    def remove_label_everywhere(self, label_id: str) -> None:
        # labelIds is a JSON list, so it can't be filtered portably in SQL -
        # but a label only ever appears on tasks in its own project.
        label = self.labels.get(label_id)
        tasks = self.list_tasks_for_project(label.projectId) if label is not None else self.tasks.values()
        for task in tasks:
            if label_id in task.labelIds:
                task.labelIds = [lid for lid in task.labelIds if lid != label_id]

    def unassign_user_in_project(self, project_id: str, user_id: str) -> None:
        for task in self.tasks.where(Task.projectId == project_id, Task.assigneeId == user_id):
            task.assigneeId = None


# Single process-wide instance. Its collections route to a request-scoped
# SQLAlchemy session (see db.py), so this is safe to share across requests.
store = Store()
