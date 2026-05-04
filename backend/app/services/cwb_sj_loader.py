"""Loader for the official CWB_SJ synthetic dataset.

Downloads (on first call) and caches the curated dataset published at
https://github.com/DoreenSteven/CWB_SJ — projects, people, tasks (baseline +
current snapshots), dependencies, meeting notes (jsonl), emails. Falls back
silently when offline so the demo still seeds with the synthetic plan.
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_REPO_BASE = "https://raw.githubusercontent.com/DoreenSteven/CWB_SJ/main"
_FILES = (
    "projects.csv",
    "people.csv",
    "dependencies.csv",
    "plan_snapshots.csv",
    "meeting_notes.jsonl",
    "emails.csv",
)
_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cwb_sj"


@dataclass
class CwbSjDataset:
    projects: list[dict] = field(default_factory=list)
    people: list[dict] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    baseline_tasks: list[dict] = field(default_factory=list)
    current_tasks: list[dict] = field(default_factory=list)
    meeting_notes: list[dict] = field(default_factory=list)
    emails: list[dict] = field(default_factory=list)

    @property
    def loaded(self) -> bool:
        return bool(self.projects and self.people and self.current_tasks)


def _ensure_cached(allow_download: bool = True) -> Path | None:
    """Return cache dir if all files present (downloading missing ones); else None."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for name in _FILES:
        target = _CACHE_DIR / name
        if target.exists() and target.stat().st_size > 0:
            continue
        if not allow_download:
            return None
        try:
            with urllib.request.urlopen(f"{_REPO_BASE}/{name}", timeout=15) as resp:
                target.write_bytes(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
    return _CACHE_DIR


def load_dataset(allow_download: bool = True) -> CwbSjDataset:
    """Parse the cached dataset into typed dicts. Empty dataset if unavailable."""
    if os.getenv("CWB_SJ_OFFLINE", "0") == "1":
        allow_download = False
    cache = _ensure_cached(allow_download=allow_download)
    ds = CwbSjDataset()
    if cache is None:
        return ds

    ds.projects = _read_csv(cache / "projects.csv")
    ds.people = _read_csv(cache / "people.csv")
    ds.dependencies = _read_csv(cache / "dependencies.csv")

    for row in _read_csv(cache / "plan_snapshots.csv"):
        snap = (row.get("snapshot") or "").lower()
        if snap == "baseline":
            ds.baseline_tasks.append(row)
        elif snap == "current":
            ds.current_tasks.append(row)

    notes_path = cache / "meeting_notes.jsonl"
    if notes_path.exists():
        with notes_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ds.meeting_notes.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    ds.emails = _read_csv(cache / "emails.csv")
    return ds


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        # Use DictReader with a sniffed dialect to tolerate quoted multi-line bodies.
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


# ----- normalisation helpers used by seed.py -----

_STATUS_MAP = {
    "not started": "not_started",
    "in progress": "in_progress",
    "blocked": "blocked",
    "done": "done",
}
_PRIORITY_MAP = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}


def norm_status(v: str) -> str:
    return _STATUS_MAP.get((v or "").strip().lower(), "not_started")


def norm_priority(v: str) -> str:
    return _PRIORITY_MAP.get((v or "").strip().lower(), "medium")
