from __future__ import annotations

import pytest

from app.services.cognitive_pattern_mining_service import CognitivePatternMiningService
from app.services.task_motif_registry_service import _MEM_GRAPHS, _MEM_RULES


@pytest.mark.asyncio
async def test_cognitive_pattern_mining_generates_rules(monkeypatch) -> None:
    _MEM_RULES.clear()
    _MEM_GRAPHS.clear()
    service = CognitivePatternMiningService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "task_type": "study_plan",
                "complexity_tier": "medium",
                "strategy_pack": "study_plan_v1",
                "q_score": 0.54,
                "fallback_rate": 0.12,
                "normalized_latency": 0.6,
                "repair_success_rate": 0.4,
                "feedback_up_rate": 0.42,
                "failure_pattern_topn": [{"pattern": "failure_pattern::quality_gate::missing_goal", "count": 12}],
                "counts": {
                    "expert_selected": 120,
                    "quality_gate_blocked": 9,
                    "plan_repair_triggered": 11,
                },
            }
        ]

    monkeypatch.setattr(service.rollups, "list_rollups", _fake_rollups)
    result = await service.run_mining_job(days=14)
    assert result["status"] == "ok"
    assert result["candidate_count"] >= 1
    assert result["motif_graph_count"] >= 1
    assert len(_MEM_RULES) >= 1
    assert len(_MEM_GRAPHS) >= 1
