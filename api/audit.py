from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import AuditLog
from audit.logger import AuditLogger
from services.auth import get_current_user
from services.permissions import require_tool_permission


router = APIRouter(
    prefix="/api/audit",
    tags=["Audit"]
)


class AuditCreate(BaseModel):
    permit_id: str
    pipeline: str
    stages: list[str]
    sequence: int


@router.post("/")
def create_audit_event(
    audit_data: AuditCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "create_audit_log"
    )

    logger = AuditLogger()

    event = logger.create_event(
        permit_id=audit_data.permit_id,
        pipeline=audit_data.pipeline,
        stages=audit_data.stages,
        sequence=audit_data.sequence
    )

    saved_event = logger.save_event(
        db,
        event
    )

    return {
        "message": "Audit event created successfully",
        "audit_ref": saved_event.audit_ref,
        "permit_id": saved_event.permit_id,
        "timestamp": saved_event.timestamp,
        "pipeline": saved_event.pipeline,
        "stages": saved_event.stages.split(","),
        "sequence": saved_event.sequence,
        "previous_hash": saved_event.previous_hash,
        "event_hash": saved_event.event_hash
    }


@router.get("/")
def get_audit_events(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "view_audit_logs"
    )

    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.id.asc())
        .all()
    )

    return [
        {
            "audit_ref": log.audit_ref,
            "permit_id": log.permit_id,
            "timestamp": log.timestamp,
            "pipeline": log.pipeline,
            "stages": log.stages.split(","),
            "sequence": log.sequence,
            "previous_hash": log.previous_hash,
            "event_hash": log.event_hash
        }
        for log in logs
    ]


@router.get("/verify")
def verify_audit_chain(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "view_audit_logs"
    )

    valid = AuditLogger().verify_chain(db)

    return {
        "valid": valid,
        "message": (
            "Audit hash chain is valid"
            if valid
            else "Audit hash chain verification failed"
        )
    }