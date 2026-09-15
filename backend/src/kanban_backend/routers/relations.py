from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..errors import ApiError, not_found
from ..models import (
    AddRelationInput,
    RelationType,
    RelationWithTask,
    TaskRelation,
    User,
    utcnow_iso,
)
from ..store import new_id, store
from ..viewmodels import relation_with_task
from .tasks import get_task_or_404

router = APIRouter(tags=["Relations"])

_INVERSE = {
    RelationType.blocks: RelationType.blocked_by,
    RelationType.blocked_by: RelationType.blocks,
    RelationType.relates_to: RelationType.relates_to,
}


@router.get("/tasks/{taskId}/relations", response_model=list[RelationWithTask])
def list_relations(taskId: str, user: User = Depends(auth.get_current_user)) -> list[RelationWithTask]:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    relations = [r for r in store.relations.values() if r.taskId == taskId]
    return [relation_with_task(r) for r in relations]


@router.post("/tasks/{taskId}/relations", status_code=201, response_model=RelationWithTask)
def add_relation(
    taskId: str, input: AddRelationInput, user: User = Depends(auth.get_current_user)
) -> RelationWithTask:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)

    if input.relatedTaskId == taskId:
        raise ApiError(400, "A task cannot be linked to itself")
    related_task = get_task_or_404(input.relatedTaskId)
    if related_task.projectId != task.projectId:
        raise ApiError(400, "The tasks belong to different projects")

    already_linked = any(
        r.taskId == taskId and r.relatedTaskId == input.relatedTaskId for r in store.relations.values()
    )
    if already_linked:
        raise ApiError(409, "Those tasks are already linked")

    now = utcnow_iso()
    relation = TaskRelation(
        id=new_id("rel"), taskId=taskId, relatedTaskId=input.relatedTaskId, type=input.type, createdAt=now
    )
    store.relations[relation.id] = relation

    inverse = TaskRelation(
        id=new_id("rel"),
        taskId=input.relatedTaskId,
        relatedTaskId=taskId,
        type=_INVERSE[input.type],
        createdAt=now,
    )
    store.relations[inverse.id] = inverse

    return relation_with_task(relation)


@router.delete("/relations/{relationId}", status_code=204)
def delete_relation(relationId: str, user: User = Depends(auth.get_current_user)) -> None:
    relation = store.relations.get(relationId)
    if relation is None:
        raise not_found("Relation not found")
    task = get_task_or_404(relation.taskId)
    auth.require_contributor(task.projectId, user)

    store.relations.pop(relationId, None)
    inverse = next(
        (
            r
            for r in store.relations.values()
            if r.taskId == relation.relatedTaskId and r.relatedTaskId == relation.taskId
        ),
        None,
    )
    if inverse is not None:
        store.relations.pop(inverse.id, None)
