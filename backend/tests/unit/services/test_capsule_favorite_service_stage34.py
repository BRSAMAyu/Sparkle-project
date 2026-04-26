from __future__ import annotations

import pytest

from app.models.capsule_favorite import CapsuleFavorite
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.user import User
from app.services.capsule_favorite_service import CapsuleFavoriteService


@pytest.mark.asyncio
async def test_get_preferences_isolates_other_users_capsules(db_session, test_user) -> None:
    other_user = User(
        username="other_capsule_user",
        email="other_capsule_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(other_user)
    await db_session.flush()

    own_capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="Own capsule",
        content="content",
        related_subject="physics",
        depth_level=DepthLevel.DEEP,
    )
    other_capsule = CuriosityCapsule(
        user_id=other_user.id,
        title="Other capsule",
        content="content",
        related_subject="chemistry",
        depth_level=DepthLevel.SHALLOW,
    )
    db_session.add_all([own_capsule, other_capsule])
    await db_session.flush()

    db_session.add_all(
        [
            CapsuleFavorite(
                user_id=test_user.id,
                capsule_id=own_capsule.id,
                note="keep",
            ),
            CapsuleFavorite(
                user_id=test_user.id,
                capsule_id=other_capsule.id,
                note="should_not_leak",
            ),
            CapsuleFavorite(
                user_id=other_user.id,
                capsule_id=other_capsule.id,
                note="other_note",
            ),
        ]
    )
    await db_session.commit()

    preferences = await CapsuleFavoriteService().get_preferences(test_user.id, db_session)

    assert preferences["favorite_count"] == 1
    assert preferences["content_depth_preference"] == "deep"
    assert preferences["subject_affinity"] == ["physics"]
    assert preferences["recent_notes"] == ["keep"]


@pytest.mark.asyncio
async def test_get_preferences_derives_depth_from_three_favorites(db_session, test_user) -> None:
    capsules = [
        CuriosityCapsule(
            user_id=test_user.id,
            title="Deep TCP",
            content="content",
            related_subject="computer_networks",
            depth_level=DepthLevel.DEEP,
        ),
        CuriosityCapsule(
            user_id=test_user.id,
            title="Deep OS",
            content="content",
            related_subject="os",
            depth_level=DepthLevel.DEEP,
        ),
        CuriosityCapsule(
            user_id=test_user.id,
            title="Shallow English",
            content="content",
            related_subject="english",
            depth_level=DepthLevel.SHALLOW,
        ),
    ]
    db_session.add_all(capsules)
    await db_session.flush()
    db_session.add_all(
        [
            CapsuleFavorite(user_id=test_user.id, capsule_id=capsules[0].id, note="need rigorous examples"),
            CapsuleFavorite(user_id=test_user.id, capsule_id=capsules[1].id, note="connect concepts"),
            CapsuleFavorite(user_id=test_user.id, capsule_id=capsules[2].id, note="quick check"),
        ]
    )
    await db_session.commit()

    preferences = await CapsuleFavoriteService().get_preferences(test_user.id, db_session)

    assert preferences["favorite_count"] == 3
    assert preferences["content_depth_preference"] == "deep"
    assert preferences["subject_affinity"] == ["computer_networks", "english", "os"]
    assert set(preferences["recent_notes"]) == {"need rigorous examples", "connect concepts", "quick check"}


@pytest.mark.asyncio
async def test_get_preferences_extracts_pomodoro_method_signal(db_session, test_user) -> None:
    capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="番茄钟工作法",
        content="用 25 分钟专注 + 5 分钟休息降低启动阻力。",
        related_subject="time_management",
        depth_level=DepthLevel.MEDIUM,
    )
    db_session.add(capsule)
    await db_session.flush()
    db_session.add(CapsuleFavorite(user_id=test_user.id, capsule_id=capsule.id))
    await db_session.commit()

    preferences = await CapsuleFavoriteService().get_preferences(test_user.id, db_session)

    assert preferences["method_preferences"][0]["key"] == "pomodoro"
    assert preferences["method_preferences"][0]["label"] == "番茄钟方法"
    assert preferences["method_preference_summary"] == ["用户偏好番茄钟方法"]
