from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from loguru import logger

from app.api.deps import get_current_user_id
from app.core.rate_limiting import limiter
from app.services.suggestion_service import suggestion_service

router = APIRouter(tags=["Suggestions"])

@router.get("/suggestions", response_model=list[dict[str, Any]])
@limiter.limit("60/minute")
async def get_suggestions(
    request: Request,
    q: str = Query(..., min_length=2, max_length=50, description="Partial user input"),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get real-time intent predictions/suggestions while typing.
    Vision Item 3.

    Requires authentication via JWT token.
    """
    logger.debug(f"Suggestions request for user {current_user_id}: q='{q}'")
    suggestions = await suggestion_service.predict_intent(q, current_user_id)
    return suggestions
