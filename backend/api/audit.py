"""Audit endpoints: read the persisted KAVACH audit records.

Audit records are created only by task processing (from the KAVACH audit
reference). There is no public record-creation endpoint, so the audit truth
cannot be forged through the API.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import AuditLog
from backend.services.audit_logger import AuditLogger
from backend.services.auth import get_current_user
from backend.services.permissions import require_tool_permission

router = APIRouter(prefix="/api/audit", tags=["Audit"])


def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_current_user(credentials.credentials)


def _serialize(log: AuditLog) -> dict:
    return {
        "audit_ref": log.audit_ref,
        "permit_id": log.permit_id,
        "timestamp": log.timestamp.isoformat(),
        "pipeline": log.pipeline.split(","),
        "sequence": log.sequence,
        "previous_hash": log.previous_hash,
        "event_hash": log.event_hash,
    }


@router.get("/")
def get_audit_events(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "view_audit_logs")
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    return [_serialize(log) for log in logs]


@router.get("/verify")
def verify_audit_chain(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "view_audit_logs")
    return {"valid": AuditLogger().verify_chain(db)}