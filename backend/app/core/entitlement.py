"""
Core: <cognitive>
Phase: <none>
Stage: O-04

O-04 · entitlement 归一与判级 —— 引擎侧唯一实现（V3-FIX-02 / D17 冻结决策）。

``users.entitlement``（alembic ``ent01_20260919``，NOT NULL DEFAULT 'free'）是
付费权益的唯一真源；``flame_level`` 是游戏化展示字段，永久禁作权益判据。
本模块给引擎侧所有「entitlement → 归一值 / 是否 pro」的调用面一个单一实现，
防止历史上 ``is_pro = flame_level >= 3`` 的派生逻辑在任何角落复发（游客
flame_level 曾被 guest_seed 写到 15，导致全部游客以 is_pro=true 进 pro 层，
真实付费用户反被压 free 层——O-04 卡要杀的正是这类混用）。

值域约定（应用层约束，与迁移 docstring 一致）：
- 存储值：'free' | 'pro'
- 未知 / 缺失 / 空白 / 值域外（如 'premium' 不得出现在 DB 列）一律 → 'free'
  （宁降不升，成本 fail-safe；迁移给全部存量行安全默认 'free'）
- 网关侧同语义实现：backend/gateway/internal/service/user_context.go
  ``IsProEntitlement``（equal-fold "pro"）；两侧判级必须保持一致，改动需同步。
- 请求级 LLM 分层覆盖（extra_context.user_tier）中 premium/paid 视同 pro 的
  行为仅存在于 agent_grpc_service._resolve_request_user_tier，不属 DB 判级。
"""

from __future__ import annotations

ENTITLEMENT_FREE = "free"
ENTITLEMENT_PRO = "pro"

#: 请求级 tier 的有界 label 词表（metrics 用；ContextVar 未标记 → "unknown"，
#: 对应内部批量/定时任务/测试等无用户请求面）。
TIER_LABELS: tuple[str, ...] = (ENTITLEMENT_FREE, ENTITLEMENT_PRO, "unknown")


def normalize_entitlement(raw: object | None) -> str:
    """任意输入 → 'free' | 'pro'。只有精确 'pro'（trim/大小写归一后）判 pro。"""
    value = str(raw or "").strip().lower()
    return ENTITLEMENT_PRO if value == ENTITLEMENT_PRO else ENTITLEMENT_FREE


def entitlement_grants_pro(raw: object | None) -> bool:
    """存储值是否授予 pro 权益。未知/缺失一律 False（宁降不升）。"""
    return normalize_entitlement(raw) == ENTITLEMENT_PRO


def request_tier_label(tier: str | None) -> str:
    """请求级 tier（llm_router ContextVar）→ 有界 metrics label。

    词表封闭：'free' | 'pro' | 'unknown'；None/未知值 → 'unknown'。
    """
    value = str(tier or "").strip().lower()
    if value in (ENTITLEMENT_FREE, ENTITLEMENT_PRO):
        return value
    return "unknown"
