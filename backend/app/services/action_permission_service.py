"""P-04 · 低风险 Auto-execute 预授权 allowlist（grant/revoke 权威面）.

ACTION §3 + 卡 P-04：仅对**用户显式预授权**的低风险操作类别允许 proactive auto
execution。本模块是类别级授权的读写权威，不重建任何 proposal/action 真源：

- **授权真源**：``UserPreferencesCenter.explicit`` JSONB 的独立命名空间键
  ``action_auto_allowlist``（P-03 mute/cooldown 同款载体与读写模式——共用一行
  存储但键集不相交，零迁移）。每类别一条记录：
  ``{"granted_at": iso, "revoked_at": iso|None}``；revoke 保留记录（审计痕迹），
  再 grant 覆盖 ``revoked_at``（授权可逆、幂等）。
- **fail-closed**：偏好行缺失/形态非法/读取异常 → 一律按「未授予」处理（宁可
  保守）——授权面的任何存储层故障都不可能放大成 auto。
- **可授资格封闭**：只有命令处理器显式声明 ``auto_eligible=True`` 的类别可被
  授予（``task_commands.py`` 按命令域不可逆性声明；新命令域缺省**不可**授予）。
  ``task.create_batch``（不可逆）在授权入口即拒——不是仅靠风险门兜底。
- **判定时序**：``is_category_granted`` 由 command path 每次 create proposal 时
  调用（授权不缓存），revoke 对新操作与未落账的 auto proposal 即时生效。

与总开关（``UserSettings.low_risk_auto_execute``，X-03 真源）取**与**关系：
两者齐备且操作级风险门（low + reversible + 无人工审批标记）通过才 auto。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Mapping
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import CommandValidationError
from app.models.user_preferences import UserPreferencesCenter
from app.models.user_settings import UserSettings
from app.services.action_commands.task_commands import COMMAND_HANDLERS, get_command_handler

__all__ = [
    "ActionPermissionService",
    "AUTO_ALLOWLIST_NAMESPACE_KEY",
]

#: UserPreferencesCenter.explicit 中的独立命名空间键（P-03 mute 键同法，键集不相交）
AUTO_ALLOWLIST_NAMESPACE_KEY = "action_auto_allowlist"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


def is_auto_eligible_category(command_type: str) -> bool:
    """类别是否**可被授予** auto（处理器显式声明；未知类别 False——宁可保守）."""
    try:
        handler = get_command_handler(str(command_type))
    except CommandValidationError:
        return False
    return bool(getattr(handler, "auto_eligible", False))


def known_categories() -> list[str]:
    """命令域全词表（授权面状态投影用；封闭）。"""
    return sorted(COMMAND_HANDLERS)


class ActionPermissionService:
    """类别级 auto-execute 预授权的读写权威（grant / revoke / 判定 / 投影）."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- write ------------------------------------------------------------

    async def grant_category(self, user_id: str | UUID, category: str) -> dict[str, Any]:
        """授予类别：低风险可逆命令可被 Sparkle 直接执行（幂等，重复授予刷新时间）.

        词表外类别 / 不可逆类别（``auto_eligible=False``）→
        :class:`CommandValidationError`（授权入口即拒——高风险判定宁可保守）。
        """
        command_type = str(category).strip()
        if not is_auto_eligible_category(command_type):
            raise CommandValidationError(
                f"category {category!r} is not grantable for auto execution "
                "(unknown or irreversible-by-definition)",
                details={"category": str(category), "eligible": sorted(c for c in COMMAND_HANDLERS if is_auto_eligible_category(c))},
            )
        moment = _utcnow()

        def _mutate(section: dict[str, Any]) -> dict[str, Any]:
            raw_previous = section.get(command_type)
            previous: Mapping[str, Any] = raw_previous if isinstance(raw_previous, Mapping) else {}
            return {
                **section,
                command_type: {
                    "granted_at": _iso(moment),
                    "revoked_at": None,  # 再授予覆盖撤销（授权可逆）
                    "granted_count": int(previous.get("granted_count") or 0) + 1,
                },
            }

        await self._update_allowlist(user_id, _mutate)
        return {"category": command_type, "granted_at": _iso(moment), "revoked_at": None}

    async def revoke_category(self, user_id: str | UUID, category: str) -> dict[str, Any]:
        """撤销类别：同类操作即时回退 proposal（幂等；未授予/词表外 → revoked=False）.

        词表外类别同样拒绝（封闭词表；不发明新键）。未授予过的已词表类别返回
        ``revoked=False``（幂等 no-op，不写库）。
        """
        command_type = str(category).strip()
        if command_type not in COMMAND_HANDLERS:
            raise CommandValidationError(
                f"unknown category {category!r} (closed command vocabulary)",
                details={"known": sorted(COMMAND_HANDLERS)},
            )
        current = await self._read_allowlist(user_id)
        record = current.get(command_type)
        if not isinstance(record, Mapping) or record.get("granted_at") is None:
            return {"category": command_type, "revoked": False, "revoked_at": None}
        if record.get("revoked_at"):
            return {"category": command_type, "revoked": False, "revoked_at": str(record.get("revoked_at"))}
        moment = _utcnow()

        def _mutate(section: dict[str, Any]) -> dict[str, Any]:
            target = dict(section.get(command_type) or {})
            target["revoked_at"] = _iso(moment)
            return {**section, command_type: target}

        await self._update_allowlist(user_id, _mutate)
        return {"category": command_type, "revoked": True, "revoked_at": _iso(moment)}

    # -- read -------------------------------------------------------------

    async def is_category_granted(self, user_id: str | UUID, category: str) -> tuple[bool, str | None]:
        """``(allowed, granted_at)``——command path 的判定入口（fail-closed）.

        授予且未撤销 → ``(True, granted_at)``；其余（未授予/已 revoke/存储异常/
        形态非法）→ ``(False, None)``。
        """
        command_type = str(category).strip()
        try:
            allowlist = await self._read_allowlist(user_id)
        except Exception:  # noqa: BLE001 — 读失败按未授予（fail-closed，绝不放大成 auto）
            logger.opt(exception=True).warning(
                "action allowlist read failed; failing closed for user={} category={}",
                user_id,
                command_type,
            )
            return False, None
        record = allowlist.get(command_type)
        if not isinstance(record, Mapping):
            return False, None
        granted_at = record.get("granted_at")
        if not granted_at or record.get("revoked_at"):
            return False, None
        return True, str(granted_at)

    async def get_allowlist_state(self, user_id: str | UUID) -> dict[str, Any]:
        """授权面全量投影（UI 设置页数据源）：总开关 + 逐类别状态."""
        user_uuid = UUID(str(user_id))
        master_grant = bool(
            (
                await self.db.execute(
                    select(UserSettings.low_risk_auto_execute).where(
                        UserSettings.user_id == user_uuid,
                        UserSettings.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        )
        allowlist = await self._read_allowlist(user_id)
        categories: list[dict[str, Any]] = []
        for command_type in known_categories():
            record = allowlist.get(command_type)
            record = dict(record) if isinstance(record, Mapping) else {}
            granted_at = record.get("granted_at")
            revoked_at = record.get("revoked_at")
            category_granted = bool(granted_at) and not revoked_at
            categories.append(
                {
                    "category": command_type,
                    "eligible": is_auto_eligible_category(command_type),
                    "granted_at": str(granted_at) if granted_at else None,
                    "revoked_at": str(revoked_at) if revoked_at else None,
                    # 「该类别现在会 auto 吗」的合成真值：总开关 ∧ 类别授予
                    # （操作级风险门仍在此之上——medium/不可逆永不为 auto）。
                    "allowed": bool(master_grant and category_granted),
                }
            )
        return {
            "master_grant": master_grant,
            "categories": categories,
            "eligible_categories": [c for c in known_categories() if is_auto_eligible_category(c)],
        }

    # -- storage（P-03 ProactiveSuggestionFeedbackService 同款读写模式） ------

    async def _read_allowlist(self, user_id: str | UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return {}
        explicit = row.explicit
        if not isinstance(explicit, Mapping):
            return {}
        section = explicit.get(AUTO_ALLOWLIST_NAMESPACE_KEY)
        return dict(section) if isinstance(section, Mapping) else {}

    async def _update_allowlist(
        self, user_id: str | UUID, mutate: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        result = await self.db.execute(
            select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            section = mutate({})
            row = UserPreferencesCenter(
                user_id=user_id,
                explicit={AUTO_ALLOWLIST_NAMESPACE_KEY: section},
                last_explicit_update=_utcnow(),
            )
            self.db.add(row)
        else:
            explicit = dict(row.explicit) if isinstance(row.explicit, Mapping) else {}
            section = dict(explicit.get(AUTO_ALLOWLIST_NAMESPACE_KEY) or {})
            explicit[AUTO_ALLOWLIST_NAMESPACE_KEY] = mutate(section)
            row.explicit = explicit
            row.last_explicit_update = _utcnow()
            row.increment_version()
        await self.db.commit()
