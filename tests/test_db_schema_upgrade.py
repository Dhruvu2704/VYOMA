"""Tests for the idempotent, additive-only SQLite schema upgrade.

Reproduces the "table tasks has no column named review_status" failure: a
stale database whose ``tasks`` table predates the Phase 2 review columns is
upgraded in place by ``ensure_schema_upgraded`` with existing rows preserved
and new columns added as NULL.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from backend.db.database import Base
from backend.db import models  # noqa: F401  (register tables on Base.metadata)
from backend.db.migrations import ensure_schema_upgraded

REVIEW_COLUMNS = {
    "review_status",
    "reviewed_by",
    "review_reason",
    "reviewed_at",
}

OLD_TASKS_DDL = (
    "CREATE TABLE tasks ("
    " id INTEGER NOT NULL,"
    " filename VARCHAR NOT NULL,"
    " file_path VARCHAR,"
    " input_json TEXT,"
    " status VARCHAR NOT NULL,"
    " permit_id VARCHAR,"
    " scenario VARCHAR,"
    " audit_ref VARCHAR,"
    " result_json TEXT,"
    " error VARCHAR,"
    " created_by INTEGER,"
    " created_at DATETIME,"
    " updated_at DATETIME,"
    " PRIMARY KEY (id)"
    ")"
)


def _new_engine(path: Path):
    return create_engine(f"sqlite:///{path.as_posix()}", poolclass=NullPool)


def _column_names(engine, table: str) -> set:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).mappings()
        return {row["name"] for row in rows}


def _stale_database(path: Path):
    """Build a SQLite file whose tasks table predates the review columns."""
    engine = _new_engine(path)
    with engine.begin() as conn:
        conn.exec_driver_sql(OLD_TASKS_DDL)
        conn.exec_driver_sql(
            "INSERT INTO tasks (id, filename, status, permit_id, input_json,"
            " result_json, created_at, updated_at) VALUES (1,"
            " 'pre-phase-2.png', 'CREATED', 'MR-OLD-001',"
            " '{\"note\": \"pre-existing row\"}',"
            " '{\"final_decision\": \"PASS\"}',"
            " '2026-09-08T09:30:00', '2026-09-08T09:30:00')"
        )
    return engine


class TestSchemaUpgradeOnStaleDb(unittest.TestCase):

    def test_upgrade_adds_review_columns_and_preserves_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _stale_database(Path(temp_dir) / "stale.db")

            Base.metadata.create_all(bind=engine)
            ensure_schema_upgraded(engine)

            columns = _column_names(engine, "tasks")
            self.assertTrue(
                REVIEW_COLUMNS.issubset(columns),
                f"missing review columns; tasks has: {sorted(columns)}",
            )

            with engine.connect() as conn:
                row = dict(
                    conn.exec_driver_sql(
                        "SELECT * FROM tasks WHERE id = 1"
                    ).mappings().one()
                )
            self.assertEqual(row["filename"], "pre-phase-2.png")
            self.assertEqual(row["status"], "CREATED")
            self.assertEqual(row["permit_id"], "MR-OLD-001")
            self.assertEqual(row["input_json"], '{"note": "pre-existing row"}')
            self.assertEqual(
                row["result_json"], '{"final_decision": "PASS"}'
            )
            self.assertEqual(row["created_at"], "2026-09-08T09:30:00")
            for column in REVIEW_COLUMNS:
                self.assertIsNone(row[column], f"{column} should be NULL")

    def test_upgraded_db_accepts_review_orm_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _stale_database(Path(temp_dir) / "stale2.db")
            Base.metadata.create_all(bind=engine)
            ensure_schema_upgraded(engine)

            Session = sessionmaker(bind=engine)
            with Session() as db:
                task = models.Task(
                    filename="reviewed.png",
                    file_path="uploads/x.png",
                    input_json='{"structured_ptw": {"permit_id": "MR-OLD-001"}}',
                    status="COMPLETED",
                    permit_id="MR-OLD-001",
                    review_status="APPROVED",
                    reviewed_by=7,
                    review_reason="Confirmed on site.",
                    reviewed_at=datetime(2026, 9, 9, 10, 0, 0),
                )
                db.add(task)
                db.commit()

            with Session() as db:
                task = (
                    db.query(models.Task)
                    .filter(models.Task.filename == "reviewed.png")
                    .one()
                )
                self.assertEqual(task.review_status, "APPROVED")
                self.assertEqual(task.reviewed_by, 7)
                self.assertEqual(task.review_reason, "Confirmed on site.")
                self.assertIsNotNone(task.reviewed_at)

    def test_idempotent_double_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _stale_database(Path(temp_dir) / "stale3.db")
            Base.metadata.create_all(bind=engine)

            ensure_schema_upgraded(engine)
            first = _column_names(engine, "tasks")

            ensure_schema_upgraded(engine)
            second = _column_names(engine, "tasks")

            self.assertEqual(first, second)
            self.assertTrue(REVIEW_COLUMNS.issubset(second))

    def test_fresh_database_initializes_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _new_engine(Path(temp_dir) / "fresh.db")

            Base.metadata.create_all(bind=engine)
            ensure_schema_upgraded(engine)

            columns = _column_names(engine, "tasks")
            self.assertTrue(REVIEW_COLUMNS.issubset(columns))

            Session = sessionmaker(bind=engine)
            with Session() as db:
                task = models.Task(
                    filename="fresh.png",
                    status="CREATED",
                    review_status="CHANGES_REQUESTED",
                    reviewed_by=3,
                    review_reason="Redraw sketch.",
                    reviewed_at=datetime(2026, 9, 9, 11, 0, 0),
                )
                db.add(task)
                db.commit()
            with Session() as db:
                task = (
                    db.query(models.Task)
                    .filter(models.Task.filename == "fresh.png")
                    .one()
                )
                self.assertEqual(task.review_status, "CHANGES_REQUESTED")
                self.assertEqual(task.reviewed_by, 3)


if __name__ == "__main__":
    unittest.main()