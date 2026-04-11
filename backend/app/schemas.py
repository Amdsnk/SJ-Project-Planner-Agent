from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(ORMBase):
    id: int
    org_id: int
    email: str
    full_name: str
    role: str


class UserCreate(BaseModel):
    email: str
    full_name: str = ""
    password: str
    role: str = "reviewer"


# ---------- Project ----------
class ProjectOut(ORMBase):
    id: int
    org_id: int
    name: str
    description: str


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


# ---------- Task ----------
class TaskBase(BaseModel):
    code: str
    title: str
    owner: str = ""
    status: str = "not_started"
    priority: str = "medium"
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    progress: float = 0.0
    dependencies: str = ""
    notes: str = ""


class TaskOut(ORMBase, TaskBase):
    id: int
    updated_at: datetime


class TaskCreate(TaskBase):
    project_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    progress: Optional[float] = None
    dependencies: Optional[str] = None
    notes: Optional[str] = None


# ---------- Meeting note ----------
class MeetingNoteIn(BaseModel):
    project_id: int
    source_type: str = "meeting"
    title: str = ""
    attendees: str = ""
    occurred_at: Optional[datetime] = None
    content: str


class MeetingNoteOut(ORMBase):
    id: int
    project_id: int
    source_type: str
    title: str
    attendees: str
    occurred_at: datetime
    content: str
    processed: bool
    created_at: datetime


# ---------- Note attachment ----------
class NoteAttachmentOut(ORMBase):
    id: int
    note_id: int
    filename: str
    content_type: str
    size_bytes: int
    backend: str
    uploaded_at: datetime
    uploaded_by: str


# ---------- Draft ----------
class DraftItemOut(ORMBase):
    id: int
    action: str
    task_code: str
    title: str
    owner: str
    status: str
    priority: str
    start_date: Optional[date]
    due_date: Optional[date]
    dependencies: str
    confidence: float
    evidence: str
    rationale: str
    accepted: Optional[bool]


class DraftOut(ORMBase):
    id: int
    project_id: int
    note_id: Optional[int]
    summary: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime]
    decided_by: str
    items: list[DraftItemOut]


class DraftDecision(BaseModel):
    decided_by: str = "reviewer"
    accepted_item_ids: Optional[list[int]] = None  # if None, accept all
    rejected_item_ids: Optional[list[int]] = None


# ---------- Change log ----------
class ChangeLogOut(ORMBase):
    id: int
    task_code: str
    field: str
    old_value: str
    new_value: str
    source: str
    actor: str
    rationale: str
    created_at: datetime


# ---------- Clarification ----------
class ClarificationOut(ORMBase):
    id: int
    project_id: int
    draft_item_id: Optional[int]
    question: str
    context: str
    answer: str
    status: str
    created_at: datetime
    answered_at: Optional[datetime]


class ClarificationAnswer(BaseModel):
    answer: str


# ---------- Team member ----------
class TeamMemberOut(ORMBase):
    id: int
    name: str
    role: str
    skills: str
    capacity: float


# ---------- Change detection report ----------
class ChangeDetectionItem(BaseModel):
    task_code: str
    title: str
    change_type: str   # added/removed/date_shift/owner_change/status_change/scope_change
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    severity: str = "info"  # info/minor/major


class ChangeDetectionReport(BaseModel):
    project_id: int
    generated_at: datetime
    summary: str
    items: list[ChangeDetectionItem]


# ---------- Dashboard ----------
class DashboardKPIs(BaseModel):
    total_tasks: int
    not_started: int
    in_progress: int
    blocked: int
    done: int
    overdue: int
    upcoming_7d: int
    pending_drafts: int
    open_clarifications: int


# ---------- Assignment recommendation ----------
class AssignmentSuggestion(BaseModel):
    task_code: str
    suggested_owner: str
    score: float
    reason: str
