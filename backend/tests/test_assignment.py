"""AssignmentAgent — role/skill matching plus workload heuristic."""
from types import SimpleNamespace

import pytest

from app.agents.assignment import AssignmentAgent


def _task(code, title, **kw):
    return SimpleNamespace(
        code=code, title=title,
        owner=kw.get("owner", ""),
        status=kw.get("status", "not_started"),
        priority=kw.get("priority", "medium"),
        notes=kw.get("notes", ""),
    )


def _member(name, role="", skills="", capacity=1.0):
    return SimpleNamespace(name=name, role=role, skills=skills, capacity=capacity)


async def test_owned_tasks_are_skipped():
    tasks = [_task("T-001", "x", owner="Aman")]
    members = [_member("Priya", role="qa", skills="api,test")]
    out = await AssignmentAgent().run(tasks, members)
    assert out == []


async def test_skill_overlap_wins_over_capacity():
    tasks = [_task("T-001", "design api integration spec", notes="api")]
    designer = _member("Aman", role="architect", skills="api,design,integration",
                       capacity=0.5)
    generic = _member("Hari", role="generalist", skills="docs", capacity=1.0)
    out = await AssignmentAgent().run(tasks, [designer, generic])
    assert len(out) == 1
    assert out[0].suggested_owner == "Aman"
    assert "match=" in out[0].reason


async def test_workload_penalises_busy_member():
    # Two members with identical (zero) skill match — pick the less loaded one.
    tasks = [
        _task("T-001", "task a", owner="Aman"),
        _task("T-002", "task b", owner="Aman"),
        _task("T-003", "task c", owner="Aman"),
        _task("T-100", "unowned generic"),
    ]
    aman = _member("Aman", role="dev", skills="x", capacity=1.0)
    priya = _member("Priya", role="dev", skills="x", capacity=1.0)
    out = await AssignmentAgent().run(tasks, [aman, priya])
    assert len(out) == 1
    assert out[0].task_code == "T-100"
    assert out[0].suggested_owner == "Priya"


async def test_done_tasks_not_assigned():
    tasks = [_task("T-001", "x", status="done")]
    members = [_member("Priya", role="qa")]
    out = await AssignmentAgent().run(tasks, members)
    assert out == []
