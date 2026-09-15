"""
Unit tests for RoutingEngineMixin.

Tests the routing and classification helpers for the orchestrator.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.orchestration.routing_engine import RoutingEngineMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(RoutingEngineMixin):
    """Minimal orchestrator with RoutingEngineMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()
        self.dual_core_router = MagicMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


def test_extract_primary_challenge_area_from_plan_context(orchestrator):
    """Test _extract_primary_challenge_area extracts correctly from plan_context."""
    plan_context = {
        "user_profile": {
            "derived_insights": {
                "primary_challenge_area": "procrastination"
            }
        }
    }

    result = orchestrator._extract_primary_challenge_area(plan_context)

    assert result == "procrastination"


def test_extract_primary_challenge_area_returns_none_for_missing_data(orchestrator):
    """Test _extract_primary_challenge_area returns None when data is missing."""
    # Missing user_profile
    result1 = orchestrator._extract_primary_challenge_area({})
    assert result1 is None

    # Missing derived_insights
    result2 = orchestrator._extract_primary_challenge_area({"user_profile": {}})
    assert result2 is None

    # Missing primary_challenge_area
    result3 = orchestrator._extract_primary_challenge_area({
        "user_profile": {"derived_insights": {}}
    })
    assert result3 is None


def test_extract_session_length_preference_from_facts(orchestrator):
    """Test _extract_session_length_preference extracts from plan_context facts."""
    plan_context = {
        "facts": {
            "session_length_preference": 45
        }
    }

    result = orchestrator._extract_session_length_preference(
        user_context_payload=None,
        plan_context=plan_context,
    )

    assert result == 45


def test_extract_session_length_preference_from_user_context(orchestrator):
    """Test _extract_session_length_preference extracts from user_context_payload."""
    user_context_payload = {
        "preferences": {
            "focus_duration_preference": 60
        }
    }

    result = orchestrator._extract_session_length_preference(
        user_context_payload=user_context_payload,
        plan_context=None,
    )

    assert result == 60


def test_extract_session_length_preference_priority_order(orchestrator):
    """Test _extract_session_length_preference priority: facts > user_context > profile."""
    plan_context = {
        "facts": {"session_length_preference": 25},
        "user_profile": {
            "preferences_snapshot": {"inferred_session_length": 35}
        }
    }
    user_context_payload = {
        "preferences": {"focus_duration_preference": 45}
    }

    result = orchestrator._extract_session_length_preference(
        user_context_payload=user_context_payload,
        plan_context=plan_context,
    )

    # facts should have priority
    assert result == 25


def test_extract_difficulty_preference_from_facts(orchestrator):
    """Test _extract_difficulty_preference extracts from plan_context facts."""
    plan_context = {
        "facts": {
            "difficulty_preference": 0.8
        }
    }

    result = orchestrator._extract_difficulty_preference(
        user_context_payload=None,
        plan_context=plan_context,
    )

    assert result == 0.8


def test_extract_difficulty_preference_from_profile(orchestrator):
    """Test _extract_difficulty_preference extracts from user_profile."""
    plan_context = {
        "user_profile": {
            "preferences_snapshot": {
                "inferred_difficulty": 0.6
            }
        }
    }

    result = orchestrator._extract_difficulty_preference(
        user_context_payload=None,
        plan_context=plan_context,
    )

    assert result == 0.6


def test_extract_difficulty_preference_from_user_context(orchestrator):
    """Test _extract_difficulty_preference extracts from user_context_payload."""
    user_context_payload = {
        "preferences": {
            "difficulty_preference": 0.4
        }
    }

    result = orchestrator._extract_difficulty_preference(
        user_context_payload=user_context_payload,
        plan_context=None,
    )

    assert result == 0.4


def test_extract_difficulty_preference_returns_none_for_missing_data(orchestrator):
    """Test _extract_difficulty_preference returns None when no data found."""
    result = orchestrator._extract_difficulty_preference(
        user_context_payload={},
        plan_context={},
    )

    assert result is None
