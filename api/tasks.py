from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from pathlib import Path
import uuid

from db.database import get_db
from db.models import Task
from services.pdf_processor import extract_text_from_pdf
from services.task_processor import process_document
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth import get_current_user, require_admin

security = HTTPBearer()


router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"]
)


UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class TaskCreate(BaseModel):
    filename: str


# =========================
# CREATE TASK
# =========================

@router.post("/")
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    new_task = Task(
        filename=task_data.filename,
        status="CREATED",
        created_by=None
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "task_id": f"TASK-{new_task.id:03d}",
        "status": new_task.status
    }


# =========================
# GET ALL TASKS
# =========================

@router.get("/")
def get_tasks(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    current_user = get_current_user(
        credentials.credentials
    )

    tasks = db.query(Task).all()

    return [
        {
            "task_id": f"TASK-{task.id:03d}",
            "filename": task.filename,
            "status": task.status,
            "created_by": task.created_by,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        for task in tasks
    ]


# =========================
# UPLOAD PDF
# =========================

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    # 2. Check extension
    extension = Path(file.filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    # 3. Check MIME type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF content type"
        )

    # 4. Create uploads directory
    UPLOAD_DIR.mkdir(exist_ok=True)

    # 5. Generate safe server-side filename
    safe_filename = f"{uuid.uuid4().hex}.pdf"

    file_path = UPLOAD_DIR / safe_filename

    # 6. Save file with size limit
    size = 0

    try:
        with open(file_path, "wb") as buffer:

            while chunk := await file.read(1024 * 1024):

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum size is 10 MB"
                    )

                buffer.write(chunk)

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    # 7. Check that PDF can be read
    try:
        extracted_text = extract_text_from_pdf(
            str(file_path)
        )

        if not extracted_text.strip():
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="No readable text found in PDF"
            )

    except HTTPException:
        raise

    except Exception:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="Could not read PDF file"
        )

    # 8. Create task in database
    task = Task(
        filename=file.filename,
        file_path=str(file_path),
        status="CREATED",
        created_by=None
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # 9. Return response
    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": task.filename,
        "status": task.status,
        "message": "File uploaded successfully"
    }
    # =========================
# UPLOAD P&ID
# =========================

@router.post("/{task_id}/pid")
async def upload_pid(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validate task ID format
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

    # 2. Find task
    task = db.query(Task).filter(
        Task.id == numeric_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # 3. Check filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    # 4. Check extension
    extension = Path(file.filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    # 5. Check MIME type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF content type"
        )

    # 6. Create uploads directory
    UPLOAD_DIR.mkdir(exist_ok=True)

    # 7. Generate safe server-side filename
    safe_filename = f"{uuid.uuid4().hex}_pid.pdf"

    file_path = UPLOAD_DIR / safe_filename

    # 8. Save file with size limit
    size = 0

    try:
        with open(file_path, "wb") as buffer:

            while chunk := await file.read(1024 * 1024):

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum size is 10 MB"
                    )

                buffer.write(chunk)

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    # 9. Check that PDF can be read
    try:
        extracted_text = extract_text_from_pdf(
            str(file_path)
        )

        if not extracted_text.strip():
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="No readable text found in P&ID PDF"
            )

    except HTTPException:
        raise

    except Exception:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="Could not read P&ID PDF file"
        )

    # 10. Save P&ID path to task
    task.pid_file_path = str(file_path)

    db.commit()
    db.refresh(task)

    # 11. Return response
    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": file.filename,
        "status": task.status,
        "message": "P&ID uploaded successfully"
    }


# =========================
# PROCESS TASK
# =========================

@router.post("/{task_id}/process")
def process_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    # 1. Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # 2. Check file path
    if not task.file_path:
        raise HTTPException(
            status_code=400,
            detail="No file associated with this task"
        )

    try:
        # 3. Processing started
        task.status = "PROCESSING"
        db.commit()

        # 4. Process document
        structured_ptw = process_document(
            task.file_path
        )

        # 5. Processing completed
        task.status = "COMPLETED"
        db.commit()
        db.refresh(task)

        # 6. Return structured PTW
        return {
            "task_id": f"TASK-{task.id:03d}",
            "filename": task.filename,
            "status": task.status,
            "message": "Document processed successfully",
            "structured_ptw": structured_ptw
        }

    except Exception:
        # 7. Processing failed
        task.status = "FAILED"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Document processing failed"
        )


# =========================
# GET SINGLE TASK
# =========================

@router.get("/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    # 1. Validate task ID format
    if not task_id.startswith("TASK-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    # 2. Convert TASK-001 -> 1
    try:
        numeric_id = int(
            task_id.replace("TASK-", "")
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format"
        )

    # 3. Find task in database
    task = db.query(Task).filter(
        Task.id == numeric_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # 4. Return task
    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": task.filename,
        "status": task.status,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }


# =========================
# UPDATE TASK STATUS
# =========================

@router.put("/{task_id}")
def update_task_status(
    task_id: str,
    status: str,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    current_user = get_current_user(
        credentials.credentials
    )

    require_admin(current_user)

    # Convert TASK-001 -> 1
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

    allowed_statuses = [
        "CREATED",
        "PROCESSING",
        "COMPLETED",
        "FAILED"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {allowed_statuses}"
        )

    task.status = status

    db.commit()
    db.refresh(task)

    return {
        "task_id": f"TASK-{task.id:03d}",
        "filename": task.filename,
        "status": task.status,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }