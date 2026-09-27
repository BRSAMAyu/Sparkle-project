"""O-06 · 统一操作面 internal API —— /api/internal/ops（INTERNAL_API_KEY 门禁）.

与 FV-24 auto_degrade 路由同面同鉴权语义（X-Internal-API-Key，常数时间比较，
未配置即 500 fail-closed）。鉴权助手为本模块本地副本（auto_degrade 的同名
助手是模块私有；抽取共享助手需改既有守卫文件，为控制爆炸半径择本地复制，
语义由两侧测试各自钉住）。

端点：
- GET  /capabilities                全量 flag 状态（可观测主读面）
- GET  /capabilities/{cid}          单能力详情 + 回滚史尾部
- POST /capabilities/{cid}/mode     受控翻转（词表外 400、未知能力 404、Redis 缺席 503）
- POST /capabilities/{cid}/rollback per-capability 回滚（无恢复点 409）
- GET  /release-manifest            model/config/migration 清单

写路径绝不默认 destructive：翻转/回滚都是显式 POST + 显式目标 mode，off/live
等模式由调用方逐次给出；本路由不提供任何批量/一键全关端点。
"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import ops_surface
from app.core.cache import cache_service
from app.core.release_manifest import build_release_manifest
from app.db.session import get_db

router = APIRouter(prefix="/ops")


def _verify_internal_key(api_key: str | None) -> None:
    """与 app.api.internal.auto_degrade 同语义：未配置 500、缺席/不符 401。"""
    expected = settings.INTERNAL_API_KEY
    if not expected:
        raise HTTPException(status_code=500, detail="INTERNAL_API_KEY not configured")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-Internal-API-Key header")
    if not hmac.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


class SetModeRequest(BaseModel):
    mode: str
    actor: str = "ops-api"
    reason: str | None = None


class RollbackRequest(BaseModel):
    actor: str = "ops-api"


# route-tier: internal
@router.get("/capabilities")
async def list_capabilities(
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """全量能力 flag 状态（运行时模式 + settings 判据 + 静态描述）。"""
    _verify_internal_key(x_internal_api_key)
    capabilities = await ops_surface.list_capability_snapshots(cache_service.redis)
    return {
        "capabilities": capabilities,
        "count": len(capabilities),
        "runtime_mode_available": cache_service.redis is not None,
    }


# route-tier: internal
@router.get("/capabilities/{capability_id}")
async def get_capability(
    capability_id: str,
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    _verify_internal_key(x_internal_api_key)
    try:
        spec = ops_surface.get_spec(capability_id)
    except ops_surface.UnknownCapabilityError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    snapshot = await ops_surface.capability_snapshot(cache_service.redis, spec)
    snapshot["rollback_history"] = await ops_surface.capability_history(cache_service.redis, spec)
    return snapshot


# route-tier: internal
@router.post("/capabilities/{capability_id}/mode")
async def set_capability_mode(
    capability_id: str,
    payload: SetModeRequest,
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """受控翻转单能力三态模式（带回滚史；不丢用户态——只写能力模式键）。"""
    _verify_internal_key(x_internal_api_key)
    try:
        spec = ops_surface.get_spec(capability_id)
    except ops_surface.UnknownCapabilityError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        result = await ops_surface.set_capability_mode(
            cache_service.redis,
            spec,
            payload.mode,
            actor=payload.actor,
            reason=payload.reason,
        )
    except ops_surface.InvalidModeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ops_surface.RedisUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return result


# route-tier: internal
@router.post("/capabilities/{capability_id}/rollback")
async def rollback_capability(
    capability_id: str,
    payload: RollbackRequest,
    x_internal_api_key: str | None = Header(None),
) -> dict[str, Any]:
    """回滚单能力到回滚史中最近的异值先前模式。"""
    _verify_internal_key(x_internal_api_key)
    try:
        spec = ops_surface.get_spec(capability_id)
    except ops_surface.UnknownCapabilityError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        return await ops_surface.rollback_capability(cache_service.redis, spec, actor=payload.actor)
    except ops_surface.NoRollbackPointError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ops_surface.RedisUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


# route-tier: internal
@router.get("/release-manifest")
async def get_release_manifest(
    x_internal_api_key: str | None = Header(None),
    db: AsyncSession | None = Depends(get_db),
) -> dict[str, Any]:
    """release manifest：model/config/migration 只读快照。"""
    _verify_internal_key(x_internal_api_key)
    return await build_release_manifest(db)
