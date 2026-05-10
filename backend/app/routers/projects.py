from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user, require_role

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return db.query(models.Project).filter(models.Project.org_id == user.org_id).all()


@router.post("", response_model=schemas.ProjectOut, status_code=201)
def create_project(payload: schemas.ProjectCreate,
                   admin: models.User = Depends(require_role("admin")),
                   db: Session = Depends(get_db)):
    if db.query(models.Project).filter(
        models.Project.org_id == admin.org_id, models.Project.name == payload.name
    ).first():
        raise HTTPException(409, "Project name already exists")
    proj = models.Project(org_id=admin.org_id, **payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj
