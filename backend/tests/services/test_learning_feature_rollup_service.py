from __future__ import annotations

import pytest

from app.services.learning_event_service import _MEM_EVENTS, LearningEventService
from app.services.learning_feature_rollup_service import _MEM_ROLLUPS, LearningFeatureRollupService


async def _seed_events(service: LearningEventService) -> None:
    await service.emit(
        event_type="expert_selected",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={},
    )
    await service.emit(
        event_type="expert_fallback",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"reason": "reduce_expert_count_low_signal"},
    )
    await service.emit(
        event_type="response_feedback",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        trace_id="trace-rollup-1",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"feedback_type": "down"},
    )
    await service.emit(
        event_type="plan_execution_outcome",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        trace_id="trace-rollup-1",
        response_id="resp-rollup-1",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"success": False, "latency_ms": 2100},
    )
    await service.emit(
        event_type="prompt_selected",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="meta_policy_v1:prompt:general_v2:abc",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"prompt_version": "v2"},
    )
    await service.emit(
        event_type="prompt_applied",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="meta_policy_v1:prompt:general_v2:abc",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        trace_id="trace-rollup-1",
        response_id="resp-rollup-1",
        data={"prompt_version": "v2"},
    )
    await service.emit(
        event_type="toolchain_selected",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="meta_policy_v1:toolchain:general_v2:def",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        trace_id="trace-rollup-1",
        response_id="resp-rollup-1",
        data={"toolchain_id": "langgraph_default"},
    )
    await service.emit(
        event_type="plan_repair_triggered",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"repair_actions": ["degrade_parallelism"]},
    )
    await service.emit(
        event_type="plan_repair_succeeded",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="expert_auto",
        data={"repair_actions": ["degrade_parallelism"]},
    )
    await service.emit(
        event_type="checkpoint_done",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="execution_copilot",
        data={"status": "done"},
    )
    await service.emit(
        event_type="checkpoint_skipped",
        user_id="u1",
        session_id="s1",
        workflow_id="expert_auto_workflow",
        policy_id="expert_strategy_v2:general_v2",
        strategy_pack="general_v2",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc123def456",
        complexity_tier="medium",
        task_type="execution_copilot",
        data={"status": "skipped"},
    )


@pytest.mark.asyncio
async def test_learning_feature_rollup_builds_q_score(monkeypatch):
    monkeypatch.setattr("app.services.learning_event_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)
    monkeypatch.setattr("app.services.learning_feature_rollup_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)

    _MEM_EVENTS.clear()
    _MEM_ROLLUPS.clear()

    event_service = LearningEventService(redis_client=None)
    await _seed_events(event_service)

    rollup_service = LearningFeatureRollupService(redis_client=None)
    summary = await rollup_service.run_rollup_job(window_minutes=60)
    assert summary["status"] == "ok"
    assert summary["events"] >= 4

    rows = await rollup_service.list_rollups(days=1)
    assert rows
    row = next(
        item for item in rows
        if int((item.get("counts") or {}).get("expert_selected", 0)) > 0
    )
    total_prompt_selected = sum(int((item.get("counts") or {}).get("prompt_selected", 0)) for item in rows)
    total_prompt_applied = sum(int((item.get("counts") or {}).get("prompt_applied", 0)) for item in rows)
    total_toolchain_selected = sum(int((item.get("counts") or {}).get("toolchain_selected", 0)) for item in rows)
    assert row["strategy_pack"] == "general_v2"
    assert row["cohort_id"].startswith("cohort::")
    assert row["user_scope"].startswith("usr::")
    assert row["counts"]["expert_selected"] >= 1
    assert row["counts"]["expert_fallback"] >= 1
    assert row["counts"]["feedback_down"] >= 1
    assert total_prompt_selected >= 1
    assert total_prompt_applied >= 1
    assert total_toolchain_selected >= 1
    assert any(0.0 <= float(item.get("prompt_apply_rate", 0.0)) <= 1.0 for item in rows)
    assert any(0.0 <= float(item.get("repair_success_rate", 0.0)) <= 1.0 for item in rows)
    assert any(0.0 <= float(item.get("checkpoint_done_rate", 0.0)) <= 1.0 for item in rows)
    assert any(0.0 <= float(item.get("checkpoint_skip_rate", 0.0)) <= 1.0 for item in rows)
    assert isinstance(row.get("failure_pattern_topn", []), list)
    assert 0.0 <= float(row["q_score"]) <= 1.0
