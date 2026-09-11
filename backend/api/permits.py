"""Permit endpoints backed by the local SQLite permit register.

Permits feed the active-permit overlap evidence for KAVACH plant safety.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Permit
from backend.services.auth import get_current_user
from backend.services.permissions import require_tool_permission

router = APIRouter(prefix="/api/permits", tags=["Permits"])


def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_current_user(credentials.credentials)


class PermitCreate(BaseModel):
    permit_id: str
    plant: str
    equipment: str
    valid_from: datetime
    valid_to: datetime
    issued_by: int


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


@router.post("/", status_code=201)
def create_permit(
    permit_data: PermitCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "run_safety_analysis")

    existing = (
        db.query(Permit).filter(Permit.permit_id == permit_data.permit_id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Permit already exists")

    permit = Permit(
        permit_id=permit_data.permit_id,
        status="ACTIVE",
        plant=permit_data.plant,
        equipment=permit_data.equipment,
        valid_from=permit_data.valid_from,
        valid_to=permit_data.valid_to,
        issued_by=permit_data.issued_by,
    )
    db.add(permit)
    db.commit()
    db.refresh(permit)

    return {
        "message": "Permit created successfully",
        "permit_id": permit.permit_id,
        "status": permit.status,
    }


@router.get("/active")
def get_active_permits(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    permits = db.query(Permit).filter(Permit.status == "ACTIVE").all()
    return [
        {
            "permit_id": p.permit_id,
            "status": p.status,
            "plant": p.plant,
            "equipment": p.equipment,
            "valid_from": _iso(p.valid_from),
            "valid_to": _iso(p.valid_to),
            "issued_by": p.issued_by,
        }
        for p in permits
    ]


@router.put("/{permit_id}/status")
def update_permit_status(
    permit_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "close_permit")

    permit = db.query(Permit).filter(Permit.permit_id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    allowed_statuses = ["ACTIVE", "EXPIRED", "CLOSED"]
    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {allowed_statuses}",
        )

    permit.status = status
    db.commit()
    db.refresh(permit)

    return {
        "message": "Permit status updated successfully",
        "permit_id": permit.permit_id,
        "status": permit.status,
    }