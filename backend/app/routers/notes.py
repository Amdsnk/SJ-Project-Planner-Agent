from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project, require_role
from ..agents.orchestrator import PlannerOrchestrator
from ..services.webhooks import enqueue_webhook
from ..services.observability import get_logger
from ..services.rate_limit import limiter

router = APIRouter(prefix="/api/projects/{project_id}/notes", tags=["notes"])
_orchestrator = PlannerOrchestrator()
log = get_logger(__name__)


@router.get("", response_model=list[schemas.MeetingNoteOut])
def list_notes(project_id: int,
               proj: models.Project = Depends(require_project),
               db: Session = Depends(get_db)):
    return (
        db.query(models.MeetingNote)
        .filter(models.MeetingNote.project_id == proj.id)
        .order_by(models.MeetingNote.occurred_at.desc())
        .all()
    )


@router.post("", response_model=schemas.MeetingNoteOut, status_code=201)
@limiter.limit("30/minute")
def create_note(request: Request, project_id: int, payload: schemas.MeetingNoteIn,
                proj: models.Project = Depends(require_project),
                user: models.User = Depends(require_role("admin", "reviewer")),
                db: Session = Depends(get_db)):
    note = models.MeetingNote(
        project_id=proj.id,
        source_type=payload.source_type,
        title=payload.title or "(untitled)",
        attendees=payload.attendees,
        occurred_at=payload.occurred_at or datetime.utcnow(),
        content=payload.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    log.info("note_created", project_id=proj.id, note_id=note.id, actor=user.email)
    return note


@router.post("/{note_id}/process", response_model=schemas.DraftOut)
@limiter.limit("10/minute")
async def process_note(request: Request, project_id: int, note_id: int,
                       proj: models.Project = Depends(require_project),
                       user: models.User = Depends(require_role("admin", "reviewer")),
                       db: Session = Depends(get_db)):
    note = (
        db.query(models.MeetingNote)
        .filter(models.MeetingNote.project_id == proj.id, models.MeetingNote.id == note_id)
        .first()
    )
    if not note:
        raise HTTPException(404, "Note not found")
    draft = await _orchestrator.process_note(db, note)
    db.refresh(draft)
    log.info("draft_created", project_id=proj.id, draft_id=draft.id,
             items=len(draft.items), actor=user.email)
    enqueue_webhook(db, proj.org_id, "draft.created", {
        "project_id": proj.id, "draft_id": draft.id, "items": len(draft.items),
        "summary": draft.summary, "source_note_id": note.id,
    })
    return draft
