from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, Depends, UploadFile

from .. import auth
from ..activity_log import log_activity
from ..errors import ApiError, not_found
from ..models import Attachment, User, utcnow_iso
from ..store import new_id, store
from .tasks import get_task_or_404

router = APIRouter(tags=["Attachments"])

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
_CHUNK_SIZE = 64 * 1024


def _clean_filename(raw: str | None) -> str | None:
    """Reduce a client-supplied filename to a plain, printable basename.

    Some clients send a full path (`C:\\Users\\me\\report.pdf`), and nothing
    stops a crafted request from sending `../../x` or control characters.
    Returns None when nothing usable is left.
    """
    if not raw:
        return None
    name = PurePosixPath(raw.replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    if name in {"", ".", ".."}:
        return None
    if len(name) > MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) < 16:
            name = stem[: MAX_FILENAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:MAX_FILENAME_LENGTH]
    return name


async def _measure(file: UploadFile) -> int:
    """Size of the upload, read in chunks and stopping as soon as it's over
    the limit - never holding the whole file in memory (only its metadata is
    kept, so the bytes themselves aren't needed)."""
    size = 0
    while chunk := await file.read(_CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise ApiError(400, "File must be 5 MB or smaller")
    return size


@router.get("/tasks/{taskId}/attachments", response_model=list[Attachment])
def list_attachments(taskId: str, user: User = Depends(auth.get_current_user)) -> list[Attachment]:
    task = get_task_or_404(taskId)
    auth.require_member(task.projectId, user)
    return store.attachments.where(Attachment.taskId == taskId)


@router.post("/tasks/{taskId}/attachments", status_code=201, response_model=Attachment)
async def upload_attachment(
    taskId: str, file: UploadFile, user: User = Depends(auth.get_current_user)
) -> Attachment:
    task = get_task_or_404(taskId)
    auth.require_contributor(task.projectId, user)

    filename = _clean_filename(file.filename)
    if filename is None:
        raise ApiError(400, "File is invalid")

    size = await _measure(file)

    attachment_id = new_id("att")
    attachment = Attachment(
        id=attachment_id,
        taskId=taskId,
        filename=filename,
        fileType=file.content_type or "application/octet-stream",
        fileSize=size,
        uploadedBy=user.id,
        uploadedAt=utcnow_iso(),
        storageUrl=f"/uploads/{attachment_id}/{quote(filename)}",
    )
    store.attachments[attachment.id] = attachment
    log_activity(task.projectId, f"{user.name} attached {filename} to {task.key}", user.id, task.id)
    return attachment


@router.delete("/attachments/{attachmentId}", status_code=204)
def delete_attachment(attachmentId: str, user: User = Depends(auth.get_current_user)) -> None:
    attachment = store.attachments.get(attachmentId)
    if attachment is None:
        raise not_found("Attachment not found")
    task = get_task_or_404(attachment.taskId)
    auth.require_contributor(task.projectId, user)
    store.attachments.pop(attachmentId, None)
