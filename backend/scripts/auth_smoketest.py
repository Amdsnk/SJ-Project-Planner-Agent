"""Quick post-refactor smoke-test: login, hit dashboard, process a note."""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:8000"


def post(path: str, body: dict, token: str = "") -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def get(path: str, token: str = "") -> dict:
    req = urllib.request.Request(
        BASE + path,
        headers=({"Authorization": f"Bearer {token}"} if token else {}),
    )
    return json.loads(urllib.request.urlopen(req).read())


print("→ /api/health        :", get("/api/health"))

login = post("/api/auth/login", {
    "email": "[email protected]",
    "password": "ChangeMe!123",
})
token = login["access_token"]
print(f"→ /api/auth/login    : token len={len(token)}, ttl={login['expires_in']}s")

me = get("/api/auth/me", token)
print(f"→ /api/auth/me       : {me['email']} ({me['role']}) org={me['org_id']}")

projects = get("/api/projects", token)
print(f"→ /api/projects      : {len(projects)} project(s) — {projects[0]['name']}")
pid = projects[0]["id"]

kpi = get(f"/api/projects/{pid}/dashboard", token)
print(f"→ dashboard          : tasks={kpi['total_tasks']}, "
      f"pending_drafts={kpi['pending_drafts']}, overdue={kpi['overdue']}")

ranked = get(f"/api/projects/{pid}/priority", token)
print(f"→ priority           : top={ranked[0]['code']} score={ranked[0]['score']}")

assignments = get(f"/api/projects/{pid}/assignments", token)
print(f"→ assignments        : {len(assignments)} suggestion(s) "
      + (f"— {assignments[0]['task_code']} → {assignments[0]['suggested_owner']}" if assignments else ""))

drafts = get(f"/api/projects/{pid}/drafts", token)
pending = [d for d in drafts if d["status"] == "pending"]
print(f"→ drafts             : {len(drafts)} total, {len(pending)} pending")

changes = get(f"/api/projects/{pid}/changes", token)
print(f"→ change-log         : {len(changes)} row(s)")

diff = get(f"/api/projects/{pid}/changes/diff", token)
print(f"→ change-detection   : {len(diff['items'])} delta(s) vs baseline")

clari = get(f"/api/projects/{pid}/clarifications", token)
print(f"→ clarifications     : {len(clari)}")

# Try unauthenticated — should 401
import urllib.error
try:
    urllib.request.urlopen(BASE + "/api/projects")
    print("× no-auth call did NOT return 401")
except urllib.error.HTTPError as e:
    print(f"→ no-auth /projects  : {e.code} (expected 401)")

print("\n✓ all good")
