from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Task, Deliverable
from services.auth import get_current_user
from pydantic import BaseModel


router = APIRouter(
    prefix="/api/deliverables",
    tags=["Deliverables"]
)


@router.get("/{task_id}")
def get_deliverables(
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    # Check task ID format
    if not task_id.startswith("TASK-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    try:
        numeric_id = int(
            task_id.replace("TASK-", "")
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    # Check task exists
    task = db.query(Task).filter(
        Task.id == numeric_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # Get deliverables for this task
    deliverables = db.query(Deliverable).filter(
        Deliverable.task_id == task.id
    ).all()

    return {
        "task_id": f"TASK-{task.id:03d}",
        "deliverables": [
            {
                "id": item.id,
                "filename": item.filename,
                "file_type": item.file_type,
                "file_path": item.file_path,
                "sha256": item.sha256,
                "created_at": item.created_at
            }
            for item in deliverables
        ]
    }
class DeliverableCreate(BaseModel):
    filename: str
    file_type: str
    file_path: str
    sha256: str | None = None


@router.post("/{task_id}")
def create_deliverable(
    task_id: str,
    data: DeliverableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if not task_id.startswith("TASK-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    try:
        numeric_id = int(
            task_id.replace("TASK-", "")
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    task = db.query(Task).filter(
        Task.id == numeric_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    deliverable = Deliverable(
        task_id=task.id,
        filename=data.filename,
        file_type=data.file_type,
        file_path=data.file_path,
        sha256=data.sha256
    )

    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)

    return {
        "message": "Deliverable created successfully",
        "task_id": f"TASK-{task.id:03d}",
        "deliverable_id": deliverable.id,
        "filename": deliverable.filename,
        "file_type": deliverable.file_type,
        "file_path": deliverable.file_path,
        "sha256": deliverable.sha256
    }