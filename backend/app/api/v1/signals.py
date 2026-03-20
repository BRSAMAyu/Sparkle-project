"""
Signals Feedback API

Endpoints for collecting user feedback on candidate actions.
Enables learning loop for signal threshold calibration.
"""
import uuid
from datetime import timezone, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.candidate_action_feedback import CandidateActionFeedback
from app.models.user import User

router = APIRouter(prefix="/signals", tags=["signals"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FeedbackRequest(BaseModel):
    """Request body for candidate action feedback"""
    candidate_id: str = Field(..., description="Candidate action ID")
    action_type: str = Field(..., description="Action type identifier")
    feedback_type: str = Field(..., description="Feedback type: impression, accept, ignore, dismiss")
    executed: bool = Field(default=False, description="Was the action executed")
    completion_result: dict[str, Any] | None = Field(
        default=None,
        description="Result of executed action (if any)"
    )
    context_snapshot: dict[str, Any] | None = Field(
        default=None,
        description="ContextEnvelope at time of feedback"
    )


class FeedbackResponse(BaseModel):
    """Response for feedback submission"""
    ok: bool
    feedback_id: str
    message: str


@router.post("/feedback", response_model=FeedbackResponse, summary="记录候选动作反馈")
async def record_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Record user feedback on candidate action.

    Feedback types:
    - impression: User saw the candidate action
    - accept: User clicked on the candidate action
    - ignore: User saw but didn't interact (implicit)
    - dismiss: User explicitly dismissed the candidate

    Used by daily learning job to calculate:
    - CTR (Click-Through Rate): accept / impression
    - Completion Rate: executed / accept
    - Confidence Calibration: expected vs actual CTR

    Args:
        request: Feedback data
        current_user: Authenticated user
        db: Database session

    Returns:
        FeedbackResponse with ok status and feedback ID
    """
    try:
        # Validate feedback_type
        valid_feedback_types = ["impression", "accept", "ignore", "dismiss"]
        if request.feedback_type not in valid_feedback_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback_type. Must be one of: {valid_feedback_types}"
            )

        # Validate action_type
        if not request.action_type or len(request.action_type) > 32:
            raise HTTPException(
                status_code=400,
                detail="Invalid action_type. Must be non-empty and at most 32 characters."
            )

        # Create feedback record
        feedback = CandidateActionFeedback(
            id=uuid.uuid4(),
            user_id=current_user.id,
            candidate_id=request.candidate_id,
            action_type=request.action_type,
            feedback_type=request.feedback_type,
            executed=request.executed,
            completion_result=request.completion_result,
            context_snapshot=request.context_snapshot or {},
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        logger.info(
            f"Feedback recorded: user={current_user.id}, candidate={request.candidate_id}, "
            f"action={request.action_type}, feedback={request.feedback_type}, executed={request.executed}"
        )

        return FeedbackResponse(
            ok=True,
            feedback_id=str(feedback.id),
            message="Feedback recorded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to record feedback")
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


@router.get("/feedback/stats", summary="获取反馈统计")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get feedback statistics for current user.

    Returns:
    - Total feedback count
    - Breakdown by feedback type
    - Breakdown by action type
    - CTR (Click-Through Rate)
    - Completion rate

    This endpoint is useful for user-facing stats dashboards.
    """
    from sqlalchemy import func, select

    try:
        # Total count
        total_result = await db.execute(
            select(func.count(CandidateActionFeedback.id))
            .where(CandidateActionFeedback.user_id == current_user.id)
            .where(CandidateActionFeedback.deleted_at.is_(None))
        )
        total_count = total_result.scalar() or 0

        # Breakdown by feedback_type
        feedback_type_result = await db.execute(
            select(
                CandidateActionFeedback.feedback_type,
                func.count(CandidateActionFeedback.id).label('count')
            )
            .where(CandidateActionFeedback.user_id == current_user.id)
            .where(CandidateActionFeedback.deleted_at.is_(None))
            .group_by(CandidateActionFeedback.feedback_type)
        )
        feedback_type_breakdown = {
            row.feedback_type: row.count
            for row in feedback_type_result
        }

        # Breakdown by action_type
        action_type_result = await db.execute(
            select(
                CandidateActionFeedback.action_type,
                func.count(CandidateActionFeedback.id).label('count')
            )
            .where(CandidateActionFeedback.user_id == current_user.id)
            .where(CandidateActionFeedback.deleted_at.is_(None))
            .group_by(CandidateActionFeedback.action_type)
        )
        action_type_breakdown = {
            row.action_type: row.count
            for row in action_type_result
        }

        # CTR calculation
        impressions = feedback_type_breakdown.get('impression', 0)
        accepts = feedback_type_breakdown.get('accept', 0)
        ignores = feedback_type_breakdown.get('ignore', 0)
        dismisses = feedback_type_breakdown.get('dismiss', 0)
        ctr = (accepts / impressions * 100) if impressions > 0 else 0

        # Completion rate calculation
        executed_result = await db.execute(
            select(func.count(CandidateActionFeedback.id))
            .where(CandidateActionFeedback.user_id == current_user.id)
            .where(CandidateActionFeedback.feedback_type == 'accept')
            .where(CandidateActionFeedback.executed)
            .where(CandidateActionFeedback.deleted_at.is_(None))
        )
        executed_count = executed_result.scalar() or 0
        completion_rate = (executed_count / accepts * 100) if accepts > 0 else 0

        return {
            "ok": True,
            "total_count": total_count,
            "feedback_type_breakdown": feedback_type_breakdown,
            "action_type_breakdown": action_type_breakdown,
            "impression_count": impressions,
            "ctr_percent": round(ctr, 2),
            "completion_rate_percent": round(completion_rate, 2),
        }

    except Exception as e:
        logger.exception("Failed to get feedback stats")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
