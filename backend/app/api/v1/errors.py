"""
Error Records API Endpoints
"""
from typing import Dict, Any # Moved to top
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.error_record import ErrorRecord
from app.models.subject import Subject
from app.schemas.error import ErrorRecordCreate, ErrorRecordResponse

router = APIRouter()

@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_error_record(
    record_in: ErrorRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    保存错题记录 (v2.1)
    """
    # 验证 subject_id
    subject = await db.get(Subject, record_in.subject_id)
    if not subject:
        raise HTTPException(
            status_code=400,
            detail=f"Subject with id {record_in.subject_id} not found"
        )
    
    # 创建记录
    db_record = ErrorRecord(
        user_id=current_user.id,
        subject_id=subject.id,
        subject=subject.name, # 保留冗余字段用于快速显示或历史兼容
        topic=record_in.topic,
        error_type=record_in.error_type,
        description=record_in.description,
        ai_analysis=record_in.ai_analysis,
        image_urls=record_in.image_urls
    )
    
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    
    return {
        "success": True,
        "data": ErrorRecordResponse.model_validate(db_record)
    }
