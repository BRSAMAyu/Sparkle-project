from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.schemas import ExecutablePlan, RouteDecision, ToolCallSpec


def test_build_routing_history_includes_summary():
    context = {
        "summary": "用户正在推进一个跨阶段学习计划。",
        "messages": [{"role": "user", "content": "继续刚才的计划"}],
    }
    history = ChatOrchestrator._build_routing_history(context)
    assert history
    assert history[0]["role"] == "system"
    assert "Summary of prior conversation" in history[0]["content"]
    assert history[1]["content"] == "继续刚才的计划"


def test_adaptive_policy_upgrades_to_hybrid_for_low_confidence_complex_query():
    orchestrator = ChatOrchestrator.__new__(ChatOrchestrator)
    route = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.42,
        context_version=None,
    )
    updated, notes = orchestrator._apply_adaptive_routing_policy(
        route_decision=route,
        unified_routing_result=None,
        user_message="请帮我设计一个分阶段学习策略，然后给出每周执行计划和权衡说明",
        conversation_context={"summary": "此前已讨论过目标与时间限制"},
    )

    assert updated.execution_mode == "hybrid"
    assert updated.reason.startswith("adaptive:low_confidence_complex:")
    assert "upgraded_to_hybrid_low_confidence_complex" in notes


def test_meta_rule_toolchain_patch_degrades_parallelism_to_cap():
    plan = ExecutablePlan(
        tool_calls=[
            ToolCallSpec(id="a", name="create_plan", params={}),
            ToolCallSpec(id="b", name="create_task", params={}),
            ToolCallSpec(id="c", name="create_task", params={}),
        ],
        execution_order=[["a", "b", "c"]],
    )
    ChatOrchestrator._apply_meta_rule_patch_to_plan(
        executable_plan=plan,
        patch={
            "channel": "toolchain",
            "threshold_overrides": {"max_parallel_experts": 1, "timeout_multiplier": 1.2},
            "action_overrides": ["degrade_parallelism"],
        },
    )
    assert len(plan.execution_order) == 1
    assert len(plan.execution_order[0]) == 1
    assert all(step.timeout_ms >= 10000 for step in plan.tool_calls)
