"""
Aurora proactive pipeline — suppression state store (P-01).

把 :mod:`suppression` 需要的状态快照从既有存储（Redis 为主，用户偏好为
可选注入）组装出来。设计约定：

- **JSON 文档模式**：与 ``aurora/runtime_v1/wake_policy.py`` 的冷却载荷同
  一约定——每用户每 scope 一个 JSON 文档键，读解析、写整体覆盖，TTL 由
  写路径维护。不建新表、不动迁移。
- **scope 隔离**：``live``（真发后的状态消费）与 ``shadow``（would-notify
  的状态消费）各一份文档，互不可见——shadow 全链路可跑、可审，但永不
  碰真实抑制状态，也永不真发。
- **窗口修剪在读侧**：日界滚动 / 14d 拒绝窗 / 48h 新颖性 TTL 在
  ``build_snapshot`` 里按当前时刻裁剪，纯函数抑制链保持无时间窗逻辑。
- **fail-closed（R2 P1-1 修正）**：redis 不可用 / 读失败 / 状态文档损坏时
  ``build_snapshot`` 抛出 :class:`ProactiveStateUnavailable`，由 pipeline
  翻译成 ``state_unavailable`` 全抑制快照——**宁可少发不可误发**；绝不以
  "零计数快照" 放行（那是 fail-open）。只有「键不存在」这一合法空态返回
  空文档（新用户零计数属真实状态，不是故障）。
- redis 客户端按 duck-typing 注入（只要求 async ``get``/``set``），测试用
  内存 Fake 即可；读路径的异常语义见上，写路径失败仅告警（决定已落，
  不阻断事件流）。
"""

from __future__ import annotations

import json
from dataclasses import replace  # noqa: F401 — 测试辅助快照替换用
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from loguru import logger

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.suppression import (
    REJECTION_WINDOW_DAYS,
    SuppressionSnapshot,
)

__all__ = [
    "ProactiveSuppressionStore",
    "ProactiveStateUnavailable",
    "LIVE_SCOPE",
    "SHADOW_SCOPE",
]

LIVE_SCOPE = "live"
SHADOW_SCOPE = "shadow"

_KEY_TEMPLATE = "aurora:proactive_state:{scope}:{user_id}"
_STATE_TTL_SECONDS = 30 * 24 * 60 * 60  # 文档整体 TTL（30d），读路径持续续期。


class ProactiveStateUnavailable(RuntimeError):
    """抑制状态不可用（redis 故障 / 未配置 / 状态文档损坏）——fail-closed 信号。"""


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        from datetime import UTC

        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


