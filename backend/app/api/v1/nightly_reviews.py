from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.nightly_review import NightlyReviewResponse
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
    return review
