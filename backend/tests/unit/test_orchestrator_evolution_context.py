from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.orchestration.orchestrator import ChatOrchestrator


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
        "app.orchestration.orchestrator.SystemUpdateService.list_updates",
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
        "app.orchestration.orchestrator.SystemUpdateService.list_updates",
        AsyncMock(return_value=updates),
    ):
        await orchestrator._hydrate_evolution_context(final_state=final_state, user_id="user-1")

    assert final_state.context_data["evolution_highlights"] == ["你刚刚解锁了「冲刺先锋」。"]
