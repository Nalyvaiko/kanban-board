"""Pydantic schemas for every domain entity and request/response body.

These mirror the shapes described in `openapi.yaml` at the repo root, with
one deliberate deviation: authentication uses bearer tokens instead of
session cookies (see `auth.py`), so the auth endpoints return a token
alongside the user.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


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
# Core entities
# ---------------------------------------------------------------------------


class User(BaseModel):
    id: str
    name: str
    email: str
    avatarColor: str
    provider: Provider
    createdAt: str


class Project(BaseModel):
    id: str
    key: str
    name: str
    description: str = ""
    createdBy: str
    createdAt: str


class ProjectMember(BaseModel):
    id: str
    projectId: str
    userId: str
    role: Role
    createdAt: str


class MemberWithUser(ProjectMember):
    user: User


class Board(BaseModel):
    id: str
    projectId: str
    name: str
    createdAt: str


class Column(BaseModel):
    id: str
    boardId: str
    name: str
    position: int


class Label(BaseModel):
    id: str
    projectId: str
    name: str
    color: str


class Task(BaseModel):
    id: str
    key: str
    projectId: str
    boardId: str
    columnId: str
    title: str
    description: str = ""
    type: TaskType = TaskType.task
    priority: Priority = Priority.medium
    assigneeId: str | None = None
    labelIds: list[str] = Field(default_factory=list)
    dueDate: str | None = None
    position: int
    createdBy: str
    createdAt: str
    updatedAt: str


class Comment(BaseModel):
    id: str
    taskId: str
    authorId: str
    body: str
    createdAt: str
    updatedAt: str


class CommentWithAuthor(Comment):
    author: User


class Attachment(BaseModel):
    id: str
    taskId: str
    filename: str
    fileType: str
    fileSize: int
    uploadedBy: str
    uploadedAt: str
    storageUrl: str


class TaskRelation(BaseModel):
    id: str
    taskId: str
    relatedTaskId: str
    type: RelationType
    createdAt: str


class RelationWithTask(TaskRelation):
    relatedTask: Task


class Activity(BaseModel):
    id: str
    projectId: str
    taskId: str | None = None
    actorId: str
    message: str
    createdAt: str


class ActivityWithActor(Activity):
    actor: User


class Invitation(BaseModel):
    id: str
    projectId: str
    email: str
    role: Role
    status: InvitationStatus
    invitedBy: str
    createdAt: str


class InvitationWithProject(Invitation):
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
    position: int = Field(ge=0)


class CreateTaskInput(BaseModel):
    projectId: str
    boardId: str
    columnId: str
    title: str
    description: str | None = ""
    type: TaskType = TaskType.task
    priority: Priority = Priority.medium
    assigneeId: str | None = None
    labelIds: list[str] = Field(default_factory=list)
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
    position: int | None = Field(default=None, ge=0)


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
