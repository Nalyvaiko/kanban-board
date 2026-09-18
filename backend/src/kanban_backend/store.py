"""A thin, dict-like facade over the database.

`Store` keeps the exact same public shape the original in-memory version
had (`store.boards.get(id)`, `store.tasks[id] = task`, `store.list_boards(...)`,
cascading-delete helpers, ...), so routers don't need to know or care that
reads and writes now go through a SQLAlchemy `Session` under the hood. Each
collection attribute (`.users`, `.boards`, ...) is a `_Collection` backed by
`SessionLocal`, the process's thread-scoped session (see `db.py`).

Objects handed out by `.get()`/`.values()` are live, session-tracked rows:
mutating a field on one and letting the request finish (see the commit
middleware in `main.py`) is enough to persist it - the same "fetch it,
change a field, done" pattern the routers already use.
"""

from __future__ import annotations

import threading
from uuid import uuid4

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
        return list(SessionLocal.scalars(select(self._model)))

    def keys(self) -> list[str]:
        return [obj.id for obj in self.values()]

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
        return len(self.values())

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
                counter = TaskCounter(projectId=project_id, value=0)
                SessionLocal.add(counter)
            counter.value += 1
            SessionLocal.flush()
            return counter.value

    # -- membership -----------------------------------------------------

    def get_member(self, project_id: str, user_id: str) -> ProjectMember | None:
        for m in self.members.values():
            if m.projectId == project_id and m.userId == user_id:
                return m
        return None

    def list_members(self, project_id: str) -> list[ProjectMember]:
        return [m for m in self.members.values() if m.projectId == project_id]

    def admin_count(self, project_id: str) -> int:
        return sum(1 for m in self.list_members(project_id) if m.role.value == "admin")

    # -- boards / columns -----------------------------------------------

    def list_boards(self, project_id: str) -> list[Board]:
        return [b for b in self.boards.values() if b.projectId == project_id]

    def list_columns(self, board_id: str) -> list[Column]:
        return sorted((c for c in self.columns.values() if c.boardId == board_id), key=lambda c: c.position)

    # -- tasks ------------------------------------------------------------

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [t for t in self.tasks.values() if t.projectId == project_id]

    def list_tasks_for_column(self, column_id: str) -> list[Task]:
        return sorted((t for t in self.tasks.values() if t.columnId == column_id), key=lambda t: t.position)

    # -- cascading deletes ------------------------------------------------

    def delete_task_cascade(self, task_id: str) -> None:
        self.tasks.pop(task_id, None)
        for cid in [c.id for c in self.comments.values() if c.taskId == task_id]:
            self.comments.pop(cid, None)
        for aid in [a.id for a in self.attachments.values() if a.taskId == task_id]:
            self.attachments.pop(aid, None)
        for rid in [
            r.id for r in self.relations.values() if r.taskId == task_id or r.relatedTaskId == task_id
        ]:
            self.relations.pop(rid, None)
        for act_id in [a.id for a in self.activities.values() if a.taskId == task_id]:
            self.activities.pop(act_id, None)

    def delete_column_cascade(self, column_id: str) -> None:
        for tid in [t.id for t in self.tasks.values() if t.columnId == column_id]:
            self.delete_task_cascade(tid)
        self.columns.pop(column_id, None)

    def delete_board_cascade(self, board_id: str) -> None:
        for cid in [c.id for c in self.columns.values() if c.boardId == board_id]:
            self.delete_column_cascade(cid)
        self.boards.pop(board_id, None)

    def delete_project_cascade(self, project_id: str) -> None:
        for bid in [b.id for b in self.boards.values() if b.projectId == project_id]:
            self.delete_board_cascade(bid)
        for lid in [label.id for label in self.labels.values() if label.projectId == project_id]:
            self.labels.pop(lid, None)
        for mid in [m.id for m in self.members.values() if m.projectId == project_id]:
            self.members.pop(mid, None)
        for iid in [i.id for i in self.invitations.values() if i.projectId == project_id]:
            self.invitations.pop(iid, None)
        for act_id in [a.id for a in self.activities.values() if a.projectId == project_id]:
            self.activities.pop(act_id, None)
        self.projects.pop(project_id, None)

    def remove_label_everywhere(self, label_id: str) -> None:
        for task in self.tasks.values():
            if label_id in task.labelIds:
                task.labelIds = [lid for lid in task.labelIds if lid != label_id]

    def unassign_user_in_project(self, project_id: str, user_id: str) -> None:
        for task in self.tasks.values():
            if task.projectId == project_id and task.assigneeId == user_id:
                task.assigneeId = None


# Single process-wide instance. Its collections route to a thread-scoped
# SQLAlchemy session (see db.py), so this is safe to share across requests.
store = Store()
