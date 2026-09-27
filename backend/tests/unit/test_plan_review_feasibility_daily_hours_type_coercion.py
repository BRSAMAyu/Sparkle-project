"""V3-FIX-497 回归测试：plan_review 可行性检查 daily_hours 类型收口（str 同型）。

修前 ``_validate_feasibility`` :919 ``daily_hours = params.get("daily_hours")``
裸取值——``ToolCallSpec.params: dict[str, Any]``，LLM 生成键集值型不保证；
字符串型 ``"1"`` 真值通过 :934/:942/:951 的 ``daily_hours and`` None 守卫后
``str < int`` 直接 TypeError（快速审查通道随之 500 崩）：960 的
``daily_hours * total_days`` 字符串复合同炸（``"2" * 7`` 是字符串重复而非
数值语义）。:833 ``_resolve_daily_capacity_minutes`` 对同键族早已走
``cls._positive_float(...)`` 收口（TypeError/ValueError→None），:919 为平行
裸取不一致点。

修法（对齐 :833 先例）：``daily_hours = self._positive_float(params.get("daily_hours"))``
——数值字符串转 float 参与既有比较（``"1"`` → ``1.0``，既有守卫语义原样
生效）；垃圾值/缺键 → None，与 V3-FIX-492 缺参守卫语义衔接。
"""

from __future__ import annotations

import pytest

from app.orchestration.plan_review_service import PlanReviewService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

LIBERAL_ARTS_CONTEXT = {"skill_level": "expert", "user_background": "文科"}
PLAIN_CONTEXT = {"skill_level": "expert"}


def _expert_plan_with_params(params: dict) -> ExecutablePlan:
    # 工具名不能全落 SAFE_TOOL_CATEGORIES（query/get/...）——否则 _quick_rule_check
    # 在 feasibility 之前就走 all_tools_are_read_only 短路，打不到 :919 病灶；
    # 也不含 plan/sprint/schedule/task token——_collect_feasibility_comments 直接
    # 跳过该工具（不发 CRITICAL 短路），确保病灶就是 :919 裸取值。
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
async def test_expert_liberal_arts_string_daily_hours_low_rejected():
    """daily_hours="1"（字符串）：数值语义照常生效——专家+文科低投入仍判不可行，不 500。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "1"})

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is False, "string '1' must coerce to 1.0 and fail the <3 gate (numeric semantics, not TypeError)"


@pytest.mark.asyncio
async def test_expert_liberal_arts_string_daily_hours_sufficient_passes():
    """daily_hours="3"（字符串边界值）：与 int 型 3 同判——可行放行。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "3"})

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is True, "string '3' must coerce to 3.0 and behave identically to the int 3 (492 boundary case)"


@pytest.mark.asyncio
async def test_string_daily_hours_converts_for_total_hours_semantics():
    """daily_hours="4" × total_days=7：按 28 小时数值语义判 50 小时门槛，不字符串重复。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "4", "total_days": 7})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is False, "4h × 7d = 28h < 50h must reject — proves numeric coercion through the multiply path"


@pytest.mark.asyncio
async def test_garbage_string_daily_hours_treated_as_missing():
    """daily_hours="abc"（垃圾值）：与缺键同语义（→None 跳过守卫），不得 500。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "abc"})

    result = await service._validate_feasibility(plan, LIBERAL_ARTS_CONTEXT)

    assert result is True, "garbage value coerces to None and skips the guards — 492 missing-key parity"


@pytest.mark.asyncio
async def test_quick_rule_check_string_daily_hours_auto_approves():
    """快速审查通道端到端：字符串型 daily_hours 不再 500，高置信简单计划照常自动批准。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "3"})

    result = await service._quick_rule_check(plan, LIBERAL_ARTS_CONTEXT)

    assert result == "high_confidence_simple_plan"
