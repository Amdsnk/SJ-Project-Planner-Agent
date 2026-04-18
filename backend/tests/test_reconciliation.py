"""ReconciliationAgent — matching thresholds and decisions."""
from datetime import date

import pytest

from app.agents.extraction import ExtractedItem
from app.agents.reconciliation import ExistingTask, ReconciliationAgent


@pytest.fixture
def agent():
    return ReconciliationAgent()


@pytest.fixture
def existing():
    return [
        ExistingTask(code="T-001", title="Draft architecture deck",
                    owner="Aman", status="in_progress", priority="high",
                    due_date="2025-05-12", dependencies=""),
        ExistingTask(code="T-002", title="Review API specification",
                    owner="Priya", status="not_started", priority="medium",
                    due_date="2025-05-20", dependencies=""),
    ]


async def test_high_similarity_triggers_update(agent, existing):
    items = [ExtractedItem(title="Draft architecture deck",
                           owner="Aman", status="in_progress",
                           due_date=date(2025, 5, 14), confidence=0.8)]
    out = await agent.run(items, existing)
    assert len(out) == 1
    assert out[0].action == "update"
    assert out[0].task_code == "T-001"
    assert "2025-05-14" in (out[0].due_date or "")


async def test_low_similarity_creates_new_task(agent, existing):
    items = [ExtractedItem(title="Run vendor onboarding workshop",
                           owner="Hari", confidence=0.7)]
    out = await agent.run(items, existing)
    assert len(out) == 1
    assert out[0].action == "create"
    # Next code must be T-003 since baseline goes up to T-002.
    assert out[0].task_code == "T-003"
    assert out[0].status == "not_started"   # filled in default
    assert out[0].priority == "medium"


async def test_medium_similarity_marks_conflict(agent, existing):
    # Partial overlap: shares some tokens with T-002 (review/api), enough to
    # land in the LOW..HIGH band but not auto-update.
    items = [ExtractedItem(title="Review API plan", confidence=0.7)]
    out = await agent.run(items, existing)
    assert len(out) == 1
    assert out[0].action == "conflict"
    assert out[0].task_code == "T-002"
    assert "clarification" in out[0].rationale.lower()


async def test_empty_titles_are_skipped(agent, existing):
    items = [ExtractedItem(title=""), ExtractedItem(title="")]
    out = await agent.run(items, existing)
    assert out == []


async def test_create_task_codes_are_sequential(agent, existing):
    items = [
        ExtractedItem(title="Brand-new initiative one"),
        ExtractedItem(title="Completely different idea"),
    ]
    out = await agent.run(items, existing)
    codes = [r.task_code for r in out]
    assert codes == ["T-003", "T-004"]
