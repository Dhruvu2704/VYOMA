"""Task endpoints: upload, status, processing, deliverables.

Uploads accept a KAVACH contract envelope (.json) containing at least a
``structured_ptw`` object (and ideally a ``structured_pid``). The envelope is
stored as-is; processing hands it to the KAVACH AgentOrchestrator.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from backend.db.database import get_db
from backend.db.models import Deliverable, Task
from backend.services.audit_logger import AuditLogger
from backend.services.auth import get_current_user
from backend.services.kavach import KavachConnector
from backend.services.permissions import require_tool_permission
from backend.services.task_processor import (
    TaskProcessingError,
    _resolve_task_id,
    process_task,
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_current_user(credentials.credentials)


def get_connector(request: Request) -> KavachConnector:
    connector = getattr(request.app.state, "kavach_connector", None)
    if connector is None:
        connector = KavachConnector()
        request.app.state.kavach_connector = connector
    return connector


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


class ReviewRequest(BaseModel):
    decision: str
    reason: str


def _deliverables(db: Session, task_id: int) -> List[Dict[str, Any]]:
    rows = db.query(Deliverable).filter(Deliverable.task_id == task_id).all()
    return [
        {
            "filename": row.filename,
            "file_type": row.file_type,
            "file_path": row.file_path,
            "sha256": row.sha256,
        }
        for row in rows
    ]


def _serialize_task(db: Session, task: Task) -> Dict[str, Any]:
    result = None
    if task.result_json:
        try:
            result = json.loads(task.result_json)
        except json.JSONDecodeError:
            result = None
    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": task.filename,
        "status": task.status,
        "created_by": task.created_by,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
        "permit_id": task.permit_id,
        "scenario": task.scenario,
        "audit_ref": task.audit_ref,
        "error": task.error,
        "review_status": task.review_status,
        "reviewed_by": task.reviewed_by,
        "review_reason": task.review_reason,
        "reviewed_at": _iso(task.reviewed_at),
        "result": result,
        "deliverables": _deliverables(db, task.id),
    }


@router.get("")
def list_tasks(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    """Recent tasks for the frontend dashboard (newest first)."""
    tasks = (
        db.query(Task)
        .order_by(Task.id.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return [_serialize_task(db, task) for task in tasks]


def _validate_envelope(data: Any) -> None:
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=400,
            detail="Uploaded JSON must be an object",
        )
    if not isinstance(data.get("structured_ptw"), dict):
        raise HTTPException(
            status_code=400,
            detail="Envelope requires a 'structured_ptw' object",
        )


@router.post("/upload", status_code=201)
async def upload_task(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "upload_document")

    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if Path(filename).suffix.lower() != ".json":
        raise HTTPException(
            status_code=400,
            detail="Only JSON contract envelopes are allowed",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not valid JSON",
        ) from exc
    _validate_envelope(envelope)

    upload_dir = Path(UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.json"
    file_path = upload_dir / safe_name
    file_path.write_bytes(raw)

    ptw = envelope["structured_ptw"]
    task = Task(
        filename=filename,
        file_path=str(file_path),
        input_json=json.dumps(envelope),
        status="CREATED",
        scenario=str(envelope.get("scenario") or ""),
        permit_id=str(ptw.get("permit_id") or ""),
        created_by=current_user["user_id"],
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": task.filename,
        "status": task.status,
        "message": "File uploaded successfully",
    }


@router.get("/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    try:
        numeric_id = _resolve_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID format") from exc

    task = db.query(Task).filter(Task.id == numeric_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(db, task)


@router.post("/{task_id}/process")
def process_task_endpoint(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "run_safety_analysis")

    try:
        numeric_id = _resolve_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID format") from exc

    task = db.query(Task).filter(Task.id == numeric_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.file_path:
        raise HTTPException(
            status_code=400,
            detail="No file associated with this task",
        )

    connector = get_connector(request)
    process_task(db, task, connector)
    return _serialize_task(db, task)


DECISION_TO_REVIEW_STATUS = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "REQUEST_CHANGES": "CHANGES_REQUESTED",
}


@router.post("/{task_id}/review")
def review_task_endpoint(
    task_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    require_tool_permission(current_user, "review_task")

    try:
        numeric_id = _resolve_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID format") from exc

    task = db.query(Task).filter(Task.id == numeric_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    decision = body.decision.strip()
    reason = body.reason.strip()
    if decision not in DECISION_TO_REVIEW_STATUS:
        raise HTTPException(
            status_code=400,
            detail="Invalid decision; expected APPROVE, REJECT or REQUEST_CHANGES",
        )
    if not reason:
        raise HTTPException(status_code=400, detail="Review reason is required")

    result = None
    if task.result_json:
        try:
            result = json.loads(task.result_json)
        except json.JSONDecodeError:
            result = None
    final_verdict = (result or {}).get("final_verdict") or {}
    decided = bool(final_verdict) or bool(
        (result or {}).get("final_decision")
    )
    requires_review = bool(
        final_verdict.get("requires_human_review")
        if final_verdict
        else (result or {}).get("requires_human_review")
    )
    if not decided or not requires_review:
        raise HTTPException(status_code=400, detail="Task is not reviewable")

    if task.review_status is not None:
        raise HTTPException(status_code=409, detail="Task already reviewed")

    now = datetime.utcnow()
    task.review_status = DECISION_TO_REVIEW_STATUS[decision]
    task.reviewed_by = current_user["user_id"]
    task.review_reason = reason
    task.reviewed_at = now
    db.commit()
    db.refresh(task)

    event = AuditLogger().create_event(
        audit_ref=f"REVIEW-{task.id}-{uuid.uuid4().hex[:8]}",
        permit_id=task.permit_id or "",
        timestamp=now.isoformat(),
        pipeline=["human_review"],
        stages=json.dumps(
            {
                "decision": decision,
                "reason": reason,
                "reviewed_by": current_user["user_id"],
            }
        ),
        sequence=f"review:{task.id}",
    )
    AuditLogger().save_event(db, event)

    return _serialize_task(db, task)


@router.get("/{task_id}/deliverables")
def get_task_deliverables(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    try:
        numeric_id = _resolve_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID format") from exc

    task = db.query(Task).filter(Task.id == numeric_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": f"TASK-{task.id:03d}",
        "deliverables": _deliverables(db, task.id),
    }


@router.get("/{task_id}/deliverables/{filename}")
def download_deliverable(
    task_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_user),
):
    """Download a stored deliverable for a task.

    The file is located through the persisted deliverable row so the
    filename parameter can never be used for path traversal.
    """
    try:
        numeric_id = _resolve_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID format") from exc

    row = (
        db.query(Deliverable)
        .filter(Deliverable.task_id == numeric_id)
        .filter(Deliverable.filename == filename)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    path = Path(row.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Deliverable file is missing")

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if path.suffix.lower() == ".docx"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if path.suffix.lower() == ".xlsx"
        else "application/octet-stream"
    )
    return FileResponse(str(path), filename=row.filename, media_type=media_type)