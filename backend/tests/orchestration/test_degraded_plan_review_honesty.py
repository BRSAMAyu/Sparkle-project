"""wt600 — V3-FIX-302 降级链审查诚实化回归。

诚实性猎缺 F1（wt587 发现、wt591 二轮复核存活，台账 V3-FIX-302）：
synthesized fallback 计划跳过 LLM plan review 后伪造 decision=APPROVED 审查记录，
alignment_score 取人为抬升后的计划自身置信度（build_fallback_plan 把 source 伪装
langgraph、置信度抬到 >=0.35），用户面信封还告知「已记录本轮计划审查状态」。
wt591 精化：伪造记录不落 DB，失真面 = context_data -> 信封文案 / 置信带。

红→绿断言（degraded 诚实元数据契约）：
- F1-1: 熔断 OPEN 降级链——review_plan 零调用保持，但审查记录必须如实
  （decision=skipped、alignment_score=None），计划仍照常进入执行。
- F1-2: build_fallback_plan 的 source 如实标 langgraph_fallback、置信度不抬升
  （低置信底料 0.05 保持 0.05，不被抬到 0.35）。
- F1-3: 真实 fallback 构建产物按降级档位 0.05 走（不再继承 LLM 计划的
  0.8 启发式置信度）。
- F1-4: 审查拒绝后降级替换的第二处产物点——替换计划如实记
  decision=skipped（不再被原计划 review dict 覆写、不再伪造 APPROVED），
  original_review_decision 保留。
- F1-5: 信封消费面——降级记录走高亮「计划为降级生成，未经 LLM 审查」、
  不再宣称「已记录本轮计划审查状态」；completion_state 不误判 needs_input；
  置信带按真实低置信度落 cautious（不被 route 置信度顶成 high）；
  continuity banner 如实。
- F1-6: source 消费面兼容——langgraph_fallback 受控规划链保持既有
  generate_tasks_for_plan bypass（降级链不被 wt596 HITL 闸门卡死），
  而 confirm 级工具判定不因 source 变化被绕过。
"""

from __future__ import annotations

import importlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.orchestration.schemas import ExecutablePlan, RouteDecision, ToolCallSpec, ValidationResult
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.ux_envelope import UXEnvelopeBuilder
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

DEGRADED_SOURCE = "langgraph_fallback"
DEGRADED_DECISION = "skipped"
DEGRADED_CONFIDENCE = 0.05
HONEST_HIGHLIGHT = "计划为降级生成，未经 LLM 审查"
FAKE_HIGHLIGHT = "已记录本轮计划审查状态"


def _kwargs(stream_callback, session_id: str, message: str = "帮我做复习计划"):
    return {
        "user_message": message,
        "user_id": str(uuid.uuid4()),
        "session_id": session_id,
        "active_db": None,
        "plan_id": None,
        "conversation_context": None,
        "plan_context": None,
        "stream_callback": stream_callback,
        "user_context_payload": {},
        "orchestration_trace": None,
    }


