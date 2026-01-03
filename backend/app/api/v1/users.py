import os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserPreferences, UserProfile, UserUpdate, PasswordChange
from app.core.security import verify_password, get_password_hash
from app.config import settings
from app.utils.helpers import save_upload_file

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
    """
    return current_user

@router.put("/me", response_model=UserProfile)
async def update_me(
    obj_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile (nickname, email, preferences)
    """
    if obj_in.nickname is not None:
        current_user.nickname = obj_in.nickname
    
    if obj_in.email is not None and obj_in.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).filter(User.email == obj_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = obj_in.email

    if obj_in.depth_preference is not None:
        current_user.depth_preference = obj_in.depth_preference
    if obj_in.curiosity_preference is not None:
        current_user.curiosity_preference = obj_in.curiosity_preference
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/me/avatar", response_model=UserProfile)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's avatar
    """
    # Create upload directory if not exists
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    file_extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image format")
        
    filename = f"{current_user.id}_{uuid4().hex}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    await save_upload_file(
        file,
        file_path,
        max_size=settings.MAX_UPLOAD_SIZE,
        allowed_extensions=allowed_extensions,
        allowed_content_types=allowed_types,
    )
    
    # Update user avatar_url
    # In a real app, this should be a full URL
    current_user.avatar_url = f"/uploads/avatars/{filename}"
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/me/password")
async def change_password(
    obj_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password
    """
    if not verify_password(obj_in.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    current_user.hashed_password = get_password_hash(obj_in.new_password)
    
    db.add(current_user)
    await db.commit()
    return {"detail": "Password updated successfully"}

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
    
    return current_user
