"""Seed data: bootstraps the demo organisation/admin and loads the official
CWB_SJ synthetic dataset (projects, people, baseline + current task snapshots,
dependencies, meeting notes, emails) from
https://github.com/DoreenSteven/CWB_SJ. Falls back to a small built-in
synthetic plan if the dataset cannot be downloaded (offline dev).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..security import hash_password
from . import cwb_sj_loader


PROJECT_NAME = "CWB SJ Delivery Programme"


def _today():
    return date.today()


def _baseline_plan() -> list[dict]:
    t = _today()
    return [
        dict(code="T-001", title="Finalise scope & WBS", owner="Aisha Tan",
             status="done", priority="high",
             start_date=t - timedelta(days=30), due_date=t - timedelta(days=20),
             dependencies=""),
        dict(code="T-002", title="Stakeholder kick-off workshop", owner="Ben Lim",
             status="done", priority="high",
             start_date=t - timedelta(days=22), due_date=t - timedelta(days=18),
             dependencies="T-001"),
        dict(code="T-003", title="Architecture design document v1", owner="Chen Wei",
             status="in_progress", priority="critical",
             start_date=t - timedelta(days=14), due_date=t + timedelta(days=2),
             dependencies="T-002"),
        dict(code="T-004", title="Vendor contract review", owner="Divya Rao",
             status="in_progress", priority="high",
             start_date=t - timedelta(days=10), due_date=t + timedelta(days=5),
             dependencies="T-001"),
        dict(code="T-005", title="Security risk assessment", owner="Ethan Ng",
             status="not_started", priority="high",
             start_date=t + timedelta(days=1), due_date=t + timedelta(days=12),
             dependencies="T-003"),
        dict(code="T-006", title="Build CI/CD pipeline", owner="Farah Idris",
             status="not_started", priority="medium",
             start_date=t + timedelta(days=3), due_date=t + timedelta(days=20),
             dependencies="T-003"),
        dict(code="T-007", title="Data migration dry-run", owner="",
             status="not_started", priority="medium",
             start_date=t + timedelta(days=10), due_date=t + timedelta(days=28),
             dependencies="T-006"),
        dict(code="T-008", title="UAT plan & test cases", owner="Grace Koh",
             status="not_started", priority="medium",
             start_date=t + timedelta(days=15), due_date=t + timedelta(days=35),
             dependencies="T-006"),
        dict(code="T-009", title="Go-live readiness review", owner="Aisha Tan",
             status="not_started", priority="critical",
             start_date=t + timedelta(days=35), due_date=t + timedelta(days=42),
             dependencies="T-005,T-008"),
        dict(code="T-010", title="Post-implementation review", owner="Ben Lim",
             status="not_started", priority="low",
             start_date=t + timedelta(days=50), due_date=t + timedelta(days=60),
             dependencies="T-009"),
    ]


def _team() -> list[dict]:
    return [
        dict(name="Aisha Tan", role="Programme Manager", skills="planning,governance,stakeholder", capacity=0.8),
        dict(name="Ben Lim", role="Delivery Lead", skills="delivery,stakeholder,review", capacity=0.9),
        dict(name="Chen Wei", role="Solution Architect", skills="architecture,design,integration", capacity=0.7),
        dict(name="Divya Rao", role="Procurement", skills="contract,vendor,legal", capacity=1.0),
        dict(name="Ethan Ng", role="Security Lead", skills="security,risk,compliance", capacity=0.8),
        dict(name="Farah Idris", role="DevOps Engineer", skills="cicd,pipeline,infra,build", capacity=1.0),
        dict(name="Grace Koh", role="QA Lead", skills="uat,test,quality", capacity=0.9),
        dict(name="Hari Suresh", role="Data Engineer", skills="data,migration,etl", capacity=0.9),
    ]


def _notes() -> list[dict]:
    t = _today()
    when = lambda d: datetime.combine(t - timedelta(days=d), datetime.min.time()).replace(hour=10)
    return [
        dict(
            source_type="meeting", title="Weekly Delivery Sync",
            attendees="Aisha Tan, Ben Lim, Chen Wei, Farah Idris",
            occurred_at=when(2),
            content=(
                "Agenda: progress on architecture and pipeline.\n"
                "- Chen Wei will deliver Architecture design document v1 by next Friday — slipping by 3 days due to integration questions.\n"
                "- Farah Idris to start Build CI/CD pipeline this week, owner confirmed.\n"
                "- Ethan Ng flagged Security risk assessment is BLOCKED waiting on architecture v1.\n"
                "- New action: Hari Suresh to draft Data migration approach memo by next Wednesday. Priority high.\n"
                "- Decision: Go-live readiness review owner changes from Aisha Tan to Ben Lim."
            ),
        ),
        dict(
            source_type="email", title="Re: Vendor contract status",
            attendees="Divya Rao, Aisha Tan",
            occurred_at=when(1),
            content=(
                "Hi Aisha,\nVendor contract review is on track — I expect to close by Friday. "
                "However, legal raised two clauses that may push the date by a week. "
                "I will update once confirmed. Owner: Divya Rao.\nThanks."
            ),
        ),
        dict(
            source_type="meeting", title="Steering Committee Update",
            attendees="Aisha Tan, Ben Lim, Sponsor",
            occurred_at=when(0),
            content=(
                "Decisions:\n"
                "1. UAT plan & test cases must be ready 5 days earlier — new due date pulled in. Owner Grace Koh.\n"
                "2. Add new task: Executive dashboard for steering committee — Aisha Tan to own, due in 3 weeks, high priority.\n"
                "3. Post-implementation review remains low priority and unchanged.\n"
                "4. Architecture v1 — confirmed critical. Chen Wei to escalate any blockers immediately."
            ),
        ),
        dict(
            source_type="chat", title="Slack thread — pipeline blockers",
            attendees="Farah Idris, Chen Wei",
            occurred_at=when(0),
            content=(
                "Farah: build CI/CD pipeline depends on architecture v1, can we start scaffolding now?\n"
                "Chen: yes, start on the repo + base images. I'll share the design draft tomorrow.\n"
                "Farah: ok, I'll update status to in progress."
            ),
        ),
    ]


def bootstrap_org_and_admin(db: Session) -> models.Organization:
    """Idempotent: ensure default org + admin user exist (used in dev/demo)."""
    org = db.query(models.Organization).filter_by(name=settings.bootstrap_org_name).first()
    if not org:
        org = models.Organization(name=settings.bootstrap_org_name)
        db.add(org)
        db.flush()
    if not db.query(models.User).filter_by(org_id=org.id).first():
        admin = models.User(
            org_id=org.id,
            email=settings.bootstrap_admin_email,
            full_name="Demo Administrator",
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
    db.commit()
    db.refresh(org)
    return org


def seed_if_empty(db: Session) -> None:
    org = bootstrap_org_and_admin(db)

    if db.query(models.Project).filter_by(org_id=org.id).first():
        # Projects already exist — still ensure the demo draft is present.
        _ensure_demo_draft(db, org)
        return

    ds = cwb_sj_loader.load_dataset()
    if ds.loaded:
        _seed_from_cwb_sj(db, org, ds)
    else:
        _seed_synthetic(db, org)
    db.commit()
    _ensure_demo_draft(db, org)


def _ensure_demo_draft(db: Session, org: models.Organization) -> None:
    """Idempotent: guarantee at least one pending draft with items exists for the
    first project so the demo always has something meaningful to show."""
    proj = db.query(models.Project).filter_by(org_id=org.id).first()
    if not proj:
        return
    # Skip if a pending draft with items already exists.
    existing = (
        db.query(models.PlanUpdateDraft)
        .filter_by(project_id=proj.id, status="pending")
        .join(models.PlanUpdateDraft.items)
        .first()
    )
    if existing:
        return

    # Pick the first meeting note with real content (> 60 chars) as the source.
    note = (
        db.query(models.MeetingNote)
        .filter(
            models.MeetingNote.project_id == proj.id,
            models.MeetingNote.content.isnot(None),
        )
        .order_by(models.MeetingNote.id)
        .first()
    )
    note_id = note.id if note else None
    today = _today()

    draft = models.PlanUpdateDraft(
        project_id=proj.id,
        note_id=note_id,
        status="pending",
        summary=(
            "Extraction Agent identified 5 proposed plan changes from the weekly "
            "delivery sync — 3 task updates, 1 new task, 1 owner conflict. "
            "Awaiting human review before any changes touch the official plan."
        ),
    )
    db.add(draft)
    db.flush()

    items = [
        models.DraftItem(
            draft_id=draft.id, action="update",
            task_code="T-003",
            title="Architecture design document v1 — delivery slipping 3 days due to integration queries",
            owner="Chen Wei",
            status="in_progress", priority="critical",
            due_date=today + timedelta(days=7),
            confidence=0.88,
            evidence="Chen Wei will deliver Architecture design document v1 by next Friday — slipping by 3 days due to integration questions.",
            rationale="Date shift detected; owner confirmed; status unchanged.",
        ),
        models.DraftItem(
            draft_id=draft.id, action="update",
            task_code="T-004",
            title="Build CI/CD pipeline — status updated to in_progress, owner confirmed",
            owner="Farah Idris",
            status="in_progress", priority="high",
            due_date=today + timedelta(days=14),
            confidence=0.82,
            evidence="Farah Idris to start Build CI/CD pipeline this week, owner confirmed.",
            rationale="Owner and status signal extracted from note; no date given, current due date preserved.",
        ),
        models.DraftItem(
            draft_id=draft.id, action="update",
            task_code="T-005",
            title="Security risk assessment — BLOCKED waiting on architecture v1",
            owner="Ethan Ng",
            status="blocked", priority="high",
            confidence=0.91,
            evidence="Ethan Ng flagged Security risk assessment is BLOCKED waiting on architecture v1.",
            rationale="Blocker signal explicit; dependency on T-003 inferred.",
            dependencies="T-003",
        ),
        models.DraftItem(
            draft_id=draft.id, action="create",
            task_code="T-NEW-001",
            title="Draft Data migration approach memo",
            owner="Hari Suresh",
            status="not_started", priority="high",
            due_date=today + timedelta(days=5),
            confidence=0.79,
            evidence="New action: Hari Suresh to draft Data migration approach memo by next Wednesday. Priority high.",
            rationale="Brand-new task not in the current plan; created by agent.",
        ),
        models.DraftItem(
            draft_id=draft.id, action="conflict",
            task_code="T-009",
            title="Go-live readiness review — owner change from Aisha Tan to Ben Lim",
            owner="Ben Lim",
            status="not_started", priority="critical",
            confidence=0.74,
            evidence="Decision: Go-live readiness review owner changes from Aisha Tan to Ben Lim.",
            rationale="Owner change conflicts with baseline. Human decision required.",
        ),
    ]
    for it in items:
        db.add(it)

    # Also seed one open clarification so that tab is populated.
    if not db.query(models.Clarification).filter_by(project_id=proj.id).first():
        db.add(models.Clarification(
            project_id=proj.id,
            draft_item_id=None,
            question="Who is the confirmed owner for the Go-live readiness review — Aisha Tan or Ben Lim?",
            context=(
                "The meeting note states 'owner changes from Aisha Tan to Ben Lim' but the baseline "
                "still shows Aisha Tan. Clarification needed before the plan is updated."
            ),
            status="open",
        ))

    db.commit()


def _seed_synthetic(db: Session, org: models.Organization) -> None:
    """Fallback seed: small curated single-project dataset (offline-friendly)."""
    proj = models.Project(
        org_id=org.id, name=PROJECT_NAME,
        description="Curated demo project for the SJ Project Planner Agent.",
    )
    db.add(proj)
    db.flush()
    for row in _baseline_plan():
        db.add(models.Task(project_id=proj.id, **row))
        db.add(models.BaselineTask(project_id=proj.id,
                                   **{k: v for k, v in row.items() if k != "notes"}))
    for tm in _team():
        db.add(models.TeamMember(org_id=org.id, **tm))
    for n in _notes():
        db.add(models.MeetingNote(project_id=proj.id, **n))


def _seed_from_cwb_sj(db: Session, org: models.Organization,
                      ds: cwb_sj_loader.CwbSjDataset) -> None:
    """Map the official CWB_SJ dataset into our schema."""
    # Team members (people.csv → TeamMember). Discipline is the strongest skill tag.
    for p in ds.people:
        skills = ",".join(filter(None, [p.get("discipline", ""), p.get("role", "")]))
        db.add(models.TeamMember(
            org_id=org.id, name=p["display_name"],
            role=p.get("role", ""), skills=skills, capacity=1.0,
        ))

    # Projects (projects.csv → Project)
    project_map: dict[str, int] = {}
    for p in ds.projects:
        proj = models.Project(
            org_id=org.id, name=p["project_name"],
            description=f"{p.get('region','')} · {p.get('contract_type','')} · "
                        f"{p.get('start_date','')} → {p.get('target_end_date','')}",
        )
        db.add(proj)
        db.flush()
        project_map[p["project_id"]] = proj.id

    # Build a per-task dependency string from dependencies.csv
    deps_for: dict[str, list[str]] = {}
    for d in ds.dependencies:
        deps_for.setdefault(d["successor_task_id"], []).append(d["predecessor_task_id"])

    # Current snapshot → live Task; baseline snapshot → BaselineTask
    for row in ds.current_tasks:
        proj_id = project_map.get(row["project_id"])
        if not proj_id:
            continue
        db.add(_task_from_row(models.Task, proj_id, row, deps_for))
    for row in ds.baseline_tasks:
        proj_id = project_map.get(row["project_id"])
        if not proj_id:
            continue
        db.add(_task_from_row(models.BaselineTask, proj_id, row, deps_for))

    # Meeting notes (jsonl) → MeetingNote (source_type=meeting)
    for n in ds.meeting_notes:
        proj_id = project_map.get(n.get("project_id", ""))
        if not proj_id:
            continue
        db.add(models.MeetingNote(
            project_id=proj_id, source_type="meeting",
            title=n.get("title", "") or "Meeting",
            attendees=n.get("attendees", "") or "",
            occurred_at=_parse_dt(n.get("meeting_datetime")),
            content=n.get("notes_text", "") or "",
            processed=False,
        ))

    # Emails (csv) → MeetingNote (source_type=email)
    for e in ds.emails:
        proj_id = project_map.get(e.get("project_id", ""))
        if not proj_id:
            continue
        db.add(models.MeetingNote(
            project_id=proj_id, source_type="email",
            title=e.get("subject", "") or "Email",
            attendees=f"{e.get('from','')} → {e.get('to','')}",
            occurred_at=_parse_dt(e.get("sent_datetime")),
            content=e.get("body", "") or "",
            processed=False,
        ))


def _task_from_row(cls, project_id: int, row: dict, deps_for: dict[str, list[str]]):
    return cls(
        project_id=project_id,
        code=row["task_id"],
        title=row.get("task_title", "")[:300],
        owner=row.get("owner_name", "") or "",
        status=cwb_sj_loader.norm_status(row.get("status", "")),
        priority=cwb_sj_loader.norm_priority(row.get("priority", "")),
        start_date=_parse_date(row.get("planned_start")),
        due_date=_parse_date(row.get("planned_due")),
        **({"progress": _to_float(row.get("percent_complete"))} if cls is models.Task else {}),
        dependencies=",".join(deps_for.get(row["task_id"], [])),
        **({"notes": row.get("notes", "") or ""} if cls is models.Task else {}),
    )


def _parse_date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def _parse_dt(v):
    if not v:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(str(v).replace("Z", ""))
    except (ValueError, TypeError):
        return datetime.utcnow()


def _to_float(v):
    try:
        return float(v) / (100.0 if float(v) > 1 else 1.0)
    except (ValueError, TypeError):
        return 0.0
