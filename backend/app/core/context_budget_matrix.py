"""C-06 · tier × decision-type 上下文预算矩阵（确定性、配置驱动、零 LLM）。

CONTEXT_COMPILER_V3.md §4 Budget policy：Context 是有限预算，按"当前决策"
分配，而不是所有用户/所有决策共用一个机械上限。此前的基线是单一
``settings.CONTEXT_TOTAL_TOKEN_BUDGET``（默认 8000，对 free/pro、chat/
deep_analysis/reflection 全部一视同仁——见 REPORT 基线 B3）。

本模块三件事，全部纯函数、零 I/O：

1. **预算矩阵** ``resolve_total_budget(tier, decision_type)`` ——
   按 用户权益层（``User.entitlement``：'free' | 'pro'，V3-FIX-02/D17 冻结
   决策的唯一判据）× 决策类型（chat/deep_analysis/reflection/planning/
   learning）给出该次 LLM 调用的 context 总预算。默认矩阵是代码内常量；
   ``settings.CONTEXT_BUDGET_MATRIX_JSON`` 可整体覆盖（配置驱动，便于
   运营调参/实验，不需要改代码）。任何解析失败都回退默认矩阵（fail-soft，
   预算解析绝不阻断聊天主链路）。
2. **维度解析** ``resolve_tier`` / ``resolve_decision_type`` —— 从既有信号
   （``route_intent`` / ``intent_type`` / ``chat_mode``，见
   ``context_focus.route_intent_to_budget_intent`` 的同源映射习惯）确定性
   推导维度值；无信号时回退 ``("free", "chat")``。
3. **天花板钳制** —— 矩阵值永远被 ``settings.CONTEXT_TOTAL_TOKEN_BUDGET``
   钳制（全局硬顶保留：它是运维刹车，不是预算本身）；显式传入的
   ``total_token_budget`` 优先级最高（向后兼容，既有测试/调用点不变）。

与 C-07 的关系：预算是 cache 键**之外**的运行时参数——context_cache_key
钉的是"载荷新鲜度版本"（mepoch/pv/pol/know），预算改变 → 注入载荷变 →
下游 context_pack 产物自然不同；键机制本身零改动（见
``tests/unit/test_c06_budget_matrix.py::test_budget_change_alters_payload_but_not_cache_key``）。
"""

from __future__ import annotations

import json
from typing import Any

#: 用户权益层。唯一权威判据：``User.entitlement``（'free' | 'pro'）。
TIERS: tuple[str, ...] = ("free", "pro")

#: 决策类型。card C-06：chat/deep_analysis/reflection 等；
#: planning/learning 与既有 ``ContextBudgetScheduler`` 的 intent 键对齐。
DECISION_TYPES: tuple[str, ...] = ("chat", "deep_analysis", "reflection", "planning", "learning")

#: 默认预算矩阵（token）。free 档收紧（成本纪律），pro 档放宽（深推理
#: 决策需要更多材料与历史）；同一层内 deep_analysis/reflection 高于 chat
#: ——单次决策效用越高，允许注入的信号越多。
DEFAULT_CONTEXT_BUDGET_MATRIX: dict[str, dict[str, int]] = {
    "free": {
        "chat": 6000,
        "deep_analysis": 7000,
        "reflection": 6500,
        "planning": 7000,
        "learning": 7000,
    },
    "pro": {
        "chat": 8000,
        "deep_analysis": 11000,
        "reflection": 9000,
        "planning": 10000,
        "learning": 10000,
    },
}

#: chat_mode / route_intent / intent_type → decision_type 的确定性映射。
#: ``chat_mode`` 词表与 ``infer_route_intent_from_chat_mode`` 同源（不改动它）。
_DECISION_BY_ROUTE_INTENT: dict[str, str] = {
    "plan": "planning",
    "sprint_plan": "planning",
    "deep_analysis": "deep_analysis",
    "reflection": "reflection",
    "review": "reflection",
    "knowledge": "learning",
    "learn": "learning",
    "translation": "learning",
    "error_diagnosis": "learning",
}

_DECISION_BY_CHAT_MODE: dict[str, str] = {
    "deep_analysis": "deep_analysis",
    "reflection": "reflection",
    "review": "reflection",
    "study_plan": "planning",
}


def resolve_tier(entitlement: str | None) -> str:
    """``User.entitlement`` → 预算层。未知/缺失一律 free（成本 fail-safe）。"""
    value = str(entitlement or "").strip().lower()
    return "pro" if value == "pro" else "free"


def resolve_decision_type(
    route_intent: str | None = None,
    chat_mode: str | None = None,
    intent_type: str | None = None,
) -> str:
    """从既有路由信号确定性推导决策类型；无信号回退 chat。

    优先级：route_intent > intent_type > chat_mode（route_intent 是
    dual-core router 的产物，语义最强；chat_mode 只是前端模式名）。
    """
    for source, table in (
        (route_intent, _DECISION_BY_ROUTE_INTENT),
        (intent_type, _DECISION_BY_ROUTE_INTENT),
        (chat_mode, _DECISION_BY_CHAT_MODE),
    ):
        value = str(source or "").strip().lower()
        if not value:
            continue
        decision = table.get(value)
        if decision is not None:
            return decision
        # route_intent/intent_type 的未知值走 chat（与
        # route_intent_to_budget_intent 的兜底习惯一致），chat_mode 未知值
        # 不能枪毙后续信号。
        if table is _DECISION_BY_CHAT_MODE:
            continue
        return "chat"
    return "chat"


def load_budget_matrix(overrides: Any = None) -> dict[str, dict[str, int]]:
    """默认矩阵 + 可选 JSON 覆盖（部分覆盖合法：只覆盖给出的格子）。

    任何畸形（非 dict / 非法 tier 或 decision / 负数 / 非整数）的覆盖项
    静默忽略——预算矩阵绝不因配置错误抛异常阻断主链路。
    """
    matrix: dict[str, dict[str, int]] = {
        tier: {decision: int(budget) for decision, budget in decisions.items()}
        for tier, decisions in DEFAULT_CONTEXT_BUDGET_MATRIX.items()
    }
    if not isinstance(overrides, str) or not overrides.strip():
        return matrix
    try:
        parsed = json.loads(overrides)
    except (TypeError, ValueError):
        return matrix
    if not isinstance(parsed, dict):
        return matrix
    for tier, decisions in parsed.items():
        if tier not in TIERS or not isinstance(decisions, dict):
            continue
        for decision, budget in decisions.items():
            if decision not in DECISION_TYPES:
                continue
            if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
                continue
            matrix[tier][decision] = budget
    return matrix


def resolve_total_budget(
    tier: str = "free",
    decision_type: str = "chat",
    *,
    matrix_overrides: Any = None,
    ceiling: int | None = None,
) -> int:
    """矩阵预算 + 全局天花板钳制。任何入参畸形都落到 (free, chat) 兜底。"""
    from app.config import settings

    matrix = load_budget_matrix(
        matrix_overrides
        if matrix_overrides is not None
        else getattr(settings, "CONTEXT_BUDGET_MATRIX_JSON", "") or None
    )
    tier_key = tier if tier in TIERS else "free"
    decision_key = decision_type if decision_type in DECISION_TYPES else "chat"
    budget = int(matrix[tier_key][decision_key])
    hard_ceiling = int(
        ceiling if ceiling is not None else getattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 8000) or 8000
    )
    return max(1, min(budget, max(1, hard_ceiling)))
