"""Pipeline orchestrator.

Coordinates Extraction → Reconciliation → Clarification across one note,
producing a Plan Update Draft that humans can review before it touches the
official plan. This mirrors the Microsoft Agent Framework "sequential workflow"
pattern.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .extraction import ExtractionAgent, ExtractionInput
from .reconciliation import ExistingTask, ReconciliationAgent
from .clarification import ClarificationAgent


class PlannerOrchestrator:
    def __init__(self):
        self.extractor = ExtractionAgent()
        self.reconciler = ReconciliationAgent()
        self.clarifier = ClarificationAgent()

    async def process_note(self, db: Session, note: models.MeetingNote) -> models.PlanUpdateDraft:
        # 1. Extract
        ex = await self.extractor.run(ExtractionInput(
            note_id=note.id, title=note.title, content=note.content,
            occurred_at=note.occurred_at, attendees=note.attendees,
        ))

        # 2. Reconcile against current plan
        existing_rows = (
            db.query(models.Task).filter(models.Task.project_id == note.project_id).all()
        )
        existing = [ExistingTask(
            code=t.code, title=t.title, owner=t.owner or "",
            status=t.status or "", priority=t.priority or "",
            due_date=t.due_date.isoformat() if t.due_date else "",
            dependencies=t.dependencies or "",
        ) for t in existing_rows]
        reconciled = await self.reconciler.run(ex.items, existing)

        # 3. Persist draft + items
        draft = models.PlanUpdateDraft(
            project_id=note.project_id, note_id=note.id,
            summary=ex.summary or f"{len(reconciled)} proposed change(s) from '{note.title}'.",
            status="pending", created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.flush()
        item_rows: list[models.DraftItem] = []
        for r in reconciled:
            row = models.DraftItem(
                draft_id=draft.id, action=r.action, task_code=r.task_code,
                title=r.title, owner=r.owner, status=r.status, priority=r.priority,
                start_date=_to_date(r.start_date), due_date=_to_date(r.due_date),
                dependencies=r.dependencies, confidence=r.confidence,
                evidence=r.evidence, rationale=r.rationale,
            )
            db.add(row)
            db.flush()
            item_rows.append(row)

        # 4. Generate clarifications
        questions = await self.clarifier.run(reconciled)
        for q in questions:
            di = item_rows[q.draft_item_index] if 0 <= q.draft_item_index < len(item_rows) else None
            db.add(models.Clarification(
                project_id=note.project_id,
                draft_item_id=di.id if di else None,
                question=q.question, context=q.context, status="open",
            ))

        note.processed = True
        db.commit()
        db.refresh(draft)
        return draft


def _to_date(v):
    if not v:
        return None
    from datetime import date
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)).date()
    except Exception:
        return None
