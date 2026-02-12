from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.policy_candidate_service import PolicyCandidateService
from app.services.policy_registry_service import _MEM_CANDIDATES, _MEM_POLICIES


def _today() -> str:
    return datetime.now(UTC).replace(tzinfo=None).date().isoformat()


@pytest.mark.asyncio
async def test_policy_candidate_generation_and_approval(monkeypatch):
    monkeypatch.setattr("app.services.policy_candidate_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANARY_ROLLOUT", True)

    _MEM_CANDIDATES.clear()
    _MEM_POLICIES.clear()

    service = PolicyCandidateService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "date": _today(),
                "policy_id": "expert_strategy_v2:general_v2",
                "strategy_pack": "general_v2",
                "complexity_tier": "medium",
                "task_type": "expert_auto",
                "counts": {
                    "expert_selected": 80,
                    "expert_fallback": 10,
                    "feedback_up": 18,
                    "feedback_down": 22,
                    "plan_execution_total": 20,
                    "plan_execution_success": 14,
                    "quality_gate_blocked": 6,
                    "route_decision": 120,
                },
                "q_score": 0.51,
                "normalized_latency": 0.62,
            }
        ]

    monkeypatch.setattr(service.rollups, "list_rollups", _fake_rollups)
    result = await service.run_candidate_job(window_days=7)
    assert result["status"] == "ok"
    assert result["created"] == 1

    pending = await service.registry.list_candidates(status="pending")
    assert len(pending) == 1
    candidate_id = pending[0]["id"]
    await service.registry.approve_candidate(candidate_id=candidate_id, reviewer="admin")

    runtime = await service.registry.resolve_runtime_policy(
        strategy_pack="general_v2",
        user_id="u1",
        session_id="s1",
    )
    assert runtime is not None
    assert runtime["strategy_pack"] == "general_v2"
    assert runtime["policy_id"].startswith("meta_policy_v1:routing:general_v2:")


@pytest.mark.asyncio
async def test_policy_candidate_generation_creates_scope_layers(monkeypatch):
    monkeypatch.setattr("app.services.policy_candidate_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_candidate_service.settings.COHORT_POLICY_MIN_SUPPORT", 20)
    monkeypatch.setattr("app.services.policy_candidate_service.settings.PERSONAL_POLICY_MIN_SUPPORT", 10)

    _MEM_CANDIDATES.clear()
    _MEM_POLICIES.clear()

    service = PolicyCandidateService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "date": _today(),
                "policy_id": "expert_strategy_v2:general_v2",
                "strategy_pack": "general_v2",
                "cohort_id": "cohort::study::medium::high_engagement::rhythm_steady",
                "user_scope": "usr::111111111111",
                "complexity_tier": "medium",
                "task_type": "expert_auto",
                "counts": {
                    "expert_selected": 90,
                    "expert_fallback": 12,
                    "feedback_up": 15,
                    "feedback_down": 25,
                    "plan_execution_total": 26,
                    "plan_execution_success": 18,
                    "quality_gate_blocked": 8,
                    "route_decision": 120,
                },
                "q_score": 0.52,
                "normalized_latency": 0.58,
            }
        ]

    monkeypatch.setattr(service.rollups, "list_rollups", _fake_rollups)
    result = await service.run_candidate_job(window_days=7)
    assert result["status"] == "ok"
    assert result["created"] >= 2

    pending = await service.registry.list_candidates(status="pending")
    scopes = {(row.get("scope_type"), row.get("scope_key")) for row in pending}
    assert ("global", "all") in scopes
    assert any(scope[0] == "cohort" for scope in scopes)


@pytest.mark.asyncio
async def test_policy_registry_rollback_restores_base_policy(monkeypatch):
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANARY_ROLLOUT", True)

    _MEM_CANDIDATES.clear()
    _MEM_POLICIES.clear()
    service = PolicyCandidateService(redis_client=None)
    registry = service.registry

    await registry.upsert_policy(
        {
            "policy_id": "expert_strategy_v2:general_v2",
            "strategy_pack": "general_v2",
            "status": "active",
            "weights": {"semantic_weight": 0.4},
            "thresholds": {"min_selected_score": 0.34},
        }
    )
    await registry.upsert_policy(
        {
            "policy_id": "expert_strategy_v2:general_v2:candidate_demo",
            "base_policy": "expert_strategy_v2:general_v2",
            "strategy_pack": "general_v2",
            "status": "canary",
            "weights": {"semantic_weight": 0.5},
            "thresholds": {"min_selected_score": 0.36},
        }
    )

    rolled = await registry.rollback_policy(
        policy_id="expert_strategy_v2:general_v2:candidate_demo",
        reason="guardrail_exceeded",
    )
    assert rolled is not None
    assert rolled["status"] == "rolled_back"

    base = await registry.get_policy("expert_strategy_v2:general_v2")
    assert base is not None
    assert base["status"] == "active"


