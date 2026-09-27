"""V3-FIX-492 回归测试：plan_review 可行性检查 daily_hours None 守卫。

修前 ``_validate_feasibility`` :939 ``if _is_liberal_arts(user_background) and daily_hours < 3:``
在「difficulty ∈ {expert, master, 精通} 且 user_background 判定文科 且 tool_calls
参数缺 daily_hours 键」三重合取下对 None 裸比较直接 TypeError——快速审查通道
（_quick_rule_check 自动批准路径）随之 500 崩。:934 与 :948 同函数分支均带
``daily_hours and`` 短路守卫，:939 为漏网不一致点。
"""

from __future__ import annotations

import pytest

from app.orchestration.plan_review_service import PlanReviewService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

LIBERAL_ARTS_CONTEXT = {"skill_level": "expert", "user_background": "文科"}


def _expert_plan_with_params(params: dict) -> ExecutablePlan:
    # 工具名不能全落 SAFE_TOOL_CATEGORIES（query/get/...）——否则 _quick_rule_check
    # 在 feasibility 之前就走 all_tools_are_read_only 短路，打不到 :939 病灶。
    return ExecutablePlan(
        confidence=0.97,
        rationale="expert goal plan",
        tool_calls=[
            ToolCallSpec(
                id="call_1",
                name="generate_study_material",
                params=params,
                timeout_ms=10000,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_expert_liberal_arts_missing_daily_hours_does_not_crash():
    """缺 daily_hours 键：不得 TypeError，按既有缺省语义放行（与 :934 None 跳过一致）。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert"})  # 无 daily_hours 键

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is True


@pytest.mark.asyncio
async def test_quick_rule_check_missing_daily_hours_auto_approves():
    """快速审查通道端到端：缺参不再 500，高置信简单计划照常自动批准。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert"})

    result = await service._quick_rule_check(plan, LIBERAL_ARTS_CONTEXT)

    assert result == "high_confidence_simple_plan"


@pytest.mark.asyncio
async def test_expert_liberal_arts_low_daily_hours_still_rejected():
    """守卫不得吞掉真实检查：daily_hours=1 文科专家目标仍判不可行。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 1})

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is False


@pytest.mark.asyncio
async def test_expert_liberal_arts_sufficient_daily_hours_passes():
    """daily_hours=3（边界值）：文科专家目标可行，放行。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 3})

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is True
