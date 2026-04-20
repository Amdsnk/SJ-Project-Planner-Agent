"""Assignment Recommendation Agent.

Suggests team-member assignments using simple role/skill tag matching plus a
workload heuristic (capacity minus current open-task load). All suggestions
require explicit human confirmation before they affect the plan.
"""
from __future__ import annotations

import re
from collections import Counter

from ..schemas import AssignmentSuggestion


_TAG_RE = re.compile(r"[a-z0-9]+")


def _tags(*parts: str) -> set[str]:
    return {w for p in parts for w in _TAG_RE.findall((p or "").lower()) if len(w) > 2}


class AssignmentAgent:
    name = "assignment_agent"

    async def run(self, tasks: list, members: list) -> list[AssignmentSuggestion]:
        # Compute current load per member from in-flight tasks.
        load = Counter(t.owner for t in tasks if t.owner and t.status != "done")
        suggestions: list[AssignmentSuggestion] = []
        for t in tasks:
            if t.owner or t.status == "done":
                continue
            t_tags = _tags(t.title, t.notes, t.priority)
            best, best_score, best_reason = None, -1.0, ""
            for m in members:
                m_tags = _tags(m.role, m.skills)
                overlap = len(t_tags & m_tags)
                used = load.get(m.name, 0)
                free = max(0.0, m.capacity - 0.2 * used)
                score = overlap * 1.5 + free
                if score > best_score:
                    best, best_score = m, score
                    best_reason = (f"role/skill match={overlap} tag(s); "
                                   f"capacity={m.capacity:.1f}, current_load={used}")
            if best:
                suggestions.append(AssignmentSuggestion(
                    task_code=t.code, suggested_owner=best.name,
                    score=round(best_score, 2), reason=best_reason,
                ))
        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions
