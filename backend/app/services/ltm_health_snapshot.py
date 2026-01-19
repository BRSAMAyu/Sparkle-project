from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import CONTEXT_PACK_BUILD, CONTEXT_PACK_OVER_BUDGET
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory, MemoryCorrection
from app.services.memory_jobs import MemoryJobsService


class LtmHealthSnapshotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_snapshot(self) -> Dict[str, Any]:
        evidence_missing_rate = {}
        avg_evidence_score = {}
        avg_correction_count = {}

        for model, kind in (
            (MemoryPreference, "preference"),
            (MemoryGoal, "goal"),
            (EpisodicMemory, "episodic"),
        ):
            total = await self._count(model)
            missing = await self._count(model, missing_only=True)
            evidence_missing_rate[kind] = (missing / total) if total else 0.0
            avg_evidence_score[kind] = await self._avg(model, "evidence_score")
            avg_correction_count[kind] = await self._avg(model, "correction_count")

        pack_build_count = self._metric_total(CONTEXT_PACK_BUILD)
        over_budget_total = self._metric_total(CONTEXT_PACK_OVER_BUDGET)
        over_budget_rate = (over_budget_total / pack_build_count) if pack_build_count else 0.0

        top_corrected = await self._top_corrected_items()
        job_runs = self._job_runs_summary()

        return {
            "evidence_missing_rate": evidence_missing_rate,
            "avg_evidence_score": avg_evidence_score,
            "avg_correction_count": avg_correction_count,
            "pack_build_count": pack_build_count,
            "pack_over_budget_rate": over_budget_rate,
            "top_corrected": top_corrected,
            "job_runs_24h": job_runs,
        }

    async def _count(self, model, missing_only: bool = False) -> int:
        conditions = [model.deleted_at.is_(None)]
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        if missing_only:
            conditions.append(model.evidence_missing.is_(True))
        result = await self.db.execute(select(func.count(model.id)).where(*conditions))
        return result.scalar() or 0

    async def _avg(self, model, column: str) -> float:
        conditions = [model.deleted_at.is_(None)]
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        col = getattr(model, column)
        result = await self.db.execute(select(func.avg(col)).where(*conditions))
        value = result.scalar()
        return float(value or 0.0)

    def _metric_total(self, metric) -> float:
        total = 0.0
        for metric_obj in metric._metrics.values():  # type: ignore[attr-defined]
            total += metric_obj._value.get()  # type: ignore[attr-defined]
        return total

    async def _top_corrected_items(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(
                MemoryCorrection.memory_type,
                MemoryCorrection.memory_id,
                func.count(MemoryCorrection.id).label("count"),
            )
            .group_by(MemoryCorrection.memory_type, MemoryCorrection.memory_id)
            .order_by(func.count(MemoryCorrection.id).desc())
            .limit(5)
        )
        rows = result.all()
        items: List[Dict[str, Any]] = []
        for memory_type, memory_id, count in rows:
            reasons_result = await self.db.execute(
                select(
                    MemoryCorrection.reason,
                    func.count(MemoryCorrection.id),
                )
                .where(
                    MemoryCorrection.memory_type == memory_type,
                    MemoryCorrection.memory_id == memory_id,
                )
                .group_by(MemoryCorrection.reason)
            )
            reasons = {
                reason or "unknown": reason_count for reason, reason_count in reasons_result.all()
            }
            items.append(
                {
                    "memory_type": memory_type,
                    "memory_id": str(memory_id),
                    "count": int(count),
                    "reasons": reasons,
                }
            )
        return items

    def _job_runs_summary(self) -> Dict[str, int]:
        history = MemoryJobsService.get_history()
        cutoff = datetime.utcnow() - timedelta(hours=24)
        summary = {"ok": 0, "error": 0, "disabled": 0}
        for entries in history.values():
            for entry in entries:
                timestamp = entry.get("updated_at")
                if isinstance(timestamp, datetime) and timestamp >= cutoff:
                    status = entry.get("status")
                    if status in summary:
                        summary[status] += 1
                    else:
                        summary["error"] += 1
        return summary
