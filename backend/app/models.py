from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Float, ForeignKey, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Organization(Base):
    """Tenant — every other entity is scoped to one organization."""
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    entra_tenant_id: Mapped[str] = mapped_column(String(80), default="")  # optional
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(200), default="")  # blank when SSO-only
    role: Mapped[str] = mapped_column(String(40), default="reviewer")    # admin/reviewer/viewer
    entra_oid: Mapped[str] = mapped_column(String(80), default="", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("org_id", "email", name="uq_users_org_email"),)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_projects_org_name"),)


class Task(Base):
    """Live (current) plan task."""
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    code: Mapped[str] = mapped_column(String(40), index=True)        # e.g. WBS code T-001
    title: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="not_started")  # not_started/in_progress/blocked/done
    priority: Mapped[str] = mapped_column(String(20), default="medium")     # low/medium/high/critical
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    dependencies: Mapped[str] = mapped_column(String(300), default="")     # comma-separated task codes
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BaselineTask(Base):
    """Frozen baseline plan snapshot, used for change detection."""
    __tablename__ = "baseline_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    code: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="not_started")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dependencies: Mapped[str] = mapped_column(String(300), default="")
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MeetingNote(Base):
    """Raw input source: meeting minutes, email, chat, etc."""
    __tablename__ = "meeting_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    source_type: Mapped[str] = mapped_column(String(40), default="meeting")  # meeting/email/chat
    title: Mapped[str] = mapped_column(String(300), default="")
    attendees: Mapped[str] = mapped_column(String(500), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content: Mapped[str] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NoteAttachment(Base):
    """Binary attachment for a meeting note (e.g. .eml, .docx, .pdf).

    The actual bytes are stored in Azure Blob Storage when configured, and on
    the local filesystem otherwise (see services/blob_storage.py). Only the
    storage key is persisted here.
    """
    __tablename__ = "note_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("meeting_notes.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(String(500))
    backend: Mapped[str] = mapped_column(String(20), default="local")  # local|azure
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    uploaded_by: Mapped[str] = mapped_column(String(120), default="")


class PlanUpdateDraft(Base):
    """A pending change set extracted from one or more notes; awaits human approval."""
    __tablename__ = "plan_update_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    note_id: Mapped[int | None] = mapped_column(ForeignKey("meeting_notes.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    items: Mapped[list["DraftItem"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class DraftItem(Base):
    """One proposed change inside a draft."""
    __tablename__ = "draft_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("plan_update_drafts.id"))
    action: Mapped[str] = mapped_column(String(20))  # create/update/conflict
    task_code: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    owner: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="")
    priority: Mapped[str] = mapped_column(String(20), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dependencies: Mapped[str] = mapped_column(String(300), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    evidence: Mapped[str] = mapped_column(Text, default="")          # quoted source text
    rationale: Mapped[str] = mapped_column(Text, default="")         # why this change
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # per-item override

    draft: Mapped[PlanUpdateDraft] = relationship(back_populates="items")


class ChangeLog(Base):
    """Audit log of accepted plan changes."""
    __tablename__ = "change_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    task_code: Mapped[str] = mapped_column(String(40))
    field: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[str] = mapped_column(String(500), default="")
    new_value: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    actor: Mapped[str] = mapped_column(String(120), default="agent")
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Clarification(Base):
    """Outstanding question raised by the agent that requires a human answer."""
    __tablename__ = "clarifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    draft_item_id: Mapped[int | None] = mapped_column(ForeignKey("draft_items.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open/answered/dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TeamMember(Base):
    """Used by the priority/assignment recommender."""
    __tablename__ = "team_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80), default="")
    skills: Mapped[str] = mapped_column(String(300), default="")  # comma-separated tags
    capacity: Mapped[float] = mapped_column(Float, default=1.0)   # 0..1
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_team_members_org_name"),)


class WebhookDelivery(Base):
    """Outbound webhook attempts for Power Automate / external integrations."""
    __tablename__ = "webhook_deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    event: Mapped[str] = mapped_column(String(80))
    target_url: Mapped[str] = mapped_column(String(500))
    payload: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
