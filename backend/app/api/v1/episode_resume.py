"""EpisodeResumeView API —— ``episode_resume_view.v1`` 接续读模型的唯一 REST 入口（V4-I01）.

- ``GET /episode-resume/tasks/{task_id}``：首页接续卡按需聚合（读模型，零写路径、
  零新表——B05 §5「带 TTL，不落第二真值表」）。

契约与纪律：
- 数据源只接既有权威（goal/task/run/outcome 账本/memory epoch）；``context_receipt_ref``
  是本轮 ContextSelectionReceipt 的引用（B05 §2：receipt 在 resume view 返回之前
  产生；receipt 本体契约归 V4-B05 §2 / 后续实现卡，本端点只绑 ref、缺失或 scheme
  不符时返回类型化 ``context_receipt_missing``，不造伪 receipt）。
- 降级语义（封闭词表 ``RESUME_DEGRADE_REASONS``）：对象不存在/已删、跨用户 → 404
  （house 先例 runs.py：不泄露存在性）；goal 改变需校准 / receipt 缺失 → 200 +
  类型化原因（旧计划不强推、无 receipt 不出视图）。
- 过期/陈旧判定归消费方：响应携带 ``expires_at``；``GET`` 不自动续期、不静默接续
  （B05 §9 反例「过期 EpisodeResumeView 自动接续」）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.episode_resume_service import EpisodeResumeService

router = APIRouter(prefix="/episode-resume", tags=["episode-resume"])


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return True


# route-tier: authed
@router.get("/tasks/{task_id}")
async def get_task_episode_resume(
    task_id: UUID,
    context_receipt_ref: str | None = Query(
        default=None, description="本轮 ContextSelectionReceipt ref（context_selection://…）"
    ),
    goal_id: UUID | None = Query(default=None, description="显式 goal（缺省经 task→plan→goal 既有链路解析）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """目标 Episode 接续视图（读模型；无 receipt ref 不出视图，已删对象不复活）。"""
    service = EpisodeResumeService(db)
    result = await service.build_resume_view(
        user_id=current_user.id,
        task_id=task_id,
        context_receipt_ref=context_receipt_ref or "",
        goal_id=goal_id,
    )
    if result.reason_code in ("object_not_found", "cross_object_access"):
        # house 先例（runs.py）：跨用户按 404 处理，不泄露存在性
        raise HTTPException(status_code=404, detail="episode resume target not found")
    return {"view": result.view, "reason_code": result.reason_code, "warnings": list(result.warnings)}


__all__ = ["router"]
