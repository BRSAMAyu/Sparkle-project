from datetime import timedelta

import pytest

from app.models.user import User
from app.services.personalization.inferred_preference_decay_service import InferredPreferenceDecayService
from app.services.personalization.preference_service import PreferenceService


@pytest.mark.asyncio
async def test_decay_service_covers_broad_numeric_inferred_keys(db_session) -> None:
    user = User(username="decaywide", email="decaywide@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    pref_service = PreferenceService(db_session)
    prefs = await pref_service.update_inferred_raw(
        user.id,
        {
            "error_density_score": 0.8,
            "ai_delegate_preference": 0.9,
            "preferred_focus_duration": 50,
            "chat_active_hours": [9, 10, 11],
            "execution.safety_concern_count": 3,
        },
    )
    prefs.last_inferred_update = prefs.updated_at - timedelta(days=21)
    await db_session.commit()

    result = await InferredPreferenceDecayService(db_session).apply_decay_to_user(user.id)
    refreshed = await pref_service.get_preferences(user.id)

    assert result["changes"] >= 3
    assert refreshed.inferred["error_density_score"] < 0.8
    assert refreshed.inferred["ai_delegate_preference"] < 0.9
    assert refreshed.inferred["preferred_focus_duration"] < 50
    assert refreshed.inferred["chat_active_hours"] == [9, 10, 11]
    assert refreshed.inferred["execution.safety_concern_count"] == 3


@pytest.mark.asyncio
async def test_decay_service_does_not_jump_low_values_back_to_neutral(db_session) -> None:
    user = User(username="decayjump", email="decayjump@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    pref_service = PreferenceService(db_session)
    prefs = await pref_service.update_inferred_raw(
        user.id,
        {
            "depth_preference": 0.25,
            "depth_preference_confidence": 0.6,
        },
    )
    prefs.last_inferred_update = prefs.updated_at - timedelta(days=14)
    await db_session.commit()

    await InferredPreferenceDecayService(db_session).apply_decay_to_user(user.id)
    refreshed = await pref_service.get_preferences(user.id)

    assert refreshed.inferred["depth_preference"] > 0.25
    assert refreshed.inferred["depth_preference"] != 0.5
