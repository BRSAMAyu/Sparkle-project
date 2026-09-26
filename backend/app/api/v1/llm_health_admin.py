"""LLM 模型健康管理面（V3-FIX-81，wt456b）。

Q-06 chaos S3a 实锤：llm_router 内存健康（三相滞回状态机）与 redis
`llm:*` 三相状态机并行生效，历史排障「只清 redis」后残留内存态仍把已恢复
provider 挡在门外（生成持续避开目标模型，重启引擎才恢复）——且不存在
同时清双源的出口。本模块提供单出口复位：一次调用同时清内存 + redis，
消除「清一源漏一源」陷阱。

与 wt448 V3-FIX-78 的协同边界：**只补同步/复位出口，不改判定语义**——
`_preflight_all_unhealthy`/`_model_tryable`/三相状态机本身零改动；复位后
各源按既有语义自然恢复参与判定。排障 runbook 登记见
docs/05_部署与运维/RUNBOOK_LLM_HEALTH_RESET.md。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_superuser
from app.core.llm_router import llm_router
from app.middleware.admin_audit import audit_admin_action
from app.services.llm.fallback import llm_fallback_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-health", tags=["LLM Health Admin"])


class LLMHealthResetRequest(BaseModel):
    """复位请求体：model_key 缺省 = 全量复位所有已登记模型。"""

    model_key: str | None = Field(default=None, description="指定模型键；缺省全量复位")


class LLMHealthResetResponse(BaseModel):
    """复位回执：双源各自实际清除面，供 runbook 验证步骤核对。"""

    memory_reset_keys: list[str]
    redis_cleared_keys: int
    model_key: str | None = None


async def reset_llm_health_sources(model_key: str | None = None) -> dict[str, Any]:
    """双源单出口（V3-FIX-81）：同时复位 router 内存态与 redis tracker 键。

    供管理面端点调用；独立成函数便于单测直接覆盖「双源同步」语义。
    """
    memory_reset_keys = llm_router.reset_model_health(model_key)
    try:
        redis_cleared = await llm_fallback_manager.health_tracker.reset_health(model_key)
    except Exception:
        # redis 面失败不回滚内存复位（复位是收敛操作，残留键随 TTL 自然衰减）；
        # 显式报错让调用方知道 redis 面未清，重试即可。
        logger.exception("[LLMHealthAdmin] redis health reset failed; memory side already reset")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="redis health reset failed; memory side already reset, retry",
        ) from None

    logger.warning(
        f"[LLMHealthAdmin] dual-source health reset: memory={len(memory_reset_keys)} keys, "
        f"redis_cleared={redis_cleared}, scope={'model:' + model_key if model_key else 'all'} "
        "(V3-FIX-81)"
    )
    return {
        "memory_reset_keys": memory_reset_keys,
        "redis_cleared_keys": redis_cleared,
        "model_key": model_key,
    }


# route-tier: internal
@router.post("/reset", response_model=LLMHealthResetResponse)
@audit_admin_action(category="llm_health_reset", risk="high", action="reset_llm_model_health")
async def reset_llm_model_health(
    request: LLMHealthResetRequest | None = None,
    _admin=Depends(get_current_active_superuser),
) -> LLMHealthResetResponse:
    """复位模型健康双源（内存 + redis）。

    用途：故障演练/排障后让「已恢复的 provider」立即回到候选面，无需重启引擎。
    """
    body = request or LLMHealthResetRequest()
    if body.model_key is not None and not body.model_key.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="model_key must be non-empty")
    result = await reset_llm_health_sources(body.model_key)
    return LLMHealthResetResponse(
        memory_reset_keys=result["memory_reset_keys"],
        redis_cleared_keys=result["redis_cleared_keys"],
        model_key=result["model_key"],
    )
