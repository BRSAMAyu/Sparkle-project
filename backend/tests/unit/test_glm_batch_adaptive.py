from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.glm_batch_service import GLMBatchService
from app.services.llm.concurrency import LLMConcurrencyManager, ProviderType


@pytest.mark.asyncio
async def test_glm_batch_peak_hours_are_clamped_to_two(monkeypatch):
    manager = LLMConcurrencyManager()
    monkeypatch.setattr(manager, "_now", lambda: datetime(2026, 3, 19, 15, 0, 0))
    manager._runtime[ProviderType.ZHIPU_CODING].current_limit = 5

    assert manager.get_runtime_limit("zhipu_coding") == 2
    stats = manager.get_provider_runtime_state("zhipu_coding")
    assert stats["peak_mode"] is True
    assert stats["current_limit"] == 2


@pytest.mark.asyncio
async def test_glm_batch_offpeak_success_can_raise_limit(monkeypatch):
    manager = LLMConcurrencyManager()
    monkeypatch.setattr(manager, "_now", lambda: datetime(2026, 3, 19, 21, 0, 0))
    monkeypatch.setattr("app.services.llm.concurrency.settings.GLM_BATCH_ADAPTIVE_SUCCESS_THRESHOLD", 2)
    monkeypatch.setattr("app.services.llm.concurrency.settings.GLM_BATCH_ADAPTIVE_INCREASE_COOLDOWN_SECONDS", 0)

    runtime = manager._runtime[ProviderType.ZHIPU_CODING]
    runtime.current_limit = 3
    runtime.active = 3
    runtime.waiting = 1

    await manager.report_success("zhipu_coding")
    await manager.report_success("zhipu_coding")

    assert manager.get_runtime_limit("zhipu_coding") == 4


@pytest.mark.asyncio
async def test_glm_batch_rate_limit_immediately_reduces_limit(monkeypatch):
    manager = LLMConcurrencyManager()
    monkeypatch.setattr(manager, "_now", lambda: datetime(2026, 3, 19, 22, 0, 0))
    runtime = manager._runtime[ProviderType.ZHIPU_CODING]
    runtime.hydrated = True
    runtime.last_bucket = "22"
    runtime.current_limit = 5

    await manager.report_rate_limit("zhipu_coding")

    assert manager.get_runtime_limit("zhipu_coding") == 4
    assert runtime.cooldown_until > 0


def test_glm_batch_dispatch_spills_to_standard_when_queue_is_saturated(monkeypatch):
    service = GLMBatchService()
    monkeypatch.setattr(
        service,
        "get_runtime_status",
        lambda: {
            "provider": "zhipu_coding",
            "current_limit": 2,
            "cooldown_active": False,
            "peak_mode": True,
        },
    )
    monkeypatch.setattr(service, "get_runtime_limit", lambda: 2)
    monkeypatch.setattr(
        llm_router,
        "select_model",
        lambda agent_role, task_type=None, force_tier=None: LLMSelection(
            model_key="mimo_pro",
            config=ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name="mimo-v2-pro",
                base_url="https://mimo.test",
                api_key="test-key",
                tier=ModelTier.STANDARD,
            ),
            agent_role=AgentRole.GENERATION,
            task_type=TaskType.STANDARD_RESPONSE,
            reason="test",
        ),
    )

    decision = service.decide_capsule_dispatch(
        depth_preference=0.8,
        curiosity_preference=0.9,
        requested_count=1,
        generation_type="manual",
        celery_status={
            "status": "healthy",
            "queue_worker_count": 1,
            "queue_active_tasks": 2,
            "queue_reserved_tasks": 0,
        },
    )

    assert decision.should_enqueue is False
    assert decision.execution_mode == "standard_spillover"
    assert decision.spillover_model_key == "mimo_pro"
