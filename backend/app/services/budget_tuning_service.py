from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_pack import ContextBudgetProfile

BUCKETS = ["preferences", "goals", "episodic"]
MIN_MULTIPLIER = 0.7
MAX_MULTIPLIER = 1.3
TARGET_SUM = 3.0
DECAY_DAILY = 0.98
STEP = 0.05


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BudgetTuningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_multipliers(self, intent: str) -> dict[str, float]:
        profiles = await self._load_profiles(intent)
        await self._apply_decay(profiles)
        multipliers = dict.fromkeys(BUCKETS, 1.0)
        for profile in profiles.values():
            multipliers[profile.bucket] = profile.multiplier
        return multipliers

    async def apply_feedback(self, intent: str, reasons: Iterable[str], score: float) -> dict[str, float]:
        multipliers = await self.get_multipliers(intent)
        adjusted = self._apply_reason_adjustments(multipliers, reasons, score)
        normalized = self._normalize(adjusted)

        now = _utcnow()
        profiles = await self._load_profiles(intent)
        for bucket, value in normalized.items():
            profile = profiles.get(bucket)
            if profile is None:
                profile = ContextBudgetProfile(intent=intent, bucket=bucket, multiplier=value)
                self.db.add(profile)
            else:
                profile.multiplier = value
            profile.updated_at = now

        await self.db.commit()
        return normalized

    async def reset_profiles(self, intent: str) -> dict[str, float]:
        profiles = await self._load_profiles(intent)
        now = _utcnow()
        for bucket in BUCKETS:
            profile = profiles.get(bucket)
            if profile is None:
                profile = ContextBudgetProfile(intent=intent, bucket=bucket, multiplier=1.0)
                self.db.add(profile)
            else:
                profile.multiplier = 1.0
            profile.updated_at = now
        await self.db.commit()
        return dict.fromkeys(BUCKETS, 1.0)

    async def _load_profiles(self, intent: str) -> dict[str, ContextBudgetProfile]:
        result = await self.db.execute(
            select(ContextBudgetProfile).where(
                ContextBudgetProfile.intent == intent,
                ContextBudgetProfile.deleted_at.is_(None),
            )
        )
        profiles = result.scalars().all()
        return {profile.bucket: profile for profile in profiles}

    async def _apply_decay(self, profiles: dict[str, ContextBudgetProfile]) -> None:
        if not profiles:
            return
        now = _utcnow()
        updated = False
        for profile in profiles.values():
            if not profile.updated_at:
                continue
            days = (now - profile.updated_at).days
            if days <= 0:
                continue
            factor = DECAY_DAILY ** days
            decayed = 1.0 + (profile.multiplier - 1.0) * factor
            decayed = self._clamp(decayed)
            if abs(decayed - profile.multiplier) > 1e-6:
                profile.multiplier = decayed
                profile.updated_at = now
                updated = True
        if updated:
            await self.db.commit()

    def _apply_reason_adjustments(
        self,
        multipliers: dict[str, float],
        reasons: Iterable[str],
        score: float,
    ) -> dict[str, float]:
        adjusted = dict(multipliers)
        reason_set = {reason.lower() for reason in reasons if reason}
        if "verbose" in reason_set:
            adjusted["goals"] -= STEP
            adjusted["episodic"] -= STEP
        if "incomplete" in reason_set:
            adjusted["goals"] += STEP
            adjusted["episodic"] += STEP
        if "misaligned" in reason_set:
            adjusted["preferences"] -= STEP
        if score < 0:
            adjusted["preferences"] -= 0.01
        return adjusted

    def _normalize(self, multipliers: dict[str, float]) -> dict[str, float]:
        values = dict(multipliers)
        for _ in range(2):
            total = sum(values.values())
            if total <= 0:
                values = dict.fromkeys(BUCKETS, 1.0)
                total = TARGET_SUM
            scale = TARGET_SUM / total
            for bucket in values:
                values[bucket] = values[bucket] * scale
            values = {bucket: self._clamp(values[bucket]) for bucket in values}

            fixed = {bucket for bucket in values if values[bucket] in (MIN_MULTIPLIER, MAX_MULTIPLIER)}
            remaining = [bucket for bucket in values if bucket not in fixed]
            if not remaining:
                break
            fixed_sum = sum(values[bucket] for bucket in fixed)
            remaining_sum = sum(values[bucket] for bucket in remaining)
            if remaining_sum <= 0:
                break
            scale = (TARGET_SUM - fixed_sum) / remaining_sum
            for bucket in remaining:
                values[bucket] = self._clamp(values[bucket] * scale)
        return values

    def _clamp(self, value: float) -> float:
        if value < MIN_MULTIPLIER:
            return MIN_MULTIPLIER
        if value > MAX_MULTIPLIER:
            return MAX_MULTIPLIER
        return value
