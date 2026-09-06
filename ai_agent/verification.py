"""Verification of the rule verdict against the LLM reasoning result.

Decision matrix:

    rule   +   llm     ->  agreement  ->  final_decision          human
    PASS      PASS         AGREE         PASS                       False
    FLAGGED   FLAGGED      AGREE         FLAGGED_FOR_REVIEW         True
    PASS      FLAGGED      DISAGREE      REVIEW_REQUIRED            True
    FLAGGED   PASS         DISAGREE      REVIEW_REQUIRED            True

Absolute safety rule: a disagreement can NEVER automatically approve a
permit -> if agreement == DISAGREE, requires_human_review MUST be True.
"""

from __future__ import annotations

from shared.contracts import (
    Agreement,
    FinalDecision,
    LLMReasoningResult,
    RuleVerdict,
    VerificationResult,
    RuleResult,
)


class VerificationError(Exception):
    """Raised when verification cannot be performed from the given inputs."""


class VerificationEngine:
    """Compares the rule verdict against the reasoning result."""

    def verify(
        self,
        rule_verdict: RuleVerdict,
        llm_reasoning: LLMReasoningResult,
    ) -> VerificationResult:
        rule_result: RuleResult = rule_verdict.get("rule_result")
        llm_result: RuleResult = llm_reasoning.get("llm_result")
        permit_id = rule_verdict.get("permit_id") or llm_reasoning.get("permit_id")

        if rule_result not in ("PASS", "FLAGGED"):
            raise VerificationError(f"Invalid rule_result: {rule_result!r}")
        if llm_result not in ("PASS", "FLAGGED"):
            raise VerificationError(f"Invalid llm_result: {llm_result!r}")

        if rule_result == "PASS" and llm_result == "PASS":
            agreement: Agreement = "AGREE"
            final_decision: FinalDecision = "PASS"
            human_review = False
            explanation = (
                "Rule engine and reasoning engine both PASS; permit approved."
            )
        elif rule_result == "FLAGGED" and llm_result == "FLAGGED":
            agreement = "AGREE"
            final_decision = "FLAGGED_FOR_REVIEW"
            human_review = True
            explanation = (
                "Rule engine and reasoning engine both FLAG the permit; "
                "referring for review."
            )
        elif rule_result == "PASS" and llm_result == "FLAGGED":
            agreement = "DISAGREE"
            final_decision = "REVIEW_REQUIRED"
            human_review = True
            explanation = (
                "Rule engine PASSES but reasoning engine FLAGS; divergence "
                "requires human review."
            )
        else:  # FLAGGED + PASS
            agreement = "DISAGREE"
            final_decision = "REVIEW_REQUIRED"
            human_review = True
            explanation = (
                "Rule engine FLAGS but reasoning engine PASSES; divergence "
                "requires human review and cannot auto-approve."
            )

        # Absolute safety rule enforced structurally, and guarded again here.
        if agreement == "DISAGREE" and not human_review:
            raise VerificationError(
                "Invariant violated: disagreement must require human review"
            )

        return VerificationResult(
            permit_id=permit_id,
            rule_result=rule_result,
            llm_result=llm_result,
            agreement=agreement,
            final_decision=final_decision,
            requires_human_review=human_review,
            explanation=explanation,
        )
