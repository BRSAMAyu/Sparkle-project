"""LearningJourney API —— 资料→错题→练习→检验连续体验的唯一 REST 入口（V4-U10）.

- ``GET  /learning-journey/tasks/{task_id}``：目标上下文旅程装配（读模型）；
- ``POST /learning-journey/tasks/{task_id}/check/enter``：用户显式选择检验
  （唯一写路径：I07 脚手架推进，证据不支持原地暂缓）；
- ``POST /learning-journey/tasks/{task_id}/check/submit``：检验提交判分
  （零写；客户端载荷零答案材料——出口泄漏探针强制）。

契约与纪律（对齐 episode_resume 先例）：
- 数据源只接既有权威（tasks.guide_json 策略块 / task_documents→stored_files /
  error_records）；判分权威 = 策略块 ``independent_check`` 子结构（服务端持有，
  任何响应不回显答案）。
- 出题证据门覆盖三个面（R1 F-1）：enter 写路径（显式选择 + 证据支持才推进）、
  GET 读模型（未到检验段 ``view.check`` 不携带题面）、判分面（未到检验段
  提交一律 ``HOLD.scaffold_not_at_check``，无 correct 裁决）。
- 降级语义（封闭 reason）：对象不存在/已删/跨用户 → 404（不泄露存在性）；
  策略块缺失/脏块 → 200 + ``warnings``（老目标不硬推检验）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.learning_journey_service import LearningJourneyService

router = APIRouter(prefix="/learning-journey", tags=["learning-journey"])


class CheckSubmitRequest(BaseModel):
    answer: str


def _raise_if_unfound(reason: str) -> None:
    if reason in ("object_not_found", "cross_object_access"):
        # house 先例（runs.py / episode_resume.py）：跨用户按 404 处理，不泄露存在性
        raise HTTPException(status_code=404, detail="learning journey target not found")


# route-tier: authed
@router.get("/tasks/{task_id}")
async def get_goal_learning_journey(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """目标上下文旅程视图（资料/错题/练习/检验；来源可见、答案不出库）。"""
    result = await LearningJourneyService(db).build_goal_journey(user_id=current_user.id, task_id=task_id)
    _raise_if_unfound(result.reason_code)
    return {
        "view": result.view,
        "reason_code": result.reason_code,
        "warnings": list(result.warnings),
    }


# route-tier: authed
@router.post("/tasks/{task_id}/check/enter")
async def enter_goal_independent_check(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """用户在旅程页显式选择「检验」（证据不支持 → 类型化暂缓，不推进）。"""
    result, reason = await LearningJourneyService(db).enter_check(user_id=current_user.id, task_id=task_id)
    _raise_if_unfound(reason)
    assert result is not None
    return {"view": result.view, "scaffold_persisted": result.scaffold_persisted, "reason_code": reason}


# route-tier: authed
@router.post("/tasks/{task_id}/check/submit")
async def submit_goal_independent_check(
    task_id: UUID,
    request: CheckSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """检验提交判分（确定性归一比对，零模型；响应不携带答案材料）。"""
    payload, reason = await LearningJourneyService(db).grade_check(
        user_id=current_user.id, task_id=task_id, submitted=request.answer
    )
    _raise_if_unfound(reason)
    return {"view": payload, "reason_code": reason}


__all__ = ["router"]