@pytest.mark.asyncio
async def test_policy_registry_resolve_runtime_policy_composes_layers(monkeypatch):
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_registry_service.settings.COHORT_POLICY_MIN_SUPPORT", 20)
    monkeypatch.setattr("app.services.policy_registry_service.settings.PERSONAL_POLICY_MIN_SUPPORT", 10)
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANARY_ROLLOUT", False)

    _MEM_POLICIES.clear()
    registry = PolicyCandidateService(redis_client=None).registry
    await registry.upsert_policy(
        {
            "policy_id": "expert_strategy_v2:general_v2",
            "strategy_pack": "general_v2",
            "scope_type": "global",
            "scope_key": "all",
            "status": "active",
            "support_size": 500,
            "weights": {"semantic_weight": 0.4, "affinity_weight": 0.2, "success_weight": 0.2, "complexity_weight": 0.1, "decomposition_weight": 0.05, "latency_weight": 0.05},
            "thresholds": {"min_selected_score": 0.34, "medium_complexity_threshold": 0.5, "high_complexity_threshold": 0.75},
        }
    )
    await registry.upsert_policy(
        {
            "policy_id": "expert_strategy_v2:general_v2:cohort_x",
            "strategy_pack": "general_v2",
            "scope_type": "cohort",
            "scope_key": "cohort::study::medium::high_engagement::rhythm_steady",
            "status": "active",
            "support_size": 120,
            "weights": {"semantic_weight": 0.5, "affinity_weight": 0.15, "success_weight": 0.15, "complexity_weight": 0.1, "decomposition_weight": 0.06, "latency_weight": 0.04},
            "thresholds": {"min_selected_score": 0.36, "medium_complexity_threshold": 0.52, "high_complexity_threshold": 0.77},
        }
    )
    await registry.upsert_policy(
        {
            "policy_id": "expert_strategy_v2:general_v2:personal_x",
            "strategy_pack": "general_v2",
            "scope_type": "personal",
            "scope_key": "usr::111111111111",
            "status": "active",
            "support_size": 35,
            "weights": {"semantic_weight": 0.52, "affinity_weight": 0.16, "success_weight": 0.12, "complexity_weight": 0.1, "decomposition_weight": 0.06, "latency_weight": 0.04},
            "thresholds": {"min_selected_score": 0.37, "medium_complexity_threshold": 0.53, "high_complexity_threshold": 0.78},
        }
    )

    runtime = await registry.resolve_runtime_policy(
        strategy_pack="general_v2",
        user_id="user_abc",
        session_id="session_1",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::111111111111",
    )
    assert runtime is not None
    assert runtime["policy_id"].startswith("meta_policy_v1:routing:general_v2:")
    assert isinstance(runtime["weights"], dict)
    assert isinstance(runtime["thresholds"], dict)
    assert len(runtime.get("selected_layers", [])) >= 2

    await registry.upsert_policy(
        {
            "policy_id": "meta_prompt_global",
            "strategy_pack": "general_v2",
            "channel": "prompt",
            "scope_type": "global",
            "scope_key": "all",
            "status": "active",
            "support_size": 300,
            "arm_weights": {"v1": 0.5, "v2": 0.5},
            "params": {"exploration_ratio": 0.2},
        }
    )
    prompt_runtime = await registry.resolve_runtime_policy(
        strategy_pack="general_v2",
        user_id="user_abc",
        session_id="session_1",
        channel="prompt",
    )
    assert prompt_runtime is not None
    assert str(prompt_runtime.get("channel")) == "prompt"
    assert isinstance(prompt_runtime.get("arm_weights"), dict)


@pytest.mark.asyncio
async def test_policy_candidate_generation_multi_channel(monkeypatch):
    monkeypatch.setattr("app.services.policy_candidate_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_candidate_service.settings.COHORT_POLICY_MIN_SUPPORT", 20)
    monkeypatch.setattr("app.services.policy_candidate_service.settings.PERSONAL_POLICY_MIN_SUPPORT", 10)

    _MEM_CANDIDATES.clear()
    _MEM_POLICIES.clear()

    service = PolicyCandidateService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "date": _today(),
                "policy_id": "expert_strategy_v2:general_v2",
                "strategy_pack": "general_v2",
                "cohort_id": "cohort::general::medium::medium_engagement::rhythm_steady",
                "user_scope": "usr::222222222222",
                "complexity_tier": "medium",
                "task_type": "expert_auto",
                "counts": {
                    "expert_selected": 120,
                    "expert_fallback": 14,
                    "prompt_selected": 120,
                    "prompt_applied": 88,
                    "toolchain_selected": 120,
                    "toolchain_degraded": 11,
                    "feedback_up": 28,
                    "feedback_down": 24,
                    "plan_execution_total": 32,
                    "plan_execution_success": 22,
                    "quality_gate_blocked": 10,
                    "route_decision": 140,
                },
                "q_score": 0.54,
                "normalized_latency": 0.61,
            }
        ]

    monkeypatch.setattr(service.rollups, "list_rollups", _fake_rollups)
    result = await service.run_candidate_job(window_days=7, channels=["routing", "prompt", "toolchain"])
    assert result["status"] == "ok"
    assert result["created"] >= 3
    assert set(result["channels"]) == {"routing", "prompt", "toolchain"}

    pending = await service.registry.list_candidates(status="pending")
    channels = {str(item.get("channel", "routing")) for item in pending}
    assert "routing" in channels
    assert "prompt" in channels
    assert "toolchain" in channels
