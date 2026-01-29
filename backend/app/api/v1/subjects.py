"""
Subjects API Endpoints
学科标准接口 (v2.1)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.subject_service import SubjectService

router = APIRouter()
subject_service = SubjectService()

class SubjectResponse(BaseModel):
    id: int
    name: str
    category: str

    class Config:
        from_attributes = True

class SubjectListResponse(BaseModel):
    success: bool
    data: list[SubjectResponse]

@router.get("", response_model=SubjectListResponse)
async def get_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有启用的标准学科（供前端下拉选择）
    """
    subjects = await subject_service.get_all_subjects(db)
    return {
        "success": True,
        "data": subjects
    }
