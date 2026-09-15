"""
Unit tests for SessionStateMixin.

Tests the session state management, feedback handling, and version
tracking methods.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.session_state_mixin import SessionStateMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(SessionStateMixin):
    """Minimal orchestrator with SessionStateMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


@pytest.mark.asyncio
async def test_drain_system_updates_returns_empty_when_no_updates(orchestrator):
    """Test _drain_system_updates returns empty tuples when no updates available."""
    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=[])

        responses, adaptations, preferences, highlights, progress, depth, visible_context = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert responses == []
        assert adaptations == []
        assert preferences == []
        assert highlights == []
        assert progress is None
        assert depth is None
        assert visible_context == {
            "proactive_opening_message": "",
            "pending_observation": "",
            "post_adaptation_question": "",
            "active_intervention_id": "",
            "active_interventions": [],
        }


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_evolution_kinds(orchestrator):
    """Test _drain_system_updates correctly extracts different evolution kinds."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "adaptation_record",
                "adaptation_record": {"type": "test_adaptation"}
            }
        },
        {
            "metadata": {
                "evolution_kind": "preference_learning",
                "preference_learning": {"key": "value"}
            }
        },
        {
            "metadata": {
                "evolution_kind": "highlight",
                "highlight": "Important progress!"
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth, visible_context = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert len(adaptations) == 1
        assert adaptations[0]["type"] == "test_adaptation"
        assert len(preferences) == 1
        assert preferences[0]["key"] == "value"
        assert len(highlights) == 1
        assert highlights[0] == "Important progress!"
        assert visible_context["proactive_opening_message"] == ""


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_progress_snapshot(orchestrator):
    """Test _drain_system_updates extracts progress snapshot."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "progress_snapshot",
                "progress_snapshot": {"tasks_completed": 5, "streak": 3}
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth, _ = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert progress is not None
        assert progress["tasks_completed"] == 5
        assert progress["streak"] == 3


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_understanding_depth(orchestrator):
    """Test _drain_system_updates extracts understanding depth update."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "understanding_depth",
                "understanding_depth": {"level": "intermediate"},
                "description": "User has improved"
            },
        },

    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth, _ = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert depth is not None
        assert depth["understanding_depth"]["level"] == "intermediate"
        assert depth["description"] == ""


@pytest.mark.asyncio
async def test_drain_system_updates_generates_highlight_for_understanding_depth(orchestrator):
    """Test _drain_system_updates generates highlight text for understanding depth."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "understanding_depth",
                "understanding_depth": {"level": "advanced"},
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth, _ = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        # Should generate a highlight about understanding depth
        assert any("理解已提升" in h for h in highlights)


@pytest.mark.asyncio
async def test_drain_system_updates_builds_visible_prompt_context(orchestrator):
    updates = [
        {
            "type": "plan_adjusted_from_error",
            "description": "我注意到你在条件句上连续卡住了 3 次，已经把相关练习提前。",
            "metadata": {
                "evolution_kind": "adjustment",
                "node_name": "条件句",
                "intervention_id": str(uuid4()),
            },
        },
        {
            "metadata": {
                "evolution_kind": "proactive_insight",
                "insight_text": "你最近总在周四中断学习。",
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        _, _, _, highlights, _, _, visible_context = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert any("条件句" in item for item in highlights)
        assert "条件句" in visible_context["proactive_opening_message"]
        assert "周四中断学习" in visible_context["pending_observation"]
        assert "合适吗" in visible_context["post_adaptation_question"]
        assert visible_context["active_intervention_id"]
        assert len(visible_context["active_interventions"]) == 1


@pytest.mark.asyncio
async def test_attach_active_intervention_state_updates_runtime_context(orchestrator):
    state = WorkflowState(
        context_data={
            "user_context": {},
            "visible_update_context": {
                "active_interventions": [
                    {
                        "intervention_id": str(uuid4()),
                        "source": "system_update",
                    }
                ]
            },
        }
    )
    user_context_payload = {}

    with patch("app.orchestration.session_state_mixin.InterventionFeedbackBindingService") as mock_service:
        service = mock_service.return_value
        service.resolve_active_interventions = AsyncMock(
            return_value=[
                {
                    "intervention_id": str(uuid4()),
                    "source": "pending_record",
                    "acceptance_status": "DELIVERED",
                }
            ]
        )
        service.get_last_feedback_binding = AsyncMock(
            return_value={"intervention_id": str(uuid4()), "sentiment": "accepted"}
        )

        await orchestrator._attach_active_intervention_state(
            active_db=object(),
            user_id=str(uuid4()),
            session_id="session-1",
            user_context_payload=user_context_payload,
            state=state,
        )

    assert state.context_data["active_interventions"][0]["source"] == "pending_record"
    assert state.context_data["active_intervention_id"]
    assert state.context_data["last_feedback_binding"]["sentiment"] == "accepted"
    assert user_context_payload["active_interventions"][0]["source"] == "pending_record"


@pytest.mark.asyncio
async def test_hydrate_companion_runtime_context_updates_state_and_user_context(orchestrator):
    state = WorkflowState(context_data={"user_context": {}})
    user_context_payload = {"preferences": {"depth_preference": 0.5}}

    with patch("app.orchestration.session_state_mixin.CompanionStateService") as mock_service:
        service = mock_service.return_value
        service.get_effective_state = AsyncMock(return_value={"relationship_stage": "trusted", "candor_calibration": 0.8})
        service.get_relationship_profile = AsyncMock(return_value={"trust_level": 0.7})
        service.get_recent_revisions = AsyncMock(return_value=[{"field": "candor_calibration"}])

        payload = await orchestrator._hydrate_companion_runtime_context(
            active_db=object(),
            user_id=str(uuid4()),
            session_id="session-1",
            plan_id=None,
            user_context_payload=user_context_payload,
            state=state,
        )

    assert payload["effective_companion_state"]["relationship_stage"] == "trusted"
    assert state.context_data["relationship_profile"]["trust_level"] == 0.7
    assert user_context_payload["companion_state_recent_revisions"][0]["field"] == "candor_calibration"
