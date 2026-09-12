"""Idempotent, additive-only SQLite schema upgrades.

``Base.metadata.create_all`` only creates tables that do not exist yet; it
never adds a column to a table that already exists.  A ``vyoma.db`` created
before the Phase 2 review columns were added therefore lacks them, and any
ORM access touching one of those columns raises::

    OperationalError: table tasks has no column named review_status

``ensure_schema_upgraded`` closes that gap.  For every ORM table it reads the
columns that actually exist via ``PRAGMA table_info`` and issues additive
``ALTER TABLE ... ADD COLUMN`` statements for model columns that are missing
from the existing table (nullable columns only).  It is idempotent, never
drops/renames/modifies existing columns or rows, and is a safe no-op on an
already-current schema and on non-SQLite databases.
"""

from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

logger = logging.getLogger("backend.db.migrations")


def _declared_tables():
    """Return the ORM tables registered on ``Base.metadata``."""
    from backend.db.database import Base

    import backend.db.models  # noqa: F401  (registers tables on Base.metadata)

    return list(Base.metadata.sorted_tables)


def _existing_columns(conn, table_name: str) -> set:
    rows = conn.exec_driver_sql(
        f"PRAGMA table_info({table_name})"
    ).mappings()
    return {row["name"] for row in rows}


def ensure_schema_upgraded(engine: Engine) -> None:
    """Add any model columns missing from existing SQLite tables.

    No-op for non-SQLite engines and for already-current schemas.  Additive
    only: missing nullable columns are appended via ``ALTER TABLE``; nothing
    is dropped, renamed, or rewritten, and no existing data is touched.
    """
    url = str(engine.url)
    if not url.startswith("sqlite"):
        logger.info(
            "Schema upgrade skipped: engine is not SQLite (%s)", url
        )
        return

    tables = _declared_tables()
    added = 0
    with engine.begin() as conn:
        for table in tables:
            table_name = table.name
            existing = _existing_columns(conn, table_name)
            for column in table.columns:
                if column.name in existing:
                    continue
                if column.nullable is not True:
                    logger.warning(
                        "Cannot add column %s.%s: only nullable columns are "
                        "supported by the additive upgrade; leaving it out.",
                        table_name,
                        column.name,
                    )
                    continue
                column_type = column.type.compile(dialect=engine.dialect)
                conn.exec_driver_sql(
                    f'ALTER TABLE "{table_name}" ADD COLUMN '
                    f'"{column.name}" {column_type}'
                )
                added += 1
                logger.info(
                    "Added missing column %s.%s %s",
                    table_name,
                    column.name,
                    column_type,
                )
    logger.info(
        "Schema upgrade complete: %d column(s) added across %d table(s).",
        added,
        len(tables),
    )