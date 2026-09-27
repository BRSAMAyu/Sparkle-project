"""O-06 · Release manifest —— model/config/migration 一次性快照面.

只读装配，不重建任何真源（Forbidden #1）：
- model 字段直接读 Settings 单例的模型路由配置；
- config 字段复用 ``app.config.release_flags.release_flags()``（五旗契约视图）与
  ``app.core.ops_surface`` 注册表（tri-state 能力的 settings 判据快照——不碰
  Redis，纯进程内可算，作为无 Redis 依赖的兜底观测）；
- migration 字段对 ``alembic_version`` 表做只读查询 + 代码侧 ScriptDirectory
  head 对账，任一侧缺席/失败都如实降级为 None + error 注记（绝不伪造）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.release_flags import release_flags_response
from app.core.kill_switch import resolve_settings_mode
from app.core.ops_surface import CAPABILITY_SPECS, resolve_binding

MANIFEST_VERSION = 1

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def model_snapshot() -> dict[str, Any]:
    """模型路由配置快照（settings 权威字段的只读投影）。"""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model_name": settings.LLM_MODEL_NAME,
        "llm_reason_model_name": settings.LLM_REASON_MODEL_NAME,
        "batch_llm_provider": settings.BATCH_LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


def config_snapshot() -> dict[str, Any]:
    """配置面快照：release 五旗 + tri-state 能力 settings 判据全量.

    五旗取 ``release_flags_response()`` 的冻结契约键集（shop / photon_transfer /
    public_leaderboards / public_community / visual_elements），与移动端解码面同形。
    """
    capability_modes: dict[str, str] = {}
    for spec in CAPABILITY_SPECS:
        try:
            capability_modes[spec.capability_id] = resolve_settings_mode(resolve_binding(spec))
        except Exception:  # pragma: no cover - 解析失败如实降级，不阻断清单
            capability_modes[spec.capability_id] = "unknown"
    return {
        "release_flags": release_flags_response(),
        "capability_mode_count": len(CAPABILITY_SPECS),
        "capability_settings_modes": capability_modes,
    }


async def migration_snapshot(db: AsyncSession | None) -> dict[str, Any]:
    """DB 迁移位对账：database_revision（库）vs code_head（代码），fail-soft。"""
    snapshot: dict[str, Any] = {
        "database_revision": None,
        "code_head": None,
        "up_to_date": None,
        "error": None,
    }
    if db is not None:
        try:
            row = (await db.execute(text("SELECT version_num FROM alembic_version"))).first()
            snapshot["database_revision"] = str(row[0]) if row else None
        except Exception as exc:
            snapshot["error"] = f"database_revision unavailable: {exc}"

    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
        snapshot["code_head"] = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception as exc:
        note = f"code_head unavailable: {exc}"
        snapshot["error"] = f"{snapshot['error']}; {note}" if snapshot["error"] else note

    if snapshot["database_revision"] is not None and snapshot["code_head"] is not None:
        # branch-tag 形（逗号分隔）取集合相等语义；常规单 head 取等值。
        db_revs = {rev.strip() for rev in snapshot["database_revision"].split(",")}
        code_revs = {rev.strip() for rev in snapshot["code_head"].split(",")}
        snapshot["up_to_date"] = db_revs == code_revs
    return snapshot


async def build_release_manifest(db: AsyncSession | None = None) -> dict[str, Any]:
    """装配 release manifest：model/config/migration 一次性只读快照。"""
    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model_snapshot(),
        "config": config_snapshot(),
        "migration": await migration_snapshot(db),
    }
