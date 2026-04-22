from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_snapshot import ReportSnapshot


class ReportSnapshotStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def persist_snapshot(
        self,
        *,
        user_id: UUID,
        cache_version: str,
        payload: dict[str, Any],
    ) -> ReportSnapshot:
        report_id = str(payload.get("report_id") or "").strip()
        if not report_id:
            raise ValueError("report payload missing report_id")

        result = await self.db.execute(
            select(ReportSnapshot).where(
                ReportSnapshot.report_id == report_id,
                ReportSnapshot.user_id == user_id,
                ReportSnapshot.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = ReportSnapshot(report_id=report_id, user_id=user_id)

        record.snapshot_type = "learning_report"
        record.cache_version = cache_version
        record.delivery_mode = str(payload.get("delivery_mode") or "")
        record.quality_mode = str(payload.get("quality_mode") or "")
        record.trigger_source = str(payload.get("trigger_source") or "")
        record.payload = dict(payload)

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def load_cached_payload(
        self,
        *,
        user_id: UUID,
        cache_version: str,
    ) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(ReportSnapshot.payload)
            .where(
                ReportSnapshot.user_id == user_id,
                ReportSnapshot.cache_version == cache_version,
                ReportSnapshot.deleted_at.is_(None),
            )
            .order_by(desc(ReportSnapshot.updated_at))
            .limit(1)
        )
        payload = result.scalar_one_or_none()
        return dict(payload) if isinstance(payload, dict) else None
