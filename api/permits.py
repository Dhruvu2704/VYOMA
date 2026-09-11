from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from db.database import get_db
from db.models import Permit


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


# =========================
# CREATE PERMIT
# =========================

@router.post("/")
def create_permit(
    permit_data: PermitCreate,
    db: Session = Depends(get_db)
):

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

    return {
        "message": "Permit created successfully",
        "permit_id": permit.permit_id,
        "status": permit.status
    }
    # =========================
# GET ACTIVE PERMITS
# =========================

@router.get("/active")
def get_active_permits(
    db: Session = Depends(get_db)
):
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
    # =========================
# UPDATE PERMIT STATUS
# =========================

@router.put("/{permit_id}/status")
def update_permit_status(
    permit_id: str,
    status: str,
    db: Session = Depends(get_db)
):
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

    return {
        "message": "Permit status updated successfully",
        "permit_id": permit.permit_id,
        "status": permit.status
    }