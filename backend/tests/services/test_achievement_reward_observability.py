from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.services.achievement_reward_observability import AchievementRewardObservability


@pytest.mark.asyncio
async def test_achievement_reward_observability_tracks_open_alerts_with_local_cache():
    original_redis = cache_service.redis
    original_local_cache = dict(cache_service._local_cache)
    cache_service.redis = None
    cache_service._local_cache.clear()

    try:
        await AchievementRewardObservability.record_event(
            status="scheduled",
            channel="post_commit",
            user_id="user-1",
            achievement_id="ach-1",
            achievement_name="成就一",
            quantity=30,
        )
        await AchievementRewardObservability.record_event(
            status="retry_failed",
            channel="local",
            user_id="user-1",
            achievement_id="ach-1",
            achievement_name="成就一",
            quantity=30,
            attempt=1,
            error_message="timeout",
        )
        await AchievementRewardObservability.record_event(
            status="retry_succeeded",
            channel="celery",
            user_id="user-2",
            achievement_id="ach-2",
            achievement_name="成就二",
            quantity=50,
            attempt=1,
        )

        payload = await AchievementRewardObservability.get_dashboard_payload(limit=10)

        assert payload["summary"]["tracked_events"] == 3
        assert payload["summary"]["open_alert_count"] == 1
        assert payload["summary"]["status_counts"]["retry_failed"] == 1
        assert payload["summary"]["channel_counts"]["local"] == 1
        assert payload["open_alerts"][0]["achievement_id"] == "ach-1"
        assert payload["events"][0]["status"] == "retry_succeeded"
    finally:
        cache_service.redis = original_redis
        cache_service._local_cache.clear()
        cache_service._local_cache.update(original_local_cache)
