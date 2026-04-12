from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project, require_role

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(project_id: int,
               proj: models.Project = Depends(require_project),
               db: Session = Depends(get_db)):
    return (
        db.query(models.Task)
        .filter(models.Task.project_id == proj.id)
        .order_by(models.Task.code)
        .all()
    )


@router.post("", response_model=schemas.TaskOut, status_code=201)
def create_task(project_id: int, payload: schemas.TaskCreate,
                proj: models.Project = Depends(require_project),
                user: models.User = Depends(require_role("admin", "reviewer")),
                db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["project_id"] = proj.id
    task = models.Task(**data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(project_id: int, task_id: int, payload: schemas.TaskUpdate,
                proj: models.Project = Depends(require_project),
                user: models.User = Depends(require_role("admin", "reviewer")),
                db: Session = Depends(get_db)):
    task = (
        db.query(models.Task)
        .filter(models.Task.project_id == proj.id, models.Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(404, "Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(task, field)
        if old != value:
            db.add(models.ChangeLog(
                project_id=proj.id, task_code=task.code, field=field,
                old_value=str(old or ""), new_value=str(value or ""),
                source="manual_edit", actor=user.email,
                rationale="Manual task edit via API",
            ))
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(project_id: int, task_id: int,
                proj: models.Project = Depends(require_project),
                user: models.User = Depends(require_role("admin", "reviewer")),
                db: Session = Depends(get_db)):
    task = (
        db.query(models.Task)
        .filter(models.Task.project_id == proj.id, models.Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(404, "Task not found")
    db.add(models.ChangeLog(
        project_id=proj.id, task_code=task.code, field="task",
        old_value=task.title, new_value="", source="manual_delete",
        actor=user.email, rationale="Task deleted via API",
    ))
    db.delete(task)
    db.commit()
    return {"ok": True}
