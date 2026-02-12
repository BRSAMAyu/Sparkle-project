from datetime import UTC, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest

from app.config import settings
from sqlalchemy import select

from app.models.ltm_daily_snapshot import LtmDailySnapshot
from app.models.user import User
from app.services.memory_jobs import MemoryJobsService


@pytest.mark.asyncio
async def test_daily_summary_job_writes_snapshot(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_DAILY_SUMMARY", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = MemoryJobsService(db_session)
    result = await service.run_daily_summary_job()
    assert result["status"] == "ok"

    today = _utcnow().date()
    result = await db_session.execute(
        select(LtmDailySnapshot).where(LtmDailySnapshot.snapshot_date == today)
    )
    snapshot = result.scalar_one_or_none()
    assert snapshot is not None
    assert snapshot.snapshot_date == today
