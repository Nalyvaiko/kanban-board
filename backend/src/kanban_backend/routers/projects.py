from __future__ import annotations

import re

from fastapi import APIRouter, Depends

from .. import auth
from ..errors import ApiError, not_found
from ..models import (
    CreateProjectInput,
    MyRoleResponse,
    Project,
    ProjectMember,
    Role,
    UpdateProjectInput,
    User,
    utcnow_iso,
)
from ..seed import create_default_board
from ..store import new_id, store

router = APIRouter(tags=["Projects"])


def get_project_or_404(project_id: str) -> Project:
    project = store.projects.get(project_id)
    if project is None:
        raise not_found("Project not found")
    return project


def _slugify_key(name: str) -> str:
    letters = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    return (letters or "PRJ")[:6]


@router.get("/projects", response_model=list[Project])
def list_projects(user: User = Depends(auth.get_current_user)) -> list[Project]:
    project_ids = {m.projectId for m in store.members.values() if m.userId == user.id}
    return [p for p in store.projects.values() if p.id in project_ids]


@router.post("/projects", status_code=201, response_model=Project)
def create_project(input: CreateProjectInput, user: User = Depends(auth.get_current_user)) -> Project:
    name = input.name.strip()
    if not name:
        raise ApiError(400, "Project name is required")

    key = re.sub(r"[^A-Z0-9]", "", (input.key or "").upper()) or _slugify_key(name)
    if any(p.key == key for p in store.projects.values()):
        raise ApiError(409, "That project key is already in use")

    now = utcnow_iso()
    project = Project(
        id=new_id("proj"),
        key=key,
        name=name,
        description=input.description or "",
        createdBy=user.id,
        createdAt=now,
    )
    store.projects[project.id] = project

    member = ProjectMember(
        id=new_id("mem"), projectId=project.id, userId=user.id, role=Role.admin, createdAt=now
    )
    store.members[member.id] = member

    create_default_board(store, project.id, "Main Board")
    return project


@router.get("/projects/{projectId}", response_model=Project)
def get_project(projectId: str, user: User = Depends(auth.get_current_user)) -> Project:
    project = get_project_or_404(projectId)
    auth.require_member(projectId, user)
    return project


@router.patch("/projects/{projectId}", response_model=Project)
def update_project(
    projectId: str, input: UpdateProjectInput, user: User = Depends(auth.get_current_user)
) -> Project:
    project = get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    if input.name is not None:
        project.name = input.name
    if input.description is not None:
        project.description = input.description
    return project


@router.delete("/projects/{projectId}", status_code=204)
def delete_project(projectId: str, user: User = Depends(auth.get_current_user)) -> None:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    store.delete_project_cascade(projectId)


@router.get("/projects/{projectId}/my-role", response_model=MyRoleResponse)
def get_my_role(projectId: str, user: User = Depends(auth.get_current_user)) -> MyRoleResponse:
    get_project_or_404(projectId)
    member = store.get_member(projectId, user.id)
    if member is None:
        raise ApiError(403, "You are not a member of this project")
    return MyRoleResponse(role=member.role)
