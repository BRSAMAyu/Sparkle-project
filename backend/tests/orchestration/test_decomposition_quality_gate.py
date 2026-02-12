from app.orchestration.decomposition_quality_gate import DecompositionQualityGate
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec


def test_quality_gate_rejects_low_contract_score() -> None:
    result = DecompositionQualityGate.evaluate(
        contract={"score": 0.2, "gaps": ["missing_goal"], "version": "v1"},
        plan=None,
    )
    assert not result.passed
    assert result.decomposition_contract_score == 0.2
    assert "missing_goal" in result.decomposition_gaps


def test_quality_gate_accepts_high_quality_plan() -> None:
    plan = ExecutablePlan(
        confidence=0.82,
        tool_calls=[
            ToolCallSpec(
                id="call_1",
                name="create_plan",
                params={"title": "7-day study plan"},
            )
        ],
        success_criteria={"min_success_rate": 0.8},
        execution_order=[["call_1"]],
    )
    result = DecompositionQualityGate.evaluate(
        contract={
            "score": 0.78,
            "gaps": [],
            "version": "v1",
            "goal": "14天内完成算法复习并通过模拟面试",
            "constraints": ["14 天内完成"],
            "milestones": ["第1周补齐基础", "第2周集中刷题"],
            "acceptance_criteria": ["周测正确率达到80%"],
            "risks": ["时间不足导致复习不完整"],
        },
        plan=plan,
    )
    assert result.passed
    assert result.plan_feasibility_score >= 0.55


def test_quality_gate_rejects_required_contract_gaps() -> None:
    plan = ExecutablePlan(
        confidence=0.8,
        tool_calls=[
            ToolCallSpec(
                id="call_1",
                name="create_plan",
                params={"title": "study plan"},
                depends_on=[],
            ),
            ToolCallSpec(
                id="call_2",
                name="create_task",
                params={"title": "task 1"},
                depends_on=["call_1"],
            ),
        ],
        success_criteria={"ok": True},
        execution_order=[["call_1"], ["call_2"]],
    )
    result = DecompositionQualityGate.evaluate(
        contract={
            "score": 0.82,
            "gaps": ["missing_risks"],
            "version": "v1",
            "constraints": ["30 天内完成"],
        },
        plan=plan,
    )
    assert not result.passed
    assert "missing_risks" in result.decomposition_gaps
