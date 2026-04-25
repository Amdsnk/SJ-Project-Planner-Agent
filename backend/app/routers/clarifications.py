from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project, require_role

router = APIRouter(prefix="/api/projects/{project_id}/clarifications", tags=["clarifications"])


@router.get("", response_model=list[schemas.ClarificationOut])
def list_clarifications(project_id: int,
                        proj: models.Project = Depends(require_project),
                        db: Session = Depends(get_db),
                        status: str | None = None):
    q = db.query(models.Clarification).filter(models.Clarification.project_id == proj.id)
    if status:
        q = q.filter(models.Clarification.status == status)
    return q.order_by(models.Clarification.created_at.desc()).all()


@router.post("/{clarification_id}/answer", response_model=schemas.ClarificationOut)
def answer_clarification(project_id: int, clarification_id: int,
                         payload: schemas.ClarificationAnswer,
                         proj: models.Project = Depends(require_project),
                         user: models.User = Depends(require_role("admin", "reviewer")),
                         db: Session = Depends(get_db)):
    c = (
        db.query(models.Clarification)
        .filter(
            models.Clarification.project_id == proj.id,
            models.Clarification.id == clarification_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(404, "Clarification not found")
    c.answer = payload.answer
    c.status = "answered"
    c.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c


@router.post("/{clarification_id}/dismiss", response_model=schemas.ClarificationOut)
def dismiss_clarification(project_id: int, clarification_id: int,
                          proj: models.Project = Depends(require_project),
                          user: models.User = Depends(require_role("admin", "reviewer")),
                          db: Session = Depends(get_db)):
    c = (
        db.query(models.Clarification)
        .filter(
            models.Clarification.project_id == proj.id,
            models.Clarification.id == clarification_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(404, "Clarification not found")
    c.status = "dismissed"
    c.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c
