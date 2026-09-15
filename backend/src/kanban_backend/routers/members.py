from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..errors import ApiError, forbidden, not_found
from ..models import (
    AddMemberInput,
    Invitation,
    InvitationStatus,
    InvitationWithProject,
    InviteInput,
    MemberWithUser,
    ProjectMember,
    Role,
    UpdateMemberRoleInput,
    User,
    utcnow_iso,
)
from ..store import new_id, store
from ..viewmodels import invitation_with_project, member_with_user
from .projects import get_project_or_404

router = APIRouter(tags=["Members & Invitations"])


@router.get("/projects/{projectId}/members", response_model=list[MemberWithUser])
def list_members(projectId: str, user: User = Depends(auth.get_current_user)) -> list[MemberWithUser]:
    get_project_or_404(projectId)
    auth.require_member(projectId, user)
    return [member_with_user(m) for m in store.list_members(projectId)]


@router.post("/projects/{projectId}/members", status_code=201, response_model=MemberWithUser)
def add_member(
    projectId: str, input: AddMemberInput, user: User = Depends(auth.get_current_user)
) -> MemberWithUser:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)

    email = input.email.lower()
    target = next((u for u in store.users.values() if u.email.lower() == email), None)
    if target is None:
        raise not_found("No account exists with that email")
    if store.get_member(projectId, target.id) is not None:
        raise ApiError(409, "That user is already a member")

    member = ProjectMember(
        id=new_id("mem"),
        projectId=projectId,
        userId=target.id,
        role=input.role,
        createdAt=utcnow_iso(),
    )
    store.members[member.id] = member
    return member_with_user(member)


def _get_member_or_404(project_id: str, user_id: str) -> ProjectMember:
    member = store.get_member(project_id, user_id)
    if member is None:
        raise not_found("Member not found")
    return member


@router.patch("/projects/{projectId}/members/{userId}", response_model=MemberWithUser)
def update_member_role(
    projectId: str, userId: str, input: UpdateMemberRoleInput, user: User = Depends(auth.get_current_user)
) -> MemberWithUser:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    member = _get_member_or_404(projectId, userId)

    if member.role == Role.admin and input.role != Role.admin and store.admin_count(projectId) <= 1:
        raise ApiError(400, "A project needs at least one admin")

    member.role = input.role
    return member_with_user(member)


@router.delete("/projects/{projectId}/members/{userId}", status_code=204)
def remove_member(projectId: str, userId: str, user: User = Depends(auth.get_current_user)) -> None:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    member = _get_member_or_404(projectId, userId)

    if member.role == Role.admin and store.admin_count(projectId) <= 1:
        raise ApiError(400, "A project needs at least one admin")

    store.members.pop(member.id, None)
    store.unassign_user_in_project(projectId, userId)


@router.get("/projects/{projectId}/invitations", response_model=list[Invitation])
def list_invitations(projectId: str, user: User = Depends(auth.get_current_user)) -> list[Invitation]:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)
    return [i for i in store.invitations.values() if i.projectId == projectId]


@router.post("/projects/{projectId}/invitations", status_code=201, response_model=Invitation)
def invite_user(
    projectId: str, input: InviteInput, user: User = Depends(auth.get_current_user)
) -> Invitation:
    get_project_or_404(projectId)
    auth.require_admin(projectId, user)

    email = input.email.lower()
    existing_user = next((u for u in store.users.values() if u.email.lower() == email), None)
    if existing_user and store.get_member(projectId, existing_user.id) is not None:
        raise ApiError(409, "That user is already a member")
    pending = any(
        i.projectId == projectId and i.email.lower() == email and i.status == InvitationStatus.pending
        for i in store.invitations.values()
    )
    if pending:
        raise ApiError(409, "An invitation is already pending for that email")

    invitation = Invitation(
        id=new_id("inv"),
        projectId=projectId,
        email=email,
        role=input.role,
        status=InvitationStatus.pending,
        invitedBy=user.id,
        createdAt=utcnow_iso(),
    )
    store.invitations[invitation.id] = invitation
    return invitation


@router.get("/invitations/mine", response_model=list[InvitationWithProject])
def list_my_invitations(user: User = Depends(auth.get_current_user)) -> list[InvitationWithProject]:
    email = user.email.lower()
    mine = [
        i
        for i in store.invitations.values()
        if i.email.lower() == email and i.status == InvitationStatus.pending
    ]
    return [invitation_with_project(i) for i in mine]


def _get_invitation_or_404(invitation_id: str) -> Invitation:
    invitation = store.invitations.get(invitation_id)
    if invitation is None:
        raise not_found("Invitation not found")
    return invitation


@router.delete("/invitations/{invitationId}", status_code=204)
def revoke_invitation(invitationId: str, user: User = Depends(auth.get_current_user)) -> None:
    invitation = _get_invitation_or_404(invitationId)
    auth.require_admin(invitation.projectId, user)
    store.invitations.pop(invitationId, None)


@router.post("/invitations/{invitationId}/accept", status_code=204)
def accept_invitation(invitationId: str, user: User = Depends(auth.get_current_user)) -> None:
    invitation = _get_invitation_or_404(invitationId)
    if invitation.email.lower() != user.email.lower():
        raise forbidden("That invitation is for another account")

    if store.get_member(invitation.projectId, user.id) is None:
        member = ProjectMember(
            id=new_id("mem"),
            projectId=invitation.projectId,
            userId=user.id,
            role=invitation.role,
            createdAt=utcnow_iso(),
        )
        store.members[member.id] = member
    invitation.status = InvitationStatus.accepted
