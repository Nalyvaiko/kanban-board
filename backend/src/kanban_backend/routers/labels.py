from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..errors import ApiError, not_found
from ..models import CreateLabelInput, Label, RenameLabelInput, User
from ..store import new_id, store
from .projects import get_project_or_404

router = APIRouter(tags=["Labels"])

_PALETTE = ["#3b82f6", "#8b5cf6", "#ef4444", "#f97316", "#10b981", "#06b6d4", "#eab308"]


def get_label_or_404(label_id: str) -> Label:
    label = store.labels.get(label_id)
    if label is None:
        raise not_found("Label not found")
    return label


@router.get("/projects/{projectId}/labels", response_model=list[Label])
def list_labels(projectId: str, user: User = Depends(auth.get_current_user)) -> list[Label]:
    get_project_or_404(projectId)
    auth.require_member(projectId, user)
    return [l for l in store.labels.values() if l.projectId == projectId]


@router.post("/projects/{projectId}/labels", status_code=201, response_model=Label)
def create_label(
    projectId: str, input: CreateLabelInput, user: User = Depends(auth.get_current_user)
) -> Label:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)

    name = input.name.strip().lower()
    if not name:
        raise ApiError(400, "Label name is required")
    if any(l.projectId == projectId and l.name == name for l in store.labels.values()):
        raise ApiError(409, "That label already exists")

    existing_count = sum(1 for l in store.labels.values() if l.projectId == projectId)
    color = input.color or _PALETTE[existing_count % len(_PALETTE)]
    label = Label(id=new_id("label"), projectId=projectId, name=name, color=color)
    store.labels[label.id] = label
    return label


@router.patch("/labels/{labelId}", response_model=Label)
def rename_label(labelId: str, input: RenameLabelInput, user: User = Depends(auth.get_current_user)) -> Label:
    label = get_label_or_404(labelId)
    auth.require_admin(label.projectId, user)
    label.name = input.name.strip().lower()
    return label


@router.delete("/labels/{labelId}", status_code=204)
def delete_label(labelId: str, user: User = Depends(auth.get_current_user)) -> None:
    label = get_label_or_404(labelId)
    auth.require_admin(label.projectId, user)
    store.remove_label_everywhere(labelId)
    store.labels.pop(labelId, None)
