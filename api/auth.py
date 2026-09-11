from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import User
from services.password import hash_password, verify_password
from services.auth import create_access_token


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# =========================
# REGISTER REQUEST
# =========================

class RegisterRequest(BaseModel):
    username: str
    password: str


# =========================
# LOGIN REQUEST
# =========================

class LoginRequest(BaseModel):
    username: str
    password: str


# =========================
# REGISTER USER
# =========================

@router.post("/register")
def register_user(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):

    # Check if username already exists
    existing_user = db.query(User).filter(
        User.username == user_data.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    # Hash password
    hashed_password = hash_password(
        user_data.password
    )

    # Create user
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role="USER"
    )

    # Save user
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
        "role": new_user.role
    }


# =========================
# LOGIN USER
# =========================

@router.post("/login")
def login_user(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):

    # Find user
    user = db.query(User).filter(
        User.username == user_data.username
    ).first()

    # User doesn't exist
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Verify password
    password_valid = verify_password(
        user_data.password,
        user.password_hash
    )

    # Password is incorrect
    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT token
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }