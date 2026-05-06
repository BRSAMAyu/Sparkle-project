import json
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.achievement import StreakDayStatus, UserStreakDay, UserStreakStats
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.services.streak_quality import StreakQualityService


@pytest.mark.asyncio
async def test_compute_quality_counts_real_learning_signals(db_session, test_user):
    target_day = date(2026, 5, 2)
    node = KnowledgeNode(name="Derivatives")
    db_session.add(node)
    await db_session.flush()

    db_session.add_all(
        [
            UserStreakStats(
                user_id=test_user.id,
                current_streak=5,
                max_streak=5,
                longest_streak=5,
                total_checkin_days=8,
            ),
            StudyRecord(
                user_id=test_user.id,
                node_id=node.id,
                study_minutes=70,
                mastery_delta=0.2,
                created_at=datetime(2026, 5, 2, 9, 0),
            ),
            Task(
                user_id=test_user.id,
                title="Core calculus drill",
                type=TaskType.TRAINING,
                estimated_minutes=45,
                difficulty=4,
                priority=3,
                due_date=target_day,
                status=TaskStatus.COMPLETED,
                completed_at=datetime(2026, 5, 2, 10, 0),
            ),
            Task(
                user_id=test_user.id,
                title="Light reading",
                type=TaskType.LEARNING,
                estimated_minutes=15,
                difficulty=1,
                priority=0,
                due_date=target_day,
                status=TaskStatus.PENDING,
            ),
            UserStreakDay(
                user_id=test_user.id,
                day=target_day - timedelta(days=1),
                status=StreakDayStatus.MISSED,
            ),
            UserStreakDay(
                user_id=test_user.id,
                day=target_day,
                status=StreakDayStatus.ACTIVE,
            ),
        ]
    )
    await db_session.commit()

    quality = await StreakQualityService(db_session).compute_quality(test_user.id, target_day)

    assert quality.effective_minutes == 70
    assert quality.core_tasks_completed == 1
    assert quality.difficult_breakthroughs == 2
    assert quality.plan_consistency == 0.5
    assert quality.recovery_score == 0.5
    assert quality.is_quality_day is True


@pytest.mark.asyncio
async def test_build_payload_includes_quality_trend_and_evidence(db_session, test_user):
    today = datetime.utcnow().date()
    node = KnowledgeNode(name="Vectors")
    db_session.add(node)
    await db_session.flush()
    db_session.add_all(
        [
            UserStreakStats(user_id=test_user.id, current_streak=1, max_streak=1),
            StudyRecord(
                user_id=test_user.id,
                node_id=node.id,
                study_minutes=95,
                mastery_delta=0.2,
                created_at=datetime.combine(today, datetime.min.time()),
            ),
            UserStreakDay(user_id=test_user.id, day=today, status=StreakDayStatus.ACTIVE),
        ]
    )
    await db_session.commit()

    payload = await StreakQualityService(db_session).build_payload(test_user.id)

    assert payload["current_streak"] == 1
    assert payload["quality_streak"] == 1
    assert len(payload["weekly_quality_trend"]) == 7
    assert payload["today_quality"]["is_quality_day"] is True
    assert payload["celebration_trigger"]["evidence"]


def _make_service_with_base_quality(
    effective_minutes=90,
    core_tasks=2,
    breakthroughs=1,
    plan_consistency=1.0,
    recovery=0.5,
):
    """Create StreakQualityService with mocked DB returning known base metrics.

    Base quality = 90/90*0.32 + 2/2*0.26 + 1/1*0.20 + 1.0*0.14 + 0.5*0.08
                 = 0.32 + 0.26 + 0.20 + 0.14 + 0.04 = 0.96
    """
    db = AsyncMock()
    service = StreakQualityService(db)
    service._effective_minutes = AsyncMock(return_value=effective_minutes)
    service._core_tasks_completed = AsyncMock(return_value=core_tasks)
    service._difficult_breakthroughs = AsyncMock(return_value=breakthroughs)
    service._plan_consistency = AsyncMock(return_value=plan_consistency)
    service._recovery_score = AsyncMock(return_value=recovery)
    return service


