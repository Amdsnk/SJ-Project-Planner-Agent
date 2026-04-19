"""Priority Agent.

Re-ranks tasks based on urgency (days-to-due), dependencies, status risk,
and explicit priority field. Pure deterministic — no LLM needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


_PRIORITY_WEIGHT = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0, "": 1.5}
_STATUS_WEIGHT = {"blocked": 3.0, "in_progress": 2.0, "not_started": 1.0, "done": 0.0, "": 1.0}


@dataclass
class RankedTask:
    code: str
    title: str
    score: float
    reason: str


class PriorityAgent:
    name = "priority_agent"

    async def run(self, tasks: list, today: date | None = None) -> list[RankedTask]:
        today = today or date.today()
        # Build dependency-fan-in counts.
        fan_in: dict[str, int] = {}
        for t in tasks:
            for dep in [d.strip() for d in (t.dependencies or "").split(",") if d.strip()]:
                fan_in[dep] = fan_in.get(dep, 0) + 1

        out: list[RankedTask] = []
        for t in tasks:
            if t.status == "done":
                continue
            urgency = 0.0
            if t.due_date:
                days = (t.due_date - today).days
                urgency = max(0.0, 8.0 - days) if days <= 7 else max(0.0, 3.0 - 0.1 * days)
                if days < 0:
                    urgency += 5.0  # overdue boost
            pw = _PRIORITY_WEIGHT.get(t.priority or "", 1.5)
            sw = _STATUS_WEIGHT.get(t.status or "", 1.0)
            blockiness = 1.5 * fan_in.get(t.code, 0)
            score = urgency + pw + sw + blockiness
            reasons = []
            if urgency > 0:
                reasons.append(f"urgency={urgency:.1f}")
            reasons.append(f"priority={t.priority or 'medium'}")
            reasons.append(f"status={t.status or 'unknown'}")
            if blockiness:
                reasons.append(f"blocks {fan_in.get(t.code, 0)} other(s)")
            out.append(RankedTask(code=t.code, title=t.title, score=round(score, 2),
                                  reason=", ".join(reasons)))
        out.sort(key=lambda r: r.score, reverse=True)
        return out
