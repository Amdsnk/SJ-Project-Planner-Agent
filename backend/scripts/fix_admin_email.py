"""One-off migration: rewrite any redacted bootstrap-admin email placeholders
in the users table to the real address, and reset password to demo1234.

Idempotent — safe to re-run.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.security import hash_password


def main():
    real_email = "admin" + "@" + "sj-planner.local"
    new_password = "demo1234"
    placeholders = {"[email protected]", "[email protected]"}
    with SessionLocal() as db:
        users = db.query(models.User).all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"  - id={u.id} email={u.email!r} role={u.role} active={u.is_active}")
        target = (
            db.query(models.User).filter(models.User.email == real_email).first()
            or next((u for u in users if u.email in placeholders), None)
            or (users[0] if len(users) == 1 else None)
        )
        if not target:
            print("ERROR: no admin user to update.")
            sys.exit(1)
        target.email = real_email
        target.password_hash = hash_password(new_password)
        target.is_active = True
        db.commit()
        print(f"OK. user id={target.id} -> email={target.email!r}, password reset, active=True")


if __name__ == "__main__":
    main()
