from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project, require_role
from ..services.webhooks import enqueue_webhook
from ..services.observability import get_logger

router = APIRouter(prefix="/api/projects/{project_id}/drafts", tags=["drafts"])
log = get_logger(__name__)


@router.get("", response_model=list[schemas.DraftOut])
def list_drafts(project_id: int,
                proj: models.Project = Depends(require_project),
                db: Session = Depends(get_db)):
    return (
        db.query(models.PlanUpdateDraft)
        .filter(models.PlanUpdateDraft.project_id == proj.id)
        .order_by(models.PlanUpdateDraft.created_at.desc())
        .all()
    )


@router.get("/{draft_id}", response_model=schemas.DraftOut)
def get_draft(project_id: int, draft_id: int,
              proj: models.Project = Depends(require_project),
              db: Session = Depends(get_db)):
    draft = (
        db.query(models.PlanUpdateDraft)
        .filter(
            models.PlanUpdateDraft.project_id == proj.id,
            models.PlanUpdateDraft.id == draft_id,
        )
        .first()
    )
    if not draft:
        raise HTTPException(404, "Draft not found")
    return draft


@router.post("/{draft_id}/approve", response_model=schemas.DraftOut)
def approve_draft(project_id: int, draft_id: int, decision: schemas.DraftDecision,
                  proj: models.Project = Depends(require_project),
                  user: models.User = Depends(require_role("admin", "reviewer")),
                  db: Session = Depends(get_db)):
    draft = _load_draft(db, proj.id, draft_id)
    if draft.status != "pending":
        raise HTTPException(409, f"Draft already {draft.status}")
    accepted = set(decision.accepted_item_ids or [])
    rejected = set(decision.rejected_item_ids or [])
    note_title = ""
    if draft.note_id:
        n = db.get(models.MeetingNote, draft.note_id)
        note_title = n.title if n else ""

    actor = decision.decided_by or user.email
    for item in draft.items:
        if item.id in rejected:
            item.accepted = False
            continue
        if decision.accepted_item_ids is None or item.id in accepted:
            if item.action == "conflict":
                item.accepted = False
                continue
            item.accepted = True
            _apply(db, proj.id, item, note_title, actor=actor)
    draft.status = "approved"
    draft.decided_at = datetime.utcnow()
    draft.decided_by = actor
    db.commit()
    db.refresh(draft)
    log.info("draft_approved", project_id=proj.id, draft_id=draft.id, actor=actor)
    enqueue_webhook(db, proj.org_id, "draft.approved", {
        "project_id": proj.id, "draft_id": draft.id, "decided_by": actor,
        "accepted": len([i for i in draft.items if i.accepted]),
        "rejected": len([i for i in draft.items if i.accepted is False]),
    })
    return draft


@router.post("/{draft_id}/reject", response_model=schemas.DraftOut)
def reject_draft(project_id: int, draft_id: int, decision: schemas.DraftDecision,
                 proj: models.Project = Depends(require_project),
                 user: models.User = Depends(require_role("admin", "reviewer")),
                 db: Session = Depends(get_db)):
    draft = _load_draft(db, proj.id, draft_id)
    if draft.status != "pending":
        raise HTTPException(409, f"Draft already {draft.status}")
    for item in draft.items:
        item.accepted = False
    draft.status = "rejected"
    draft.decided_at = datetime.utcnow()
    draft.decided_by = decision.decided_by or user.email
    db.commit()
    db.refresh(draft)
    log.info("draft_rejected", project_id=proj.id, draft_id=draft.id, actor=draft.decided_by)
    return draft


def _load_draft(db: Session, project_id: int, draft_id: int) -> models.PlanUpdateDraft:
    draft = (
        db.query(models.PlanUpdateDraft)
        .filter(
            models.PlanUpdateDraft.project_id == project_id,
            models.PlanUpdateDraft.id == draft_id,
        )
        .first()
    )
    if not draft:
        raise HTTPException(404, "Draft not found")
    return draft


def _apply(db: Session, project_id: int, item: models.DraftItem,
           note_title: str, actor: str = "agent") -> None:
    """Apply one accepted draft item to the live plan + write change-log rows."""
    source = f"note:{note_title}" if note_title else "agent"
    if item.action == "create":
        existing = (
            db.query(models.Task)
            .filter(models.Task.project_id == project_id, models.Task.code == item.task_code)
            .first()
        )
        if existing:
            return _apply_update(db, project_id, existing, item, source, actor)
        task = models.Task(
            project_id=project_id, code=item.task_code, title=item.title,
            owner=item.owner or "", status=item.status or "not_started",
            priority=item.priority or "medium",
            start_date=item.start_date, due_date=item.due_date,
            dependencies=item.dependencies or "",
            notes=item.evidence or "",
        )
        db.add(task)
        db.add(models.ChangeLog(
            project_id=project_id, task_code=task.code, field="task",
            old_value="", new_value=task.title, source=source,
            actor=actor, rationale=item.rationale or "Draft accepted",
        ))
        return
    if item.action in ("update",):
        task = (
            db.query(models.Task)
            .filter(models.Task.project_id == project_id, models.Task.code == item.task_code)
            .first()
        )
        if not task:
            return
        return _apply_update(db, project_id, task, item, source, actor)


def _apply_update(db, project_id, task, item, source, actor):
    fields = {
        "title": item.title, "owner": item.owner, "status": item.status,
        "priority": item.priority, "start_date": item.start_date,
        "due_date": item.due_date, "dependencies": item.dependencies,
    }
    for field, new in fields.items():
        if new in (None, ""):
            continue
        old = getattr(task, field)
        if str(old or "") == str(new or ""):
            continue
        setattr(task, field, new)
        db.add(models.ChangeLog(
            project_id=project_id, task_code=task.code, field=field,
            old_value=str(old or ""), new_value=str(new or ""),
            source=source, actor=actor, rationale=item.rationale or "Draft accepted",
        ))
    task.updated_at = datetime.utcnow()
