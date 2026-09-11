from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth import get_current_user
from services.permissions import require_tool_permission
from services.zero_egress import ZeroEgressMonitor


router = APIRouter(
    prefix="/api/security",
    tags=["Security"]
)

security = HTTPBearer()


@router.get("/zero-egress")
def check_zero_egress(
    host: str,
    port: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    current_user = get_current_user(
        credentials.credentials
    )

    require_tool_permission(
        current_user,
        "run_safety_analysis"
    )

    monitor = ZeroEgressMonitor()

    result = monitor.check_connection(
        host,
        port
    )

    return result