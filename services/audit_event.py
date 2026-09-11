from pydantic import BaseModel
from typing import List


class AuditEvent(BaseModel):
    audit_ref: str
    permit_id: str
    timestamp: str
    pipeline: str
    stages: List[str]
    sequence: int