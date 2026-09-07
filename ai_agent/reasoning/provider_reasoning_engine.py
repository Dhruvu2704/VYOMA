"""Provider-backed reasoning engine for Role 1.

Consumes the full structured context of a task (``StructuredPTW``,
``StructuredPID``, ``GraphFacts``, ``RuleVerdict``, retrieved knowledge, and
active-permit information) and produces the existing ``LLMReasoningResult``
contract.

Routing: the engine uses a ``ModelRouter`` to select the provider serving the
``reasoning`` capability, then calls ``provider.generate()`` through the clean
provider interface — the reasoning layer never embeds model-runtime logic
(e.g. Ollama) itself.

Safety boundary: the LLM/provider layer can never silently override the
deterministic safety-rule-result grounding. The PASS/FLAGGED outcome is
derived strictly from the structured evidence via ``_derive_evidence_verdict``
(the same helper the day 1 deterministic engine uses). The provider supplies a
reasoned reply and its metadata, but a provider failure (raise or malformed
response) is surfaced as ``ReasoningError``, never converted into a verdict.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from shared.contracts import (
    Confidence,
    GraphFacts,
    LLMReasoningResult,
    RuleVerdict,
    StructuredPTW,
    LlmResult,
)

from ai_agent.router.model_provider import ModelProvider, ProviderError
from ai_agent.router.model_router import ModelRouter, ModelRouterError, build_router
from ai_agent.reasoning.reasoning_engine import (
    ReasoningError,
    ReasoningEngine,
    RetrievedKnowledge,
    _confidence_from_confidence_level,
    _derive_evidence_verdict,
)


class ProviderReasoningEngine(ReasoningEngine):
    """Reasoning engine that routes the ``reasoning`` capability through a
    ModelRouter/provider abstraction."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
    ) -> None:
        self.router = router or build_router()
        self._provider: Optional[ModelProvider] = None
        self._requested_capability = "reasoning"

    @property
    def provider(self) -> Optional[ModelProvider]:
        """The currently selected provider (None until first ``reason``)."""
        return self._provider

    def select_provider(self) -> ModelProvider:
        """Resolve and cache the provider for the reasoning capability."""
        try:
            provider = self.router.select_provider(self._requested_capability)
        except ModelRouterError as exc:
            raise ReasoningError(str(exc)) from exc
        self._provider = provider
        return provider

    def reason(
        self,
        ptw: StructuredPTW,
        graph_facts: GraphFacts,
        rule_verdict: RuleVerdict,
        retrieved: Optional[RetrievedKnowledge] = None,
        structured_pid: Optional[Dict[str, Any]] = None,
        active_permits: Optional[List[Dict[str, Any]]] = None,
        task: Optional[Dict[str, Any]] = None,
    ) -> LLMReasoningResult:
        permit_id = rule_verdict.get("permit_id") or ptw.get("permit_id")

        if not graph_facts:
            raise ValueError("graph_facts are required for reasoning")
        if not rule_verdict:
            raise ValueError("rule_verdict is required for reasoning")

        provider = self.select_provider()

        prompt = _build_reasoning_prompt(
            ptw=ptw,
            graph_facts=graph_facts,
            rule_verdict=rule_verdict,
            structured_pid=structured_pid,
            active_permits=active_permits,
            task=task,
            retrieved=retrieved,
        )

        # Call through the clean provider interface. Provider/model failures
        # and malformed responses are surfaced, never turned into a verdict.
        try:
            response = provider.generate(
                prompt,
                capability=self._requested_capability,
            )
        except ProviderError as exc:
            raise ReasoningError(
                f"Reasoning provider {provider.name!r} failed: {exc}"
            ) from exc

        if response is None or not response.ok or not response.content:
            raise ReasoningError(
                f"Reasoning provider {provider.name!r} returned a malformed "
                "or empty response; cannot produce a verdict."
            )

        # Ground the verdict strictly in the structured evidence — a provider
        # can never silently override the deterministic safety result.
        result, explanation = _derive_evidence_verdict(graph_facts, rule_verdict)

        # Append the provider's reasoned reply as non-authoritative context.
        if response.content:
            explanation = f"{explanation} Model note: {response.content.strip()}"

        confidence: Confidence = _confidence_from_confidence_level(
            rule_verdict.get("confidence", "MEDIUM")
        )

        return LLMReasoningResult(
            permit_id=permit_id,
            llm_result=result,
            explanation=explanation,
            confidence=confidence,
        )


def _build_reasoning_prompt(
    *,
    ptw: StructuredPTW,
    graph_facts: GraphFacts,
    rule_verdict: RuleVerdict,
    structured_pid: Optional[Dict[str, Any]] = None,
    active_permits: Optional[List[Dict[str, Any]]] = None,
    task: Optional[Dict[str, Any]] = None,
    retrieved: Optional[RetrievedKnowledge] = None,
) -> str:
    """Assemble a prompt from the structured context (all untrusted data)."""
    permit_id = rule_verdict.get("permit_id") or ptw.get("permit_id")
    lines: List[str] = [
        "Industrial-safety reasoning request.",
        f"permit_id: {permit_id}",
        f"work_type: {ptw.get('work_type')}",
        f"scope: {ptw.get('scope')}",
        f"equipment_tags: {ptw.get('equipment_tags')}",
        f"rule_result: {rule_verdict.get('rule_result')}",
        f"rules_triggered: {rule_verdict.get('rules_triggered')}",
        f"unresolved_tags: {graph_facts.get('unresolved_tags')}",
        f"active_isolations: {graph_facts.get('active_isolations')}",
    ]
    if structured_pid is not None:
        lines.append(
            "structured_pid: " + json.dumps(structured_pid, sort_keys=True)
        )
    if active_permits is not None:
        lines.append(
            "active_permits: " + json.dumps(active_permits, sort_keys=True)
        )
    if task is not None:
        lines.append("task: " + json.dumps(task, sort_keys=True))
    if retrieved:
        lines.append("retrieved: " + json.dumps(retrieved, sort_keys=True))
    lines.append(
        "Ground your conclusion strictly in the supplied evidence. "
        "Do not invent plant topology or safety facts."
    )
    return "\n".join(lines)
