"""J-05 ·「我卡住了」旗舰恢复旅程 —— /experience/stuck-journey 路由。

三面入口（home/goal/action）统一恢复面：start（真实 context + ≤1 问或
主 intervention）、answer（branch_key 直传收敛）、correct（「不是这个
原因」纠正反馈环）。路由只做鉴权/校验/装配，判定在 A-03 引擎 + 装配
服务（stuck_journey_service），零业务逻辑下沉复制。

经 ``_include_experience_routers`` 自动注册（文件名 *_router.py 约定）；
网关侧 /experience/* 走整组通配代理（proxy_routes.go Experience Routes），
无需逐路由登记。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.aurora.friction_diagnosis import FRICTION_TYPES, _QUESTION_BANK_INDEX
from app.models.user import User
from app.services.stuck_journey_service import (
    STUCK_JOURNEY_SURFACES,
    StuckJourneyService,
)

router = APIRouter(prefix="/experience", tags=["experience"])


class StuckJourneyStartRequest(BaseModel):
    surface: str = Field(description="Entry surface: home | goal | action")
    goal_id: UUID | None = None
    task_id: UUID | None = None


class StuckJourneyAnswerRequest(BaseModel):
    surface: str = Field(description="Entry surface: home | goal | action")
    question_id: str
    branch_key: str
    goal_id: UUID | None = None
    task_id: UUID | None = None


class StuckJourneyCorrectRequest(BaseModel):
    surface: str = Field(description="Entry surface: home | goal | action")
    friction_type: str
    intervention_key: str | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None
    reason_text: str | None = Field(default=None, max_length=500)


def _validated_surface(surface: str) -> str:
    value = (surface or "").strip().lower()
    if value not in STUCK_JOURNEY_SURFACES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"surface must be one of {sorted(STUCK_JOURNEY_SURFACES)}",
        )
    return value


def _validated_question(question_id: str, branch_key: str) -> tuple[str, str]:
    spec = _QUESTION_BANK_INDEX.get((question_id or "").strip())
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unknown question_id",
        )
    keys = {branch.key for branch in spec.branches}
    if (branch_key or "").strip() not in keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="branch_key not in question branches",
        )
    return question_id.strip(), branch_key.strip()


def _validated_friction_type(friction_type: str) -> str:
    value = (friction_type or "").strip().lower()
    if value not in FRICTION_TYPES or value == "unknown":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="friction_type must be a known friction type (not unknown)",
        )
    return value


# route-tier: authed
@router.post("/stuck-journey/start", response_model=dict[str, Any])
async def start_stuck_journey(
    payload: StuckJourneyStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """「我卡住了」统一入口：真实 context 投影 + ≤1 高价值问 / 主 intervention。"""
    surface = _validated_surface(payload.surface)
    service = StuckJourneyService(db)
    return await service.start(
        user_id=current_user.id,
        surface=surface,
        goal_id=payload.goal_id,
        task_id=payload.task_id,
    )


# route-tier: authed
@router.post("/stuck-journey/answer", response_model=dict[str, Any])
async def answer_stuck_journey(
    payload: StuckJourneyAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """单问回答（branch_key 直传）：≤2 轮收敛到主 intervention。"""
    surface = _validated_surface(payload.surface)
    question_id, branch_key = _validated_question(payload.question_id, payload.branch_key)
    service = StuckJourneyService(db)
    return await service.answer(
        user_id=current_user.id,
        surface=surface,
        question_id=question_id,
        branch_key=branch_key,
        goal_id=payload.goal_id,
        task_id=payload.task_id,
    )


# route-tier: authed
@router.post("/stuck-journey/correct", response_model=dict[str, Any])
async def correct_stuck_journey(
    payload: StuckJourneyCorrectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """「不是这个原因」：纠正落库进反馈环，返回按纠正重派生的旅程输出。"""
    surface = _validated_surface(payload.surface)
    friction_type = _validated_friction_type(payload.friction_type)
    service = StuckJourneyService(db)
    return await service.correct(
        user_id=current_user.id,
        surface=surface,
        friction_type=friction_type,
        intervention_key=payload.intervention_key,
        goal_id=payload.goal_id,
        task_id=payload.task_id,
        reason_text=payload.reason_text,
    )
