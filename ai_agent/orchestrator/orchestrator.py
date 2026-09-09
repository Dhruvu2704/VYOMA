"""Top-level Agent Orchestrator.

Day 1 controlled workflow engine for a single task:

    PERCEIVE -> UNDERSTAND -> PLAN -> RETRIEVE -> USE TOOL -> REASON
    -> VERIFY -> ACT -> LOG

The orchestrator is model-agnostic: it depends on the reasoning interface,
the rule verdicts/graph facts (evidence), the retriever interface, and the
model router for categorization. No LLM or external service is invoked in
Milestone 1 — reasoning is deterministic and evidence-only.

``AgentState`` is the single state object threaded through every stage.
A failed stage records the error, identifies the failed stage, and prevents
a fake approval. It never silently continues as if the failed operation had
succeeded.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.contracts import (
    AuditEvent,
    AuditLogger,
    GraphFacts,
    OrchestratorResult,
    PlanStep,
    RuleVerdict,
    StructuredPTW,
)

from ai_agent.agent_state import (
    AgentState,
    ExecutionTraceEntry,
    StageError,
)
from ai_agent.audit import InMemoryAuditLogger
from ai_agent.config import OllamaConfig
from ai_agent.planner import TaskAwarePlanner
from ai_agent.rag.retriever import Retriever, build_retriever
from ai_agent.reasoning.reasoning_engine import (
    DeterministicReasoningEngine,
    ReasoningEngine,
)
from ai_agent.router.model_router import ModelRouter, build_router
from ai_agent.task_classifier import TaskClassifier, TaskType
from ai_agent.tool_registry import ToolRegistry, ToolRegistryError
from ai_agent.verification import VerificationEngine


class OrchestratorError(Exception):
    """Raised when a fixture cannot be run through the pipeline."""


class StageFailure(Exception):
    """Internal signal that a pipeline stage failed.

    Carries the name of the failed stage so the orchestrator can record it
    on ``AgentState``.
    """

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message


class AgentOrchestrator:
    """Runs the full Role 1 controlled workflow over ``AgentState``."""

    PIPELINE_STAGES: List[str] = [
        "perceive",
        "understand",
        "plan",
        "retrieve",
        "use_tool",
        "reason",
        "verify",
        "act",
        "log",
    ]

    def __init__(
        self,
        reasoning_engine: Optional[ReasoningEngine] = None,
        retriever: Optional[Retriever] = None,
        router: Optional[ModelRouter] = None,
        audit_logger: Optional[AuditLogger] = None,
        classifier: Optional[TaskClassifier] = None,
        planner: Optional[TaskAwarePlanner] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.reasoning = reasoning_engine or DeterministicReasoningEngine()
        self.retriever = retriever or build_retriever()
        self.router = router or build_router()
        self.verifier = VerificationEngine()
        self.classifier = classifier or TaskClassifier()
        self.planner = planner or TaskAwarePlanner(router=self.router)
        self.tools: ToolRegistry = tool_registry or ToolRegistry()
        # Role 1 depends on the AuditLogger interface only; the in-memory
        # implementation is a local default until Role 4 provides the backend.
        self.audit_logger: AuditLogger = audit_logger or InMemoryAuditLogger()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_state(self, fixture: Dict[str, Any]) -> AgentState:
        state = AgentState()
        task_request = fixture.get("task_request")
        if isinstance(task_request, dict):
            if not state.task_id and task_request.get("task_id"):
                state.task_id = str(task_request["task_id"])
            if not state.permit_id and task_request.get("permit_id"):
                state.permit_id = str(task_request["permit_id"])
            if not state.task_type and task_request.get("task_type"):
                state.task_type = str(task_request["task_type"])
            state._task_request = task_request
        for key in (
            "task_request",
            "structured_ptw",
            "structured_pid",
            "graph_facts",
            "rule_verdict",
        ):
            section = fixture.get(key)
            if isinstance(section, dict) and not state.permit_id:
                if section.get("permit_id"):
                    state.permit_id = str(section["permit_id"])
                    break
        if not state.task_id:
            state.task_id = state.permit_id
        state.input_files = list(
            fixture.get("document_refs")
            or (task_request.get("document_refs") if isinstance(task_request, dict) else None)
            or []
        )
        return state

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _perceive(self, state: AgentState, fixture: Dict[str, Any]) -> AgentState:
        task_request = fixture.get("task_request")
        if not isinstance(task_request, dict):
            raise StageFailure("perceive", "fixture missing 'task_request' object")
        if not state.permit_id:
            state.permit_id = str(task_request.get("permit_id", ""))
        state._task_request = task_request
        state.task_type = str(task_request.get("task_type", ""))
        # Classify deterministically (no LLM). A classification failure is a
        # perceive-stage failure.
        try:
            state.task_type = self.classifier.classify(fixture)
        except TaskClassificationError as exc:
            raise StageFailure("perceive", str(exc)) from exc
        return state

    def _understand(self, state: AgentState, fixture: Dict[str, Any]) -> AgentState:
        ptw = fixture.get("structured_ptw")
        if not isinstance(ptw, dict):
            raise StageFailure("understand", "fixture missing 'structured_ptw' object")
        state.structured_ptw = StructuredPTW(**ptw)
        pid = fixture.get("structured_pid")
        if isinstance(pid, dict):
            from shared.contracts import StructuredPID

            state.structured_pid = StructuredPID(**pid)
        rule_verdict = fixture.get("rule_verdict")
        if isinstance(rule_verdict, dict):
            state.rule_verdict = RuleVerdict(**rule_verdict)
        graph_facts = fixture.get("graph_facts")
        if isinstance(graph_facts, dict):
            state.graph_facts = GraphFacts(**graph_facts)
        return state

    def _plan(self, state: AgentState, task_type: TaskType) -> AgentState:
        state.plan = self.planner.plan(task_type, state.permit_id)
        return state

    def _retrieve(self, state: AgentState, fixture: Dict[str, Any]) -> AgentState:
        ptw = state.structured_ptw
        if ptw is None:
            raise StageFailure("retrieve", "structured_ptw is required before retrieval")
        query = f"{ptw.get('work_type')} {ptw.get('scope')}"
        state.rag_context = self.retriever.retrieve(
            query,
            permit_id=ptw.get("permit_id"),
            context=fixture.get("knowledge"),
        )
        return state

    def _use_tool(self, state: AgentState) -> AgentState:
        """Execute the planned tool step against the closed tool registry.

        Unknown tools are rejected outright (they are not in the closed
        registry).  Conceptual tools that are ``known`` but not yet
        implemented in Milestone 1 are recorded as informational notes and
        skipped — they never fabricate a result, and they never claim the
        operation succeeded.  A real tool backend slots in later without
        changing the workflow.
        """
        if state.plan is None:
            raise StageFailure("use_tool", "no plan available for tool dispatch")
        tool_name = None
        for step in state.plan:
            if step["step"] == "use_tool" and step.get("tool"):
                tool_name = step["tool"]
                break
        if tool_name is None:
            return state
        if not self.tools.is_known(tool_name):
            raise StageFailure(
                "use_tool",
                f"Unknown/unregistered tool {tool_name!r}; tool rejected.",
            )
        try:
            self.tools.handle(tool_name, permit_id=state.permit_id)
        except ToolRegistryError:
            # Registered-but-not-implemented is a documented Milestone 1
            # limitation.  Recorded as a non-fatal note (NOT an error): the
            # tool did not execute, but no safety-critical stage depends on it
            # yet.  Genuine failures stay in ``state.errors``.
            state.tool_notes.append(
                StageError(
                    stage="use_tool",
                    error_type="ToolUnavailable",
                    message=f"Tool {tool_name!r} is registered but not "
                    "implemented in Milestone 1; skipped as non-fatal.",
                    timestamp=_utc_now(),
                )
            )
        return state

    def _reason(self, state: AgentState) -> AgentState:
        if state.structured_ptw is None or state.graph_facts is None or state.rule_verdict is None:
            raise StageFailure(
                "reason",
                "cannot reason without ptw, graph_facts and rule_verdict",
            )
        # Route reasoning through the configured engine, passing the full
        # structured context. The engine (deterministic or provider-backed)
        # grounds its conclusion in the supplied evidence; it never invents
        # facts and never silently overrides the safety rule result.
        state.llm_result = self.reasoning.reason(
            ptw=state.structured_ptw,
            graph_facts=state.graph_facts,
            rule_verdict=state.rule_verdict,
            retrieved=state.rag_context,
            structured_pid=state.structured_pid,
            active_permits=state.active_permits,
            task=state._task_request,
        )
        # Record which provider/model served the reasoning stage so the audit
        # trace captures the model/provider activity.
        state.reasoning_provider = _reasoning_provider_name(self.reasoning)
        return state

    def _verify(self, state: AgentState) -> AgentState:
        if state.rule_verdict is None or state.llm_result is None:
            raise StageFailure(
                "verify", "rule_verdict and llm_result are required for verification"
            )
        state.verification = self.verifier.verify(state.rule_verdict, state.llm_result)
        return state

    def _final_verdict(self, state: AgentState) -> AgentState:
        if state.verification is None:
            raise StageFailure("act", "verification required to produce a final verdict")
        verification = state.verification
        state.final_verdict = {
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
        return state

    def _act(self, state: AgentState) -> AgentState:
        """Produce the final verdict (the actionable output of the workflow)."""
        return self._final_verdict(state)

    def _log(self, state: AgentState) -> AgentState:
        audit_ref = (state.final_verdict or {}).get("audit_ref") or _new_audit_ref()
        event = AuditEvent(
            audit_ref=audit_ref,
            permit_id=state.permit_id,
            timestamp=_utc_now(),
            pipeline=self.PIPELINE_STAGES,
            stages=self._stages_snapshot(state),
            sequence=[
                {"step": s, "status": "done", "audit_ref": audit_ref}
                for s in self.PIPELINE_STAGES
            ],
        )
        confirmed_ref = self.audit_logger.log(event)
        if confirmed_ref != audit_ref:
            raise StageFailure(
                "log",
                f"AuditLogger returned mismatched audit_ref: "
                f"{confirmed_ref!r} != {audit_ref!r}",
            )
        state.audit_refs.append(audit_ref)
        state._audit_event = event
        return state

    def _stages_snapshot(self, state: AgentState) -> Dict[str, Any]:
        """Build the audit ``stages`` dict from current AgentState."""
        return {
            "task_request": state._task_request,
            "perceived": state._task_request,
            "understood": state.structured_ptw,
            "structured_pid": state.structured_pid,
            "graph_facts": state.graph_facts,
            "rule_verdict": state.rule_verdict,
            "retrieved": state.rag_context,
            "llm_reasoning": state.llm_result,
            "reasoning_provider": state.reasoning_provider,
            "verification": state.verification,
            "final_verdict": state.final_verdict,
            "task_type": state.task_type,
            "execution_trace": state.execution_trace,
        }

    # ------------------------------------------------------------------
    # Execution trace helpers
    # ------------------------------------------------------------------

    def _begin_stage(self, state: AgentState, stage: str) -> None:
        state.current_stage = stage
        state.execution_trace.append(
            ExecutionTraceEntry(stage=stage, status="running", timestamp=_utc_now())
        )

    def _complete_stage(self, state: AgentState, stage: str) -> None:
        for entry in state.execution_trace:
            if entry["stage"] == stage:
                entry["status"] = "completed"
                entry["timestamp"] = _utc_now()
        state.current_stage = None

    def _fail_stage(self, state: AgentState, stage: str) -> None:
        for entry in state.execution_trace:
            if entry["stage"] == stage:
                entry["status"] = "failed"
                entry["timestamp"] = _utc_now()
        state.current_stage = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, fixture: Dict[str, Any] | str | Path) -> OrchestratorResult:
        """Run the full controlled workflow against a fixture or fixture path.

        Returns:
            An ``OrchestratorResult``.  On a stage failure, the result still
            carries a valid ``AgentState``-derived structure via ``audit`` and
            the error is captured in ``state.errors``.  A failed workflow
            never fabricates a PASS.

        Raises:
            OrchestratorError: if the fixture cannot be parsed at all.
        """
        if isinstance(fixture, (str, Path)):
            try:
                fixture = load_fixture(fixture)
            except (OSError, json.JSONDecodeError) as exc:
                raise OrchestratorError(f"Could not load fixture: {exc}") from exc

        state = self._init_state(fixture)

        # Stage dispatch table: PERCEIVE -> UNDERSTAND -> PLAN -> RETRIEVE
        # -> USE TOOL -> REASON -> VERIFY -> ACT -> LOG.
        stages = [
            ("perceive", self._perceive),
            ("understand", self._understand),
            ("plan", self._plan),
            ("retrieve", self._retrieve),
            ("use_tool", self._use_tool),
            ("reason", self._reason),
            ("verify", self._verify),
            ("act", self._act),
            ("log", self._log),
        ]

        for stage_name, stage_fn in stages:
            self._begin_stage(state, stage_name)
            try:
                if stage_name == "plan":
                    stage_fn(state, state.task_type)
                elif stage_name in ("use_tool", "reason", "verify", "act", "log"):
                    stage_fn(state)
                else:
                    stage_fn(state, fixture)
                self._complete_stage(state, stage_name)
            except StageFailure as exc:
                self._fail_stage(state, exc.stage)
                state.errors.append(
                    StageError(
                        stage=exc.stage,
                        error_type="StageFailure",
                        message=exc.message,
                        timestamp=_utc_now(),
                    )
                )
                break
            except Exception as exc:  # noqa: BLE001 - record and stop safely
                self._fail_stage(state, stage_name)
                state.errors.append(
                    StageError(
                        stage=stage_name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        timestamp=_utc_now(),
                    )
                )
                break

        # A failed workflow must never fabricate a PASS.
        # If we failed before/at verification, leave final_verdict unset.

        return self._compose_result(state)

    def _compose_result(self, state: AgentState) -> OrchestratorResult:
        """Build the public OrchestratorResult from the final AgentState.

        On success, the result mirrors the previous Milestone 1 shape.  On
        failure, the ``final_verdict``/``verification``/``llm_reasoning`` may
        be ``None`` and the error detail is exposed via the audit ``stages``
        and a top-level ``errors`` key.
        """
        result = OrchestratorResult(
            permit_id=state.permit_id,
            plan=state.plan or _empty_plan(),
            llm_reasoning=state.llm_result,
            verification=state.verification,
            final_verdict=state.final_verdict,
            audit=state._audit_event
            or AuditEvent(
                audit_ref=(state.audit_refs[-1] if state.audit_refs else _new_audit_ref()),
                permit_id=state.permit_id,
                timestamp=_utc_now(),
                pipeline=self.PIPELINE_STAGES,
                stages=self._stages_snapshot(state) if state.final_verdict else {},
                sequence=[
                    {"step": s, "status": "done", "audit_ref": ""}
                    for s in self.PIPELINE_STAGES
                ],
            ),
        )
        # Surface error state on the result for callers/tests.
        result["errors"] = [dict(e) for e in state.errors]
        result["execution_trace"] = list(state.execution_trace)
        result["failed_stage"] = state.failed_stage
        return result


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _empty_plan() -> List[PlanStep]:
    return [PlanStep(step=s, tool=None, model_category=None, status="planned")
            for s in AgentOrchestrator.PIPELINE_STAGES]


def _reasoning_provider_name(engine: object) -> str:
    """Best-effort identifier of the reasoning backend for the audit trace."""
    provider = getattr(engine, "provider", None)
    name = getattr(provider, "name", None)
    if name:
        return str(name)
    engine_name = getattr(engine, "name", None)
    if engine_name:
        return str(engine_name)
    return type(engine).__name__


def build_provider_orchestrator(
    config: Optional[OllamaConfig] = None,
    *,
    transport: Optional[object] = None,
) -> AgentOrchestrator:
    """Factory: an orchestrator whose REASON stage uses the real local model.

    Wires ``ProviderReasoningEngine`` backed by an Ollama-serving router so the
    full pipeline (Task -> ... -> REASON -> ... -> FinalVerdict) runs through a
    local open-weight LLM. There is NO cloud fallback: if the local endpoint is
    unreachable the reason stage fails explicitly and no verdict is produced.

    The default deterministic path (``AgentOrchestrator()``) is unchanged.

    Args:
        config: ``OllamaConfig``; loaded from environment/defaults if ``None``.
        transport: optional HTTP transport stub (testing only).

    Returns:
        An ``AgentOrchestrator`` using the provider-backed reasoning engine.
    """
    from ai_agent.router.model_router import build_local_model_router
    from ai_agent.reasoning.provider_reasoning_engine import ProviderReasoningEngine

    router = build_local_model_router(config=config, transport=transport)
    engine = ProviderReasoningEngine(router=router)
    return AgentOrchestrator(reasoning_engine=engine, router=router)


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