def _install_circuit_open_stubs(orchestrator) -> SimpleNamespace:
    """熔断 OPEN 降级链外围 stub；build_fallback_plan 走真实实现。"""
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(False, "failure_count_exceeded"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(
        return_value=SimpleNamespace(snapshot_id="snap-wt600", context_versions={})
    )
    orchestrator.version_conflict_service.check_all_conflicts = AsyncMock(
        return_value=SimpleNamespace(has_conflict=False)
    )
    # 工厂默认 validate_plan（is_valid=True、无风险判定），preflight 放行。
    orchestrator.grounding_validator.preflight_check = AsyncMock(
        return_value={"is_ready": True, "blocked_by": []}
    )
    return SimpleNamespace(snapshot_id="snap-wt600")


@pytest.mark.asyncio
async def test_f1_1_fallback_review_record_is_not_fake_approved(orchestrator_factory, monkeypatch):  # noqa: F811
    """F1-1 熔断 OPEN：跳过 LLM 审查可以，但审查记录必须如实。"""
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()
    _install_circuit_open_stubs(orchestrator)

    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    review_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        execution_engine_module,
        "plan_review_service",
        SimpleNamespace(review_plan=review_mock, store_review_result=AsyncMock(return_value="action-x")),
    )

    frames: list = []

    async def stream_callback(response) -> None:
        frames.append(response)

    state = WorkflowState()
    decision, plan, _snapshot, should_return = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low"),
        state=state,
        **_kwargs(stream_callback, "sess-wt600-f1-1"),
    )

    # 行为保持：降级链仍可执行（跳过 LLM 审查本身是允许的降级）。
    assert should_return is False
    assert plan is not None
    assert state.context_data.get("executable_plan") is plan
    assert "synthesized fallback" in str(plan.rationale).lower(), "fallback 产出点 rationale 契约必须保持"
    review_mock.assert_not_awaited(), "降级链本就不该调 LLM 审查（现状保持）"

    record = state.context_data.get("plan_review")
    assert isinstance(record, dict), "降级链仍须写入审查状态供信封消费"
    assert record.get("decision") == DEGRADED_DECISION, (
        f"跳过审查必须如实记 skipped（现状伪造 approved: {record.get('decision')}）"
    )
    assert record.get("alignment_score") is None, (
        f"未经 LLM 审查的 alignment_score 必须为 None（现状伪造 {record.get('alignment_score')}）"
    )
    assert record.get("review_skipped") is True, "降级记录必须带 review_skipped 标记（review 未执行可区分）"
    assert record.get("confidence") == plan.confidence, "记录置信度必须等于计划真实置信度"


@pytest.mark.asyncio
async def test_f1_2_fallback_plan_source_and_confidence_are_honest():
    """F1-2 低置信底料不被抬升、source 不伪装（wt591 实验 2 复刻）。"""
    planner = LangGraphPlanner(redis_client=None)

    def _low_confidence_convert(langgraph_state, snapshot, user_id, session_id):
        return ExecutablePlan(
            schema_version="5.0",
            source="langgraph",
            confidence=0.05,
            rationale="low-confidence base",
        )

    planner._convert_to_plan = _low_confidence_convert  # type: ignore[method-assign]

    plan = planner.build_fallback_plan(
        message="帮我做复习计划",
        snapshot=SimpleNamespace(snapshot_id="snap-f1-2", context_versions={}),
        user_id="user-wt600",
        session_id="sess-wt600-f1-2",
        rationale="Circuit breaker OPEN: failure_count_exceeded. Using synthesized fallback plan.",
    )

    assert plan.source == DEGRADED_SOURCE, f"fallback source 必须如实标 {DEGRADED_SOURCE}（现状伪装: {plan.source}）"
    assert plan.confidence == 0.05, f"置信度不得抬升（现状: {plan.confidence}）"
    assert "synthesized fallback" in plan.rationale.lower(), "rationale 契约保持"


@pytest.mark.asyncio
async def test_f1_3_real_fallback_build_uses_degraded_confidence_tier():
    """F1-3 真实构建产物：降级计划按 0.05 真实档位，不继承 LLM 计划的 0.8 启发式。"""
    planner = LangGraphPlanner(redis_client=None)
    plan = planner.build_fallback_plan(
        message="帮我制定一份两周的线性代数复习计划",
        snapshot=SimpleNamespace(snapshot_id="snap-f1-3", context_versions={}),
        user_id="user-wt600",
        session_id="sess-wt600-f1-3",
        rationale="Planner timeout after 3s, synthesized fallback",
    )

    assert plan.source == DEGRADED_SOURCE
    assert plan.confidence == DEGRADED_CONFIDENCE, (
        f"降级计划真实置信度是模板档位 {DEGRADED_CONFIDENCE}（现状: {plan.confidence}）"
    )
    assert plan.tool_calls, "降级计划仍须产出可执行工具链（行为保持）"


def _rejected_review(plan_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        decision="rejected",
        confidence=0.9,
        alignment_score=0.2,
        alignment_summary="stub review rejected",
        reasoning_summary="",
        reasoning_details=[],
        reasoning_source="stub",
        user_facing_reason="",
        review_id="review-wt600",
        plan_id=plan_id,
        quality_report={},
        review_feedback_entry={},
        to_dict=lambda: {"decision": "rejected", "confidence": 0.9, "alignment_score": 0.2},
    )


