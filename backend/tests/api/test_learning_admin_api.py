from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser
from app.api.v1.learning_admin import router as learning_admin_router
from app.services.policy_registry_service import PolicyRegistryService, _MEM_CANDIDATES, _MEM_POLICIES


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(learning_admin_router)
    app.dependency_overrides[get_current_active_superuser] = lambda: SimpleNamespace(id=uuid4(), is_superuser=True)
    return TestClient(app)


def test_learning_admin_candidate_approve_flow(monkeypatch):
    monkeypatch.setattr("app.services.policy_candidate_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANDIDATE_PIPELINE", True)
    monkeypatch.setattr("app.services.policy_registry_service.settings.ENABLE_POLICY_CANARY_ROLLOUT", True)

    _MEM_CANDIDATES.clear()
    _MEM_POLICIES.clear()
    registry = PolicyRegistryService(redis_client=None)

    candidate = {
        "id": "pc_test_1",
        "policy_id": "expert_strategy_v2:general_v2:candidate_test",
        "base_policy": "expert_strategy_v2:general_v2",
        "strategy_pack": "general_v2",
        "channel": "routing",
        "weights": {"semantic_weight": 0.4, "affinity_weight": 0.2, "success_weight": 0.2, "complexity_weight": 0.1, "decomposition_weight": 0.05, "latency_weight": 0.05},
        "thresholds": {"high_complexity_threshold": 0.75, "medium_complexity_threshold": 0.5, "min_selected_score": 0.34},
        "created_from_window": "last_7d",
        "expected_delta": 0.08,
        "risk_level": "medium",
        "status": "pending",
    }

    client = _build_client()
    with client:
        client.app.dependency_overrides[get_current_active_superuser] = lambda: SimpleNamespace(id=uuid4(), is_superuser=True)
        # seed candidate in in-memory registry
        import anyio
        anyio.run(registry.create_candidate, candidate)

        resp = client.get("/admin/learning/policy-candidates")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

        approve = client.post("/admin/learning/policy-candidates/pc_test_1/approve", json={"note": "ship canary"})
        assert approve.status_code == 200
        assert approve.json()["candidate"]["status"] == "approved"

        weekly = client.get("/admin/learning/weekly-report")
        assert weekly.status_code == 200
        body = weekly.json()
        assert "policy_report" in body
        assert "fairness" in body

        fairness = client.get("/admin/learning/fairness-dashboard")
        assert fairness.status_code == 200
        assert "fairness_overview" in fairness.json()

        fairness_by_task = client.get("/admin/learning/fairness-dashboard?view=task")
        assert fairness_by_task.status_code == 200
        assert fairness_by_task.json()["view"] == "task"
        reasoning_weekly = client.get("/admin/learning/reasoning-weekly-report")
        assert reasoning_weekly.status_code == 200
        assert "q_score_by_policy" in reasoning_weekly.json()
        assert "q_score_by_cube" in reasoning_weekly.json()

        meta_list = client.get("/admin/learning/meta-candidates?channel=routing")
        assert meta_list.status_code == 200
        assert len(meta_list.json()["items"]) >= 1

        meta_report = client.get("/admin/learning/meta-weekly-report")
        assert meta_report.status_code == 200
        assert "candidate_count_by_channel" in meta_report.json()

        gen_meta = client.post("/admin/learning/meta-candidates/generate?channels=routing,prompt")
        assert gen_meta.status_code == 200
        assert "channels" in gen_meta.json()

        tuning = client.get("/admin/learning/meta-tuning-package")
        assert tuning.status_code == 200
        assert "recommendations" in tuning.json()

        research_benchmarks = client.get("/admin/learning/research-benchmarks")
        assert research_benchmarks.status_code == 200
        assert "candidate_pool" in research_benchmarks.json()

        research_candidate = {
            "id": "pc_research_api_1",
            "policy_id": "expert_strategy_v2:general_v2:candidate_research_api_1",
            "base_policy": "expert_strategy_v2:general_v2",
            "strategy_pack": "general_v2",
            "channel": "routing",
            "scope_type": "global",
            "scope_key": "all",
            "research_track": True,
            "weights": {"semantic_weight": 0.4},
            "thresholds": {"min_selected_score": 0.35},
            "status": "research_pending",
        }
        anyio.run(registry.create_candidate, research_candidate)
        promote = client.post("/admin/learning/research-promotions/pc_research_api_1/approve", json={"note": "promote"})
        assert promote.status_code == 200
        assert promote.json()["status"] == "ok"
