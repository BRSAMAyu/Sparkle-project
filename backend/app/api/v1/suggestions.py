from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any
from app.services.suggestion_service import suggestion_service

router = APIRouter(tags=["Suggestions"])

@router.get("/suggestions", response_model=List[Dict[str, Any]])
async def get_suggestions(
    q: str = Query(..., min_length=1, description="Partial user input"),
    user_id: str = Query(..., description="User ID for context")
):
    """
    Get real-time intent predictions/suggestions while typing.
    Vision Item 3.
    """
    suggestions = await suggestion_service.predict_intent(q, user_id)
    return suggestions
