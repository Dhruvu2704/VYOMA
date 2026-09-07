"""AgentState — the single state object passed through the Role 1 workflow.

AgentState carries all pipeline state from PERCEIVE through LOG. Each stage
reads from and writes to this object. A failed stage records the error,
identifies the failed stage, and prevents a fake approval.

This is a Role 1 internal type; it lives in ``ai_agent/``, not in
``shared/contracts.py``, because other roles do not need to know about
the internal workflow state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from shared.contracts import (
    ActivePermits,
    AuditEvent,
    FinalVerdict,
    GraphFacts,
    LLMReasoningResult,
    PlanStep,
    RuleVerdict,
    StructuredPID,
    StructuredPTW,
    VerificationResult,
)


class StageError(TypedDict):
    """Records a failure at a specific pipeline stage."""

    stage: str
    error_type: str
    message: str
    timestamp: str


class ExecutionTraceEntry(TypedDict):
    """One entry in the execution trace recording stage progression."""

    stage: str
    status: str
    timestamp: str


@dataclass
class AgentState:
    """Single state object passed through the controlled workflow.

    Carries all pipeline data from PERCEIVE through LOG. Each stage
    reads relevant fields and writes its outputs back to the state.

    Fields are initialised to safe defaults so that partial pipeline
    completion still yields a inspectable state.
    """

    # -- Identity -----------------------------------------------------------
    task_id: str = ""
    task_type: str = ""
    permit_id: str = ""

    # -- Input --------------------------------------------------------------
    input_files: List[str] = field(default_factory=list)

    # -- Extracted evidence (populated by perceive / understand) -------------
    structured_ptw: Optional[StructuredPTW] = None
    structured_pid: Optional[StructuredPID] = None
    graph_facts: Optional[GraphFacts] = None
    active_permits: Optional[ActivePermits] = None
    rule_verdict: Optional[RuleVerdict] = None

    # -- Retrieved knowledge (populated by retrieve) -------------------------
    rag_context: List[Dict[str, Any]] = field(default_factory=list)

    # -- Plan (populated by plan) -------------------------------------------
    plan: Optional[List[PlanStep]] = None

    # -- Computed results ---------------------------------------------------
    llm_result: Optional[LLMReasoningResult] = None
    verification: Optional[VerificationResult] = None
    final_verdict: Optional[FinalVerdict] = None

    # -- Tracking -----------------------------------------------------------
    errors: List[StageError] = field(default_factory=list)
    tool_notes: List[StageError] = field(default_factory=list)
    audit_refs: List[str] = field(default_factory=list)
    execution_trace: List[ExecutionTraceEntry] = field(default_factory=list)
    current_stage: Optional[str] = None

    # -- Internal (audit compatibility) -------------------------------------
    _task_request: Optional[Dict[str, Any]] = field(default=None, repr=False)
    _audit_event: Optional[AuditEvent] = field(default=None, repr=False)

    # -- Derived helpers ----------------------------------------------------

    @property
    def has_errors(self) -> bool:
        """True if any stage has recorded an error."""
        return len(self.errors) > 0

    @property
    def failed_stage(self) -> Optional[str]:
        """The name of the first stage that failed, or ``None``."""
        for entry in self.execution_trace:
            if entry["status"] == "failed":
                return entry["stage"]
        return None

    @property
    def is_failed(self) -> bool:
        """True if the pipeline encountered a stage failure."""
        return any(e["status"] == "failed" for e in self.execution_trace)

    @property
    def completed_stages(self) -> List[str]:
        """List of stage names that completed successfully."""
        return [e["stage"] for e in self.execution_trace if e["status"] == "completed"]
