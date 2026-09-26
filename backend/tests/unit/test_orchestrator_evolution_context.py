from datetime import timezone, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.chat import ChatSession
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.orchestration.orchestrator import ChatOrchestrator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}

    async def exists(self, key: str) -> int:
        return 1 if key in self.values else 0

    async def setex(self, key: str, seconds: int, value: str):
        self.values[key] = value


@pytest.mark.asyncio
async def test_hydrate_evolution_context_backfills_preference_learnings():
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = AsyncMock()

    final_state = SimpleNamespace(context_data={})
    updates = [
        {
            "metadata": {
                "evolution_kind": "preference_learning",
                "preference_learning": {
                    "user_facing_message": "我记住了你更喜欢简洁的回答方式。",
                    "source": "memory_preference",
                },
            }
        },
        {
            "metadata": {
                "evolution_kind": "adaptation_record",
                "adaptation_record": {
                    "user_facing_message": "我发现你最近的任务偏难了，帮你调轻了一些。",
                    "source": "adaptive_replanner",
                },
            }
        },
    ]

    with patch(
        "app.orchestration.session_state_mixin.SystemUpdateService.list_updates",
        AsyncMock(return_value=updates),
    ):
        await orchestrator._hydrate_evolution_context(final_state=final_state, user_id="user-1")

    assert final_state.context_data["preference_learnings"][0]["user_facing_message"] == "我记住了你更喜欢简洁的回答方式。"
    assert final_state.context_data["adaptation_records"][0]["source"] == "adaptive_replanner"


@pytest.mark.asyncio
async def test_hydrate_evolution_context_backfills_highlights():
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = AsyncMock()

    final_state = SimpleNamespace(context_data={})
    updates = [
        {
            "metadata": {
                "evolution_kind": "highlight",
                "highlight": "你刚刚解锁了「冲刺先锋」。",
            }
        }
    ]

    with patch(
        "app.orchestration.session_state_mixin.SystemUpdateService.list_updates",
        AsyncMock(return_value=updates),
    ):
        await orchestrator._hydrate_evolution_context(final_state=final_state, user_id="user-1")

    assert final_state.context_data["evolution_highlights"] == ["你刚刚解锁了「冲刺先锋」。"]


@pytest.mark.asyncio
async def test_hydrate_evolution_context_backfills_perceptible_highlights():
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = AsyncMock()

    final_state = SimpleNamespace(context_data={})
    updates = [
        {
            "metadata": {
                "evolution_kind": "proactive_insight",
                "insight_text": "你最近晚间开始学习时，完成率会明显下降。",
            }
        }
    ]

    with patch(
        "app.orchestration.session_state_mixin.SystemUpdateService.list_updates",
        AsyncMock(return_value=updates),
    ):
        await orchestrator._hydrate_evolution_context(final_state=final_state, user_id="user-1")

    assert "你最近晚间开始学习时，完成率会明显下降。" in final_state.context_data["evolution_highlights"]


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_understanding_depth_hint():
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = AsyncMock()

    updates = [
        {
            "description": "我现在不只知道你的偏好，还能更稳定地预判你会怎么执行了。",
            "metadata": {
                "evolution_kind": "understanding_depth",
                "natural_hint": "如果自然，可以顺带一句提到：我现在不只知道你的偏好，还能比较稳定地预判你的执行节奏。",
                "understanding_depth": {"level": "L3", "score": 3},
            },
        }
    ]

    with patch(
        "app.orchestration.session_state_mixin.SystemUpdateService.drain",
        AsyncMock(return_value=updates),
    ):
        _, _, _, highlights, _, understanding_depth_update, _ = await orchestrator._drain_system_updates("user-1")

    assert understanding_depth_update is not None
    assert understanding_depth_update["understanding_depth"]["level"] == "L3"
    assert "自然" in understanding_depth_update["natural_hint"]
    assert any("L3" in item for item in highlights)


