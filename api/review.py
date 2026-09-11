from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Permit, Verdict, ReviewDecision
from services.auth import get_current_user, require_role
from audit.logger import AuditLogger


router = APIRouter(
    prefix="/api/review",
    tags=["Human Review"]
)


class ReviewRequest(BaseModel):
    decision: str
    comment: str | None = None


@router.post("/{permit_id}")
def submit_review(
    permit_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_role(
        current_user,
        ["SAFETY_OFFICER", "ADMIN"]
    )

    permit = db.query(Permit).filter(
        Permit.permit_id == permit_id
    ).first()

    if not permit:
        raise HTTPException(
            status_code=404,
            detail="Permit not found"
        )

    if review.decision not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVE or REJECT"
        )

    latest_verdict = db.query(Verdict).filter(
        Verdict.permit_id == permit.permit_id
    ).order_by(
        Verdict.id.desc()
    ).first()

    if not latest_verdict:
        raise HTTPException(
            status_code=404,
            detail="Final verdict not found"
        )

    if latest_verdict.final_verdict != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=400,
            detail="Human review is not required for this permit"
        )

    review_decision = ReviewDecision(
        permit_id=permit.permit_id,
        reviewer_id=current_user["user_id"],
        decision=review.decision,
        comment=review.comment
    )

    db.add(review_decision)
    db.commit()
    db.refresh(review_decision)

    latest_verdict.final_verdict = review.decision
    db.commit()
    db.refresh(latest_verdict)

    audit_logger = AuditLogger()

    audit_event = audit_logger.create_event(
        permit_id=permit.permit_id,
        pipeline="HUMAN_REVIEW",
        stages=[
            "REVIEW_SUBMITTED",
            f"HUMAN_DECISION_{review.decision}"
        ],
        sequence=review_decision.id
    )

    audit_logger.save_event(
        db,
        audit_event
    )

    return {
        "permit_id": permit.permit_id,
        "decision": review_decision.decision,
        "comment": review_decision.comment,
        "reviewer_id": review_decision.reviewer_id,
        "timestamp": review_decision.timestamp,
        "final_verdict": latest_verdict.final_verdict,
        "message": "Human review submitted successfully"
    }


@router.get("/{permit_id}")
def get_review(
    permit_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    require_role(
        current_user,
        ["SAFETY_OFFICER", "ADMIN"]
    )

    permit = db.query(Permit).filter(
        Permit.permit_id == permit_id
    ).first()

    if not permit:
        raise HTTPException(
            status_code=404,
            detail="Permit not found"
        )

    review = db.query(ReviewDecision).filter(
        ReviewDecision.permit_id == permit.permit_id
    ).order_by(
        ReviewDecision.id.desc()
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Human review not found"
        )

    return {
        "permit_id": review.permit_id,
        "decision": review.decision,
        "comment": review.comment,
        "reviewer_id": review.reviewer_id,
        "timestamp": review.timestamp
    }