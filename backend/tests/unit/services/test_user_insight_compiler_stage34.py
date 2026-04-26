from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.user_insight_state import UserInsightState
from app.services.user_insight_compiler import UserInsightCompiler


@pytest.mark.asyncio
async def test_apply_content_signals_writes_capsule_snapshot_when_stage34_shadow_enabled(
    db_session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.user_insight_compiler.CapsuleFavoriteService.get_preferences",
        AsyncMock(
            return_value={
                "favorite_count": 3,
                "content_depth_preference": "deep",
                "subject_affinity": ["physics", "math"],
                "recent_notes": ["revisit", "important"],
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.user_insight_compiler.AuroraStage34KillSwitchService.get_feature_mode",
        AsyncMock(return_value="shadow"),
    )

    state = UserInsightState()

    await UserInsightCompiler(db_session)._apply_content_signals(uuid4(), state)

    assert state.stable_preferences["content_depth_preference"] == "deep"
    assert state.stable_preferences["content_subject_affinities"] == ["physics", "math"]
    capsule = state.stable_preferences["capsule"]
    assert capsule["favorite_count"] == 3
    assert capsule["content_depth_preference"] == "deep"
    assert capsule["subject_affinity"] == ["physics", "math"]
    assert capsule["recent_notes"] == ["revisit", "important"]
    assert capsule["mode"] == "shadow"
    # F10 added method preference extraction fields
    assert "method_preferences" in capsule
    assert "method_preference_summary" in capsule

