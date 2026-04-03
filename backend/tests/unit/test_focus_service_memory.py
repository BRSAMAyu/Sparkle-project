from datetime import timezone, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.focus_service import FocusService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_focus_service_writes_episodic_memory_for_completed_session(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    publish = AsyncMock()
    collect = AsyncMock()
    create_memory = AsyncMock()

    monkeypatch.setattr("app.services.focus_service.event_bus.publish", publish)
    monkeypatch.setattr(
        "app.services.focus_service.AutoFragmentCollector.collect_from_focus_session",
        collect,
    )
    monkeypatch.setattr(
        "app.services.focus_service.MemoryService.create_episodic_memory",
        create_memory,
    )

    end_time = _utcnow()
    start_time = end_time - timedelta(minutes=30)

    result = await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=None,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=30,
    )

    assert result["session_id"]
    create_memory.assert_awaited_once()
    kwargs = create_memory.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["source_type"] == "focus_session"
    assert "30 分钟专注" in kwargs["summary"]
