"""Role-based tool permission checks for the backend."""

from __future__ import annotations

from fastapi import HTTPException

TOOL_PERMISSIONS = {
    "view_permits": ["USER", "SAFETY_OFFICER", "ADMIN"],
    "upload_document": ["USER", "SAFETY_OFFICER", "ADMIN"],
    "run_safety_analysis": ["SAFETY_OFFICER", "ADMIN"],
    "close_permit": ["SAFETY_OFFICER", "ADMIN"],
    "review_task": ["SAFETY_OFFICER", "ADMIN"],
    "view_audit_logs": ["SAFETY_OFFICER", "ADMIN"],
    "manage_users": ["ADMIN"],
}


def require_tool_permission(current_user: dict, tool_name: str) -> dict:
    if tool_name not in TOOL_PERMISSIONS:
        raise HTTPException(status_code=403, detail="Unknown tool")
    if current_user["role"] not in TOOL_PERMISSIONS[tool_name]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to use this tool",
        )
    return current_user