from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.nightly_review import NightlyReviewResponse, NightlyReviewFeedbackRequest
from app.services.nightly_review_service import NightlyReviewService

router = APIRouter(prefix="/reviews/nightly", tags=["nightly_reviews"])


@router.get("/latest", response_model=NightlyReviewResponse)
async def get_latest_review(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NightlyReviewService(db)
    review = await service.get_latest(current_user.id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    widget_payload = {
        "type": "nightly_review",
        "data": {
            "review_id": str(review.id),
            "review_date": review.review_date.isoformat(),
            "summary": review.summary_text,
            "todo_items": review.todo_items or [],
            "evidence_refs": review.evidence_refs or [],
        },
    }
    return NightlyReviewResponse(
        id=review.id,
        user_id=review.user_id,
        review_date=review.review_date,
        summary_text=review.summary_text,
        todo_items=review.todo_items,
        evidence_refs=review.evidence_refs,
        widget_payload=widget_payload,
        model_version=review.model_version,
        status=review.status,
        reviewed_at=review.reviewed_at,
        created_at=review.created_at,
    )


@router.post("/{review_id}/feedback", response_model=NightlyReviewResponse)
async def submit_review_feedback(
    review_id: UUID,
    data: NightlyReviewFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.action != "reviewed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action")

    service = NightlyReviewService(db)
    review = await service.mark_reviewed(review_id, current_user.id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    widget_payload = {
        "type": "nightly_review",
        "data": {
            "review_id": str(review.id),
            "review_date": review.review_date.isoformat(),
            "summary": review.summary_text,
            "todo_items": review.todo_items or [],
            "evidence_refs": review.evidence_refs or [],
        },
    }
    return NightlyReviewResponse(
        id=review.id,
        user_id=review.user_id,
        review_date=review.review_date,
        summary_text=review.summary_text,
        todo_items=review.todo_items,
        evidence_refs=review.evidence_refs,
        widget_payload=widget_payload,
        model_version=review.model_version,
        status=review.status,
        reviewed_at=review.reviewed_at,
        created_at=review.created_at,
    )