@pytest.mark.asyncio
async def test_f1_4_review_degraded_replacement_keeps_honest_record(orchestrator_factory, monkeypatch):  # noqa: F811
    """F1-4 第二产物点：审查拒绝后降级替换的计划必须如实记 skipped，不被原计划 review dict 覆写。"""
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()

    plan = ExecutablePlan(
        schema_version="5.0",
        source="langgraph",
        confidence=0.9,
        rationale="wt600 complex plan",
        collaboration_mode="single",
        agents_involved=[],
        tool_calls=[
            ToolCallSpec(id="t1", name="create_plan", params={"goal": "两周掌握线性代数"}),
            ToolCallSpec(id="t2", name="create_task", params={"title": "任务一"}),
            ToolCallSpec(id="t3", name="create_task", params={"title": "任务二"}),
            ToolCallSpec(id="t4", name="create_task", params={"title": "任务三"}),
        ],
    )

    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator.lang_graph_planner.plan = AsyncMock(return_value=plan)
    orchestrator.lang_graph_planner.pop_rendered_plan_artifact = MagicMock(return_value=None)
    orchestrator.lang_graph_planner.get_plan_summary = MagicMock(return_value="summary")
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(
        return_value=SimpleNamespace(snapshot_id="snap-wt600-f1-4", context_versions={})
    )
    orchestrator.version_conflict_service.check_all_conflicts = AsyncMock(
        return_value=SimpleNamespace(has_conflict=False)
    )
    orchestrator.grounding_validator.validate_plan = AsyncMock(
        return_value=ValidationResult(is_valid=True, requires_confirmation=False, requires_hitl=False)
    )
    orchestrator.grounding_validator.preflight_check = AsyncMock(
        return_value={"is_ready": True, "blocked_by": []}
    )

    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    review_mock = AsyncMock(return_value=_rejected_review(plan.plan_id))
    monkeypatch.setattr(
        execution_engine_module,
        "plan_review_service",
        SimpleNamespace(review_plan=review_mock, store_review_result=AsyncMock(return_value="action-y")),
    )

    frames: list = []

    async def stream_callback(response) -> None:
        frames.append(response)

    state = WorkflowState()
    _decision, replaced_plan, _snapshot, should_return = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="plan request", risk_level="low"),
        state=state,
        **_kwargs(stream_callback, "sess-wt600-f1-4", message="帮我制定学习计划"),
    )

    assert should_return is False, "审查拒绝降级为最小计划链后仍须照常进入执行（行为保持）"
    assert replaced_plan is not None and replaced_plan is not plan, "复杂计划必须被替换为降级计划"
    assert "synthesized fallback" in str(replaced_plan.rationale).lower(), "替换产物 rationale 契约保持"

    record = state.context_data.get("plan_review")
    assert isinstance(record, dict)
    assert record.get("decision") == DEGRADED_DECISION, (
        f"替换计划未经审查，必须如实记 skipped（现状: {record.get('decision')}——"
        "要么伪造 approved，要么被原计划 rejected review dict 覆写）"
    )
    assert record.get("alignment_score") is None, "替换计划未经审查，alignment_score 必须为 None"
    assert record.get("original_review_decision") == "rejected", "原计划真实审查结论必须保留可追溯"


