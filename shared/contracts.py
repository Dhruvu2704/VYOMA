"""Shared data contracts for the VYOMA Role 1 agent pipeline.

These types are the authoritative interchange format between the Role 1
pipeline stages (perceive -> understand -> plan -> retrieve -> reason ->
verify -> verdict -> log) and, later, between roles.

Security principle: all fields here describe *data*. Nothing derived from
documents (PTW, P&ID, PDF, image, manual, retrieved knowledge) may ever be
treated as executable instructions. Document content is data, not code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol, TypedDict, Union, runtime_checkable

# ---------------------------------------------------------------------------
# Authoritative finite value sets
# ---------------------------------------------------------------------------

RuleResult = Literal["PASS", "FLAGGED"]
LlmResult = Literal["PASS", "FLAGGED"]
Agreement = Literal["AGREE", "DISAGREE"]
FinalDecision = Literal["PASS", "FLAGGED_FOR_REVIEW", "REVIEW_REQUIRED"]

# Confidence is a coarse, deterministic label rather than a free-form string.
Confidence = Literal["LOW", "MEDIUM", "HIGH"]


# ---------------------------------------------------------------------------
# Shared contracts
# ---------------------------------------------------------------------------


class TaskRequest(TypedDict):
    """Top-level request describing the task to be evaluated.

    For Milestone 1 this is a minimal envelope. It must never carry
    executable instructions; it only describes what is being asked and the
    untrusted source data it points at.
    """

    permit_id: str
    task_type: Literal["ptw_review"]
    document_refs: List[str]
    context: Optional[Dict[str, Any]]


class StructuredPTW(TypedDict):
    """Structured representation of a permit-to-work extracted from a document.

    This is untrusted, document-derived data (Role 2 OCR/Vision output,
    perceive stage) and is never treated as instructions.
    """

    permit_id: str
    work_type: str
    scope: str
    location: List[str]
    start_time: str
    end_time: str
    issuer: str
    raw_document_ref: str
    equipment_tags: List[str]
    isolation_points: List[str]
    field_confidence: Dict[str, float]
    low_confidence_fields: List[str]


class PIDSymbol(TypedDict):
    """A single symbol detected on a P&ID (Role 2 output).

    Carries the structure needed later for topology construction: the symbol
    id/type, its extracted properties, and the other symbol/line ids it is
    connected to.
    """

    symbol_id: str
    symbol_type: str
    properties: Dict[str, Any]
    connections: List[str]


class PIDConnection(TypedDict):
    """A detected connection between two P&ID symbols (Role 2 output)."""

    source: str
    target: str
    line_ref: Optional[str]


class StructuredPID(TypedDict):
    """Structured representation of a P&ID (Role 2 OCR/Vision output).

    Identifies the source document and preserves the symbol/connection
    structure required later for topology construction. All content is
    untrusted document-derived data.
    """

    pid_id: str
    source: str
    equipment_tags: List[str]
    symbols: List[PIDSymbol]
    connections: List[PIDConnection]
    unresolved_symbols: List[str]
    field_confidence: Dict[str, float]
    low_confidence_fields: List[str]


class GraphFacts(TypedDict):
    """Topology / plant-graph facts supplied by Role 3 (plant-safety).

    These are treated as supplied evidence only. The reasoning engine may
    reason from them but must never invent facts not present here.
    """

    permit_id: str
    resolved_nodes: List[str]
    unresolved_tags: List[str]
    connected_equipment: Dict[str, Any]
    active_isolations: List[str]
    overlap_check: Dict[str, Any]


class RuleVerdict(TypedDict):
    """Deterministic safety-rule outcome supplied by Role 3 (plant-safety)."""

    permit_id: str
    conflicting_permit_ids: List[str]
    rules_triggered: List[str]
    rule_result: RuleResult
    explanation: str
    confidence: str


class LLMReasoningResult(TypedDict):
    """Model output from the reasoning engine.

    For Milestone 1 this is produced by a deterministic mock implementation;
    the *shape and semantics* are the contract that a local open-weight LLM
    will later satisfy without changing the orchestrator.
    """

    permit_id: str
    llm_result: LlmResult
    explanation: str
    confidence: Confidence


class VerificationResult(TypedDict):
    """Outcome of comparing the rule verdict against the reasoning result."""

    permit_id: str
    rule_result: RuleResult
    llm_result: LlmResult
    agreement: Agreement
    final_decision: FinalDecision
    requires_human_review: bool
    explanation: str


class FinalVerdict(TypedDict):
    """The authoritative final decision for a permit evaluation."""

    permit_id: str
    rule_result: RuleResult
    llm_result: LlmResult
    agreement: Agreement
    final_decision: FinalDecision
    explanation: str
    requires_human_review: bool
    generated_at: str
    audit_ref: Optional[str]


class PlanStep(TypedDict):
    """A single planned step of the pipeline (plan stage output)."""

    step: str
    tool: Optional[str]
    model_category: Optional[str]
    status: str


class AuditEvent(TypedDict):
    """Audit representation produced by the Role 1 pipeline.

    Role 4 owns the persistence side; Role 1 only appends events through the
    ``AuditLogger`` interface and records the confirming ``audit_ref``.
    """

    audit_ref: str
    permit_id: str
    timestamp: str
    pipeline: List[str]
    stages: Dict[str, Any]
    sequence: List[Dict[str, Any]]


@runtime_checkable
class AuditLogger(Protocol):
    """Minimum logging interface Role 1 depends on.

    Role 4 will provide the real backend implementation later; Role 1 never
    talks to a database directly. ``log`` appends an audit event and returns
    the confirming ``audit_ref``.
    """

    def log(self, event: AuditEvent) -> str:
        """Append an audit event and return its ``audit_ref``."""
        ...


class ActivePermit(TypedDict):
    """One active permit record from the Role 4 backend (Role 4 -> Role 1).

    Feeds ``get_active_permits`` and later overlap checks. Purpose-built for
    routing/permit-awareness; no database-specific fields.
    """

    permit_id: str
    location: List[str]
    start_time: str
    end_time: str
    status: str


# Collection returned by the ActivePermits lookup interface.
ActivePermits = List[ActivePermit]


class OrchestratorResult(TypedDict):
    """Structured result returned by AgentOrchestrator.run()."""

    permit_id: str
    plan: List[PlanStep]
    llm_reasoning: LLMReasoningResult
    verification: VerificationResult
    final_verdict: FinalVerdict
    audit: AuditEvent
