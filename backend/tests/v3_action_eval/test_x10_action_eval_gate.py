"""X-10 · 评测 gate 测试 —— 场景集守卫 + 判定器单测（含变异红证）.

三层：
1. **场景集结构守卫**：≥60 场景、家族×旅程覆盖、expected 封闭键集；
2. **判定器单测（变异红证）**：对合成 six-tuple 注入错误（错 mode / 假成功 /
   高风险 auto / 幂等破坏 / 极性谎报 / LLM 泄漏），判定器必须红——证明
   77/77 全绿不是判定器失明；
3. **真实端到端抽检**：每家族至少一个场景走真实服务层+DB 复跑（pytest 内联），
   与 devtools CLI 全量轮互为印证。
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.action_proposal import ActionProposal
from app.models.agent_run import AgentRun
from app.models.user_settings import UserSettings
from app.services.action_allocation_policy import AllocationFactors, decide_allocation
from tests.v3_action_eval.dbfixture import ScenarioDB
from tests.v3_action_eval.runner import run_round, run_scenario
from tests.v3_action_eval.scenario_schema import (
    GOLDEN_JOURNEYS,
    SIX_TUPLE_KEYS,
    coverage_matrix,
    load_scenarios,
)
from tests.v3_action_eval.verdicts import judge_scenario

# ---------------------------------------------------------------------------
# 1. 场景集结构守卫
# ---------------------------------------------------------------------------


def test_scenario_set_has_at_least_60_scenarios():
    scenarios = load_scenarios()
    assert len(scenarios) >= 60, f"X-10 requires >=60 scenarios, got {len(scenarios)}"


def test_scenario_set_covers_all_families_and_golden_journeys():
    matrix = coverage_matrix(load_scenarios())
    for family in ("allocation", "authorization", "proposal", "run_steps", "outcome", "journey"):
        assert matrix["families"].get(family, 0) >= 4, f"family {family} under-covered: {matrix['families']}"
    assert set(matrix["journeys"]) >= GOLDEN_JOURNEYS, f"GJ04-07 must all be covered, got {matrix['journeys']}"


def test_expected_targets_are_closed_vocabulary():
    """expected 键封闭（防 fixture 漂移导致判定器静默跳过检查）。"""
    allowed = {
        "mode",
        "requires_human_approval",
        "requires_user_authored_evidence",
        "feasible_modes",
        "why_contains",
        "offer_allowed",
        "offer_reason",
        "offer_downgrade",
        "offer_requires_human_approval",
        "authorization_mode",
        "reason_contains",
        "proposal_status",
        "task_status",
        "task_updated",
        "receipt_present",
        "commit_allowed",
        "denied",
        "missing_record_denied",
        "second_applied",
        "second_already_committed",
        "second_created",
        "second_replay",
        "transitions_count",
        "proposals_count",
        "tasks_created",
        "receipt_effects_count",
        "subjectless",
        "error",
        "error_expected",
        "sweep_count",
        "actual_minutes_not_estimated",
        "actual_minutes_max",
        "run_status",
        "terminal_reason",
        "wait_kind",
        "step_completed_s1",
        "step_completed_s2_by",
        "step_completed",
        "event_step_completed",
        "wire_steps_count",
        "wire_owner_first",
        "wire_owner_second",
        "steps_total",
        "plan_owner_unchanged",
        "awaiting_step_id",
        "awaiting_state",
        "awaiting_prompt",
        "cold_start_ownership",
        "cold_start_prompt",
        "first_key_recorded",
        "resume_count",
        "user_resumed_events",
        "outcome_polarity",
        "run_outcome_polarity",
        "truth_class",
        "truth_class_not_actual",
        "never_positive",
        "polarity",
        "ledger_entry_present",
        "outcome_captured",
        "declared_preserved",
        "run_receipt_materialized",
        "task_outcome_actual_via_receipt",
        "approval_gate_visited",
        "awaiting_visited",
        "receipt_ref_present",
        "owner_sequence",
        "high_risk_auto_zero",
        "stuck_recorded",
        "rescope_history",
        "rescope_fields_applied",
        "evidence_fulfilled",
        "study_record_echo",
        "ids_equal",
        "id_prefix",
        "event_name",
        "content_free",
        "phases",
    }
    for scenario in load_scenarios():
        unknown = set(scenario.expected) - allowed
        assert not unknown, f"{scenario.scenario_id}: unknown expected keys {sorted(unknown)}"


# ---------------------------------------------------------------------------
# 2. 判定器单测（变异红证：判定器必须能红）
# ---------------------------------------------------------------------------


def _synthetic_six_tuple(**overrides):
    six = {
        "decision": {"mode": "hybrid", "decision_id": "alloc_x", "why": ["D6.gray_zone_default_hybrid"]},
        "execution": {
            "steps": [{"op": "decide_allocation", "ok": True, "error": None, "elapsed_ms": 0.1}],
            "service_ops": 1,
        },
        "result": {"mode": "hybrid"},
        "outcome": {"kind": "decision_only"},
        "latency": {"total_ms": 1.0, "phases": {}},
        "cost": {"llm_calls": 0, "llm_tokens": 0, "service_ops": 1, "db_transactions": 1},
    }
    six.update(overrides)
    return six


def _scenario_by_id(scenario_id: str):
    return next(s for s in load_scenarios() if s.scenario_id == scenario_id)


def _failed_ids(verdict: dict) -> list[str]:
    return [c["id"] for c in verdict["checks"] if not c["passed"]]


@pytest.mark.asyncio
async def test_judge_catches_wrong_allocation_decision():
    scenario = _scenario_by_id("alloc_a01_learning_user_core_writing")
    six = _synthetic_six_tuple(
        decision={"mode": "agent", "decision_id": "alloc_x", "why": []}, result={"mode": "agent"}
    )
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        verdict = await judge_scenario(scenario, six, ctx)
    assert verdict["verdict"] == "fail"
    failed = _failed_ids(verdict)
    # 记录面与策略复算不一致（谎报 agent）必须被 deterministic_recompute 抓住
    assert any("decision.deterministic_recompute" in f for f in failed), failed


@pytest.mark.asyncio
async def test_judge_catches_high_risk_auto_agent():
    """变异：高风险因子被误判 agent → high_risk_auto 旗标必须点亮（进全局计数）。"""
    scenario = _scenario_by_id("alloc_a10_high_risk_low_tool_human")
    factors = AllocationFactors.coerce(scenario.inputs["factors"])
    real = decide_allocation(factors)
    assert real.mode != "agent"
    six = _synthetic_six_tuple(
        decision={"mode": "agent", "decision_id": "alloc_bad", "why": []}, result={"mode": "agent"}
    )
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        verdict = await judge_scenario(scenario, six, ctx)
    assert verdict["verdict"] == "fail"
    assert verdict["high_risk_auto"] is True, "mutated high-risk auto must be flagged for the global counter"


@pytest.mark.asyncio
async def test_judge_catches_false_success_on_proposal():
    """变异：场景声称 COMMITTED 但 DB 真相是 PENDING → 判定必须红（假成功抓现形）。"""
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context(auto_grant=False)
        proposal = ActionProposal(
            id=uuid4(),
            user_id=ctx.user.id,
            status="PENDING",
            command_type="task.update_fields",
            source="task",
            subject_type="task",
            payload={"task_id": str(uuid4()), "fields": {"priority": 1}},
            authorization={"mode": "confirmation", "reason_codes": ["awaiting_user_confirmation"]},
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30),
        )
        ctx.session.add(proposal)
        await ctx.session.commit()

        scenario = _scenario_by_id("auth_z01_service_auto_grant_executes")
        six = _synthetic_six_tuple(
            decision={"mode": "auto"},
            result={
                "authorization_mode": "auto",
                "proposal_status": "COMMITTED",  # 谎报
                "task_status": "PENDING",
                "task_title": "unchanged",
                "receipt_present": True,  # 谎报
            },
            outcome={"kind": "authorization_service_path", "executed": True},
        )
        verdict = await judge_scenario(scenario, six, ctx)
        assert verdict["verdict"] == "fail"
        failed = _failed_ids(verdict)
        assert any("db.proposal_status" in f for f in failed), failed
        assert any("db.receipt_present_on_commit" in f for f in failed), failed


@pytest.mark.asyncio
async def test_judge_catches_double_resume_violation():
    """变异：同一步骤被 resume 两次（幂等破坏）→ resume_count 独立复核必须红。"""
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        steps = [
            {"step_id": "s1", "ordinal": 1, "owner": "human", "completion_condition": {"kind": "user_confirmation"}},
        ]
        run_row = AgentRun(
            id=uuid4(),
            user_id=ctx.user.id,
            kind="execution",
            objective="mutated double resume",
            status="RUNNING",
            steps=steps,
            steps_total=1,
            heartbeat_at=datetime.now(UTC).replace(tzinfo=None),
        )
        ctx.session.add(run_row)
        await ctx.session.commit()

        scenario = _scenario_by_id("run_r08_double_confirm_same_key_first_wins")
        six = _synthetic_six_tuple(
            decision={"step_plan": [{"step_id": "s1", "owner": "human"}]},
            result={"run_status": "RUNNING", "resume_count": 2, "user_resumed_events": 2, "second_replay": False},
            outcome={"kind": "run_step_state"},
        )
        verdict = await judge_scenario(scenario, six, ctx)
        assert verdict["verdict"] == "fail"
        failed = _failed_ids(verdict)
        assert any("db.resume_count" in f for f in failed), failed


@pytest.mark.asyncio
async def test_judge_catches_outcome_polarity_lie():
    """变异：失败 run 谎报 POSITIVE outcome → 极性封闭映射复核必须红。"""
    scenario = _scenario_by_id("outc_o08_failed_run_negative")
    six = _synthetic_six_tuple(
        decision={"terminal_action": "run_failed"},
        result={"run_outcome_polarity": "positive", "never_positive": False},
        outcome={"kind": "outcome_capture"},
    )
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        verdict = await judge_scenario(scenario, six, ctx)
    assert verdict["verdict"] == "fail"
    failed = _failed_ids(verdict)
    # 结果面谎报被 target 检查抓住；封闭极性映射（真源复算）确认真实极性是 negative
    assert any("target.run_outcome_polarity" in f for f in failed), failed
    polarity_map = next(c for c in verdict["checks"] if c["id"] == "db.run_receipt_polarity_map")
    assert polarity_map["passed"] and polarity_map["actual"] == "negative", polarity_map


@pytest.mark.asyncio
async def test_judge_catches_llm_cost_leak():
    """变异：cost.llm_calls > 0 → zero-LLM 断言必须红（禁止真实 LLM 红线）。"""
    scenario = _scenario_by_id("alloc_a05_delegated_mechanical_batch")
    six = _synthetic_six_tuple(cost={"llm_calls": 3, "llm_tokens": 1200, "service_ops": 1, "db_transactions": 1})
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        verdict = await judge_scenario(scenario, six, ctx)
    assert verdict["verdict"] == "fail"
    assert any(c["id"] == "cost.zero_llm" and not c["passed"] for c in verdict["checks"])


@pytest.mark.asyncio
async def test_judge_catches_unexpected_execution_error():
    scenario = _scenario_by_id("prop_p01_approve_complete_receipt_and_honest_minutes")
    six = _synthetic_six_tuple(
        execution={
            "steps": [{"op": "approve", "ok": False, "error": "unexpected:RuntimeError", "elapsed_ms": 1.0}],
            "service_ops": 2,
        },
        result={},
        outcome={},
    )
    async with ScenarioDB() as sdb:
        ctx = await sdb.new_context()
        verdict = await judge_scenario(scenario, six, ctx)
    assert verdict["verdict"] == "fail"
    assert any(c["id"] == "execution.no_unexpected_error" and not c["passed"] for c in verdict["checks"])


# ---------------------------------------------------------------------------
# 3. 真实端到端抽检（pytest 内联复跑；全量轮由 devtools CLI 执行）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inline_rerun_core_cases_all_families():
    """每家族抽 1 场景真实复跑（含 GJ07），全部必须 pass——防止 CLI 与测试漂移。"""
    sample_ids = [
        "alloc_a04_learning_adversarial_full_pressure",
        "auth_z03_irreversible_target_never_auto",
        "prop_p07_expired_approve_persists_expired",
        "run_r09_double_confirm_different_keys_still_once",
        "outc_o07_partial_run_neutral_never_positive",
        "journey_gj07_hybrid_prep_await_resume",
    ]
    scenarios = [s for s in load_scenarios() if s.scenario_id in sample_ids]
    payload = await run_round(scenarios)
    assert payload["summary"]["pass"] == len(sample_ids), payload["summary"]["failed_cases"]
    assert payload["summary"]["false_success_count"] == 0
    assert payload["summary"]["high_risk"]["auto_agent_violations"] == 0
    assert payload["meta"]["real_llm_calls"] == 0


@pytest.mark.asyncio
async def test_runner_six_tuple_complete_and_deterministic_rerun():
    """六元组恒完整；同场景复跑判定稳定（确定性口径）。"""
    scenario = _scenario_by_id("alloc_a01_learning_user_core_writing")
    first = await run_scenario(scenario)
    second = await run_scenario(scenario)
    for case in (first, second):
        for key in SIX_TUPLE_KEYS:
            assert key in case["six_tuple"]
    assert first["verdict"]["verdict"] == second["verdict"]["verdict"] == "pass"
    # decision_id 确定性：同因子同决策 id
    assert (
        first["six_tuple"]["decision"]["decision_id"] == second["six_tuple"]["decision"]["decision_id"]
    )
