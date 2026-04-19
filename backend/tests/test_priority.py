"""PriorityAgent — deterministic ranking."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.agents.priority import PriorityAgent


def _t(code, title, **kw):
    return SimpleNamespace(
        code=code, title=title,
        owner=kw.get("owner", ""),
        status=kw.get("status", "not_started"),
        priority=kw.get("priority", "medium"),
        due_date=kw.get("due_date"),
        dependencies=kw.get("dependencies", ""),
    )


@pytest.fixture
def today():
    return date(2025, 5, 1)


async def test_done_tasks_are_excluded(today):
    tasks = [_t("T-001", "shipped", status="done")]
    out = await PriorityAgent().run(tasks, today=today)
    assert out == []


async def test_overdue_outranks_far_future(today):
    overdue = _t("T-001", "late", due_date=today - timedelta(days=3),
                 priority="medium")
    far = _t("T-002", "later", due_date=today + timedelta(days=60),
             priority="medium")
    out = await PriorityAgent().run([overdue, far], today=today)
    assert out[0].code == "T-001"
    assert out[0].score > out[1].score


async def test_blocking_other_tasks_boosts_score(today):
    blocker = _t("T-001", "blocker", priority="medium",
                 due_date=today + timedelta(days=14))
    a = _t("T-002", "a", dependencies="T-001", priority="medium",
           due_date=today + timedelta(days=14))
    b = _t("T-003", "b", dependencies="T-001", priority="medium",
           due_date=today + timedelta(days=14))
    out = await PriorityAgent().run([blocker, a, b], today=today)
    blocker_score = next(r.score for r in out if r.code == "T-001")
    a_score = next(r.score for r in out if r.code == "T-002")
    assert blocker_score > a_score
    assert "blocks 2" in next(r.reason for r in out if r.code == "T-001")


async def test_critical_priority_outranks_low(today):
    crit = _t("T-001", "c", priority="critical")
    low = _t("T-002", "l", priority="low")
    out = await PriorityAgent().run([crit, low], today=today)
    assert out[0].code == "T-001"


async def test_blocked_status_increases_score_over_not_started(today):
    blocked = _t("T-001", "x", status="blocked", priority="medium")
    fresh = _t("T-002", "y", status="not_started", priority="medium")
    out = await PriorityAgent().run([blocked, fresh], today=today)
    assert out[0].code == "T-001"
