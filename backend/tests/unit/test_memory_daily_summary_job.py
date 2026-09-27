from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.ltm_daily_snapshot import LtmDailySnapshot
from app.models.user import User
from app.services.memory_jobs import MemoryJobsService

# wt611 时钟加固（V3-FIX-321 批一）：job 模块钟与校验口径一并冻结至
# 2026-09-25 20:00 naive UTC（上海本地 09-26 04:00）——消 job 写入与断言
# 读取跨越 UTC 午夜的竞态窗；断言语义零改动（snapshot_date == 冻结今日）。
FROZEN_UTC_NOW = datetime(2026, 9, 25, 20, 0)
FROZEN_TODAY = date(2026, 9, 25)


@pytest.fixture(autouse=True)
def _freeze_memory_jobs_clock(monkeypatch):
    monkeypatch.setattr(
        "app.services.memory_jobs._utcnow",
        lambda: FROZEN_UTC_NOW,
        raising=False,
    )


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

    today = FROZEN_TODAY
    result = await db_session.execute(
        select(LtmDailySnapshot).where(LtmDailySnapshot.snapshot_date == today)
    )
    snapshot = result.scalar_one_or_none()
    assert snapshot is not None
    assert snapshot.snapshot_date == today
