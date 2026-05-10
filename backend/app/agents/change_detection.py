"""Change Detection Agent.

Compares the live plan against the frozen baseline snapshot and produces an
auditable list of material changes (date shifts, owner changes, scope adds/removes).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from ..schemas import ChangeDetectionItem, ChangeDetectionReport


@dataclass
class _Row:
    code: str
    title: str
    owner: str
    status: str
    priority: str
    due_date: str  # ISO or ""
    start_date: str
    dependencies: str


class ChangeDetectionAgent:
    name = "change_detection_agent"

    async def run(self, project_id: int, baseline: Iterable[_Row], current: Iterable[_Row]) -> ChangeDetectionReport:
        b = {r.code: r for r in baseline}
        c = {r.code: r for r in current}
        items: list[ChangeDetectionItem] = []

        for code in sorted(set(b) | set(c)):
            br, cr = b.get(code), c.get(code)
            if br and not cr:
                items.append(ChangeDetectionItem(
                    task_code=code, title=br.title, change_type="removed",
                    field="task", old_value=br.title, new_value="", severity="major",
                ))
                continue
            if cr and not br:
                items.append(ChangeDetectionItem(
                    task_code=code, title=cr.title, change_type="added",
                    field="task", old_value="", new_value=cr.title, severity="major",
                ))
                continue
            assert br and cr
            for field, label, sev in [
                ("owner", "owner_change", "minor"),
                ("status", "status_change", "minor"),
                ("priority", "priority_change", "minor"),
                ("due_date", "date_shift", "major"),
                ("start_date", "date_shift", "minor"),
                ("dependencies", "scope_change", "minor"),
                ("title", "scope_change", "minor"),
            ]:
                ov, nv = getattr(br, field), getattr(cr, field)
                if (ov or "") != (nv or ""):
                    items.append(ChangeDetectionItem(
                        task_code=code, title=cr.title, change_type=label, field=field,
                        old_value=str(ov or ""), new_value=str(nv or ""), severity=sev,
                    ))

        major = sum(1 for x in items if x.severity == "major")
        minor = len(items) - major
        summary = (f"{len(items)} change(s) vs baseline — {major} material, {minor} minor."
                   if items else "No changes vs baseline.")
        return ChangeDetectionReport(
            project_id=project_id, generated_at=datetime.utcnow(),
            summary=summary, items=items,
        )


def row_from_task(t) -> _Row:
    return _Row(
        code=t.code, title=t.title, owner=t.owner or "",
        status=t.status or "", priority=t.priority or "",
        due_date=t.due_date.isoformat() if t.due_date else "",
        start_date=t.start_date.isoformat() if t.start_date else "",
        dependencies=t.dependencies or "",
    )
