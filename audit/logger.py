import uuid
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from services.audit_event import AuditEvent
from db.models import AuditLog


class AuditLogger:

    def create_event(
        self,
        permit_id: str,
        pipeline: str,
        stages: list[str],
        sequence: int
    ) -> AuditEvent:

        event = AuditEvent(
            audit_ref=f"AUDIT-{uuid.uuid4().hex[:8]}",
            permit_id=permit_id,
            timestamp=datetime.utcnow().isoformat(),
            pipeline=pipeline,
            stages=stages,
            sequence=sequence
        )

        return event

    def save_event(
        self,
        db: Session,
        event: AuditEvent
    ):

        previous_event = (
            db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .first()
        )

        if previous_event:
            previous_hash = previous_event.event_hash
        else:
            previous_hash = "GENESIS"

        data = (
            event.audit_ref
            + event.permit_id
            + event.timestamp
            + event.pipeline
            + ",".join(event.stages)
            + str(event.sequence)
            + previous_hash
        )

        event_hash = hashlib.sha256(
            data.encode()
        ).hexdigest()

        audit_log = AuditLog(
            audit_ref=event.audit_ref,
            permit_id=event.permit_id,
            timestamp=datetime.fromisoformat(event.timestamp),
            pipeline=event.pipeline,
            stages=",".join(event.stages),
            sequence=event.sequence,
            previous_hash=previous_hash,
            event_hash=event_hash
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        return audit_log

    def verify_chain(self, db: Session):

        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.id.asc())
            .all()
        )

        previous_hash = "GENESIS"

        for log in logs:

            data = (
                log.audit_ref
                + log.permit_id
                + log.timestamp.isoformat()
                + log.pipeline
                + log.stages
                + str(log.sequence)
                + previous_hash
            )

            calculated_hash = hashlib.sha256(
                data.encode()
            ).hexdigest()

            if log.previous_hash != previous_hash:
                return False

            if log.event_hash != calculated_hash:
                return False

            previous_hash = log.event_hash

        return True