def test_f1_5_envelope_honest_copy_band_and_completion_for_degraded():
    """F1-5 信封消费面：降级记录走如实文案/置信带/完成态，不再冒充已审查。"""
    builder = UXEnvelopeBuilder()

    # 1) highlights：降级记录如实文案，不再宣称「已记录本轮计划审查状态」。
    degraded_state = WorkflowState(
        context_data={"plan_review": {"decision": DEGRADED_DECISION, "alignment_score": None, "confidence": 0.05}}
    )
    memory_updates = builder._memory_updates(degraded_state, {})
    assert HONEST_HIGHLIGHT in memory_updates["highlights"], (
        f"降级记录必须出现如实文案（现状: {memory_updates['highlights']}）"
    )
    assert FAKE_HIGHLIGHT not in memory_updates["highlights"], "降级记录不得再宣称已记录计划审查状态"

    reviewed_state = WorkflowState(context_data={"plan_review": {"decision": "approved", "alignment_score": 0.9}})
    reviewed_updates = builder._memory_updates(reviewed_state, {})
    assert FAKE_HIGHLIGHT in reviewed_updates["highlights"], "真实审查记录的既有文案保持"

    # 2) completion_state：skipped 不是需要用户输入的审查结论。
    completion = builder._completion_state(degraded_state, SimpleNamespace(tool_calls=[{"name": "create_plan"}]), None)
    assert completion != "needs_input", f"降级计划不得被误判为 needs_input（现状: {completion}）"

    # 3) 置信带：真实低置信度按 cautious 档走，不被 route 置信度顶成 high/medium 默认。
    band = builder._confidence_band(
        SimpleNamespace(source=DEGRADED_SOURCE, confidence=DEGRADED_CONFIDENCE, tool_calls=[]),
        SimpleNamespace(confidence=0.9),
        None,
    )
    assert band == "cautious", f"降级计划置信带必须按真实低置信度落 cautious（现状: {band}）"

    # 4) continuity banner：降级链不再谎称「已生成计划审查结果」。
    banner = builder._continuity_banner(conversation_context=None, plan_context=None, final_state=degraded_state)
    assert banner is not None
    assert "降级" in str(banner.get("message") or ""), f"banner 必须如实说明降级（现状: {banner}）"
    assert "计划审查结果" not in str(banner.get("message") or ""), "banner 不得再谎称已生成审查结果"

    # 5) 会话阶段锁定：降级记录 + 可执行计划仍是 plan_ready（词表变更不误伤阶段判定）。
    stage = builder._conversation_stage(
        chat_mode="study_plan",
        completion_state=completion,
        recovery_kind="none",
        final_state=degraded_state,
        executable_plan=SimpleNamespace(tool_calls=[{"name": "create_plan"}]),
        execution_validation=None,
        plan_context=None,
        full_response="第一步",
    )
    assert stage == "plan_ready", f"降级计划就绪阶段不得回退（现状: {stage}）"


@pytest.mark.asyncio
async def test_f1_6_degraded_source_keeps_planning_bypass():
    """F1-6 source 消费面兼容：降级受控链保持 bypass，confirm 级工具判定不被绕过。"""
    import importlib.util
    from pathlib import Path

    from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

    dynamic_tool_registry.ensure_package_registered("app.tools")
    assert "batch_create_tasks" in {t.name for t in dynamic_tool_registry.get_all_tools()}

    # _install_import_stubs 会把 sys.modules 的 grounding_validator 换成桩；
    # 按文件路径以私有名加载真实实现（与 test_hitl_gate_wiring 同法）。
    real_path = Path(__file__).resolve().parents[2] / "app" / "orchestration" / "grounding_validator.py"
    spec = importlib.util.spec_from_file_location("_wt600_real_grounding_validator", real_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = module.GroundingValidator(redis_client=None)

    degraded_chain = ExecutablePlan(
        schema_version="5.0",
        source=DEGRADED_SOURCE,
        confidence=DEGRADED_CONFIDENCE,
        rationale="wt600 degraded planning chain, synthesized fallback",
        tool_calls=[
            ToolCallSpec(id="t0", name="create_plan", params={"goal": "两周掌握线性代数"}),
            ToolCallSpec(
                id="t1",
                name="generate_tasks_for_plan",
                params={"plan_id": "plan-1"},
                depends_on=["t0"],
            ),
        ],
    )
    verdict = await validator.validate_plan(plan=degraded_chain)
    assert verdict.is_valid is True
    assert verdict.requires_hitl is False, (
        "降级受控规划链必须保持既有 bypass（否则降级链被 wt596 闸门卡死，违背降级可执行契约）"
    )
    assert verdict.requires_confirmation is False

    risky_plan = ExecutablePlan(
        schema_version="5.0",
        source=DEGRADED_SOURCE,
        confidence=DEGRADED_CONFIDENCE,
        rationale="wt600 degraded risky plan",
        tool_calls=[
            ToolCallSpec(id="t1", name="batch_create_tasks", params={"tasks": [{"title": "任务一"}]}),
        ],
    )
    risky_verdict = await validator.validate_plan(plan=risky_plan)
    assert risky_verdict.requires_hitl is True, "confirm 级工具判定不得因 source 变化被绕过"
