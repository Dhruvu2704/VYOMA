import os

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt, JWTError


load_dotenv()

SECRET_KEY = os.getenv("VYOMA_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("VYOMA_SECRET_KEY is not configured")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(
    user_id: int,
    username: str,
    role: str
):

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    data = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire
    }

    token = jwt.encode(
        data,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def verify_access_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


def get_current_user(token: str):

    payload = verify_access_token(token)

    user_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")

    if not user_id or not username or not role:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    return {
        "user_id": user_id,
        "username": username,
        "role": role
    }


def require_role(
    current_user: dict,
    allowed_roles: list[str]
):

    if current_user["role"] not in allowed_roles:

        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action"
        )

    return current_user


def require_admin(current_user: dict):

    return require_role(
        current_user,
        ["ADMIN"]
    )

