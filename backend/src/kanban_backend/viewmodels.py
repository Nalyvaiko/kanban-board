"""Composes "with relation" view models (e.g. a comment plus its author)
out of the base entities held in the store. Shared by several routers.
"""

from __future__ import annotations

from .errors import not_found
from .models import (
    Activity,
    ActivityWithActor,
    Comment,
    CommentWithAuthor,
    Invitation,
    InvitationWithProject,
    MemberWithUser,
    ProjectMember,
    RelationWithTask,
    TaskRelation,
)
from .store import Store, store


def _user_or_404(db: Store, user_id: str):
    user = db.users.get(user_id)
    if user is None:
        raise not_found("User not found")
    return user


def member_with_user(member: ProjectMember, db: Store = store) -> MemberWithUser:
    user = _user_or_404(db, member.userId)
    return MemberWithUser(**member.model_dump(), user=user)


def comment_with_author(comment: Comment, db: Store = store) -> CommentWithAuthor:
    author = _user_or_404(db, comment.authorId)
    return CommentWithAuthor(**comment.model_dump(), author=author)


def activity_with_actor(activity: Activity, db: Store = store) -> ActivityWithActor:
    actor = _user_or_404(db, activity.actorId)
    return ActivityWithActor(**activity.model_dump(), actor=actor)


def relation_with_task(relation: TaskRelation, db: Store = store) -> RelationWithTask:
    related_task = db.tasks.get(relation.relatedTaskId)
    if related_task is None:
        raise not_found("Related task not found")
    return RelationWithTask(**relation.model_dump(), relatedTask=related_task)


def invitation_with_project(invitation: Invitation, db: Store = store) -> InvitationWithProject:
    project = db.projects.get(invitation.projectId)
    if project is None:
        raise not_found("Project not found")
    return InvitationWithProject(**invitation.model_dump(), project=project)
