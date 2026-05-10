from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_project
from ..agents.priority import PriorityAgent
from ..agents.assignment import AssignmentAgent

router = APIRouter(prefix="/api/projects/{project_id}", tags=["dashboard"])
_priority = PriorityAgent()
_assigner = AssignmentAgent()


@router.get("/dashboard", response_model=schemas.DashboardKPIs)
def kpis(project_id: int,
         proj: models.Project = Depends(require_project),
         db: Session = Depends(get_db)):
    today = date.today()
    tasks = db.query(models.Task).filter(models.Task.project_id == proj.id).all()
    pending_drafts = (
        db.query(models.PlanUpdateDraft)
        .filter(models.PlanUpdateDraft.project_id == proj.id,
                models.PlanUpdateDraft.status == "pending")
        .count()
    )
    open_clarifications = (
        db.query(models.Clarification)
        .filter(models.Clarification.project_id == proj.id,
                models.Clarification.status == "open")
        .count()
    )
    return schemas.DashboardKPIs(
        total_tasks=len(tasks),
        not_started=sum(1 for t in tasks if t.status == "not_started"),
        in_progress=sum(1 for t in tasks if t.status == "in_progress"),
        blocked=sum(1 for t in tasks if t.status == "blocked"),
        done=sum(1 for t in tasks if t.status == "done"),
        overdue=sum(1 for t in tasks if t.due_date and t.due_date < today and t.status != "done"),
        upcoming_7d=sum(
            1 for t in tasks if t.due_date and today <= t.due_date <= today + timedelta(days=7)
            and t.status != "done"
        ),
        pending_drafts=pending_drafts,
        open_clarifications=open_clarifications,
    )


@router.get("/priority")
async def priority_ranking(project_id: int,
                           proj: models.Project = Depends(require_project),
                           db: Session = Depends(get_db)):
    tasks = db.query(models.Task).filter(models.Task.project_id == proj.id).all()
    ranked = await _priority.run(tasks)
    return [{"code": r.code, "title": r.title, "score": r.score, "reason": r.reason}
            for r in ranked]


@router.get("/assignments", response_model=list[schemas.AssignmentSuggestion])
async def assignment_suggestions(project_id: int,
                                 proj: models.Project = Depends(require_project),
                                 db: Session = Depends(get_db)):
    tasks = db.query(models.Task).filter(models.Task.project_id == proj.id).all()
    members = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.org_id == proj.org_id)
        .all()
    )
    return await _assigner.run(tasks, members)


@router.get("/team", response_model=list[schemas.TeamMemberOut])
def team(project_id: int,
         proj: models.Project = Depends(require_project),
         db: Session = Depends(get_db)):
    return (
        db.query(models.TeamMember)
        .filter(models.TeamMember.org_id == proj.org_id)
        .order_by(models.TeamMember.name)
        .all()
    )
