from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project
from ..agents.change_detection import ChangeDetectionAgent, row_from_task

router = APIRouter(prefix="/api/projects/{project_id}/changes", tags=["changes"])
_detector = ChangeDetectionAgent()


@router.get("", response_model=list[schemas.ChangeLogOut])
def list_change_log(project_id: int,
                    proj: models.Project = Depends(require_project),
                    db: Session = Depends(get_db),
                    limit: int = 100):
    return (
        db.query(models.ChangeLog)
        .filter(models.ChangeLog.project_id == proj.id)
        .order_by(models.ChangeLog.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/diff", response_model=schemas.ChangeDetectionReport)
async def diff_against_baseline(project_id: int,
                                proj: models.Project = Depends(require_project),
                                db: Session = Depends(get_db)):
    current = db.query(models.Task).filter(models.Task.project_id == proj.id).all()
    baseline = db.query(models.BaselineTask).filter(models.BaselineTask.project_id == proj.id).all()
    return await _detector.run(
        proj.id,
        [row_from_task(t) for t in baseline],
        [row_from_task(t) for t in current],
    )
