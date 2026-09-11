from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Permit, Verdict
from services.rule_result import RuleResult
from services.llm_result import LLMResult
from services.verifier import verify_results
from services.final_verdict import FinalVerdict
from services.auth import get_current_user
from services.permissions import require_tool_permission
from audit.logger import AuditLogger


router = APIRouter(
    prefix="/api/final-verdict",
    tags=["Final Verdict"]
)


@router.post("/", response_model=FinalVerdict)
def create_final_verdict(
    rule_result: RuleResult,
    llm_result: LLMResult,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "run_safety_analysis"
    )

    if rule_result.permit_id != llm_result.permit_id:
        raise HTTPException(
            status_code=400,
            detail="Rule result and LLM result must belong to the same permit"
        )

    permit = db.query(Permit).filter(
        Permit.permit_id == rule_result.permit_id
    ).first()

    if not permit:
        raise HTTPException(
            status_code=404,
            detail="Permit not found"
        )

    result = verify_results(
        rule_result,
        llm_result
    )

    verdict = FinalVerdict(**result)

    verdict_record = Verdict(
        permit_id=permit.permit_id,
        final_verdict=verdict.final_decision
    )

    db.add(verdict_record)
    db.commit()
    db.refresh(verdict_record)

    audit_logger = AuditLogger()

    audit_event = audit_logger.create_event(
        permit_id=permit.permit_id,
        pipeline="FINAL_VERDICT",
        stages=[
            "RULE_RESULT_RECEIVED",
            "LLM_RESULT_RECEIVED",
            "VERDICT_GENERATED"
        ],
        sequence=verdict_record.id
    )

    audit_logger.save_event(
        db,
        audit_event
    )

    return verdict


@router.get("/{permit_id}")
def get_final_verdict(
    permit_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_tool_permission(
        current_user,
        "run_safety_analysis"
    )

    permit = db.query(Permit).filter(
        Permit.permit_id == permit_id
    ).first()

    if not permit:
        raise HTTPException(
            status_code=404,
            detail="Permit not found"
        )

    verdict = db.query(Verdict).filter(
        Verdict.permit_id == permit.permit_id
    ).order_by(
        Verdict.id.desc()
    ).first()

    if not verdict:
        raise HTTPException(
            status_code=404,
            detail="Final verdict not found"
        )

    return {
        "permit_id": verdict.permit_id,
        "final_verdict": verdict.final_verdict,
        "created_at": verdict.created_at
    }