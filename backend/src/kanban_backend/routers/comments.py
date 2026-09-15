from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..activity_log import log_activity
from ..errors import ApiError, forbidden, not_found
from ..models import AddCommentInput, Comment, CommentWithAuthor, Role, User, utcnow_iso
from ..store import new_id, store
from ..viewmodels import comment_with_author
from .tasks import get_task_or_404

router = APIRouter(tags=["Comments"])


@router.get("/tasks/{taskId}/comments", response_model=list[CommentWithAuthor])
def list_comments(taskId: str, user: User = Depends(auth.get_current_user)) -> list[CommentWithAuthor]:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    comments = sorted(
        (c for c in store.comments.values() if c.taskId == taskId), key=lambda c: c.createdAt
    )
    return [comment_with_author(c) for c in comments]


@router.post("/tasks/{taskId}/comments", status_code=201, response_model=CommentWithAuthor)
def add_comment(
    taskId: str, input: AddCommentInput, user: User = Depends(auth.get_current_user)
) -> CommentWithAuthor:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)
    body = input.body.strip()
    if not body:
        raise ApiError(400, "Comment cannot be empty")

    now = utcnow_iso()
    comment = Comment(
        id=new_id("comment"), taskId=taskId, authorId=user.id, body=body, createdAt=now, updatedAt=now
    )
    store.comments[comment.id] = comment
    log_activity(task.projectId, f"{user.name} commented on {task.key}", user.id, task.id)
    return comment_with_author(comment)


def _get_comment_or_404(comment_id: str) -> Comment:
    comment = store.comments.get(comment_id)
    if comment is None:
        raise not_found("Comment not found")
    return comment


@router.patch("/comments/{commentId}", response_model=CommentWithAuthor)
def update_comment(
    commentId: str, input: AddCommentInput, user: User = Depends(auth.get_current_user)
) -> CommentWithAuthor:
    comment = _get_comment_or_404(commentId)
    if comment.authorId != user.id:
        raise forbidden("You can only edit your own comments")
    body = input.body.strip()
    if not body:
        raise ApiError(400, "Comment cannot be empty")
    comment.body = body
    comment.updatedAt = utcnow_iso()
    return comment_with_author(comment)


@router.delete("/comments/{commentId}", status_code=204)
def delete_comment(commentId: str, user: User = Depends(auth.get_current_user)) -> None:
    comment = _get_comment_or_404(commentId)
    task = store.tasks.get(comment.taskId)
    is_author = comment.authorId == user.id
    is_admin = task is not None and (m := store.get_member(task.projectId, user.id)) and m.role == Role.admin
    if not is_author and not is_admin:
        raise forbidden("You can only delete your own comments")
    store.comments.pop(commentId, None)
