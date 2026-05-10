"""Integration tests for the new export + attachment endpoints.

The tests boot a real FastAPI ``TestClient`` against a fresh in-memory style
SQLite DB so we exercise the auth dependency, the org-scoped queries, and the
local-filesystem path of the blob storage backend.
"""
from __future__ import annotations

import importlib
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Sandbox the DB and the local-fs attachment store so the test is isolated
    # from the dev seed.
    sandbox = tmp_path_factory.mktemp("exports_attachments")
    db_path = sandbox / "test.db"
    att_root = sandbox / "attachments"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["CWB_SJ_OFFLINE"] = "1"        # use the small synthetic seed
    os.environ["BLOB_FORCE_LOCAL"] = "1"
    os.environ["LOCAL_ATTACHMENT_ROOT"] = str(att_root)
    os.environ["COSMOS_DISABLE"] = "1"

    # Reload config so that settings picks up the env vars above.
    from app import config as _config
    importlib.reload(_config)

    # Patch the database module's engine/SessionLocal **in-place** rather than
    # reloading it.  Reloading database.py would create a brand-new Base class
    # with empty metadata (no models registered), so create_all would produce
    # zero tables.  By patching the existing module object we keep the original
    # Base — which already has every model class registered — while redirecting
    # all queries to the sandboxed SQLite file.
    from app import database as _database
    _test_engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    _database.engine = _test_engine
    _database.SessionLocal = sessionmaker(
        bind=_test_engine, autoflush=False, autocommit=False, future=True
    )
    # Create every table on the fresh test DB using the intact Base metadata.
    _database.Base.metadata.create_all(bind=_test_engine)

    # Reload seed + blob_storage so they pick up the reloaded config/settings.
    from app.services import seed as _seed
    importlib.reload(_seed)
    from app.services import blob_storage as _blob
    importlib.reload(_blob)

    # Reloading main re-runs create_app() which calls create_all (idempotent)
    # and seed_if_empty against the patched engine.
    from app import main as _main
    importlib.reload(_main)

    with TestClient(_main.app) as c:
        yield c

    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture(scope="module")
def auth_headers(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@sj-planner.local", "password": "ChangeMe!123"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- exports ----

def test_health_reports_blob_local(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    assert h["blob_storage_enabled"] is False  # local-fs fallback active
    assert h["cosmos_enabled"] is False


def test_export_tasks_csv_has_header_and_rows(client, auth_headers):
    r = client.get("/api/exports/tasks", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.splitlines()
    assert lines, "csv must not be empty"
    # Header is stable contract for Power BI Web.Contents().
    assert lines[0].startswith(
        "task_id,task_code,org_id,project_id,project_name,title,owner,status,priority"
    )
    assert len(lines) > 1, "synthetic seed should produce at least one task"


def test_export_tasks_json_format(client, auth_headers):
    r = client.get("/api/exports/tasks?format=json", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and body
    row = body[0]
    for col in ("task_id", "task_code", "org_id", "project_id", "title",
                "is_overdue", "is_due_within_7d"):
        assert col in row


def test_export_change_log_drafts_clarifications_all_csv(client, auth_headers):
    for ep in ("change_log", "drafts", "clarifications"):
        r = client.get(f"/api/exports/{ep}", headers=auth_headers)
        assert r.status_code == 200, f"{ep}: {r.text[:200]}"
        assert r.headers["content-type"].startswith("text/csv")
        # Header line is always present even if the table is empty.
        assert r.text.splitlines(), f"{ep}: empty body"


def test_exports_require_auth(client):
    r = client.get("/api/exports/tasks")
    assert r.status_code == 401


# ------------------------------------------------------------ attachments ----

def test_attachments_list_then_upload_download_delete(client, auth_headers):
    # Pick the first project + note from the synthetic seed.
    projs = client.get("/api/projects", headers=auth_headers).json()
    assert projs, "synthetic seed must create at least one project"
    pid = projs[0]["id"]
    notes = client.get(f"/api/projects/{pid}/notes", headers=auth_headers).json()
    assert notes, "synthetic seed must create at least one note"
    nid = notes[0]["id"]

    base = f"/api/projects/{pid}/notes/{nid}/attachments"
    assert client.get(base, headers=auth_headers).json() == []

    payload = b"hello sj planner"
    r = client.post(
        base,
        headers=auth_headers,
        files={"file": ("evidence.txt", payload, "text/plain")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "evidence.txt"
    assert body["size_bytes"] == len(payload)
    assert body["backend"] == "local"
    aid = body["id"]

    # Listing now reflects the upload.
    listed = client.get(base, headers=auth_headers).json()
    assert len(listed) == 1 and listed[0]["id"] == aid

    # Round-trip the bytes through the download endpoint.
    r = client.get(f"{base}/{aid}/download", headers=auth_headers)
    assert r.status_code == 200
    assert r.content == payload
    assert "evidence.txt" in r.headers.get("content-disposition", "")

    # Delete cleans up the metadata row.
    r = client.delete(f"{base}/{aid}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(base, headers=auth_headers).json() == []


def test_attachment_upload_rejects_empty_file(client, auth_headers):
    projs = client.get("/api/projects", headers=auth_headers).json()
    notes = client.get(
        f"/api/projects/{projs[0]['id']}/notes", headers=auth_headers
    ).json()
    base = f"/api/projects/{projs[0]['id']}/notes/{notes[0]['id']}/attachments"

    r = client.post(
        base, headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert r.status_code == 400


def test_attachment_endpoints_require_auth(client):
    # 401 via the auth dependency (project lookup never even runs).
    r = client.get("/api/projects/1/notes/1/attachments")
    assert r.status_code == 401
