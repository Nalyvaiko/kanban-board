"""Domain entities and request/response schemas for every route.

Entities (`User`, `Project`, `Task`, ...) are `SQLModel` tables: the same
class is both the SQLAlchemy-mapped row and the Pydantic schema FastAPI uses
to validate/serialize responses, so a value fetched from the database can be
mutated in place and persisted just by committing the session - no separate
DTO/ORM conversion step.

Request bodies and "with relation" response shapes (e.g. `CommentWithAuthor`)
don't need a table, so they stay plain Pydantic models; a couple of them
subclass an entity to reuse its fields, which SQLModel supports directly.

These mirror the shapes described in `openapi.yaml` at the repo root, with
one deliberate deviation: authentication uses bearer tokens instead of
session cookies (see `auth.py`), so the auth endpoints return a token
alongside the user.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr
from pydantic import Field as PField
from sqlalchemy import JSON
from sqlalchemy import Column as SAColumn
from sqlmodel import Field, SQLModel


def utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string with a trailing `Z`, matching
    the `date-time` format used throughout openapi.yaml."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class Role(str, Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class TaskType(str, Enum):
    task = "task"
    bug = "bug"
    feature = "feature"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class RelationType(str, Enum):
    blocks = "blocks"
    blocked_by = "blocked_by"
    relates_to = "relates_to"


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"


class Provider(str, Enum):
    password = "password"
    google = "google"


# ---------------------------------------------------------------------------
# Core entities (SQLModel tables)
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: str = Field(primary_key=True)
    name: str
    email: str = Field(index=True)
    avatarColor: str
    provider: Provider
    createdAt: str


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: str = Field(primary_key=True)
    key: str = Field(index=True)
    name: str
    description: str = ""
    createdBy: str
    createdAt: str


class ProjectMemberBase(SQLModel):
    projectId: str = Field(index=True)
    userId: str = Field(index=True)
    role: Role
    createdAt: str


class ProjectMember(ProjectMemberBase, table=True):
    __tablename__ = "project_member"

    id: str = Field(primary_key=True)


class MemberWithUser(ProjectMemberBase):
    id: str
    user: User


class Board(SQLModel, table=True):
    __tablename__ = "board"

    id: str = Field(primary_key=True)
    projectId: str = Field(index=True)
    name: str
    createdAt: str


class Column(SQLModel, table=True):
    __tablename__ = "column"

    id: str = Field(primary_key=True)
    boardId: str = Field(index=True)
    name: str
    position: int


class Label(SQLModel, table=True):
    __tablename__ = "label"

    id: str = Field(primary_key=True)
    projectId: str = Field(index=True)
    name: str
    color: str


class Task(SQLModel, table=True):
    __tablename__ = "task"

    id: str = Field(primary_key=True)
    key: str = Field(index=True)
    projectId: str = Field(index=True)
    boardId: str = Field(index=True)
    columnId: str = Field(index=True)
    title: str
    description: str = ""
    type: TaskType = TaskType.task
    priority: Priority = Priority.medium
    assigneeId: str | None = None
    labelIds: list[str] = Field(default_factory=list, sa_column=SAColumn(JSON))
    dueDate: str | None = None
    position: int
    createdBy: str
    createdAt: str
    updatedAt: str


class CommentBase(SQLModel):
    taskId: str = Field(index=True)
    authorId: str
    body: str
    createdAt: str
    updatedAt: str


class Comment(CommentBase, table=True):
    __tablename__ = "comment"

    id: str = Field(primary_key=True)


class CommentWithAuthor(CommentBase):
    id: str
    author: User


class Attachment(SQLModel, table=True):
    __tablename__ = "attachment"

    id: str = Field(primary_key=True)
    taskId: str = Field(index=True)
    filename: str
    fileType: str
    fileSize: int
    uploadedBy: str
    uploadedAt: str
    storageUrl: str


class TaskRelationBase(SQLModel):
    taskId: str = Field(index=True)
    relatedTaskId: str = Field(index=True)
    type: RelationType
    createdAt: str


class TaskRelation(TaskRelationBase, table=True):
    __tablename__ = "task_relation"

    id: str = Field(primary_key=True)


class RelationWithTask(TaskRelationBase):
    id: str
    relatedTask: Task


class ActivityBase(SQLModel):
    projectId: str = Field(index=True)
    taskId: str | None = Field(default=None, index=True)
    actorId: str
    message: str
    createdAt: str


class Activity(ActivityBase, table=True):
    __tablename__ = "activity"

    id: str = Field(primary_key=True)


class ActivityWithActor(ActivityBase):
    id: str
    actor: User


class InvitationBase(SQLModel):
    projectId: str = Field(index=True)
    email: str = Field(index=True)
    role: Role
    status: InvitationStatus
    invitedBy: str
    createdAt: str


class Invitation(InvitationBase, table=True):
    __tablename__ = "invitation"

    id: str = Field(primary_key=True)


class InvitationWithProject(InvitationBase):
    id: str
    project: Project


class BoardData(BaseModel):
    board: Board
    columns: list[Column]
    tasks: list[Task]


class DashboardData(BaseModel):
    projects: list[Project]
    myTasks: list[Task]
    overdueTasks: list[Task]


# ---------------------------------------------------------------------------
# Auth-support tables (not part of the public API surface)
# ---------------------------------------------------------------------------


class Credential(SQLModel, table=True):
    """userId -> salted password hash. Kept out of the `User` model on
    purpose, same as the original in-memory store."""

    __tablename__ = "credential"

    userId: str = Field(primary_key=True)
    passwordHash: str


class Token(SQLModel, table=True):
    """Bearer token -> userId."""

    __tablename__ = "token"

    token: str = Field(primary_key=True)
    userId: str = Field(index=True)


class TaskCounter(SQLModel, table=True):
    """Per-project counter backing each task's human-readable key
    (`"WEB-1"`, `"WEB-2"`, ...). Persisted so numbering survives restarts."""

    __tablename__ = "task_counter"

    projectId: str = Field(primary_key=True)
    value: int = 0


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    # Not constrained with Field(min_length=...) on purpose: the route
    # checks this itself so it can return the spec's 400 instead of
    # FastAPI's default 422 for a body validation failure.
    password: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginInput(BaseModel):
    idToken: str


class UpdateProfileInput(BaseModel):
    name: str


class CreateProjectInput(BaseModel):
    name: str
    key: str | None = None
    description: str | None = ""


class UpdateProjectInput(BaseModel):
    name: str | None = None
    description: str | None = None


class AddMemberInput(BaseModel):
    email: EmailStr
    role: Role


class UpdateMemberRoleInput(BaseModel):
    role: Role


class InviteInput(BaseModel):
    email: EmailStr
    role: Role


class CreateBoardInput(BaseModel):
    name: str


class CreateColumnInput(BaseModel):
    name: str


class RenameColumnInput(BaseModel):
    name: str


class ReorderColumnInput(BaseModel):
    position: int = PField(ge=0)


class CreateTaskInput(BaseModel):
    projectId: str
    boardId: str
    columnId: str
    title: str
    description: str | None = ""
    type: TaskType = TaskType.task
    priority: Priority = Priority.medium
    assigneeId: str | None = None
    labelIds: list[str] = PField(default_factory=list)
    dueDate: str | None = None


class UpdateTaskInput(BaseModel):
    title: str | None = None
    description: str | None = None
    type: TaskType | None = None
    priority: Priority | None = None
    assigneeId: str | None = None
    labelIds: list[str] | None = None
    dueDate: str | None = None
    columnId: str | None = None


class MoveTaskInput(BaseModel):
    columnId: str
    position: int | None = PField(default=None, ge=0)


class AddCommentInput(BaseModel):
    body: str


class CreateLabelInput(BaseModel):
    name: str
    color: str | None = None


class RenameLabelInput(BaseModel):
    name: str


class AddRelationInput(BaseModel):
    relatedTaskId: str
    type: RelationType


class MyRoleResponse(BaseModel):
    role: Role


class TokenResponse(BaseModel):
    token: str
    user: User
