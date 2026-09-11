from services.rule_result import RuleResult
from services.llm_result import LLMResult


def verify_results(
    rule_result: RuleResult,
    llm_result: LLMResult
) -> dict:

    # Check whether both results agree
    agreement = rule_result.result == llm_result.result

    # If they agree
    if agreement:

        final_decision = rule_result.result

        requires_human_review = False

        explanation = (
            "Rule engine and LLM produced the same result."
        )

    # If they disagree
    else:

        final_decision = "HUMAN_REVIEW"

        requires_human_review = True

        explanation = (
            "Rule engine and LLM produced different results. "
            "Human Safety Officer review is required."
        )

    return {
        "permit_id": rule_result.permit_id,
        "rule_result": rule_result.result,
        "llm_result": llm_result.result,
        "agreement": agreement,
        "final_decision": final_decision,
        "explanation": explanation,
        "requires_human_review": requires_human_review
    }