from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from .. import auth
from ..activity_log import log_activity
from ..errors import ApiError, not_found
from ..models import Attachment, User, utcnow_iso
from ..store import new_id, store
from .tasks import get_task_or_404

router = APIRouter(tags=["Attachments"])

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.get("/tasks/{taskId}/attachments", response_model=list[Attachment])
def list_attachments(taskId: str, user: User = Depends(auth.get_current_user)) -> list[Attachment]:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    return [a for a in store.attachments.values() if a.taskId == taskId]


@router.post("/tasks/{taskId}/attachments", status_code=201, response_model=Attachment)
async def upload_attachment(
    taskId: str, file: UploadFile, user: User = Depends(auth.get_current_user)
) -> Attachment:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)

    if not file.filename:
        raise ApiError(400, "File is invalid")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ApiError(400, "File must be 5 MB or smaller")

    attachment_id = new_id("att")
    attachment = Attachment(
        id=attachment_id,
        taskId=taskId,
        filename=file.filename,
        fileType=file.content_type or "application/octet-stream",
        fileSize=len(contents),
        uploadedBy=user.id,
        uploadedAt=utcnow_iso(),
        storageUrl=f"/uploads/{attachment_id}/{file.filename}",
    )
    store.attachments[attachment.id] = attachment
    log_activity(task.projectId, f"{user.name} attached {file.filename} to {task.key}", user.id, task.id)
    return attachment


@router.delete("/attachments/{attachmentId}", status_code=204)
def delete_attachment(attachmentId: str, user: User = Depends(auth.get_current_user)) -> None:
    attachment = store.attachments.get(attachmentId)
    if attachment is None:
        raise not_found("Attachment not found")
    task = get_task_or_404(attachment.taskId)
    auth.require_contributor(task.projectId, user)
    store.attachments.pop(attachmentId, None)
