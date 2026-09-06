"""Model-agnostic reasoning engine for the Role 1 agent pipeline.

Milestone 1 uses a deterministic, fixture/mock reasoning implementation.

Design contract: the engine exposes a single entry point so that a local
open-weight LLM can later slot in *without* changing the orchestrator. The
orchestrator only ever depends on this interface and on shared contracts.

Security/grounding rules enforced here:

- The engine may reason ONLY from the supplied evidence: ``graph_facts``,
  ``rule_verdict``, and optionally retrieved knowledge. It never invents
  plant topology, equipment connections, isolation points, permit conflicts,
  or any other industrial fact.
- If the evidence contains unresolved tags or otherwise insufficient
  information to certify safety, the reasoning result must NOT be an
  unqualified PASS.
"""

from __future__ import annotations

from typing import List, Optional

from shared.contracts import (
    Confidence,
    GraphFacts,
    LLMReasoningResult,
    RuleVerdict,
    StructuredPTW,
    LlmResult,
)

# e.g. interface of a returned knowledge chunk (RAG placeholder output).
RetrievedKnowledge = List[dict]


class ReasoningEngine:
    """Reasoning interface.

    A future local open-weight LLM implementation will subclass or otherwise
    fulfil this same contract. The orchestrator must not care which backend
    produced the result.
    """

    def reason(
        self,
        ptw: StructuredPTW,
        graph_facts: GraphFacts,
        rule_verdict: RuleVerdict,
        retrieved: Optional[RetrievedKnowledge] = None,
    ) -> LLMReasoningResult:
        """Evaluate the supplied evidence and produce an LLMReasoningResult.

        Raises:
            ValueError: if required evidence keys are missing.
        """
        raise NotImplementedError


def _confidence_from_confidence_level(value: str) -> Confidence:
    upper = (value or "MEDIUM").upper()
    if upper in ("LOW", "MEDIUM", "HIGH"):
        return upper  # type: ignore[return-value]
    return "MEDIUM"


class DeterministicReasoningEngine(ReasoningEngine):
    """Deterministic, evidence-only reasoning implementation for Milestone 1.

    Logic (intentionally simple and explainable):

    * If any unresolved tags exist -> cannot certify safety -> FLAGGED.
    * If the rule verdict is FLAGGED for any other reason -> FLAGGED.
    * If active isolations are not confirmed -> FLAGGED.
    * Only when all tags are resolved, the rule verdict is PASS, and there
      are no unconfirmed isolations / overlaps -> PASS.

    All conclusions reference only the evidence actually present.
    """

    def reason(
        self,
        ptw: StructuredPTW,
        graph_facts: GraphFacts,
        rule_verdict: RuleVerdict,
        retrieved: Optional[RetrievedKnowledge] = None,
    ) -> LLMReasoningResult:
        permit_id = rule_verdict.get("permit_id") or ptw.get("permit_id")

        if not graph_facts:
            raise ValueError("graph_facts are required for reasoning")
        if not rule_verdict:
            raise ValueError("rule_verdict is required for reasoning")

        unresolved = graph_facts.get("unresolved_tags") or []
        active_isolations = graph_facts.get("active_isolations") or []
        rule_result = rule_verdict.get("rule_result")

        reasons: List[str] = []

        if unresolved:
            reasons.append(
                f"Unresolved tags prevent certification of safety: {unresolved}"
            )

        if active_isolations:
            reasons.append(
                f"Active isolation(s) not confirmed for safe work: {active_isolations}"
            )

        if rule_result == "FLAGGED":
            rules = rule_verdict.get("rules_triggered") or []
            reasons.append(
                "Deterministic safety rules flagged the permit "
                f"(rules: {rules}); {rule_verdict.get('explanation', '')}".strip()
            )

        # Evidence may be insufficient even if the rule verdict is PASS.
        evidence_complete = not unresolved and not active_isolations

        if reasons or not evidence_complete:
            result: LlmResult = "FLAGGED"
            explanation = (
                "Safety cannot be certified from the supplied evidence. "
                + " ".join(reasons)
            )
        else:
            result = "PASS"
            explanation = (
                "All supplied evidence is consistent and complete: tags "
                "resolved, no unconfirmed isolations, and rules PASS."
            )

        confidence: Confidence = _confidence_from_confidence_level(
            rule_verdict.get("confidence", "MEDIUM")
        )

        return LLMReasoningResult(
            permit_id=permit_id,
            llm_result=result,
            explanation=explanation,
            confidence=confidence,
        )
