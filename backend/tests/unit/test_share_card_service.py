from datetime import datetime

import pytest
from PIL import Image

from app.config import settings
from app.core.cache import cache_service
from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement, VisualEffectType
from app.services.share_card_service import ShareCardService


def _build_achievement() -> Achievement:
    achievement = Achievement(
        id="share_test",
        name="银河见证者",
        description="完成第三阶段收敛并分享成果",
        type=AchievementType.MILESTONE,
        rarity=AchievementRarity.EPIC,
        trigger_code="TASKS_TOTAL",
        trigger_config={"count": 1},
        visual_effect_type=VisualEffectType.SUPERNOVA,
        visual_config={"particle_count": 42},
        reward_config=[{"type": "title", "value": "observer"}],
        total_unlocked=1,
    )
    achievement.created_at = datetime(2026, 3, 10, 9, 0, 0)
    achievement.updated_at = datetime(2026, 3, 10, 9, 0, 0)
    return achievement


@pytest.mark.asyncio
async def test_generate_share_card_creates_png_and_increments_share_count(
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    cache_service._local_cache.clear()

    achievement = _build_achievement()
    db_session.add(achievement)
    db_session.add(
        UserAchievement(
            user_id=test_user.id,
            achievement_id=achievement.id,
            progress=1.0,
            progress_value=1,
            progress_target=1,
            unlocked_at=datetime(2026, 3, 10, 10, 0, 0),
            share_count=0,
        )
    )
    await db_session.commit()

    service = ShareCardService(db_session)
    result, _, user_achievement = await service.generate_achievement_share_card(test_user.id, achievement.id)

    card_path = tmp_path / "achievement-cards" / str(test_user.id) / "share_test_v1.png"
    assert result.card_url == f"/uploads/achievement-cards/{test_user.id}/share_test_v1.png"
    assert result.mime_type == "image/png"
    assert card_path.exists()
    assert user_achievement.share_count == 1

    with Image.open(card_path) as image:
        assert image.size == (ShareCardService.WIDTH, ShareCardService.HEIGHT)


@pytest.mark.asyncio
async def test_generate_share_card_reuses_cached_file_without_re_rendering(
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    cache_service._local_cache.clear()

    achievement = _build_achievement()
    db_session.add(achievement)
    db_session.add(
        UserAchievement(
            user_id=test_user.id,
            achievement_id=achievement.id,
            progress=1.0,
            progress_value=1,
            progress_target=1,
            unlocked_at=datetime(2026, 3, 10, 10, 0, 0),
            share_count=0,
        )
    )
    await db_session.commit()

    service = ShareCardService(db_session)
    first_result, _, _ = await service.generate_achievement_share_card(test_user.id, achievement.id)

    async def _should_not_render(*args, **kwargs):
        raise AssertionError("Share card should be served from cache")

    monkeypatch.setattr(service, "_render_and_store_card", _should_not_render)
    second_result, _, user_achievement = await service.generate_achievement_share_card(test_user.id, achievement.id)

    assert second_result.card_url == first_result.card_url
    assert user_achievement.share_count == 2


@pytest.mark.asyncio
async def test_generate_share_card_rejects_locked_achievement(
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    cache_service._local_cache.clear()

    achievement = _build_achievement()
    db_session.add(achievement)
    db_session.add(
        UserAchievement(
            user_id=test_user.id,
            achievement_id=achievement.id,
            progress=0.5,
            progress_value=1,
            progress_target=2,
            unlocked_at=None,
        )
    )
    await db_session.commit()

    service = ShareCardService(db_session)

    with pytest.raises(ValueError, match="Achievement not unlocked yet"):
        await service.generate_achievement_share_card(test_user.id, achievement.id)