@pytest.mark.asyncio
async def test_build_returning_context_includes_last_progress_and_due_tasks(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    session = ChatSession(
        user_id=user_id,
        last_message_at=_utcnow() - timedelta(days=4),
    )
    completed_task = Task(
        id=uuid4(),
        user_id=user_id,
        title="微积分第三章",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        tags=[],
        completed_at=_utcnow() - timedelta(days=5),
    )
    overdue_task = Task(
        id=uuid4(),
        user_id=user_id,
        title="线代复盘",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        difficulty=2,
        energy_cost=2,
        tags=[],
        due_date=_utcnow().date() - timedelta(days=1),
    )
    db_session.add_all([user, session, completed_task, overdue_task])
    await db_session.commit()

    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = FakeRedis()

    payload = await orchestrator._build_returning_context(
        user_id=str(user_id),
        session_id="sess-return",
        db_session=db_session,
    )

    assert payload is not None
    assert payload["overdue_task_count"] == 1
    assert "微积分第三章" in payload["last_progress"]
    assert "线代复盘" in payload["briefing_text"]


@pytest.mark.asyncio
async def test_build_returning_context_overdue_window_uses_user_local_day(db_session, monkeypatch):
    """V3-FIX-207：overdue 窗口切用户本地日（Task.due_date 是墙上钟日界列）。

    冻结 NOW = 2026-09-25 23:30 UTC（上海本地 = 09-26 07:30，沿
    test_today_view_local_date_boundary 冻结钟族）：
    - 上海用户（缺省 tz）：本地今日 = 09-26，due_date=09-26（本地今日到期、
      未完）按窗口 `<=` 语义计入 overdue；修前按 UTC 今日 09-25 切 → 漏计；
    - UTC 用户控制组：本地今日 = 09-25，同钟 due_date=09-26 是「明日」→
      不计入，证边界确由用户时区驱动。
    """
    from datetime import date as _date

    from app.models.user import PushPreference

    now = datetime(2026, 9, 25, 23, 30)  # naive UTC；上海 = 09-26 07:30
    monkeypatch.setattr("app.orchestration.context_builder.utcnow", lambda: now)

    shanghai_user_id = uuid4()
    utc_user_id = uuid4()
    shanghai_user = User(
        id=shanghai_user_id,
        username=f"user_{shanghai_user_id.hex[:8]}",
        email=f"{shanghai_user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    utc_user = User(
        id=utc_user_id,
        username=f"user_{utc_user_id.hex[:8]}",
        email=f"{utc_user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(PushPreference(user_id=utc_user_id, timezone="UTC"))
    session = ChatSession(user_id=shanghai_user_id, last_message_at=now - timedelta(days=4))
    utc_session = ChatSession(user_id=utc_user_id, last_message_at=now - timedelta(days=4))
    due_local_today = Task(
        id=uuid4(),
        user_id=shanghai_user_id,
        title="本地今日到期复盘",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        difficulty=2,
        energy_cost=2,
        tags=[],
        due_date=_date(2026, 9, 26),
    )
    due_local_today_utc = Task(
        id=uuid4(),
        user_id=utc_user_id,
        title="UTC 用户明日到期",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        difficulty=2,
        energy_cost=2,
        tags=[],
        due_date=_date(2026, 9, 26),
    )
    db_session.add_all([shanghai_user, utc_user, session, utc_session, due_local_today, due_local_today_utc])
    await db_session.commit()

    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = FakeRedis()

    shanghai_payload = await orchestrator._build_returning_context(
        user_id=str(shanghai_user_id),
        session_id="sess-return-shanghai",
        db_session=db_session,
    )
    utc_payload = await orchestrator._build_returning_context(
        user_id=str(utc_user_id),
        session_id="sess-return-utc",
        db_session=db_session,
    )

    assert shanghai_payload is not None
    assert shanghai_payload["overdue_task_count"] == 1, (
        f"上海晨间（本地 09-26 07:30）本地今日到期的未完任务应计入 overdue；"
        f"修前按 UTC 今日 09-25 切 → 漏计：{shanghai_payload}"
    )
    assert utc_payload is not None
    assert (
        utc_payload["overdue_task_count"] == 0
    ), f"UTC 用户本地今日=09-25，due_date=09-26 是明日到期，不应计入：{utc_payload}"
