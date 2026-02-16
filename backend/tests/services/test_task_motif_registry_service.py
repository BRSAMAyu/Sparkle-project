from __future__ import annotations

import pytest

from app.services.task_motif_registry_service import TaskMotifRegistryService, _MEM_GRAPHS, _MEM_RULES


@pytest.mark.asyncio
async def test_task_motif_registry_lifecycle() -> None:
    _MEM_RULES.clear()
    _MEM_GRAPHS.clear()
    service = TaskMotifRegistryService()

    payload = {
        "rule_id": "cr_lifecycle_1",
        "domain": "education",
        "task_type": "study_plan",
        "complexity_tier": "medium",
        "trigger_conditions": {"quality_gate_blocked_min": 3},
        "recommended_actions": ["require_minimal_clarification"],
        "expected_delta_q": 0.05,
        "support_size": 80,
        "confidence": 0.73,
        "fairness_risk": 0.08,
        "latency_risk": 0.11,
        "evidence_window": "last_14d",
        "status": "draft",
        "version": "v1",
    }
    saved = await service.upsert_rule(payload, redis_client=None)
    assert saved["status"] == "draft"

    validated = await service.validate_rule(rule_id="cr_lifecycle_1", reviewer="admin", redis_client=None)
    assert validated["status"] == "validated"
    assert validated["validated_by"] == "admin"

    approved = await service.approve_rule(
        rule_id="cr_lifecycle_1",
        reviewer="admin",
        activate=False,
        redis_client=None,
    )
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "admin"

    activated = await service.activate_rule(rule_id="cr_lifecycle_1", reviewer="admin", redis_client=None)
    assert activated["status"] == "active"
    assert activated["activated_by"] == "admin"
    assert isinstance(activated.get("status_history"), list)
    assert len(activated["status_history"]) >= 3

    rejected = await service.reject_rule(rule_id="cr_lifecycle_1", reviewer="admin", redis_client=None)
    assert rejected["status"] == "deprecated"


@pytest.mark.asyncio
async def test_task_motif_registry_graph_storage() -> None:
    _MEM_GRAPHS.clear()
    service = TaskMotifRegistryService()
    graph = {
        "graph_id": "motif_graph_1",
        "domain": "education",
        "task_type": "study_plan",
        "complexity_tier": "medium",
        "nodes": [{"id": "goal", "type": "goal"}],
        "edges": [{"source": "goal", "target": "milestones", "relation": "decompose"}],
        "coverage": 0.82,
        "stability_score": 0.79,
    }
    await service.upsert_graph(graph, redis_client=None)
    loaded = await service.get_graph("motif_graph_1", redis_client=None)
    assert loaded is not None
    assert loaded["coverage"] == 0.82
