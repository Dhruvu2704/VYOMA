from pydantic import BaseModel
from typing import Optional


class FinalVerdict(BaseModel):
    permit_id: str
    rule_result: str
    llm_result: str
    agreement: bool
    final_decision: str
    explanation: Optional[str] = None
    requires_human_review: bool