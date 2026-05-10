"""Attachment endpoints for meeting notes (e.g. .eml, .docx, .pdf).

Bytes are stored via :mod:`app.services.blob_storage` (Azure Blob when
configured, local filesystem otherwise). Only metadata is persisted in the
relational store.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project, require_role
from ..services import blob_storage
from ..services.observability import get_logger
from ..services.rate_limit import limiter

router = APIRouter(
    prefix="/api/projects/{project_id}/notes/{note_id}/attachments",
    tags=["attachments"],
)
log = get_logger(__name__)

_MAX_BYTES = 25 * 1024 * 1024  # 25 MiB per file


def _resolve_note(db: Session, project_id: int, note_id: int) -> models.MeetingNote:
    note = (
        db.query(models.MeetingNote)
        .filter(models.MeetingNote.project_id == project_id,
                models.MeetingNote.id == note_id)
        .first()
    )
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@router.get("", response_model=list[schemas.NoteAttachmentOut])
def list_attachments(project_id: int, note_id: int,
                     proj: models.Project = Depends(require_project),
                     db: Session = Depends(get_db)):
    _resolve_note(db, proj.id, note_id)
    return (
        db.query(models.NoteAttachment)
        .filter(models.NoteAttachment.note_id == note_id)
        .order_by(models.NoteAttachment.uploaded_at.desc())
        .all()
    )


@router.post("", response_model=schemas.NoteAttachmentOut, status_code=201)
@limiter.limit("20/minute")
async def upload_attachment(request: Request, project_id: int, note_id: int,
                            file: UploadFile = File(...),
                            proj: models.Project = Depends(require_project),
                            user: models.User = Depends(require_role("admin", "reviewer")),
                            db: Session = Depends(get_db)):
    _resolve_note(db, proj.id, note_id)
    payload = await file.read()
    if len(payload) > _MAX_BYTES:
        raise HTTPException(413, f"File exceeds {_MAX_BYTES} bytes limit")
    if not payload:
        raise HTTPException(400, "Empty file")

    stored = blob_storage.upload(proj.id, note_id, file.filename or "upload.bin", payload)
    att = models.NoteAttachment(
        note_id=note_id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        storage_key=stored.key,
        backend=stored.backend,
        uploaded_by=user.email,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    log.info("attachment_uploaded", project_id=proj.id, note_id=note_id,
             attachment_id=att.id, backend=stored.backend, size=stored.size_bytes,
             actor=user.email)
    return att


@router.get("/{attachment_id}/download")
def download_attachment(project_id: int, note_id: int, attachment_id: int,
                        proj: models.Project = Depends(require_project),
                        db: Session = Depends(get_db)):
    _resolve_note(db, proj.id, note_id)
    att = db.get(models.NoteAttachment, attachment_id)
    if not att or att.note_id != note_id:
        raise HTTPException(404, "Attachment not found")
    try:
        gen = blob_storage.stream(att.storage_key, att.backend)
    except FileNotFoundError:
        raise HTTPException(410, "Attachment bytes are no longer available")
    headers = {"content-disposition": f'attachment; filename="{att.filename}"'}
    return StreamingResponse(gen, media_type=att.content_type, headers=headers)


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(project_id: int, note_id: int, attachment_id: int,
                      proj: models.Project = Depends(require_project),
                      user: models.User = Depends(require_role("admin", "reviewer")),
                      db: Session = Depends(get_db)):
    _resolve_note(db, proj.id, note_id)
    att = db.get(models.NoteAttachment, attachment_id)
    if not att or att.note_id != note_id:
        raise HTTPException(404, "Attachment not found")
    blob_storage.delete(att.storage_key, att.backend)
    db.delete(att)
    db.commit()
    log.info("attachment_deleted", project_id=proj.id, attachment_id=attachment_id,
             actor=user.email)
    return None
