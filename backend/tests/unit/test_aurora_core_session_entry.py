import json
from datetime import UTC, datetime, timedelta

import pytest

from app.aurora.core_session import AuroraCoreSessionService
from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot  # noqa: F401
from app.signals.aurora_core_session import AuroraCoreSessionEntryReason


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def delete(self, key: str) -> int:
        self.data.pop(key, None)
        return 1


@pytest.mark.asyncio
async def test_core_session_opening_uses_entry_reason_three_elements() -> None:
    service = AuroraCoreSessionService(FakeRedis())
    entry_reason = AuroraCoreSessionEntryReason(
        trigger_source="status_bar",
        observed_signals=["两张任务卡都超时", "计划偏离目标"],
        suggested_agenda_preview=["确认观察", "校准策略"],
        why_now="继续推进前需要先校准任务颗粒度",
        estimated_minutes=4,
    )

    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        band_status="risk_found",
        wake_reasons=["task_time_overrun"],
        entry_reason=entry_reason,
    )

    opening = session.messages[0].content
    assert "我注意到" in opening
    assert "两张任务卡都超时" in opening
    assert "现在聊这个是因为继续推进前需要先校准任务颗粒度" in opening
    assert "这大概需要 4 分钟" in opening
    assert session.entry_reason["trigger_source"] == "status_bar"


@pytest.mark.asyncio
async def test_core_session_pause_resume_with_resume_token() -> None:
    redis = FakeRedis()
    service = AuroraCoreSessionService(redis)
    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )

    paused = await service.pause_session(user_id="u1", session_id=session.session_id)
    assert paused.status == "paused"
    assert paused.resume_token
    assert paused.resume_token != session.session_id

    active_pointer = await redis.get("aurora:core_session:active:u1")
    assert active_pointer is None
    current_pointer = await redis.get("aurora:core_session:current:u1")
    assert current_pointer == session.session_id

    resumed = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        resume_token=paused.resume_token,
    )
    assert resumed.session_id == session.session_id
    assert resumed.status == "active"
    assert resumed.resume_token != paused.resume_token
    assert any("从刚才暂停的地方继续" in message.content for message in resumed.messages)


@pytest.mark.asyncio
async def test_core_session_resume_token_rotates_after_user_interaction() -> None:
    service = AuroraCoreSessionService(FakeRedis())
    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )
    original_token = session.resume_token

    updated = await service.respond(
        user_id="u1",
        session_id=session.session_id,
        content="是的",
        semantic_value="confirmed",
    )

    assert updated.resume_token
    assert updated.resume_token != original_token
    assert await service.store.load_by_resume_token(original_token) is None
    assert (await service.store.load_by_resume_token(updated.resume_token)).session_id == session.session_id


@pytest.mark.asyncio
async def test_core_session_expiry_returns_friendly_summary() -> None:
    service = AuroraCoreSessionService(FakeRedis())
    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )
    session.add_user_message("我先去处理别的。", is_freeform=True)
    session.last_activity_at = (datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=30)).isoformat()
    session.expires_at = (datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)).isoformat()
    await service.store.save(session)

    current = await service.get_current_session("u1")

    assert current is not None
    assert current.status == "expired"
    assert current.resume_token == ""
    assert current.calibration_result is not None
    assert "上次" in current.calibration_result.user_visible_summary
    assert "深度对话已结束" in current.messages[-1].content


@pytest.mark.asyncio
async def test_core_session_freeform_correction_closure_has_visible_result() -> None:
    service = AuroraCoreSessionService(FakeRedis())
    session = await service.start_session(
        user_id="u1",
        conversation_id="c1",
        band_status="needs_confirm",
        wake_reasons=["standard_layer_uncertainty"],
    )

    updated = await service.respond(
        user_id="u1",
        session_id=session.session_id,
        content="不是任务太大，是我还不会 TCP 滑动窗口。",
        semantic_value="freeform_correction",
        is_freeform=True,
    )
    assert updated.status == "active"
    assert updated.messages[-1].is_freeform is False

    closed = await service.close_session(user_id="u1", session_id=session.session_id)
    result = closed.calibration_result
    assert result is not None
    payload = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert payload["user_visible_summary"]
    assert payload["state_patches"]
    assert payload["next_changes"]
    assert any(patch["state_key"] == "aurora_assumption" for patch in payload["state_patches"])


@pytest.mark.asyncio
async def test_core_session_loads_from_postgres_when_redis_misses(db_session) -> None:
    redis = FakeRedis()
    service = AuroraCoreSessionService(redis, db=db_session)
    session = await service.start_session(
        user_id="u-pg",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )
    await service.respond(
        user_id="u-pg",
        session_id=session.session_id,
        content="是的，计划偏了",
        semantic_value="confirmed",
    )
    resume_token = (await service.get_session(session.session_id)).resume_token
    redis.data.clear()

    restored = await AuroraCoreSessionService(redis, db=db_session).resume_session(
        user_id="u-pg",
        resume_token=resume_token,
    )

    assert restored.session_id == session.session_id
    assert restored.status == "active"
    assert any(message.content == "是的，计划偏了" for message in restored.messages)
    assert await redis.get(f"aurora:core_session:{session.session_id}") is not None


@pytest.mark.asyncio
async def test_core_session_idle_timeout_pauses_instead_of_expiring(db_session) -> None:
    service = AuroraCoreSessionService(FakeRedis(), db=db_session)
    session = await service.start_session(
        user_id="u-idle",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )
    session.last_activity_at = (datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=11)).isoformat()
    await service.store.save(session)

    current = await service.get_current_session("u-idle")

    assert current is not None
    assert current.status == "paused"
    assert current.resume_token
    assert current.calibration_result is None
    assert "暂停在这里" in current.messages[-1].content


@pytest.mark.asyncio
async def test_core_session_respond_after_idle_pause_keeps_user_turn(db_session) -> None:
    service = AuroraCoreSessionService(FakeRedis(), db=db_session)
    session = await service.start_session(
        user_id="u-idle-response",
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )
    session.last_activity_at = (datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=11)).isoformat()
    await service.store.save(session)
    paused = await service.get_current_session("u-idle-response")

    updated = await service.respond(
        user_id="u-idle-response",
        session_id=paused.session_id,
        content="继续，刚刚说到计划偏了。",
        semantic_value="confirmed",
    )

    assert updated.status == "active"
    assert any(message.role == "user" and "继续" in message.content for message in updated.messages)
    assert updated.user_turn_count == 1
