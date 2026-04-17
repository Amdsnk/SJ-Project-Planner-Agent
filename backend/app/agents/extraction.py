"""Extraction Agent.

Converts unstructured meeting notes / emails into structured task candidates:
{title, owner, due_date, status, priority, dependencies, evidence, confidence}.
Uses Azure OpenAI when configured, otherwise a deterministic regex/heuristic
parser so the demo always works.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from dateutil import parser as dateparser

from ..services.llm import chat_json


_STATUS_KEYWORDS = {
    "blocked": ["blocked", "stuck", "waiting on", "on hold", "at risk"],
    "done": ["done", "completed", "closed", "finished", "delivered", "shipped"],
    "in_progress": ["in progress", "underway", "started", "ongoing", "wip", "working on"],
    "not_started": ["not started", "planned", "to start", "kick off", "kick-off"],
}
_PRIORITY_KEYWORDS = {
    "critical": ["critical", "urgent", "asap", "blocker", "p0"],
    "high": ["high priority", "high-priority", "p1", "important"],
    "low": ["low priority", "nice to have", "p3"],
}
_OWNER_RE = re.compile(
    r"(?:owner[:\-]\s*|assigned to\s+|@|will\s+|to\s+|by\s+)([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
)
_DATE_RE = re.compile(
    r"(?:by|due|before|on|deadline[:\-]?)\s+"
    r"([A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|next\s+\w+|tomorrow|today)",
    re.IGNORECASE,
)
_TASK_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+(.{6,})$", re.MULTILINE)
_DEP_RE = re.compile(r"(?:depends on|after|blocked by|requires)\s+([A-Z]-?\d{2,4}|[A-Z][a-zA-Z ]+ task)", re.IGNORECASE)


@dataclass
class ExtractedItem:
    title: str
    owner: str = ""
    status: str = ""
    priority: str = ""
    start_date: date | None = None
    due_date: date | None = None
    dependencies: str = ""
    evidence: str = ""
    confidence: float = 0.6
    rationale: str = ""


@dataclass
class ExtractionInput:
    note_id: int
    title: str
    content: str
    occurred_at: datetime
    attendees: str = ""


@dataclass
class ExtractionResult:
    items: list[ExtractedItem] = field(default_factory=list)
    summary: str = ""


_LLM_SYSTEM = (
    "You are the Extraction Agent in an agentic project-planning system. "
    "Read the provided meeting note/email and emit one structured action item "
    "per concrete decision or task. For each item, fill in title, owner (single "
    "person name or empty), status (not_started/in_progress/blocked/done or empty), "
    "priority (low/medium/high/critical or empty), start_date and due_date as "
    "YYYY-MM-DD strings or null, dependencies (free text), evidence (one short "
    "verbatim quote from the source), and confidence (0..1). "
    "Be conservative — leave fields empty rather than hallucinating."
)


_SCHEMA_HINT = (
    '{"summary": str, "items": [{"title": str, "owner": str, "status": str, '
    '"priority": str, "start_date": str|null, "due_date": str|null, '
    '"dependencies": str, "evidence": str, "confidence": number}]}'
)


class ExtractionAgent:
    name = "extraction_agent"

    async def run(self, inp: ExtractionInput) -> ExtractionResult:
        data = await chat_json(
            _LLM_SYSTEM,
            f"Note title: {inp.title}\nDate: {inp.occurred_at.isoformat()}\n"
            f"Attendees: {inp.attendees}\n---\n{inp.content}",
            schema_hint=_SCHEMA_HINT,
        )
        if data and isinstance(data.get("items"), list):
            return _from_llm(data)
        return _heuristic_extract(inp)


def _from_llm(data: dict[str, Any]) -> ExtractionResult:
    out = ExtractionResult(summary=str(data.get("summary", "")))
    for raw in data.get("items", []):
        try:
            out.items.append(ExtractedItem(
                title=str(raw.get("title", "")).strip(),
                owner=str(raw.get("owner", "")).strip(),
                status=_norm_status(raw.get("status", "")),
                priority=_norm_priority(raw.get("priority", "")),
                start_date=_parse_date(raw.get("start_date")),
                due_date=_parse_date(raw.get("due_date")),
                dependencies=str(raw.get("dependencies", "")).strip(),
                evidence=str(raw.get("evidence", "")).strip(),
                confidence=float(raw.get("confidence", 0.7)),
                rationale="LLM extraction",
            ))
        except Exception:
            continue
    return out


def _heuristic_extract(inp: ExtractionInput) -> ExtractionResult:
    items: list[ExtractedItem] = []
    base = inp.occurred_at.date()
    for line in _candidate_lines(inp.content):
        title = re.sub(r"\s+", " ", line).strip().rstrip(".")
        if len(title) < 6:
            continue
        item = ExtractedItem(title=title, evidence=line.strip(), confidence=0.55,
                             rationale="Heuristic extraction (no LLM configured).")
        item.owner = _guess_owner(line)
        item.status = _guess_status(line)
        item.priority = _guess_priority(line)
        item.due_date = _guess_due_date(line, base)
        item.dependencies = _guess_deps(line)
        items.append(item)
    summary = f"Heuristic extraction produced {len(items)} action item(s) from '{inp.title}'."
    return ExtractionResult(items=items, summary=summary)


def _candidate_lines(text: str) -> list[str]:
    lines = [m.group(1) for m in _TASK_LINE_RE.finditer(text)]
    if lines:
        return lines
    # Fall back to sentences containing action verbs.
    verbs = ("will", "to ", "should", "must", "owns", "deliver", "complete", "review", "draft", "send", "update")
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        s = sent.strip()
        if 8 < len(s) < 240 and any(v in s.lower() for v in verbs):
            out.append(s)
    return out


def _guess_owner(line: str) -> str:
    m = _OWNER_RE.search(line)
    return (m.group(1).strip() if m else "")


def _guess_status(line: str) -> str:
    low = line.lower()
    for status, kws in _STATUS_KEYWORDS.items():
        if any(kw in low for kw in kws):
            return status
    return ""


def _guess_priority(line: str) -> str:
    low = line.lower()
    for pri, kws in _PRIORITY_KEYWORDS.items():
        if any(kw in low for kw in kws):
            return pri
    return ""


def _guess_due_date(line: str, anchor: date) -> date | None:
    m = _DATE_RE.search(line)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw.lower() == "today":
        return anchor
    if raw.lower() == "tomorrow":
        return anchor + timedelta(days=1)
    if raw.lower().startswith("next "):
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target = raw.split()[1].lower()
        if target in weekdays:
            delta = (weekdays.index(target) - anchor.weekday()) % 7 or 7
            return anchor + timedelta(days=delta)
        if target == "week":
            return anchor + timedelta(days=7)
    try:
        return dateparser.parse(raw, default=datetime.combine(anchor, datetime.min.time())).date()
    except Exception:
        return None


def _guess_deps(line: str) -> str:
    m = _DEP_RE.search(line)
    return (m.group(1).strip() if m else "")


def _parse_date(v: Any) -> date | None:
    if not v:
        return None
    try:
        return dateparser.parse(str(v)).date()
    except Exception:
        return None


def _norm_status(v: str) -> str:
    v = (v or "").strip().lower().replace("-", "_").replace(" ", "_")
    return v if v in {"not_started", "in_progress", "blocked", "done", ""} else ""


def _norm_priority(v: str) -> str:
    v = (v or "").strip().lower()
    return v if v in {"low", "medium", "high", "critical", ""} else ""
