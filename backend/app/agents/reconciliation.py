"""Reconciliation Agent.

Decides whether each extracted item is:
  - "create"   : a new task,
  - "update"   : a change to an existing task, or
  - "conflict" : ambiguous / requires human clarification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .extraction import ExtractedItem


@dataclass
class ExistingTask:
    code: str
    title: str
    owner: str
    status: str
    priority: str
    due_date: str  # ISO or ""
    dependencies: str


@dataclass
class ReconciledItem:
    action: str            # create / update / conflict
    task_code: str
    title: str
    owner: str
    status: str
    priority: str
    start_date: str | None
    due_date: str | None
    dependencies: str
    confidence: float
    evidence: str
    rationale: str


_STOP = {"the", "a", "an", "and", "or", "for", "to", "with", "of", "on", "in"}


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _STOP and len(w) > 2}


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ta, tb = _tokens(a), _tokens(b)
    jacc = len(ta & tb) / max(1, len(ta | tb))
    seq = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return 0.6 * seq + 0.4 * jacc


class ReconciliationAgent:
    name = "reconciliation_agent"
    HIGH = 0.72
    LOW = 0.45

    async def run(self, items: list[ExtractedItem], existing: list[ExistingTask]) -> list[ReconciledItem]:
        out: list[ReconciledItem] = []
        next_code_idx = _next_code_index(existing)
        for it in items:
            if not it.title:
                continue
            best, score = _best_match(it.title, existing)
            if best and score >= self.HIGH:
                out.append(self._update(it, best, score))
            elif best and score >= self.LOW:
                out.append(self._conflict(it, best, score))
            else:
                code = f"T-{next_code_idx:03d}"
                next_code_idx += 1
                out.append(self._create(it, code))
        return out

    def _create(self, it: ExtractedItem, code: str) -> ReconciledItem:
        return ReconciledItem(
            action="create", task_code=code, title=it.title,
            owner=it.owner, status=it.status or "not_started",
            priority=it.priority or "medium",
            start_date=it.start_date.isoformat() if it.start_date else None,
            due_date=it.due_date.isoformat() if it.due_date else None,
            dependencies=it.dependencies, confidence=it.confidence,
            evidence=it.evidence,
            rationale="No similar existing task found — proposing a new task.",
        )

    def _update(self, it: ExtractedItem, match: ExistingTask, score: float) -> ReconciledItem:
        diffs = []
        if it.owner and it.owner != match.owner:
            diffs.append(f"owner: '{match.owner}' → '{it.owner}'")
        if it.status and it.status != match.status:
            diffs.append(f"status: '{match.status}' → '{it.status}'")
        if it.priority and it.priority != match.priority:
            diffs.append(f"priority: '{match.priority}' → '{it.priority}'")
        if it.due_date and it.due_date.isoformat() != (match.due_date or ""):
            diffs.append(f"due: '{match.due_date or '—'}' → '{it.due_date.isoformat()}'")
        if it.dependencies and it.dependencies != match.dependencies:
            diffs.append(f"deps: '{match.dependencies or '—'}' → '{it.dependencies}'")
        rationale = (f"Matched existing task {match.code} (similarity {score:.2f}). "
                     + ("Changes: " + "; ".join(diffs) if diffs else "No field changes — restating."))
        return ReconciledItem(
            action="update", task_code=match.code, title=it.title or match.title,
            owner=it.owner, status=it.status, priority=it.priority,
            start_date=it.start_date.isoformat() if it.start_date else None,
            due_date=it.due_date.isoformat() if it.due_date else None,
            dependencies=it.dependencies,
            confidence=min(0.95, it.confidence + 0.1),
            evidence=it.evidence, rationale=rationale,
        )

    def _conflict(self, it: ExtractedItem, match: ExistingTask, score: float) -> ReconciledItem:
        return ReconciledItem(
            action="conflict", task_code=match.code, title=it.title,
            owner=it.owner, status=it.status, priority=it.priority,
            start_date=it.start_date.isoformat() if it.start_date else None,
            due_date=it.due_date.isoformat() if it.due_date else None,
            dependencies=it.dependencies,
            confidence=max(0.3, it.confidence - 0.2), evidence=it.evidence,
            rationale=(f"Possibly related to existing task {match.code} ('{match.title}'), "
                       f"similarity {score:.2f}. Human clarification recommended."),
        )


def _best_match(title: str, existing: list[ExistingTask]) -> tuple[ExistingTask | None, float]:
    best, best_score = None, 0.0
    for e in existing:
        s = _similarity(title, e.title)
        if s > best_score:
            best, best_score = e, s
    return best, best_score


def _next_code_index(existing: list[ExistingTask]) -> int:
    n = 0
    for e in existing:
        m = re.match(r"T-(\d+)", e.code or "")
        if m:
            n = max(n, int(m.group(1)))
    return n + 1
