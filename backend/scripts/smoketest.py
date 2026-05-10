"""Smoke test: process every seeded note through the orchestrator and print
a summary of resulting drafts, change-detection, priority and assignments.
Run from backend/: ``./.venv/Scripts/python.exe scripts/smoketest.py``
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.agents.orchestrator import PlannerOrchestrator
from app.agents.priority import PriorityAgent
from app.agents.assignment import AssignmentAgent
from app.agents.change_detection import ChangeDetectionAgent, row_from_task


async def main():
    orchestrator = PlannerOrchestrator()
    with SessionLocal() as db:
        proj = db.query(models.Project).first()
        notes = db.query(models.MeetingNote).filter_by(project_id=proj.id, processed=False).all()
        print(f"Project: {proj.name}  | unprocessed notes: {len(notes)}")
        for note in notes:
            draft = await orchestrator.process_note(db, note)
            print(f"  • Draft {draft.id} from '{note.title}': {len(draft.items)} item(s) — {draft.summary}")
            for it in draft.items:
                print(f"      - [{it.action}] {it.task_code} {it.title!r} owner={it.owner!r} due={it.due_date} conf={it.confidence:.2f}")

        ranked = await PriorityAgent().run(db.query(models.Task).filter_by(project_id=proj.id).all())
        print("\nTop 5 prioritised tasks:")
        for r in ranked[:5]:
            print(f"  {r.score:>5.1f}  {r.code}  {r.title}  ({r.reason})")

        suggestions = await AssignmentAgent().run(
            db.query(models.Task).filter_by(project_id=proj.id).all(),
            db.query(models.TeamMember).all(),
        )
        print(f"\nUnassigned-task suggestions: {len(suggestions)}")
        for s in suggestions:
            print(f"  {s.task_code} → {s.suggested_owner} (score {s.score})  {s.reason}")

        report = await ChangeDetectionAgent().run(
            proj.id,
            baseline=[row_from_task(t) for t in db.query(models.BaselineTask).filter_by(project_id=proj.id).all()],
            current=[row_from_task(t) for t in db.query(models.Task).filter_by(project_id=proj.id).all()],
        )
        print(f"\nChange-detection vs baseline: {report.summary}")
        for it in report.items[:10]:
            print(f"  [{it.severity}] {it.task_code} {it.change_type} {it.field}: {it.old_value!r} → {it.new_value!r}")


if __name__ == "__main__":
    asyncio.run(main())
