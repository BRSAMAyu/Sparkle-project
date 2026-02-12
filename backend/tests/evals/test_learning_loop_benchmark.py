from __future__ import annotations

import pytest

from app.services.policy_candidate_service import PolicyCandidateService
from app.services.policy_registry_service import _MEM_CANDIDATES


@pytest.mark.asyncio
async def test_learning_loop_benchmark_guardrail(monkeypatch):
    monkeypatch.setattr("app.services.policy_candidate_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    _MEM_CANDIDATES.clear()

    service = PolicyCandidateService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "date": "2026-02-12",
                "policy_id": "expert_strategy_v2:study_plan_v1",
                "strategy_pack": "study_plan_v1",
                "complexity_tier": "high",
                "task_type": "study_plan",
                "counts": {
                    "expert_selected": 120,
                    "expert_fallback": 14,
                    "feedback_up": 30,
                    "feedback_down": 28,
                    "plan_execution_total": 32,
                    "plan_execution_success": 25,
                    "quality_gate_blocked": 7,
                    "route_decision": 170,
                },
                "q_score": 0.58,
                "normalized_latency": 0.5,
            }
        ]

    monkeypatch.setattr(service.rollups, "list_rollups", _fake_rollups)
    result = await service.run_candidate_job(window_days=7)

    assert result["status"] == "ok"
    assert result["baseline_q_score"] >= 0.0
    assert result["total_groups"] == 1
    assert result["created"] == 1
