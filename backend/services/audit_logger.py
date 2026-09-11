"""Persistent audit log for KAVACH processing results.

The authoritative audit reference is produced by the KAVACH orchestrator.
This module persists that record (with its stages/sequence snapshot) and
chains the persisted rows with SHA-256 hashes so the local audit history can
be verified. It does not replace the KAVACH audit snapshot.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.db.models import AuditLog


class AuditLogger:

    def create_event(
        self,
        audit_ref: str,
        permit_id: str,
        timestamp: str,
        pipeline: List[str],
        stages: str,
        sequence: str,
    ) -> Dict[str, Any]:
        return {
            "audit_ref": audit_ref,
            "permit_id": permit_id,
            "timestamp": timestamp,
            "pipeline": pipeline,
            "stages": stages,
            "sequence": sequence,
        }

    def save_event(self, db: Session, event: Dict[str, Any]) -> AuditLog:
        previous_event = (
            db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .first()
        )
        previous_hash = (
            previous_event.event_hash if previous_event else "GENESIS"
        )

        log = AuditLog(
            audit_ref=event["audit_ref"],
            permit_id=event["permit_id"],
            timestamp=_parse_timestamp(event["timestamp"]),
            pipeline=",".join(event["pipeline"]),
            stages=event["stages"],
            sequence=event["sequence"],
            previous_hash=previous_hash,
            event_hash="",
        )

        self._rehash(db, log)

        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def _rehash(self, db: Session, log: AuditLog) -> None:
        data = (
            log.audit_ref
            + log.permit_id
            + log.timestamp.isoformat()
            + log.pipeline
            + log.stages
            + log.sequence
            + log.previous_hash
        )
        log.event_hash = hashlib.sha256(data.encode("utf-8")).hexdigest()

    def verify_chain(self, db: Session) -> bool:
        logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        previous_hash = "GENESIS"
        for log in logs:
            data = (
                log.audit_ref
                + log.permit_id
                + log.timestamp.isoformat()
                + log.pipeline
                + log.stages
                + log.sequence
                + previous_hash
            )
            if log.previous_hash != previous_hash:
                return False
            if (
                log.event_hash
                != hashlib.sha256(data.encode("utf-8")).hexdigest()
            ):
                return False
            previous_hash = log.event_hash
        return True


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt