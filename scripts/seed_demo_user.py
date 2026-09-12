"""Idempotent demo-user seeder for the VYOMA + KAVACH local backend.

Creates the database tables if they do not exist and inserts a single
SAFETY_OFFICER account named ``officer`` when that username is absent.

Safe to run repeatedly: re-running never duplicates or modifies the user.

NOTE: the fixed password is a developer/demo convenience only. It is not a
security control — production must rely on real accounts provisioned server-side.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.db.database import Base, SessionLocal, engine
from backend.db.models import User
from backend.db.migrations import ensure_schema_upgraded
from backend.services.password import hash_password

DEMO_USERNAME = "officer"
DEMO_PASSWORD = "pass"

ROLE = "SAFETY_OFFICER"


def main() -> int:
    Base.metadata.create_all(bind=engine)
    ensure_schema_upgraded(engine)
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == DEMO_USERNAME).first()
        if existing is not None:
            print(
                f"Demo user '{DEMO_USERNAME}' already exists "
                f"(role={existing.role}); no changes."
            )
            return 0
        db.add(
            User(
                username=DEMO_USERNAME,
                password_hash=hash_password(DEMO_PASSWORD),
                role=ROLE,
            )
        )
        db.commit()
        print(f"Created demo user '{DEMO_USERNAME}' with role {ROLE}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())