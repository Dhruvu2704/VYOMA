from fastapi import APIRouter

from services.rule_result import RuleResult
from services.llm_result import LLMResult
from services.verifier import verify_results
from services.final_verdict import FinalVerdict


router = APIRouter(
    prefix="/api/final-verdict",
    tags=["Final Verdict"]
)


@router.post("/", response_model=FinalVerdict)
def create_final_verdict(
    rule_result: RuleResult,
    llm_result: LLMResult
):

    # Verify Rule Engine result against LLM result
    result = verify_results(
        rule_result,
        llm_result
    )

    # Convert result into FinalVerdict
    verdict = FinalVerdict(**result)

    return verdict