from pydantic import BaseModel
from typing import List, Optional


class LLMResult(BaseModel):
    permit_id: str
    result: str
    violations: List[str] = []
    warnings: List[str] = []
    explanation: Optional[str] = None