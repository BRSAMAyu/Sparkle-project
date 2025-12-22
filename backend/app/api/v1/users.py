from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserPreferences, UserProfile

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
    """
    # current_user object already contains preferences
    return UserProfile.model_validate(current_user)

@router.put("/me/preferences", response_model=UserProfile)
async def update_my_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's depth and curiosity preferences
    """
    current_user.depth_preference = preferences.depth_preference
    current_user.curiosity_preference = preferences.curiosity_preference
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return UserProfile.model_validate(current_user)
