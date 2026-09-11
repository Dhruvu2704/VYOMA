from fastapi import APIRouter

from services.rule_result import RuleResult


router = APIRouter(
    prefix="/api/rule-results",
    tags=["Rule Results"]
)


@router.post("/")
def receive_rule_result(rule_result: RuleResult):

    return {
        "message": "Rule result received successfully",
        "rule_result": rule_result
    }