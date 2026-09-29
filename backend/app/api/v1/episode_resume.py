"""EpisodeResumeView API —— ``episode_resume_view.v1`` 接续读模型的唯一 REST 入口（V4-I01）.

- ``GET /episode-resume/tasks/{task_id}``：首页接续卡按需聚合（读模型，零写路径、
  零新表——B05 §5「带 TTL，不落第二真值表」）。

契约与纪律：
- 数据源只接既有权威（goal/task/run/outcome 账本/memory epoch）；``context_receipt_ref``
  是本轮 ContextSelectionReceipt 的引用（B05 §2：receipt 在 resume view 返回之前
  产生；receipt 本体契约归 V4-B05 §2，本端点只绑 ref、缺失或 scheme 不符时返回
  类型化 ``context_receipt_missing``，不造伪 receipt）。
- 降级语义（封闭词表 ``RESUME_DEGRADE_REASONS``）：对象不存在/已删、跨用户 → 404
  （house 先例 runs.py：不泄露存在性）；goal 改变需校准 / receipt 缺失 → 200 +
  类型化原因（旧计划不强推、无 receipt 不出视图）。
- 过期/陈旧判定归消费方：响应携带 ``expires_at``；``GET`` 不自动续期、不静默接续
  （B05 §9 反例「过期 EpisodeResumeView 自动接续」）。
- FIX-567 · resume_view 角色回执生产（B05 §2「receipt 在 resume view 返回之前」）：
  视图成功聚合后、HTTP 返回前，把本轮真实选择装配为 ``selection_role="resume_view"``
  回执落账（``CONTEXT_SELECTION_RECEIPT_MODE`` off 不产生；装配/落账失败只降级记
  WARN，绝不阻断视图主链路——与 ContextPackBuilder 面同纪律）。U01 消费面
  （``episode_resume_provider``）经 I06 ``latest`` 读面以该角色门判定接续依据。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.episode_resume_service import (
    EpisodeResumeService,
    ResumeSelectionObservations,
)

router = APIRouter(prefix="/episode-resume", tags=["episode-resume"])


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return True


async def _record_resume_view_receipt(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    observations: ResumeSelectionObservations,
) -> None:
    """resume view 选择 → ``resume_view`` 角色回执落账（FIX-567；mode 门 + fail-soft）。

    - mode 门：``CONTEXT_SELECTION_RECEIPT_MODE`` ∈ {shadow, live} 才产生（off =
      V3 路径零变化，与 ContextPackBuilder 面同口径）；
    - 装配为纯函数（``assemble_resume_view_receipt``），落账前过契约校验
      （``record_receipt`` fail-closed：违例不落库）；
    - 任何失败只降级记 WARN，不阻断视图返回（回执是 I1 授权无关元数据，不是
      业务事实）。
    """
    from app.config import settings
    from app.core.kill_switch import normalize_mode
    from app.orchestration.context_receipt_assembly import (
        assemble_resume_view_receipt,
    )
    from app.services.context_selection_receipt_service import record_receipt

    mode = normalize_mode(getattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "shadow"))
    if mode not in {"shadow", "live"}:
        return
    try:
        receipt = assemble_resume_view_receipt(
            user_id=user_id if isinstance(user_id, UUID) else UUID(str(user_id)),
            goal_id=observations.goal_id,
            task_id=observations.task_id,
            goal_version=observations.goal_version,
            task_version=observations.task_version,
            memory_epoch=observations.memory_epoch,
        )
        receipt_id = await record_receipt(db, user_id=user_id, receipt=receipt)
        if receipt_id is not None:
            logger.info("FIX-567 resume_view selection receipt {}", receipt.to_log_line())
    except Exception as exc:  # noqa: BLE001 - 回执失败只降级，不阻断视图主链路
        logger.warning("FIX-567 resume_view selection receipt failed: {}", exc)


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
    # FIX-567：视图成功返回前落 resume_view 角色回执（降级视图无选择发生不产生）。
    if result.view is not None and result.observations is not None:
        await _record_resume_view_receipt(db, user_id=current_user.id, observations=result.observations)
    return {"view": result.view, "reason_code": result.reason_code, "warnings": list(result.warnings)}


__all__ = ["router"]
