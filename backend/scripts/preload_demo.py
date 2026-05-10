"""Preload demo data: process every seeded note through the agent pipeline,
auto-approve the first draft (so the audit trail / change-log have content),
and leave the rest as 'pending' so the reviewer can experience the approval UX.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app.database import Base, SessionLocal, engine
from app import models
from app.agents.orchestrator import PlannerOrchestrator
from app.routers.drafts import _apply
from app.services.seed import seed_if_empty


async def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db)

    # Cap how many notes we feed through the agent at preload time so the demo
    # fixtures stay snappy even when seeded with the full CWB_SJ dataset
    # (~230 notes). Override with PRELOAD_MAX_NOTES env var.
    max_notes = int(os.getenv("PRELOAD_MAX_NOTES", "8"))

    orchestrator = PlannerOrchestrator()
    with SessionLocal() as db:
        proj = db.query(models.Project).first()
        if not proj:
            print("No project — seed didn't run.")
            return

        notes = (
            db.query(models.MeetingNote)
            .filter_by(processed=False)
            .order_by(models.MeetingNote.occurred_at.asc())
            .limit(max_notes)
            .all()
        )
        drafts = []
        for note in notes:
            d = await orchestrator.process_note(db, note)
            drafts.append(d)
            print(f"draft #{d.id}  ←  '{note.title}'  →  {len(d.items)} item(s)")

        # Auto-approve the first draft so dashboards/change-log show real activity.
        if drafts:
            d0 = drafts[0]
            note_title = ""
            if d0.note_id:
                n = db.get(models.MeetingNote, d0.note_id)
                note_title = n.title if n else ""
            for item in d0.items:
                # Accept all non-conflict items automatically.
                if item.action == "conflict":
                    item.accepted = False
                    continue
                item.accepted = True
                _apply(db, d0.project_id, item, note_title, actor="demo_seed")
            d0.status = "approved"
            d0.decided_at = datetime.utcnow()
            d0.decided_by = "demo_seed"
            db.commit()
            print(f"auto-approved draft #{d0.id} as demo activity.")

        # Manually answer one open clarification so the UI shows both states.
        c = (
            db.query(models.Clarification)
            .filter_by(status="open")
            .first()
        )
        if c:
            c.answer = "Confirmed — please proceed as proposed."
            c.status = "answered"
            c.answered_at = datetime.utcnow()
            db.commit()
            print(f"answered clarification #{c.id}.")

        print("\nDemo state:")
        print(f"  tasks:           {db.query(models.Task).count()}")
        print(f"  drafts:          {db.query(models.PlanUpdateDraft).count()}")
        print(f"  pending drafts:  {db.query(models.PlanUpdateDraft).filter_by(status='pending').count()}")
        print(f"  change-log rows: {db.query(models.ChangeLog).count()}")
        print(f"  clarifications:  {db.query(models.Clarification).count()}")


if __name__ == "__main__":
    asyncio.run(main())
