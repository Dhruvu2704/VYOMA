from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from db.database import get_db
from db.models import Permit
from services.auth import get_current_user
from services.permissions import require_tool_permission
from audit.logger import AuditLogger


router = APIRouter(
    prefix="/api/permits",
    tags=["Permits"]
)


class PermitCreate(BaseModel):
    permit_id: str
    plant: str
    equipment: str
    valid_from: datetime
    valid_to: datetime
    issued_by: int


@router.post("/")
def create_permit(
    permit_data: PermitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "create_permit"
    )

    existing_permit = db.query(Permit).filter(
        Permit.permit_id == permit_data.permit_id
    ).first()

    if existing_permit:
        raise HTTPException(
            status_code=400,
            detail="Permit already exists"
        )

    permit = Permit(
        permit_id=permit_data.permit_id,
        status="ACTIVE",
        plant=permit_data.plant,
        equipment=permit_data.equipment,
        valid_from=permit_data.valid_from,
        valid_to=permit_data.valid_to,
        issued_by=permit_data.issued_by
    )

    db.add(permit)
    db.commit()
    db.refresh(permit)

    audit_logger = AuditLogger()

    audit_event = audit_logger.create_event(
        permit_id=permit.permit_id,
        pipeline="PERMIT",
        stages=["PERMIT_CREATED"],
        sequence=permit.id
    )

    audit_logger.save_event(
        db,
        audit_event
    )

    return {
        "message": "Permit created successfully",
        "permit_id": permit.permit_id,
        "status": permit.status
    }


@router.get("/active")
def get_active_permits(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "view_permits"
    )

    permits = db.query(Permit).filter(
        Permit.status == "ACTIVE"
    ).all()

    return [
        {
            "permit_id": permit.permit_id,
            "status": permit.status,
            "plant": permit.plant,
            "equipment": permit.equipment,
            "valid_from": permit.valid_from,
            "valid_to": permit.valid_to,
            "issued_by": permit.issued_by
        }
        for permit in permits
    ]


@router.put("/{permit_id}/status")
def update_permit_status(
    permit_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "close_permit"
    )

    permit = db.query(Permit).filter(
        Permit.permit_id == permit_id
    ).first()

    if not permit:
        raise HTTPException(
            status_code=404,
            detail="Permit not found"
        )

    allowed_statuses = [
        "ACTIVE",
        "EXPIRED",
        "CLOSED"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {allowed_statuses}"
        )

    permit.status = status

    db.commit()
    db.refresh(permit)

    audit_logger = AuditLogger()

    audit_event = audit_logger.create_event(
        permit_id=permit.permit_id,
        pipeline="PERMIT",
        stages=[f"PERMIT_STATUS_{status}"],
        sequence=permit.id
    )

    audit_logger.save_event(
        db,
        audit_event
    )

    return {
        "message": "Permit status updated successfully",
        "permit_id": permit.permit_id,
        "status": permit.status
    }