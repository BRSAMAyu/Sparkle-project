"""P-04 · Action Permission API —— 低风险 auto-execute 预授权面端点.

- ``GET  /action-permissions``：授权面全量投影（总开关 + 逐类别
  eligible/granted_at/revoked_at/allowed——设置页数据源）；
- ``POST /action-permissions/{category}/grant``：授予类别（低风险可逆命令可被
  Sparkle 直接执行；词表外/不可逆类别 422——授权入口即拒）；
- ``POST /action-permissions/{category}/revoke``：撤销类别（同类操作即时回退
  proposal；幂等）。

设计边界：
- 类别词表 = X-03 ActionCommandType 封闭词表（不发明新类别空间）；「可授资格」
  由命令处理器声明的 ``auto_eligible`` 导出（不可逆类别不可授予）；
- **总开关**（UserSettings.low_risk_auto_execute）只读投影——本面不写
  UserSettings（既有 settings 面权威不动）；auto = 总开关 ∧ 类别授予 ∧ 风险门；
- 每次 auto 执行的 receipt 携带 ``revoke_entry.path`` 指向本面的 revoke 端点
  （可追溯、可纠正）。

网关侧由 backend/gateway/internal/handler/proxy_routes.go 的 /action-permissions
代理组转发（Go 纯 proxy，无业务逻辑，分层边界不变）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.action_command import ActionCommandError
from app.db.session import get_db
from app.models.user import User
from app.services.action_permission_service import ActionPermissionService

router = APIRouter(prefix="/action-permissions", tags=["action-permissions"])


class PermissionMutationResponse(BaseModel):
    """grant/revoke 的响应（类别 + 时间戳 + 幂等标志）."""

    category: str
    granted_at: str | None = None
    revoked_at: str | None = None
    revoked: bool = False
    applied: bool = True


class PermissionStateResponse(BaseModel):
    master_grant: bool
    categories: list[dict[str, Any]]
    eligible_categories: list[str]


def _to_http_error(exc: ActionCommandError) -> HTTPException:
    return HTTPException(status_code=exc.http_status, detail=exc.to_payload())


# route-tier: authed
@router.get("", response_model=PermissionStateResponse)
async def get_permission_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """授权面全量投影（本人；无跨用户面——权限是每用户自己的预授权）."""
    state = await ActionPermissionService(db).get_allowlist_state(current_user.id)
    return PermissionStateResponse(**state)


# route-tier: authed
@router.post("/{category}/grant", response_model=PermissionMutationResponse)
async def grant_category(
    category: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """授予类别：允许 Sparkle 对该类别低风险可逆操作 proactive auto execute."""
    service = ActionPermissionService(db)
    try:
        record = await service.grant_category(current_user.id, category)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return PermissionMutationResponse(applied=True, **record)


# route-tier: authed
@router.post("/{category}/revoke", response_model=PermissionMutationResponse)
async def revoke_category(
    category: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销类别：同类操作即时回退 proposal（幂等；未授予 → revoked=False）."""
    service = ActionPermissionService(db)
    try:
        record = await service.revoke_category(current_user.id, category)
    except ActionCommandError as exc:
        raise _to_http_error(exc) from None
    return PermissionMutationResponse(applied=bool(record.get("revoked")), **record)
