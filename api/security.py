from fastapi import APIRouter, Depends
from services.auth import get_current_user
from security.zero_egress import ZeroEgressMonitor

router = APIRouter(
    prefix="/api/security",
    tags=["Security"]
)

monitor = ZeroEgressMonitor()


@router.get("/zero-egress")
def get_zero_egress_status(
    current_user=Depends(get_current_user)
):
    return monitor.get_status()


@router.get("/zero-egress/events")
def get_zero_egress_events(
    current_user=Depends(get_current_user)
):
    return monitor.get_events()