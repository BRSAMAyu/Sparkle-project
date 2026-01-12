"""
Curiosity Capsules API
"""
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.curiosity_capsule_service import curiosity_capsule_service
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class CuriosityCapsuleSchema(BaseModel):
    id: UUID
    title: str
    content: str
    is_read: bool
    created_at: datetime
    related_subject: str | None = None

    class Config:
        from_attributes = True

@router.get("/today", response_model=List[CuriosityCapsuleSchema])
async def get_today_capsules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available curiosity capsules for today.
    If none exist, might trigger generation (optional).
    """
    capsules = await curiosity_capsule_service.get_today_capsules(current_user.id, db)
    
    if not capsules:
        # Auto-generate one for demo purposes if list is empty
        new_capsule = await curiosity_capsule_service.generate_daily_capsule(current_user.id, db)
        if new_capsule:
            capsules = [new_capsule]
            
    return capsules

@router.post("/{id}/read")
async def mark_capsule_read(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a capsule as read.
    """
    await curiosity_capsule_service.mark_as_read(id, db)
    return {"success": True}

@router.post("/generate", response_model=CuriosityCapsuleSchema)
async def generate_capsule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger capsule generation (for testing/demo).
    """
    capsule = await curiosity_capsule_service.generate_daily_capsule(current_user.id, db)
    if not capsule:
        raise HTTPException(status_code=400, detail="Could not generate capsule")
    return capsule
