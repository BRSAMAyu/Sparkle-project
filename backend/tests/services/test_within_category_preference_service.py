from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.within_category_preference_service import (
    WithinCategoryPreferenceService,
)


class _FakeLearner:
    def __init__(self, probabilities: dict[tuple[str, str], float]) -> None:
        self._probabilities = probabilities

    async def get_probability(self, source: str, target: str) -> float:
        return self._probabilities[(source, target)]


@pytest.mark.asyncio
async def test_build_hint_returns_bounded_payload_for_stable_same_category_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(tool_name="create_plan", usage_count=5),
            SimpleNamespace(tool_name="generate_tasks_for_plan", usage_count=3),
        ]
    )

    class _FakeToolPreferenceRouter:
        def __init__(self, db_session, user_id, redis_client=None):
            self.db_session = db_session
            self.user_id = user_id
            self.redis_client = redis_client
            self.learner = _FakeLearner(
                {
                    ("state_plan", "create_plan"): 0.82,
                    ("state_plan", "generate_tasks_for_plan"): 0.58,
                }
            )

        async def update_learner_from_history(self) -> None:
            return None

    monkeypatch.setenv("SPARKLE_CL1_WITHIN_CATEGORY_WIRE_ON", "true")
    monkeypatch.setattr(
        "app.services.within_category_preference_service.ToolPreferenceRouter",
        _FakeToolPreferenceRouter,
    )

    service = WithinCategoryPreferenceService(db=db, redis_client=object())
    service._get_shadow_summary = AsyncMock(
        return_value={
            "total_records": 7,
            "divergence_rate": 0.14,
        }
    )

    hint = await service.build_hint(user_id=uuid4(), request_category="plan")

    assert hint == {
        "claim_scope": "within_category_only",
        "surface": "dashboard.predicted_intent_card",
        "request_category": "plan",
        "preferred_tool": "create_plan",
        "confidence": 0.82,
        "support_count": 8,
        "shadow_records": 7,
        "divergence_rate": 0.14,
    }


@pytest.mark.asyncio
async def test_build_hint_auto_disables_when_shadow_divergence_is_too_high(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPARKLE_CL1_WITHIN_CATEGORY_WIRE_ON", "true")
    service = WithinCategoryPreferenceService(db=AsyncMock(), redis_client=object())
    service.shadow_recorder = SimpleNamespace(
        get_divergence_summary=AsyncMock(
            return_value={
                "total_records": 9,
                "divergence_rate": 0.5,
            }
        )
    )

    hint = await service.build_hint(user_id=uuid4(), request_category="task")

    assert hint is None
