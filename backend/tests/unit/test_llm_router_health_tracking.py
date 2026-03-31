"""
Circuit Breaker Integration Tests for LLMRouter

Tests that LLMRouter properly tracks model health and applies circuit breaker
protection when selecting models.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.agent_profiles import AgentRole, TaskType
from app.core.llm_router import LLMRouter, LLMSelection, ModelHealthState


@pytest.fixture
def llm_router():
    """Create LLMRouter instance."""
    return LLMRouter()


def test_router_tracks_model_health_success(llm_router):
    """Test that successful model calls are tracked."""
    model_key = "xiaomi_chat"

    # First failure to create health state entry
    llm_router.report_model_failure(model_key)

    # Then report success
    llm_router.report_model_success(model_key)

    # Health state should be initialized and healthy
    assert model_key in llm_router._model_health
    assert llm_router._model_health[model_key].is_healthy is True
    assert llm_router._model_health[model_key].consecutive_failures == 0


def test_router_tracks_model_health_failure(llm_router):
    """Test that failed model calls are tracked."""
    model_key = "xiaomi_chat"

    # Report failures below threshold
    for _ in range(3):
        llm_router.report_model_failure(model_key)

    # Should still be healthy (below threshold of 5)
    assert llm_router._model_health[model_key].is_healthy is True
    assert llm_router._model_health[model_key].consecutive_failures == 3

    # Report more failures to exceed threshold
    for _ in range(2):
        llm_router.report_model_failure(model_key)

    # Should now be marked unhealthy
    assert llm_router._model_health[model_key].is_healthy is False
    assert llm_router._model_health[model_key].consecutive_failures == 5


def test_router_skips_unhealthy_models_in_selection(llm_router):
    """Test that unhealthy models are skipped during model selection."""
    model_key = "xiaomi_chat"

    # Mark model as unhealthy
    llm_router.report_model_failure(model_key)
    llm_router.report_model_failure(model_key)
    llm_router.report_model_failure(model_key)
    llm_router.report_model_failure(model_key)
    llm_router.report_model_failure(model_key)

    # Select model - should skip xiaomi_chat
    selection = llm_router.select_model(
        agent_role=AgentRole.GENERATION,
        task_type=TaskType.STANDARD_RESPONSE,
    )

    # Should NOT select the unhealthy model
    assert selection.model_key != model_key


def test_router_auto_recovers_model_after_cooldown(llm_router):
    """Test that unhealthy models auto-recover after cooldown period."""
    model_key = "xiaomi_chat"

    # Mark model as unhealthy
    for _ in range(5):
        llm_router.report_model_failure(model_key)

    assert llm_router._model_health[model_key].is_healthy is False

    # Simulate time passing (more than 300 seconds)
    llm_router._model_health[model_key].last_failure_at = time.monotonic() - 400

    # Check recovery should reset to healthy
    llm_router._model_health[model_key].check_recovery()
    assert llm_router._model_health[model_key].is_healthy is True


def test_router_uses_fallback_model_when_primary_unhealthy(llm_router):
    """Test that router falls back to next tier when primary is unhealthy."""
    # Mark all FAST tier models as unhealthy
    for model_key in ["xiaomi_chat", "dashscope_fast", "glm_4_7_flash_no_thinking"]:
        for _ in range(5):
            llm_router.report_model_failure(model_key)

    # Select model - should fall back to STANDARD tier
    selection = llm_router.select_model(
        agent_role=AgentRole.GENERATION,
        task_type=TaskType.QUICK_QUERY,
    )

    # Should select from STANDARD tier (not FAST)
    assert selection.config.tier.value in {"standard", "plus"}


def test_model_health_state_defaults_to_healthy():
    """Test that ModelHealthState defaults to healthy state."""
    state = ModelHealthState()

    assert state.is_healthy is True
    assert state.consecutive_failures == 0
    assert state.last_failure_at is None


def test_model_health_state_recovers_after_success():
    """Test that a success resets the health state."""
    state = ModelHealthState()

    # Record failures to trip
    for _ in range(5):
        state.record_failure()

    assert state.is_healthy is False

    # Single success should recover
    state.record_success()

    assert state.is_healthy is True
    assert state.consecutive_failures == 0


def test_router_reports_success_clears_previous_failures(llm_router):
    """Test that reporting success after failures resets the state."""
    model_key = "xiaomi_chat"

    # Report failures
    for _ in range(3):
        llm_router.report_model_failure(model_key)

    assert llm_router._model_health[model_key].consecutive_failures == 3

    # Report success
    llm_router.report_model_success(model_key)

    # Should reset
    assert llm_router._model_health[model_key].consecutive_failures == 0
    assert llm_router._model_health[model_key].is_healthy is True


def test_select_model_returns_fallback_when_all_models_unhealthy(llm_router):
    """Test that select_model returns a fallback when all preferred models are unhealthy."""
    # Mark all FAST and STANDARD tier models as unhealthy
    unhealthy_models = [
        "xiaomi_chat", "xiaomi_standard_thinking",
        "dashscope_fast", "dashscope_standard_thinking", "dashscope_chat",
        "glm_4_7_flash_no_thinking",
    ]
    for model_key in unhealthy_models:
        for _ in range(5):
            llm_router.report_model_failure(model_key)

    # Should still return a valid selection (fallback to deeper tier)
    selection = llm_router.select_model(
        agent_role=AgentRole.GENERATION,
        task_type=TaskType.QUICK_QUERY,  # Prefer FAST tier
    )

    assert isinstance(selection, LLMSelection)
    assert selection.model_key is not None
    # Should not be from FAST tier since all are unhealthy
    assert selection.config.tier.value not in {"fast"}


def test_health_check_does_not_create_state_for_unknown_models(llm_router):
    """Test that checking health of unknown model returns True (healthy)."""
    unknown_model = "totally_fake_model_key"

    # Should return True (healthy) for unknown models
    assert llm_router._is_model_healthy(unknown_model) is True

    # Should not create a health state entry
    assert unknown_model not in llm_router._model_health


def test_select_model_ignores_unhealthy_in_policy_routing(llm_router):
    """Test that policy-based routing skips unhealthy models."""
    # Mark a model that might be preferred by policy as unhealthy
    for _ in range(5):
        llm_router.report_model_failure("dashscope_standard_thinking")

    # Select model with standard tier preference
    from app.core.agent_profiles import ModelTier
    selection = llm_router.select_model(
        agent_role=AgentRole.GENERATION,
        task_type=TaskType.STANDARD_RESPONSE,
        force_tier=ModelTier.STANDARD,
    )

    # Should skip the unhealthy model
    assert selection.model_key != "dashscope_standard_thinking"
