"""One-off helper: reset the bootstrap admin password to a known value.

Usage:
    python scripts/reset_admin.py [email protected] demo1234
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.security import hash_password


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "[email protected]"
    password = sys.argv[2] if len(sys.argv) > 2 else "demo1234"
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"User {email!r} not found. Existing users:")
            for u in db.query(models.User).all():
                print(f"  - {u.email!r}  role={u.role}  active={u.is_active}")
            sys.exit(1)
        user.password_hash = hash_password(password)
        user.is_active = True
        db.commit()
        print(f"OK. {email} -> password reset, is_active=True, role={user.role}")


if __name__ == "__main__":
    main()
