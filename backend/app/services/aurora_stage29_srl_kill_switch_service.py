from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings
from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AuroraStage29SRLKillSwitchService:
    PREFIX = "aurora:stage29:srl:"
    LAG_STREAK_KEY = "lag_high_points"
    MISJUDGMENT_STREAK_KEY = "misjudgment_high_days"
    MASTER_BINDING = KillSwitchBinding(
        stage="29",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_SRL_MODE",
    )
    TRACKER_BINDING = KillSwitchBinding(
        stage="29",
        feature="tracker",
        redis_key="tracker_mode",
        settings_attr="AURORA_SRL_TRACKER_MODE",
    )
    BRIDGE_BINDING = KillSwitchBinding(
        stage="29",
        feature="bridge",
        redis_key="bridge_mode",
        settings_attr="AURORA_SRL_BRIDGE_MODE",
    )
    SCAFFOLDING_BINDING = KillSwitchBinding(
        stage="29",
        feature="scaffolding_consume",
        redis_key="scaffolding_consume_mode",
        settings_attr="AURORA_SRL_SCAFFOLDING_CONSUME_MODE",
    )

    async def get_mode(self) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
        )

    async def get_tracker_mode(self) -> str:
        if await self.get_mode() == "off":
            record_mode_gauge("29", "tracker", "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.TRACKER_BINDING,
        )

    async def get_bridge_mode(self) -> str:
        if await self.get_mode() == "off":
            record_mode_gauge("29", "bridge", "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BRIDGE_BINDING,
        )

    async def get_scaffolding_consume_mode(self) -> str:
        if await self.get_mode() == "off":
            record_mode_gauge("29", "scaffolding_consume", "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.SCAFFOLDING_BINDING,
        )

    async def set_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
            mode=mode,
        )

    async def set_tracker_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.TRACKER_BINDING,
            mode=mode,
        )

    async def set_bridge_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BRIDGE_BINDING,
            mode=mode,
        )

    async def set_scaffolding_consume_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.SCAFFOLDING_BINDING,
            mode=mode,
        )

    async def ordered_shutdown(self) -> dict[str, str]:
        await self.set_scaffolding_consume_mode("off")
        await self.set_bridge_mode("off")
        await self.set_tracker_mode("off")
        return await self.summary()

    async def ordered_startup(self, mode: str = "live") -> dict[str, str]:
        normalized = self._normalize_mode(mode)
        await self.set_mode(normalized)
        await self.set_tracker_mode(normalized)
        await self.set_bridge_mode(normalized)
        await self.set_scaffolding_consume_mode(normalized)
        return await self.summary()

    async def summary(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            "tracker_mode": await self.get_tracker_mode(),
            "bridge_mode": await self.get_bridge_mode(),
            "scaffolding_consume_mode": await self.get_scaffolding_consume_mode(),
        }

    async def record_event_lag_p95(self, lag_seconds: float, *, now: datetime | None = None) -> str:
        reference_time = now or _utcnow()
        normalized = max(0.0, float(lag_seconds))
        threshold = float(settings.AURORA_SRL_EVENT_LAG_P95_THRESHOLD_SECONDS)
        redis_client = cache_service.redis
        if normalized <= threshold:
            await self._reset_lag_points()
            return await self.get_bridge_mode()

        encoded = reference_time.isoformat()
        if redis_client is not None:
            key = f"{self.PREFIX}{self.LAG_STREAK_KEY}"
            raw = await redis_client.get(key)
            values = [item for item in str(raw or "").split(",") if item]
            values.append(encoded)
            cutoff = reference_time - timedelta(minutes=3)
            values = [
                item
                for item in values
                if datetime.fromisoformat(item) >= cutoff
            ]
            await redis_client.set(key, ",".join(values))
            if len(values) >= 3:
                await self.set_bridge_mode("shadow")
                await self.set_scaffolding_consume_mode("shadow")
                return "shadow"
            return await self.get_bridge_mode()

        values = list(getattr(settings, "_aurora_stage29_lag_points", []))
        values.append(encoded)
        cutoff = reference_time - timedelta(minutes=3)
        settings._aurora_stage29_lag_points = [
            item for item in values if datetime.fromisoformat(item) >= cutoff
        ]
        if len(settings._aurora_stage29_lag_points) >= 3:
            await self.set_bridge_mode("shadow")
            await self.set_scaffolding_consume_mode("shadow")
            return "shadow"
        return await self.get_bridge_mode()

    async def record_misjudgment_rate(self, misjudgment_rate: float, *, day_key: str | None = None) -> str:
        normalized = max(0.0, min(1.0, float(misjudgment_rate)))
        threshold = float(settings.AURORA_SRL_MISJUDGMENT_THRESHOLD)
        label = day_key or _utcnow().date().isoformat()
        redis_client = cache_service.redis

        if normalized <= threshold:
            await self._reset_misjudgment_days()
            return await self.get_bridge_mode()

        if redis_client is not None:
            key = f"{self.PREFIX}{self.MISJUDGMENT_STREAK_KEY}"
            raw = await redis_client.get(key)
            values = [item for item in str(raw or "").split(",") if item]
            if label not in values:
                values.append(label)
            values = sorted(values)[-3:]
            await redis_client.set(key, ",".join(values))
            if len(values) >= 3:
                await self.set_bridge_mode("shadow")
                await self.set_scaffolding_consume_mode("shadow")
                return "shadow"
            return await self.get_bridge_mode()

        values = list(getattr(settings, "_aurora_stage29_misjudgment_days", []))
        if label not in values:
            values.append(label)
        settings._aurora_stage29_misjudgment_days = sorted(values)[-3:]
        if len(settings._aurora_stage29_misjudgment_days) >= 3:
            await self.set_bridge_mode("shadow")
            await self.set_scaffolding_consume_mode("shadow")
            return "shadow"
        return await self.get_bridge_mode()

    async def _reset_lag_points(self) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.LAG_STREAK_KEY}")
            return
        settings._aurora_stage29_lag_points = []

    async def _reset_misjudgment_days(self) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.MISJUDGMENT_STREAK_KEY}")
            return
        settings._aurora_stage29_misjudgment_days = []
