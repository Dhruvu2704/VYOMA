"""Top-level Agent Orchestrator.

Milestone 1 pipeline for a single fixture:

    PERCEIVE -> UNDERSTAND -> PLAN -> RETRIEVE -> REASON -> VERIFY
    -> FINAL VERDICT -> LOG

The orchestrator is model-agnostic: it depends on the reasoning interface,
the rule verdicts/graph facts (evidence), the retriever interface, and the
model router for categorization. No LLM or external service is invoked in
Milestone 1 — reasoning is deterministic and evidence-only.

Audit: an internal, in-memory audit representation is produced and returned.
It is NOT persisted to the backend yet.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.contracts import (
    AuditEvent,
    AuditLogger,
    GraphFacts,
    LLMReasoningResult,
    OrchestratorResult,
    PlanStep,
    RuleVerdict,
    StructuredPTW,
    TaskRequest,
    VerificationResult,
)

from ai_agent.audit import InMemoryAuditLogger
from ai_agent.rag.retriever import Retriever, build_retriever
from ai_agent.reasoning.reasoning_engine import (
    DeterministicReasoningEngine,
    ReasoningEngine,
)
from ai_agent.router.model_router import ModelRouter, build_router
from ai_agent.verification import VerificationEngine


class OrchestratorError(Exception):
    """Raised when a fixture cannot be run through the pipeline."""


class AgentOrchestrator:
    """Runs the full Role 1 evidence pipeline against a fixture."""

    def __init__(
        self,
        reasoning_engine: Optional[ReasoningEngine] = None,
        retriever: Optional[Retriever] = None,
        router: Optional[ModelRouter] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self.reasoning = reasoning_engine or DeterministicReasoningEngine()
        self.retriever = retriever or build_retriever()
        self.router = router or build_router()
        self.verifier = VerificationEngine()
        # Role 1 depends on the AuditLogger interface only; the in-memory
        # implementation is a local default until Role 4 provides the backend.
        self.audit_logger: AuditLogger = audit_logger or InMemoryAuditLogger()

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _perceive(self, fixture: Dict[str, Any]) -> TaskRequest:
        task_request = fixture.get("task_request")
        if not isinstance(task_request, dict):
            raise OrchestratorError("fixture missing 'task_request' object")
        return TaskRequest(**task_request)

    def _understand(self, fixture: Dict[str, Any]) -> StructuredPTW:
        ptw = fixture.get("structured_ptw")
        if not isinstance(ptw, dict):
            raise OrchestratorError("fixture missing 'structured_ptw' object")
        return StructuredPTW(**ptw)

    def _plan(self, task_request: TaskRequest, ptw: StructuredPTW) -> List[PlanStep]:
        permit_id = ptw.get("permit_id") or task_request.get("permit_id")
        return [
            PlanStep(step="perceive", tool=None, model_category=None, status="done"),
            PlanStep(step="understand", tool=None, model_category=None, status="done"),
            PlanStep(step="plan", tool=None, model_category=None, status="done"),
            PlanStep(
                step="retrieve",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="reason",
                tool=None,
                model_category=self.router.resolve("reasoning"),
                status="planned",
            ),
            PlanStep(step="verify", tool=None, model_category=None, status="planned"),
            PlanStep(step="verdict", tool=None, model_category=None, status="planned"),
            PlanStep(step="log", tool="log_event", model_category=None, status="planned"),
        ]

    def _retrieve(
        self, fixture: Dict[str, Any], ptw: StructuredPTW
    ) -> List[Dict[str, Any]]:
        query = f"{ptw.get('work_type')} {ptw.get('scope')}"
        knowledge = self.retriever.retrieve(
            query,
            permit_id=ptw.get("permit_id"),
            context=fixture.get("knowledge"),
        )
        return knowledge

    def _extract_rule_verdict(self, fixture: Dict[str, Any]) -> RuleVerdict:
        verdict = fixture.get("rule_verdict")
        if not isinstance(verdict, dict):
            raise OrchestratorError("fixture missing 'rule_verdict' object")
        # Rule verdict / graph facts are supplied by Role 3 (plant-safety)
        # and are treated strictly as evidence to be reasoned from.
        return RuleVerdict(**verdict)

    def _extract_graph_facts(self, fixture: Dict[str, Any]) -> GraphFacts:
        graph_facts = fixture.get("graph_facts")
        if not isinstance(graph_facts, dict):
            raise OrchestratorError("fixture missing 'graph_facts' object")
        return GraphFacts(**graph_facts)

    def _reason(
        self,
        ptw: StructuredPTW,
        graph_facts: GraphFacts,
        rule_verdict: RuleVerdict,
        retrieved: List[Dict[str, Any]],
        selected_model: str,
    ) -> LLMReasoningResult:
        return self.reasoning.reason(
            ptw=ptw,
            graph_facts=graph_facts,
            rule_verdict=rule_verdict,
            retrieved=retrieved,
        )

    def _verify(
        self, rule_verdict: RuleVerdict, llm_reasoning: LLMReasoningResult
    ) -> VerificationResult:
        return self.verifier.verify(rule_verdict, llm_reasoning)

    def _final_verdict(self, verification: VerificationResult) -> Dict[str, Any]:
        return {
            "permit_id": verification["permit_id"],
            "rule_result": verification["rule_result"],
            "llm_result": verification["llm_result"],
            "agreement": verification["agreement"],
            "final_decision": verification["final_decision"],
            "explanation": verification["explanation"],
            "requires_human_review": verification["requires_human_review"],
            "generated_at": _utc_now(),
            "audit_ref": _new_audit_ref(),
        }

    def _log(
        self,
        permit_id: str,
        pipeline_stages: List[str],
        stages: Dict[str, Any],
    ) -> AuditEvent:
        audit_ref = stages["final_verdict"].get("audit_ref") or _new_audit_ref()
        event = AuditEvent(
            audit_ref=audit_ref,
            permit_id=permit_id,
            timestamp=_utc_now(),
            pipeline=pipeline_stages,
            stages=stages,
            sequence=[
                {"step": s, "status": "done", "audit_ref": audit_ref}
                for s in pipeline_stages
            ],
        )
        # Push through the shared AuditLogger interface (Role 4 implements it
        # for real); the return value confirms the appended audit_ref.
        confirmed_ref = self.audit_logger.log(event)
        if confirmed_ref != audit_ref:
            raise OrchestratorError(
                f"AuditLogger returned mismatched audit_ref: "
                f"{confirmed_ref!r} != {audit_ref!r}"
            )
        return event

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, fixture: Dict[str, Any] | str | Path) -> OrchestratorResult:
        """Run the full pipeline against a fixture dict or fixture file path."""
        if isinstance(fixture, (str, Path)):
            fixture = load_fixture(fixture)
        permit_id = _fixture_permit_id(fixture)

        task_request = self._perceive(fixture)
        ptw = self._understand(fixture)
        plan = self._plan(task_request, ptw)
        retrieved = self._retrieve(fixture, ptw)
        rule_verdict = self._extract_rule_verdict(fixture)
        graph_facts = self._extract_graph_facts(fixture)
        selected_model = self.router.resolve("reasoning")

        llm_reasoning = self._reason(
            ptw=ptw,
            graph_facts=graph_facts,
            rule_verdict=rule_verdict,
            retrieved=retrieved,
            selected_model=selected_model,
        )
        verification = self._verify(rule_verdict, llm_reasoning)
        final_verdict = self._final_verdict(verification)

        stages = {
            "perceived": task_request,
            "understood": ptw,
            "graph_facts": graph_facts,
            "rule_verdict": rule_verdict,
            "retrieved": retrieved,
            "llm_reasoning": llm_reasoning,
            "verification": verification,
            "final_verdict": final_verdict,
        }
        audit = self._log(
            permit_id=permit_id,
            pipeline_stages=[
                "perceive",
                "understand",
                "plan",
                "retrieve",
                "reason",
                "verify",
                "final_verdict",
                "log",
            ],
            stages=stages,
        )

        return OrchestratorResult(
            permit_id=permit_id,
            plan=plan,
            llm_reasoning=llm_reasoning,
            verification=verification,
            final_verdict=final_verdict,
            audit=audit,
        )


# ---------------------------------------------------------------------------
# Module-level helpers (kept free of both stdlib and external deps)
# ---------------------------------------------------------------------------


def _fixture_permit_id(fixture: Dict[str, Any]) -> str:
    for key in ("task_request", "structured_ptw", "rule_verdict", "graph_facts"):
        section = fixture.get(key)
        if isinstance(section, dict) and section.get("permit_id"):
            return str(section["permit_id"])
    raise OrchestratorError("fixture does not identify a permit_id")


def _new_audit_ref() -> str:
    return f"AUD-{uuid.uuid4().hex[:12].upper()}"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_fixture(path: str | Path) -> Dict[str, Any]:
    """Load a fixture JSON file into a dict.

    Fixture files are project-owned data (in ``ai_agent/fixtures``), not
    untrusted uploaded documents. They are still validated structurally by
    the pipeline stages.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)