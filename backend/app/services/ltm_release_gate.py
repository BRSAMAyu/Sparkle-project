from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import LTM_EVAL_AVG_SCORE, LTM_EVAL_TOTAL
from app.core.context_budget import DEFAULT_BUDGETS
from app.models.context_pack import ContextBudgetProfile
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.services.memory_jobs import MemoryJobsService


@dataclass
class ReleaseGateResult:
    ok: bool
    reasons: list[str]
    metrics: dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LtmReleaseGate:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check(self) -> ReleaseGateResult:
        reasons: list[str] = []
        metrics: dict[str, Any] = {}

        evidence_missing_rate = await self._evidence_missing_rate()
        metrics["evidence_missing_rate"] = evidence_missing_rate
        if evidence_missing_rate is None:
            reasons.append("evidence_missing_rate_unavailable")
        elif evidence_missing_rate > settings.LTM_RELEASE_EVIDENCE_MISSING_THRESHOLD:
            reasons.append("evidence_missing_rate_exceeds_threshold")

        eval_score = self._get_eval_score()
        metrics["ltm_eval_score"] = eval_score
        if eval_score is None:
            reasons.append("ltm_eval_score_unavailable")
        elif eval_score < settings.LTM_RELEASE_EVAL_THRESHOLD:
            reasons.append("ltm_eval_below_threshold")

        job_ratio = self._job_success_ratio()
        metrics["job_success_ratio_24h"] = job_ratio
        if job_ratio is None:
            reasons.append("memory_job_success_ratio_unavailable")
        elif job_ratio < settings.LTM_RELEASE_JOB_SUCCESS_THRESHOLD:
            reasons.append("memory_job_success_ratio_below_threshold")

        multiplier_status = await self._budget_multipliers_within_bounds()
        metrics["budget_multipliers_ok"] = multiplier_status["ok"]
        metrics["budget_multipliers"] = multiplier_status["details"]
        if not multiplier_status["ok"]:
            reasons.append("budget_multipliers_out_of_bounds")

        return ReleaseGateResult(ok=not reasons, reasons=reasons, metrics=metrics)

    async def _evidence_missing_rate(self) -> float | None:
        totals = 0
        missing = 0
        for model in (MemoryPreference, MemoryGoal, EpisodicMemory):
            result_total = await self.db.execute(
                select(func.count(model.id)).where(model.deleted_at.is_(None))
            )
            total = result_total.scalar() or 0
            totals += total
            result_missing = await self.db.execute(
                select(func.count(model.id)).where(
                    model.deleted_at.is_(None),
                    model.evidence_missing.is_(True),
                )
            )
            missing += result_missing.scalar() or 0
        if totals == 0:
            return None
        return missing / totals

    def _get_eval_score(self) -> float | None:
        if not self._has_eval_runs():
            return None
        try:
            return float(LTM_EVAL_AVG_SCORE._value.get())  # type: ignore[attr-defined]
        except Exception:
            return None

    def _has_eval_runs(self) -> bool:
        try:
            total = 0.0
            for metric in LTM_EVAL_TOTAL._metrics.values():  # type: ignore[attr-defined]
                total += metric._value.get()  # type: ignore[attr-defined]
            return total > 0
        except Exception:
            return False

    def _job_success_ratio(self) -> float | None:
        history = MemoryJobsService.get_history()
        cutoff = _utcnow() - timedelta(hours=24)
        total = 0
        ok = 0
        for entries in history.values():
            for entry in entries:
                timestamp = entry.get("updated_at")
                if isinstance(timestamp, datetime) and timestamp >= cutoff:
                    total += 1
                    if entry.get("status") == "ok":
                        ok += 1
        if total == 0:
            return None
        return ok / total

    async def _budget_multipliers_within_bounds(self) -> dict[str, Any]:
        lower = settings.LTM_RELEASE_BUDGET_MULTIPLIER_MIN
        upper = settings.LTM_RELEASE_BUDGET_MULTIPLIER_MAX
        details: dict[str, dict[str, float]] = {}
        if not settings.ENABLE_BUDGET_TUNING:
            return {"ok": True, "details": details}

        result = await self.db.execute(select(ContextBudgetProfile))
        profiles = result.scalars().all()
        for profile in profiles:
            details.setdefault(profile.intent, {})[profile.bucket] = profile.multiplier

        ok = True
        for intent in DEFAULT_BUDGETS:
            buckets = details.get(intent, {})
            for bucket in DEFAULT_BUDGETS[intent]:
                value = buckets.get(bucket, 1.0)
                if value < lower or value > upper:
                    ok = False
        return {"ok": ok, "details": details}
