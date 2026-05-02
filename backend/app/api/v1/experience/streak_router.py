"""Experience BFF endpoint for quality-weighted streaks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.streak_quality import StreakQualityService

router = APIRouter(prefix="/experience", tags=["experience"])


# route-tier: authed
@router.get("/streak-quality", response_model=dict[str, Any])
async def get_streak_quality(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return streak quality, weekly trend, and celebration evidence for the current user."""
    return await StreakQualityService(db).build_payload(current_user.id)
