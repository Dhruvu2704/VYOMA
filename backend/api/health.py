"""Health / root endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Service"])


@router.get("/")
def root():
    return {"message": "VYOMA + KAVACH Backend is running"}


@router.get("/api/health")
def health():
    return {"status": "ok"}