def _patch_cache(fatigue_json=None, crisis_json=None):
    """Patch cache_service.get to return specific fatigue/crisis data."""
    responses = {}

    if fatigue_json is not None:
        responses["fatigue"] = json.dumps(fatigue_json)
    if crisis_json is not None:
        responses["crisis"] = json.dumps(crisis_json)

    async def _get(key: str):
        if "fatigue" in key and "fatigue" in responses:
            return responses["fatigue"]
        if "crisis" in key and "crisis" in responses:
            return responses["crisis"]
        return None

    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(side_effect=_get)
    return patch("app.core.cache.cache_service", mock_cache)


class TestFatiguePenaltyIntegration:
    """Tests for fatigue/crisis penalty logic in compute_quality (QA-P1-20)."""

    @pytest.mark.asyncio
    async def test_no_fatigue_no_penalty(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "low", "evidence": []}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96, abs=0.01)

    @pytest.mark.asyncio
    async def test_critical_fatigue_zeroes_quality(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "critical", "evidence": ["high stress"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score == 0.0
        assert result.is_quality_day is False

    @pytest.mark.asyncio
    async def test_high_fatigue_penalty(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "high", "evidence": ["repeated help-seeking"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96 - 0.20, abs=0.01)

    @pytest.mark.asyncio
    async def test_high_fatigue_late_night_cap(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "high", "evidence": ["深夜学习", "repeated"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score <= 0.55

    @pytest.mark.asyncio
    async def test_medium_fatigue_penalty(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "medium", "evidence": ["declining accuracy"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96 - 0.10, abs=0.01)

    @pytest.mark.asyncio
    async def test_medium_fatigue_late_night_cap(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "medium", "evidence": ["深夜学习"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score <= 0.65

    @pytest.mark.asyncio
    async def test_late_night_only_cap(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "low", "evidence": ["深夜学习"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.quality_score <= 0.75

    @pytest.mark.asyncio
    async def test_crisis_active_penalty(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "low", "evidence": []}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=True):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96 - 0.10, abs=0.01)

    @pytest.mark.asyncio
    async def test_crisis_stacks_on_fatigue(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "high", "evidence": ["repeated"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=True):
            result = await service.compute_quality("user-1")
        expected = 0.96 - 0.20 - 0.10
        assert result.quality_score == pytest.approx(expected, abs=0.01)

    @pytest.mark.asyncio
    async def test_redis_failure_defaults_low_fatigue(self):
        service = _make_service_with_base_quality()
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=Exception("redis connection refused"))
        with patch("app.core.cache.cache_service", mock_cache):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96, abs=0.01)

    @pytest.mark.asyncio
    async def test_redis_failure_defaults_no_crisis(self):
        service = _make_service_with_base_quality()
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=Exception("redis down"))
        with patch("app.core.cache.cache_service", mock_cache):
            result = await service.compute_quality("user-1")
        assert result.quality_score == pytest.approx(0.96, abs=0.01)

    @pytest.mark.asyncio
    async def test_fatigue_cache_avoids_duplicate_redis_calls(self):
        service = _make_service_with_base_quality()
        fatigue_data = {"fatigue_level": "high", "evidence": []}
        call_count = 0

        async def _get(key: str):
            nonlocal call_count
            call_count += 1
            if "fatigue" in key:
                return json.dumps(fatigue_data)
            return None

        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=_get)
        with patch("app.core.cache.cache_service", mock_cache):
            await service.compute_quality("user-1")
            await service.compute_quality("user-1")
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fatigue_drops_below_quality_day_threshold(self):
        service = _make_service_with_base_quality(
            effective_minutes=25, core_tasks=0, breakthroughs=0,
            plan_consistency=0.0, recovery=0.0,
        )
        fatigue_data = {"fatigue_level": "high", "evidence": ["repeated"]}
        with _patch_cache(fatigue_json=fatigue_data, crisis_json=False):
            result = await service.compute_quality("user-1")
        assert result.is_quality_day is False
