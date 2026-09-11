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

        # Get the most recent audit event
        previous_event = (
            db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .first()
        )

        # First event starts the chain
        if previous_event:
            previous_hash = previous_event.event_hash
        else:
            previous_hash = "GENESIS"

        # Create data to hash
        data = (
            event.audit_ref
            + event.permit_id
            + event.timestamp
            + event.pipeline
            + ",".join(event.stages)
            + str(event.sequence)
            + previous_hash
        )

        # Generate SHA-256 hash
        event_hash = hashlib.sha256(
            data.encode()
        ).hexdigest()

        # Create database record
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

        # Get all audit events in order
        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.id.asc())
            .all()
        )

        # The first event must start from GENESIS
        previous_hash = "GENESIS"

        # Check every event
        for log in logs:

            # Recreate the original data
            data = (
                log.audit_ref
                + log.permit_id
                + log.timestamp.isoformat()
                + log.pipeline
                + log.stages
                + str(log.sequence)
                + previous_hash
            )

            # Calculate the hash again
            calculated_hash = hashlib.sha256(
                data.encode()
            ).hexdigest()

            # Check previous hash
            if log.previous_hash != previous_hash:
                return False

            # Check event hash
            if log.event_hash != calculated_hash:
                return False

            # Move to the next event
            previous_hash = log.event_hash

        return True