"""V3-FIX-499 回归测试：plan_review 可行性检查 total_days 类型收口（str 同型）。

修前 ``_validate_feasibility`` :927 ``total_days = params.get("total_days",
params.get("duration_days"))`` 裸取值——``ToolCallSpec.params: dict[str, Any]``，
LLM 生成键集值型不保证；字符串型 ``"5"`` 真值通过 :956 的 ``total_days and``
None 守卫后 ``str <= int`` 直接 TypeError（运行级探针实录 wt767）：
:966 ``daily_hours * total_days`` 在 497 修后 daily_hours=float 下遇字符串
total_days 为 ``float * str`` TypeError（数值语义仍错）。同函数
``_collect_feasibility_comments`` :721 对同键族已走 ``self._positive_float(...)``
收口（TypeError/ValueError→None），:927 为平行裸取不一致点。

修法（对齐 :721 先例，与 497 同型）：``total_days = self._positive_float(
params.get("total_days", params.get("duration_days")))`` ——数值字符串转
float 参与既有比较/乘法（``"5"`` → ``5.0``，既有守卫语义原样生效）；
垃圾值/缺键 → None，与既有 falsy 守卫语义衔接。
"""

from __future__ import annotations

import pytest

from app.orchestration.plan_review_service import PlanReviewService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

PLAIN_CONTEXT = {"skill_level": "expert"}


def _expert_plan_with_params(params: dict) -> ExecutablePlan:
    # 与 497 测试同款：工具名不落 SAFE_TOOL_CATEGORIES（避开 all_tools_are_read_only
    # 短路），也不含 plan/sprint/schedule/task token（避开 _collect_feasibility_comments
    # 的 CRITICAL 短路），确保病灶就是 :927 裸取值。
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
async def test_string_total_days_expert_low_hours_rejected():
    """total_days="5"（字符串）+ daily_hours=3：数值语义照常生效——5≤7 且 3h<4h 判不可行，不 500。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 3, "total_days": "5"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is False, "string '5' must coerce to 5.0 and hit the ≤7 + <4h gate (numeric semantics, not TypeError)"


@pytest.mark.asyncio
async def test_string_total_days_boundary_seven_matches_numeric():
    """total_days="7"（字符串边界值）：与 int 型 7 同判——≤7 门槛含边界。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 3, "total_days": "7"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is False, "string '7' must coerce to 7.0 and behave identically to the int 7 boundary"


@pytest.mark.asyncio
async def test_string_total_days_over_seven_no_crash_no_penalty():
    """total_days="10"（字符串 >7）：规则只辖 ≤7，收口后跳过该块——不 500 也不误罚。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 5, "total_days": "10"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is True, "string '10' coerces to 10.0 > 7 and must skip the ≤7 rule without TypeError"


@pytest.mark.asyncio
async def test_string_total_days_multiply_numeric_semantics():
    """daily_hours="4" × total_days="7"（双双字符串）：按 28 小时数值语义判 50 小时门槛，非字符串重复。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "4", "total_days": "7"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is False, "4.0 * 7.0 = 28h < 50h must reject — proves numeric coercion through the multiply path"


@pytest.mark.asyncio
async def test_garbage_total_days_treated_as_missing():
    """total_days="abc"（垃圾值）：与缺键同语义（→None 跳过 ≤7 块），不得 500。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 3, "total_days": "abc"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is True, "garbage value coerces to None and skips the ≤7 block — missing-key parity"


@pytest.mark.asyncio
async def test_duration_days_fallback_key_string_coerced():
    """total_days 缺键、duration_days="5"（回退键字符串型）：回退取值同样收口。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": 3, "duration_days": "5"})

    result = await service._validate_feasibility(plan, PLAIN_CONTEXT)

    assert result is False, "fallback duration_days='5' must coerce and hit the same ≤7 + <4h gate"


@pytest.mark.asyncio
async def test_quick_rule_check_string_total_days_auto_approves():
    """快速审查通道端到端：字符串型 total_days 不再 500，8h×7d≥50h 可行计划照常自动批准。"""
    service = PlanReviewService(redis_client=object())
    plan = _expert_plan_with_params({"difficulty": "expert", "daily_hours": "8", "total_days": "7"})

    result = await service._quick_rule_check(plan, PLAIN_CONTEXT)

    assert result == "high_confidence_simple_plan"
