"""Authentication endpoints: register and login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.services.auth import create_access_token
from backend.services.password import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register_user(user_data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }


@router.post("/login")
def login_user(user_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(user_id=user.id, username=user.username, role=user.role)

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
    }