class ProactiveSuppressionStore:
    """抑制状态读写（Redis JSON 文档，wake_policy 冷却键同族约定）。"""

    def __init__(self, redis: Any = None):
        self.redis = redis

    # -- key --------------------------------------------------------------

    @staticmethod
    def state_key(scope: str, user_id: str) -> str:
        return _KEY_TEMPLATE.format(scope=scope, user_id=str(user_id))

    # -- read -------------------------------------------------------------

    async def build_snapshot(
        self,
        user_id: str,
        *,
        scope: str = LIVE_SCOPE,
        now: datetime | None = None,
        quiet_window: tuple[str, str] | None | bool = True,
        muted_triggers: frozenset[str] | None = None,
    ) -> SuppressionSnapshot:
        """构建当前抑制快照（读侧完成窗口修剪）。

        Raises:
            ProactiveStateUnavailable: redis 未配置 / 读失败 / 文档损坏——
                调用方（pipeline）必须翻译成 ``state_unavailable`` 全抑制，
                不得以零计数快照放行（fail-closed，R2 P1-1）。
        """
        now = now or _utcnow()
        doc = await self._load(user_id, scope)
        knobs = proactive_config

        # quiet hours：显式传 None 关闭；缺省读管线旋钮（env 可覆写）。
        if quiet_window is True:
            quiet_window = (
                (knobs.PROACTIVE_QUIET_START, knobs.PROACTIVE_QUIET_END)
                if knobs.PROACTIVE_QUIET_HOURS_ENABLED
                else None
            )

        daily_count = self._day_count(doc, now)
        last_notify = self._last_notify(doc)
        rejections = self._recent_rejections(doc, now)
        seen = self._seen_subject_keys(doc, now)

        if muted_triggers is None:
            muted_triggers = frozenset(str(m) for m in (doc.get("muted_triggers") or ()))

        return SuppressionSnapshot(
            now=now,
            quiet_window=quiet_window,  # type: ignore[arg-type]
            timezone=knobs.PROACTIVE_QUIET_TIMEZONE,
            proactive_action_disabled=bool(doc.get("proactive_action_disabled")),
            muted_triggers=muted_triggers,
            daily_count=daily_count,
            daily_cap=knobs.PROACTIVE_DAILY_CAP,
            last_notify_at=last_notify,
            cooldown_minutes=knobs.PROACTIVE_COOLDOWN_MINUTES,
            recent_rejections=rejections,
            rejection_threshold=knobs.PROACTIVE_REJECTION_THRESHOLD,
            seen_subject_keys=seen,
        )

    # -- write ------------------------------------------------------------

    async def record_notification(
        self,
        user_id: str,
        *,
        trigger: str,
        subject_key: str,
        scope: str = LIVE_SCOPE,
        now: datetime | None = None,
    ) -> None:
        """通知（或 would-notify）落状态：日计数 +1、last_notify、novelty 集合。"""
        now = now or _utcnow()
        doc = await self._load(user_id, scope)

        day = self._day_of(now)
        if doc.get("day") != day:
            doc["day"] = day
            doc["day_count"] = 0
        doc["day_count"] = int(doc.get("day_count") or 0) + 1

        last_notify = dict(doc.get("last_notify") or {})
        last_notify[str(trigger)] = now.isoformat()
        doc["last_notify"] = last_notify

        if subject_key:
            seen = dict(doc.get("seen") or {})
            seen[f"{trigger}:{subject_key}"] = now.isoformat()
            doc["seen"] = seen

        doc["updated_at"] = now.isoformat()
        await self._save(user_id, scope, doc)

    async def record_rejection(
        self,
        user_id: str,
        *,
        trigger: str,
        scope: str = LIVE_SCOPE,
        now: datetime | None = None,
    ) -> None:
        """用户拒绝/负反馈落状态（喂 recent_rejection 抑制器）。"""
        now = now or _utcnow()
        doc = await self._load(user_id, scope)
        rejections = dict(doc.get("rejections") or {})
        entry = dict(rejections.get(str(trigger)) or {})
        entry["count"] = int(entry.get("count") or 0) + 1
        entry["updated_at"] = now.isoformat()
        rejections[str(trigger)] = entry
        doc["rejections"] = rejections
        doc["updated_at"] = now.isoformat()
        await self._save(user_id, scope, doc)

    # -- internals --------------------------------------------------------

    @staticmethod
    def _day_of(now: datetime) -> str:
        return now.date().isoformat()

    def _day_count(self, doc: Mapping[str, Any], now: datetime) -> int:
        if doc.get("day") != self._day_of(now):
            return 0
        return int(doc.get("day_count") or 0)

    def _last_notify(self, doc: Mapping[str, Any]) -> dict[str, datetime]:
        result: dict[str, datetime] = {}
        for trigger, raw in (doc.get("last_notify") or {}).items():
            parsed = _parse_dt(raw)
            if parsed is not None:
                result[str(trigger)] = parsed
        return result

    def _recent_rejections(self, doc: Mapping[str, Any], now: datetime) -> dict[str, int]:
        window_start = now - timedelta(days=REJECTION_WINDOW_DAYS)
        result: dict[str, int] = {}
        for trigger, entry in (doc.get("rejections") or {}).items():
            if not isinstance(entry, Mapping):
                continue
            updated = _parse_dt(entry.get("updated_at"))
            if updated is None or updated < window_start:
                continue
            result[str(trigger)] = int(entry.get("count") or 0)
        return result

    def _seen_subject_keys(self, doc: Mapping[str, Any], now: datetime) -> frozenset[str]:
        from app.aurora.proactive.suppression import NOVELTY_TTL

        cutoff = now - NOVELTY_TTL
        seen: set[str] = set()
        for key, raw in (doc.get("seen") or {}).items():
            parsed = _parse_dt(raw)
            if parsed is not None and parsed >= cutoff:
                seen.add(str(key))
        return frozenset(seen)

    async def _load(self, user_id: str, scope: str) -> dict[str, Any]:
        """读状态文档；键不存在返回空 dict（合法零态），其余故障上抛。"""
        if self.redis is None:
            raise ProactiveStateUnavailable("proactive state redis not configured")
        try:
            raw = await self.redis.get(self.state_key(scope, user_id))
        except Exception as exc:
            logger.warning("proactive state load failed scope={} user={}: {!r}", scope, user_id, exc)
            raise ProactiveStateUnavailable(f"proactive state read failed: {exc!r}") from exc
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("proactive state doc corrupt scope={} user={}: {!r}", scope, user_id, exc)
            raise ProactiveStateUnavailable(f"proactive state doc corrupt: {exc!r}") from exc
        if not isinstance(parsed, dict):
            raise ProactiveStateUnavailable("proactive state doc is not a mapping")
        return parsed

    async def _save(self, user_id: str, scope: str, doc: Mapping[str, Any]) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.set(
                self.state_key(scope, user_id),
                json.dumps(doc, ensure_ascii=False, default=str),
                ex=_STATE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("proactive state save failed scope={} user={}: {!r}", scope, user_id, exc)
