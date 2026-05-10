"""ChangeDetectionAgent — diff between baseline and current plan."""
import pytest

from app.agents.change_detection import ChangeDetectionAgent, _Row


def _row(code, **kw):
    return _Row(
        code=code, title=kw.get("title", code),
        owner=kw.get("owner", ""),
        status=kw.get("status", "not_started"),
        priority=kw.get("priority", "medium"),
        due_date=kw.get("due_date", ""),
        start_date=kw.get("start_date", ""),
        dependencies=kw.get("dependencies", ""),
    )


async def test_no_changes_returns_clean_summary():
    base = [_row("T-001", title="A", owner="Aman", due_date="2025-05-10")]
    cur = [_row("T-001", title="A", owner="Aman", due_date="2025-05-10")]
    rep = await ChangeDetectionAgent().run(1, base, cur)
    assert rep.items == []
    assert "No changes" in rep.summary


async def test_added_and_removed_tasks_are_major():
    base = [_row("T-001")]
    cur = [_row("T-002")]
    rep = await ChangeDetectionAgent().run(1, base, cur)
    types = {(i.task_code, i.change_type, i.severity) for i in rep.items}
    assert ("T-001", "removed", "major") in types
    assert ("T-002", "added", "major") in types


async def test_due_date_shift_is_major():
    base = [_row("T-001", due_date="2025-05-10")]
    cur = [_row("T-001", due_date="2025-05-20")]
    rep = await ChangeDetectionAgent().run(1, base, cur)
    matches = [i for i in rep.items if i.field == "due_date"]
    assert len(matches) == 1
    assert matches[0].change_type == "date_shift"
    assert matches[0].severity == "major"
    assert matches[0].old_value == "2025-05-10"
    assert matches[0].new_value == "2025-05-20"


async def test_owner_change_is_minor():
    base = [_row("T-001", owner="Aman")]
    cur = [_row("T-001", owner="Priya")]
    rep = await ChangeDetectionAgent().run(1, base, cur)
    owner_changes = [i for i in rep.items if i.field == "owner"]
    assert len(owner_changes) == 1
    assert owner_changes[0].severity == "minor"
    assert owner_changes[0].change_type == "owner_change"


async def test_summary_counts_major_and_minor():
    base = [_row("T-001", owner="Aman", due_date="2025-05-10")]
    cur = [_row("T-001", owner="Priya", due_date="2025-05-20")]
    rep = await ChangeDetectionAgent().run(1, base, cur)
    # 1 major (date_shift) + 1 minor (owner_change)
    assert "1 material" in rep.summary
    assert "1 minor" in rep.summary
