from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation_run import SimulationRun
from app.services.simulation.simulation_state import LearningSimulationState


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed


class SimulationRunStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def persist_payload(self, *, user_id: UUID, payload: dict[str, Any]) -> SimulationRun:
        session_id = str(payload.get("id") or "").strip()
        if not session_id:
            raise ValueError("simulation session payload missing id")
        result = await self.db.execute(
            select(SimulationRun).where(
                SimulationRun.session_id == session_id,
                SimulationRun.user_id == user_id,
                SimulationRun.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = SimulationRun(session_id=session_id, user_id=user_id)

        record.scenario_key = str(payload.get("scenario_key") or "study_group")
        record.topic = str(payload.get("topic") or "学习讨论")
        record.state = str(payload.get("state") or LearningSimulationState.COMPLETED.value)
        record.payload = dict(payload)
        record.insight_summary = str(payload.get("insight_summary") or "")
        record.last_active_at = _parse_dt(payload.get("last_active_at"))
        if record.state == LearningSimulationState.COMPLETED.value:
            record.completed_at = record.last_active_at or record.completed_at

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def load_payload(self, *, session_id: str, user_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(SimulationRun.payload).where(
                SimulationRun.session_id == session_id,
                SimulationRun.user_id == user_id,
                SimulationRun.deleted_at.is_(None),
            )
        )
        payload = result.scalar_one_or_none()
        return dict(payload) if isinstance(payload, dict) else None
