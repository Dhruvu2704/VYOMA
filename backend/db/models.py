"""SQLAlchemy ORM models for the VYOMA + KAVACH backend.

The backend persists references and results around the KAVACH pipeline; it
does not rebuild the orchestrator's internal state machine.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from backend.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="USER")
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    input_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="CREATED")
    permit_id = Column(String, nullable=True)
    scenario = Column(String, nullable=True)
    audit_ref = Column(String, nullable=True)
    result_json = Column(Text, nullable=True)
    error = Column(String, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Permit(Base):
    __tablename__ = "permits"

    id = Column(Integer, primary_key=True, index=True)
    permit_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    plant = Column(String, nullable=False)
    equipment = Column(String, nullable=False)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    issued_by = Column(Integer, nullable=True)


class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    final_verdict = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    file_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_ref = Column(String, unique=True, nullable=False)
    permit_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pipeline = Column(String, nullable=False)
    stages = Column(String, nullable=False)
    sequence = Column(String, nullable=False)
    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=False)