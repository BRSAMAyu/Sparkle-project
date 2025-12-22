"""
Cognitive Prism API
认知棱镜相关 API
"""
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.cognitive import BehaviorPattern
from app.schemas.cognitive import CognitiveFragmentCreate, CognitiveFragmentResponse, BehaviorPatternResponse
from app.services.cognitive_service import CognitiveService

router = APIRouter()

@router.post("/fragments", response_model=CognitiveFragmentResponse)
async def create_fragment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    fragment_in: CognitiveFragmentCreate,
    background_tasks: BackgroundTasks
):
    """
    创建一个新的认知碎片 (闪念/拦截)
    """
    service = CognitiveService(db)
    # Note: For MVP, passing background_tasks to service. 
    # Be aware of session lifecycle issues in prod. 
    # Here we might await it directly in service if background task fails due to closed session.
    # In `CognitiveService.create_fragment`, we logic handles execution.
    # To be safe and simple for now, we can await it inside the service (latency < 2s usually)
    # or ensure the service implementation handles it correctly.
    # Given the implementation I wrote, it tries to use the passed session in BG task which is risky.
    # I will modify the service call to NOT use background_tasks for the DB part, 
    # or I accept that it might be synchronous for now to avoid session closed errors.
    
    # Let's make it synchronous for reliability in this prototype phase
    fragment = await service.create_fragment(
        user_id=current_user.id,
        data=fragment_in,
        background_tasks=None # Force sync execution
    )
    return fragment

@router.get("/fragments", response_model=List[CognitiveFragmentResponse])
async def get_fragments(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0,
):
    """
    获取用户的认知碎片列表
    """
    service = CognitiveService(db)
    fragments = await service.get_fragments(
        user_id=current_user.id,
        limit=limit,
        offset=skip
    )
    return fragments

@router.post("/analysis/trigger", response_model=List[BehaviorPatternResponse])
async def trigger_analysis(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动触发行为定式分析 (测试用)
    """
    service = CognitiveService(db)
    patterns = await service.generate_weekly_report(user_id=current_user.id)
    return patterns

@router.get("/patterns", response_model=List[BehaviorPatternResponse])
async def get_patterns(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的行为定式列表
    """
    # For now, just return all non-archived patterns or sort by recent
    stmt = (
        select(BehaviorPattern)
        .where(BehaviorPattern.user_id == current_user.id)
        .order_by(BehaviorPattern.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
