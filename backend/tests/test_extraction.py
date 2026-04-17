"""ExtractionAgent — heuristic path (offline, no LLM)."""
from datetime import datetime

import pytest

from app.agents.extraction import ExtractionAgent, ExtractionInput


@pytest.fixture
def agent():
    return ExtractionAgent()


@pytest.fixture
def occurred_at():
    return datetime(2025, 5, 1, 10, 0, 0)


async def test_extracts_bullet_action_items(agent, occurred_at):
    content = (
        "Discussion notes:\n"
        "- Aman will draft the architecture deck by May 12, 2025.\n"
        "- Priya to review the API spec, high priority.\n"
        "- Kickoff workshop is blocked waiting on vendor signoff.\n"
    )
    result = await agent.run(ExtractionInput(
        note_id=1, title="Weekly sync", content=content, occurred_at=occurred_at,
        attendees="Aman, Priya, Hari",
    ))
    titles = [i.title.lower() for i in result.items]
    assert len(result.items) >= 3
    assert any("architecture" in t for t in titles)
    assert any("api spec" in t for t in titles)


async def test_owner_status_priority_and_due_date_are_inferred(agent, occurred_at):
    # ISO date + explicit "assigned to" so the heuristic owner regex doesn't
    # mis-grab the month name from a "by <Month> <day>" phrase.
    content = "- owner: Aman — deliver the rollout plan, high priority, due 2025-05-15."
    result = await agent.run(ExtractionInput(
        note_id=1, title="x", content=content, occurred_at=occurred_at,
    ))
    assert result.items, "expected at least one extracted item"
    item = result.items[0]
    assert item.owner == "Aman"
    assert item.priority == "high"
    assert item.due_date and item.due_date.isoformat() == "2025-05-15"


async def test_blocked_status_keyword_detected(agent, occurred_at):
    content = "- Vendor onboarding is blocked waiting on legal review."
    result = await agent.run(ExtractionInput(
        note_id=1, title="x", content=content, occurred_at=occurred_at,
    ))
    assert result.items
    assert result.items[0].status == "blocked"


async def test_relative_dates_resolve_against_anchor(agent, occurred_at):
    # 1 May 2025 is a Thursday; "next monday" → 5 May 2025.
    content = "- Priya will publish the FAQ by next monday."
    result = await agent.run(ExtractionInput(
        note_id=1, title="x", content=content, occurred_at=occurred_at,
    ))
    assert result.items
    assert result.items[0].due_date and result.items[0].due_date.isoformat() == "2025-05-05"


async def test_no_action_items_returns_empty(agent, occurred_at):
    content = "Casual chat about the weather and lunch."
    result = await agent.run(ExtractionInput(
        note_id=1, title="x", content=content, occurred_at=occurred_at,
    ))
    assert result.items == []


async def test_dependencies_extracted(agent, occurred_at):
    content = "- Final QA depends on T-002 before sign-off."
    result = await agent.run(ExtractionInput(
        note_id=1, title="x", content=content, occurred_at=occurred_at,
    ))
    assert result.items
    assert "T-002" in result.items[0].dependencies
