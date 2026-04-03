from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.weekly_digest_service import WeeklyDigestService


@pytest.mark.asyncio
async def test_generate_for_user_builds_digest_and_hands_off_artifact_and_delivery() -> None:
    db = AsyncMock()
    service = WeeklyDigestService(db, redis=None)
    user_id = uuid4()
    plan_card_id = uuid4()
    artifact_id = uuid4()

    service._already_generated = AsyncMock(return_value=False)
    service._mark_generated = AsyncMock()
    service._get_user = AsyncMock(
        return_value=User(
            id=user_id,
            username="ava",
            email="ava@example.com",
            hashed_password="hashed",
            nickname="Ava",
        )
    )
    service.growth_dashboard_service.build_snapshot = AsyncMock(
        return_value={
            "growth_status": {"headline": "Ava，你本周在热力学上进步了 22%"},
            "growth_signal": {
                "topic": "热力学",
                "summary": "热力学掌握度从 0.38 提升到 0.61",
                "delta_points": 22.0,
            },
            "active_plan_progress": {"plan_name": "热力学冲刺", "phase_name": "第二章复盘"},
        }
    )
    service.weekly_report_service.build_weekly_report = AsyncMock(
        return_value={
            "weekly_summary": "你在热力学第二章上的卡点明显松动了。",
            "one_key_adjustment": "我会继续把高难任务前移到上午。",
            "top_learning_items": [{"text": "热力学第二章复盘更稳了"}],
        }
    )
    service.stats_service.get_weekly_summary = AsyncMock(
        return_value={
            "tasks_completed": 8,
            "focus_duration_minutes": 210,
            "active_days": 5,
            "mastery_gain": 23.5,
            "nodes_learned": 3,
        }
    )
    service._recent_patterns = AsyncMock(
        return_value=[SimpleNamespace(pattern_name="拖延临近截止日", confidence_score=0.81)]
    )
    service._upcoming_tasks = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "title": "完成热力学第二章题组"},
            {"id": str(uuid4()), "title": "整理可逆过程错题"},
        ]
    )
    service._resolve_active_plan_card = AsyncMock(return_value=SimpleNamespace(id=plan_card_id))
    service._store_artifact = AsyncMock(return_value=SimpleNamespace(id=artifact_id))
    service._deliver_and_mark_artifact = AsyncMock()
    service._mark_delivered = AsyncMock()

    digest = await service.generate_for_user(user_id=user_id, deliver=True)

    assert digest is not None
    assert digest["digest_kind"] == "weekly_growth_digest"
    assert digest["headline"] == "Ava，你本周在热力学上进步了 22%"
    assert digest["summary"] == "你在热力学第二章上的卡点明显松动了。"
    assert digest["what_you_did"] == ["完成了 8 个任务", "累计专注 210 分钟", "活跃了 5 天"]
    assert "热力学掌握度从 0.38 提升到 0.61" in digest["what_moved"]
    assert "累计掌握度提升约 23.5，覆盖 3 个知识点。" in digest["what_moved"]
    assert digest["system_noticed"] == [
        "你最近更容易出现「拖延临近截止日」模式，我会继续按这个规律调整建议。",
        "我会继续把高难任务前移到上午。",
    ]
    assert digest["whats_coming"] == ["完成热力学第二章题组", "整理可逆过程错题"]
    assert digest["artifact_id"] == str(artifact_id)
    assert digest["delivery_scheduled_for"].endswith("08:00:00")
    service._store_artifact.assert_awaited_once_with(plan_card_id, digest)
    service._deliver_and_mark_artifact.assert_awaited_once_with(
        user_id=user_id,
        digest=digest,
        artifact=service._store_artifact.return_value,
    )
    service._mark_delivered.assert_awaited_once_with(user_id)
    service._mark_generated.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_generate_for_user_skips_when_no_meaningful_summary_exists() -> None:
    db = AsyncMock()
    service = WeeklyDigestService(db, redis=None)
    user_id = uuid4()

    service._already_generated = AsyncMock(return_value=False)
    service._mark_generated = AsyncMock()
    service._get_user = AsyncMock(
        return_value=User(
            id=user_id,
            username="ava",
            email="ava@example.com",
            hashed_password="hashed",
        )
    )
    service.growth_dashboard_service.build_snapshot = AsyncMock(return_value={})
    service.weekly_report_service.build_weekly_report = AsyncMock(return_value=None)
    service.stats_service.get_weekly_summary = AsyncMock(return_value={})
    service._recent_patterns = AsyncMock(return_value=[])
    service._upcoming_tasks = AsyncMock(return_value=[])
    service._resolve_active_plan_card = AsyncMock()
    service._store_artifact = AsyncMock()
    service._deliver_and_mark_artifact = AsyncMock()
    service._mark_delivered = AsyncMock()

    digest = await service.generate_for_user(user_id=user_id, deliver=True)

    assert digest is None
    service._resolve_active_plan_card.assert_not_called()
    service._store_artifact.assert_not_called()
    service._deliver_and_mark_artifact.assert_not_called()
    service._mark_delivered.assert_not_called()
    service._mark_generated.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_pending_for_user_delivers_latest_stored_digest_once() -> None:
    db = AsyncMock()
    service = WeeklyDigestService(db, redis=None)
    user_id = uuid4()
    artifact = SimpleNamespace(
        payload={
            "digest_kind": "weekly_growth_digest",
            "headline": "Ava，你本周在热力学上进步了 22%",
            "summary": "你在热力学第二章上的卡点明显松动了。",
        }
    )

    service._already_delivered = AsyncMock(return_value=False)
    service._mark_delivered = AsyncMock()
    service._latest_pending_digest_artifact = AsyncMock(return_value=artifact)
    service._deliver_and_mark_artifact = AsyncMock()

    digest = await service.deliver_pending_for_user(user_id=user_id)

    assert digest is artifact.payload
    service._deliver_and_mark_artifact.assert_awaited_once_with(
        user_id=user_id,
        digest=artifact.payload,
        artifact=artifact,
    )
    service._mark_delivered.assert_awaited_once_with(user_id)
