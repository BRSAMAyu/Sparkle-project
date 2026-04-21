from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from prometheus_client import Counter as PrometheusCounter

from app.config import settings
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.core.event_types import JITAI_TRIGGERED
from app.core.metrics import get_or_create_metric
from app.schemas.foresight import Deviation, ForesightHint
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService


JITAI_TRIGGERED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_jitai_triggered_total",
    "Total JITAI foresight hints triggered",
    ["dim"],
)
JITAI_SKIPPED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_jitai_skipped_total",
    "Skipped JITAI hint emissions by reason",
    ["reason"],
)

TEMPLATE_REGISTRY: dict[str, dict[str, str]] = {
    "study_pace:below": {
        "template_id": "study_pace_below",
        "message": "你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。",
    },
    "study_pace:above": {
        "template_id": "study_pace_above",
        "message": "你最近学习强度高于常态，今晚记得留一段缓冲收尾。",
    },
    "completion_rate:below": {
        "template_id": "completion_rate_below",
        "message": "你最近完成率在下滑，先只收掉一个最小闭环。",
    },
    "completion_rate:above": {
        "template_id": "completion_rate_above",
        "message": "你最近完成率高于常态，适合趁热补一段复盘巩固。",
    },
    "engagement_level:below": {
        "template_id": "engagement_level_below",
        "message": "你最近互动投入偏低，先做一次很短的主动提问或记录。",
    },
    "engagement_level:above": {
        "template_id": "engagement_level_above",
        "message": "你最近投入很深，别忘了留一点空间做轻量总结。",
    },
    "mood_valence:below": {
        "template_id": "mood_valence_below",
        "message": "你最近情绪倾向偏低，先选一个最稳的小动作找回节奏。",
    },
    "mood_valence:above": {
        "template_id": "mood_valence_above",
        "message": "你最近状态比平时更亮，适合承接一件需要推进感的任务。",
    },
    "plan_adherence:below": {
        "template_id": "plan_adherence_below",
        "message": "你最近有些偏离原计划，先把今天的主线重新钉住。",
    },
    "plan_adherence:above": {
        "template_id": "plan_adherence_above",
        "message": "你最近跟计划很稳，可以顺手把下一步准备动作补齐。",
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JITAITrigger:
    LOCAL_STATE_ATTR = "_aurora_stage27_jitai_local_state"
    RATE_RETENTION_DAYS = 4

    def __init__(self) -> None:
        self.kill_switch = AuroraStage27ForesightKillSwitchService()

    async def generate_hints(
        self,
        *,
        user_id: UUID,
        deviations: tuple[Deviation, ...],
        now: datetime | None = None,
        mutate_state: bool = True,
    ) -> tuple[ForesightHint, ...]:
        normalized_user_id = self._require_user_id(user_id)
        reference_time = now or _utcnow()
        hints: list[ForesightHint] = []

        for deviation in deviations:
            if abs(float(deviation.z_score)) < float(settings.AURORA_FORESIGHT_DEVIATION_Z_THRESHOLD) or float(deviation.confidence) < 0.5:
                JITAI_SKIPPED_TOTAL.labels(reason="low_confidence").inc()
                continue

            template = self._resolve_template(dim=deviation.dim, direction=deviation.direction)
            if template is None:
                logger.warning("Missing JITAI template for dim={} direction={}", deviation.dim, deviation.direction)
                continue

            if mutate_state:
                if await self._is_on_cooldown(normalized_user_id, deviation.dim, now=reference_time):
                    JITAI_SKIPPED_TOTAL.labels(reason="cooldown").inc()
                    continue
                if await self._daily_budget_used(normalized_user_id, now=reference_time) >= int(settings.AURORA_FORESIGHT_JITAI_DAILY_BUDGET):
                    JITAI_SKIPPED_TOTAL.labels(reason="budget").inc()
                    continue

            hint = ForesightHint(
                hint_id=f"jitai_{uuid.uuid4().hex}",
                dim=deviation.dim,
                message=template["message"],
                z_score=round(float(deviation.z_score), 4),
                confidence=round(float(deviation.confidence), 4),
                generated_at=reference_time,
                template_id=template["template_id"],
            )
            hints.append(hint)

            if mutate_state:
                await self._mark_triggered(normalized_user_id, hint, now=reference_time)

        return tuple(hints[: int(settings.AURORA_FORESIGHT_JITAI_DAILY_BUDGET)])

    async def record_misfire(self, *, now: datetime | None = None) -> float:
        reference_time = now or _utcnow()
        await self._increment_rate_counter("misfires", now=reference_time)
        return await self._evaluate_auto_downgrade(now=reference_time)

    async def get_daily_budget_usage(self, *, user_id: UUID, now: datetime | None = None) -> int:
        normalized_user_id = self._require_user_id(user_id)
        return await self._daily_budget_used(normalized_user_id, now=now or _utcnow())

    async def get_misfire_rate(self, *, days_ago: int = 0, now: datetime | None = None) -> float:
        reference_time = (now or _utcnow()) - timedelta(days=max(0, int(days_ago)))
        triggered = await self._get_rate_counter("triggered", now=reference_time)
        if triggered <= 0:
            return 0.0
        misfires = await self._get_rate_counter("misfires", now=reference_time)
        return float(misfires) / float(triggered)

    @staticmethod
    def _require_user_id(user_id: UUID | str) -> str:
        normalized = str(user_id or "").strip()
        if not normalized:
            raise ValueError("JITAITrigger requires a non-empty user_id")
        return normalized

    @staticmethod
    def _resolve_template(*, dim: str, direction: str) -> dict[str, str] | None:
        return TEMPLATE_REGISTRY.get(f"{dim}:{direction}")

    async def _mark_triggered(self, user_id: str, hint: ForesightHint, *, now: datetime) -> None:
        await self._set_cooldown(user_id=user_id, dim=hint.dim, now=now)
        await self._increment_budget(user_id=user_id, now=now)
        await self._increment_rate_counter("triggered", now=now)
        JITAI_TRIGGERED_TOTAL.labels(dim=hint.dim).inc()
        await self._evaluate_auto_downgrade(now=now)
        try:
            await event_bus.publish(
                JITAI_TRIGGERED,
                {
                    "event_type": JITAI_TRIGGERED,
                    "user_id": user_id,
                    "dim": hint.dim,
                    "hint_id": hint.hint_id,
                    "template_id": hint.template_id,
                    "generated_at": hint.generated_at.isoformat(),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive around infra
            logger.warning("Failed to publish jitai_triggered event: {}", exc)

    async def _evaluate_auto_downgrade(self, *, now: datetime) -> float:
        rates = [await self.get_misfire_rate(days_ago=offset, now=now) for offset in range(3)]
        if all(rate > float(settings.AURORA_FORESIGHT_JITAI_MISFIRE_THRESHOLD) for rate in rates):
            if await self.kill_switch.get_mode() == "live":
                await self.kill_switch.set_feature_mode("deviation", "shadow")
                await self.kill_switch.set_feature_mode("jitai", "shadow")
        return rates[0] if rates else 0.0

    async def _daily_budget_used(self, user_id: str, *, now: datetime) -> int:
        key = self._budget_key(user_id, now=now)
        return int(await self._get_state_value(key, default=0))

    async def _increment_budget(self, *, user_id: str, now: datetime) -> int:
        key = self._budget_key(user_id, now=now)
        return int(await self._increment_state_value(key, expire_at=self._day_expiry(now), amount=1))

    async def _is_on_cooldown(self, user_id: str, dim: str, *, now: datetime) -> bool:
        key = self._cooldown_key(user_id=user_id, dim=dim)
        expires_at = await self._get_state_value(key, default=None)
        if expires_at is None:
            return False
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if not isinstance(expires_at, datetime):
            return False
        if expires_at <= now:
            await self._delete_state_key(key)
            return False
        return True

    async def _set_cooldown(self, *, user_id: str, dim: str, now: datetime) -> None:
        expires_at = now + timedelta(hours=int(settings.AURORA_FORESIGHT_JITAI_COOLDOWN_HOURS))
        await self._set_state_value(self._cooldown_key(user_id=user_id, dim=dim), expires_at=expires_at, value=expires_at.isoformat())

    async def _increment_rate_counter(self, kind: str, *, now: datetime) -> int:
        return int(
            await self._increment_state_value(
                self._rate_key(kind, now=now),
                expire_at=self._rate_expiry(now),
                amount=1,
            )
        )

    async def _get_rate_counter(self, kind: str, *, now: datetime) -> int:
        return int(await self._get_state_value(self._rate_key(kind, now=now), default=0))

    @classmethod
    def _rate_key(cls, kind: str, *, now: datetime) -> str:
        return f"jitai:rate:{kind}:{now.date().isoformat()}"

    @classmethod
    def _budget_key(cls, user_id: str, *, now: datetime) -> str:
        return f"jitai:budget:{user_id}:{now.date().isoformat()}"

    @classmethod
    def _cooldown_key(cls, *, user_id: str, dim: str) -> str:
        return f"jitai:cooldown:{user_id}:{dim}"

    @staticmethod
    def _day_expiry(now: datetime) -> datetime:
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    def _rate_expiry(cls, now: datetime) -> datetime:
        # Retain daily rate counters long enough to evaluate the rolling 3-day
        # misfire window required by Rule AL auto-downgrade.
        return (now + timedelta(days=cls.RATE_RETENTION_DAYS)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    async def _get_state_value(self, key: str, *, default: Any) -> Any:
        redis_client = cache_service.redis
        if redis_client is not None:
            value = await redis_client.get(f"aurora:stage27:{key}")
            return default if value is None else value
        store = self._local_store()
        expires_at = store["expirations"].get(key)
        if expires_at is not None and expires_at <= _utcnow():
            store["values"].pop(key, None)
            store["expirations"].pop(key, None)
            return default
        return store["values"].get(key, default)

    async def _set_state_value(self, key: str, *, value: Any, expires_at: datetime) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            ttl = max(1, int((expires_at - _utcnow()).total_seconds()))
            await redis_client.set(f"aurora:stage27:{key}", value, ex=ttl)
            return
        store = self._local_store()
        store["values"][key] = value
        store["expirations"][key] = expires_at

    async def _delete_state_key(self, key: str) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"aurora:stage27:{key}")
            return
        store = self._local_store()
        store["values"].pop(key, None)
        store["expirations"].pop(key, None)

    async def _increment_state_value(self, key: str, *, expire_at: datetime, amount: int) -> int:
        redis_client = cache_service.redis
        if redis_client is not None:
            redis_key = f"aurora:stage27:{key}"
            value = await redis_client.incrby(redis_key, amount)
            await redis_client.expire(redis_key, max(1, int((expire_at - _utcnow()).total_seconds())))
            return int(value)
        store = self._local_store()
        self._prune_local_store(store)
        store["values"][key] = int(store["values"].get(key, 0)) + amount
        store["expirations"][key] = expire_at
        return int(store["values"][key])

    @classmethod
    def _local_store(cls) -> dict[str, dict[str, Any]]:
        store = getattr(settings, cls.LOCAL_STATE_ATTR, None)
        if isinstance(store, dict):
            return store
        store = {"values": {}, "expirations": {}}
        setattr(settings, cls.LOCAL_STATE_ATTR, store)
        return store

    @staticmethod
    def _prune_local_store(store: dict[str, dict[str, Any]]) -> None:
        now = _utcnow()
        expired = [
            key
            for key, expires_at in dict(store.get("expirations", {})).items()
            if isinstance(expires_at, datetime) and expires_at <= now
        ]
        for key in expired:
            store["values"].pop(key, None)
            store["expirations"].pop(key, None)
