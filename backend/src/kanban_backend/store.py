"""A process-local, in-memory data store.

Nothing here touches a database - every collection is a plain dict keyed by
id, held for the lifetime of the process. This is intentional for the MVP:
it lets the whole backend run with zero setup, and it is small enough that
swapping it for a real database later only means rewriting this one module.

`Store` also owns a handful of cascading-delete helpers, since those are
pure data operations shared by several routers (e.g. deleting a project
must also delete its boards, tasks, comments, ...).
"""

from __future__ import annotations

import threading
from uuid import uuid4

from .models import (
    Activity,
    Attachment,
    Board,
    Column,
    Comment,
    Invitation,
    Label,
    Project,
    ProjectMember,
    Task,
    TaskRelation,
    User,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        self.users: dict[str, User] = {}
        # userId -> "salt$hex_digest"; kept out of the User model on purpose.
        self.credentials: dict[str, str] = {}
        # bearer token -> userId
        self.tokens: dict[str, str] = {}

        self.projects: dict[str, Project] = {}
        self.members: dict[str, ProjectMember] = {}
        self.boards: dict[str, Board] = {}
        self.columns: dict[str, Column] = {}
        self.labels: dict[str, Label] = {}
        self.tasks: dict[str, Task] = {}
        self.comments: dict[str, Comment] = {}
        self.attachments: dict[str, Attachment] = {}
        self.relations: dict[str, TaskRelation] = {}
        self.activities: dict[str, Activity] = {}
        self.invitations: dict[str, Invitation] = {}

        # projectId -> next numeric suffix for that project's task keys.
        self._task_seq: dict[str, int] = {}

    def reset(self) -> None:
        """Wipes all data. Used between test cases to start from a blank slate."""
        for collection in (
            self.users,
            self.credentials,
            self.tokens,
            self.projects,
            self.members,
            self.boards,
            self.columns,
            self.labels,
            self.tasks,
            self.comments,
            self.attachments,
            self.relations,
            self.activities,
            self.invitations,
            self._task_seq,
        ):
            collection.clear()

    # -- generic helpers ----------------------------------------------------

    def next_task_number(self, project_id: str) -> int:
        with self._lock:
            n = self._task_seq.get(project_id, 0) + 1
            self._task_seq[project_id] = n
            return n

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


# Single process-wide instance. Good enough for the MVP; a real deployment
# would replace this module with a database-backed implementation.
store = Store()
