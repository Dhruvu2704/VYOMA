from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="CREATED")
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Permit(Base):
    __tablename__ = "permits"

    id = Column(Integer, primary_key=True, index=True)
    permit_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)
    plant = Column(String, nullable=False)
    equipment = Column(String, nullable=False)
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    issued_by = Column(Integer, nullable=False)


class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    final_verdict = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    reviewer_id = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)
    comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    payload = Column(Text)
    previous_hash = Column(String)
    event_hash = Column(String)


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String)
    file_path = Column(String, nullable=False)
    sha256 = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_ref = Column(String, unique=True, nullable=False)
    permit_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pipeline = Column(String, nullable=False)
    stages = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)

    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=False)
class User(Base):
    __tablename__ = "users"

id = Column(Integer, primary_key=True, index=True)
username = Column(String, unique=True, nullable=False)
password_hash = Column(String, nullable=False)
role = Column(String, nullable=False, default="USER")