"""Tabular exports for Power BI / Excel / Power Query.

Provides the same projections as the SQL views in ``infra/powerbi/views.sql``
but reachable directly via HTTPS so consumers that cannot connect to Postgres
(e.g. Power BI Service in another tenant, Power Automate flow that feeds an
Excel file) can ingest the data with ``Web.Contents()``.

Every endpoint returns a CSV by default; pass ``format=json`` for JSON.
All exports are scoped to the caller's organisation.
"""
import csv
import io
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _emit(rows: list[dict[str, Any]], columns: list[str], fmt: str, filename: str):
    if fmt == "json":
        # ``jsonable_encoder`` handles date/datetime → ISO-8601 strings, which is
        # what Power Query / Excel / pandas all expect.
        return JSONResponse(jsonable_encoder(rows))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ("" if r.get(k) is None else r[k]) for k in columns})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get("/tasks")
def export_tasks(format: str = Query("csv", pattern="^(csv|json)$"),
                 user: models.User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    today = date.today()
    horizon = today + timedelta(days=7)
    stmt = (
        select(models.Task, models.Project)
        .join(models.Project, models.Project.id == models.Task.project_id)
        .where(models.Project.org_id == user.org_id)
    )
    rows = []
    for task, proj in db.execute(stmt).all():
        rows.append({
            "task_id": task.id, "task_code": task.code,
            "org_id": proj.org_id, "project_id": proj.id, "project_name": proj.name,
            "title": task.title, "owner": task.owner, "status": task.status,
            "priority": task.priority, "start_date": task.start_date,
            "due_date": task.due_date, "progress": task.progress or 0.0,
            "dependencies": task.dependencies,
            "is_overdue": int(bool(task.due_date and task.due_date < today
                                   and task.status != "done")),
            "is_due_within_7d": int(bool(task.due_date and today <= task.due_date <= horizon
                                         and task.status != "done")),
            "updated_at": task.updated_at,
        })
    cols = ["task_id", "task_code", "org_id", "project_id", "project_name",
            "title", "owner", "status", "priority", "start_date", "due_date",
            "progress", "dependencies", "is_overdue", "is_due_within_7d",
            "updated_at"]
    return _emit(rows, cols, format, "sj_planner_tasks")


@router.get("/change_log")
def export_change_log(format: str = Query("csv", pattern="^(csv|json)$"),
                      user: models.User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    stmt = (
        select(models.ChangeLog, models.Project)
        .join(models.Project, models.Project.id == models.ChangeLog.project_id)
        .where(models.Project.org_id == user.org_id)
        .order_by(models.ChangeLog.created_at.desc())
    )
    rows = [{
        "change_id": c.id, "org_id": p.org_id, "project_id": p.id,
        "project_name": p.name, "task_code": c.task_code, "field": c.field,
        "old_value": c.old_value, "new_value": c.new_value,
        "source": c.source, "actor": c.actor, "rationale": c.rationale,
        "created_at": c.created_at,
    } for c, p in db.execute(stmt).all()]
    cols = ["change_id", "org_id", "project_id", "project_name", "task_code",
            "field", "old_value", "new_value", "source", "actor", "rationale",
            "created_at"]
    return _emit(rows, cols, format, "sj_planner_change_log")


@router.get("/drafts")
def export_drafts(format: str = Query("csv", pattern="^(csv|json)$"),
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    stmt = (
        select(models.PlanUpdateDraft, models.Project)
        .join(models.Project, models.Project.id == models.PlanUpdateDraft.project_id)
        .where(models.Project.org_id == user.org_id)
    )
    rows = []
    for d, p in db.execute(stmt).all():
        items = d.items
        accepted = sum(1 for i in items if i.accepted is True)
        rejected = sum(1 for i in items if i.accepted is False)
        conflicts = sum(1 for i in items if i.action == "conflict")
        hrs = None
        if d.decided_at and d.created_at:
            hrs = round((d.decided_at - d.created_at).total_seconds() / 3600.0, 2)
        rows.append({
            "draft_id": d.id, "org_id": p.org_id, "project_id": p.id,
            "project_name": p.name, "note_id": d.note_id, "summary": d.summary,
            "status": d.status, "decided_by": d.decided_by,
            "created_at": d.created_at, "decided_at": d.decided_at,
            "hours_to_decision": hrs, "item_count": len(items),
            "accepted_count": accepted, "rejected_count": rejected,
            "conflict_count": conflicts,
        })
    cols = ["draft_id", "org_id", "project_id", "project_name", "note_id",
            "summary", "status", "decided_by", "created_at", "decided_at",
            "hours_to_decision", "item_count", "accepted_count",
            "rejected_count", "conflict_count"]
    return _emit(rows, cols, format, "sj_planner_drafts")


@router.get("/clarifications")
def export_clarifications(format: str = Query("csv", pattern="^(csv|json)$"),
                          user: models.User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    stmt = (
        select(models.Clarification, models.Project)
        .join(models.Project, models.Project.id == models.Clarification.project_id)
        .where(models.Project.org_id == user.org_id)
    )
    rows = []
    for c, p in db.execute(stmt).all():
        hrs = None
        if c.answered_at and c.created_at:
            hrs = round((c.answered_at - c.created_at).total_seconds() / 3600.0, 2)
        rows.append({
            "clarification_id": c.id, "org_id": p.org_id, "project_id": p.id,
            "project_name": p.name, "draft_item_id": c.draft_item_id,
            "question": c.question, "context": c.context, "answer": c.answer,
            "status": c.status, "created_at": c.created_at,
            "answered_at": c.answered_at, "hours_to_answer": hrs,
        })
    cols = ["clarification_id", "org_id", "project_id", "project_name",
            "draft_item_id", "question", "context", "answer", "status",
            "created_at", "answered_at", "hours_to_answer"]
    return _emit(rows, cols, format, "sj_planner_clarifications")
