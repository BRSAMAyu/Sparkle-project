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

from datetime import datetime

from app.core.time_utils import ensure_naive_utc, utcnow

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


def entitlement_effective(
    raw: object | None,
    expires_at: datetime | None = None,
    *,
    now: datetime | None = None,
) -> str:
    """有效权益判级：存储值 + 可选到期时间 → 'free' | 'pro'。

    D-REDEEM 扩展（``users.entitlement_expires_at``，NULL = 永久）：
    - expires_at 为 NULL → 与 ``normalize_entitlement`` 完全同语义（存量行为
      零变化：手工/历史授予的永久 pro 不受影响）；
    - expires_at 已过 → 'free'（到期降级）。降级方向恒为 pro→free，与
      「宁降不升」的 fail-safe 指向一致：判级故障最多丢权益、绝不送成本。
    两侧（引擎/网关）判级必须保持一致，改动需同步 gateway
    ``IsProEntitlementEffective``。
    """
    tier = normalize_entitlement(raw)
    if tier != ENTITLEMENT_PRO:
        return ENTITLEMENT_FREE
    expiry = ensure_naive_utc(expires_at) if expires_at is not None else None
    if expiry is None:
        return ENTITLEMENT_PRO
    now_naive = ensure_naive_utc(now) if now is not None else utcnow()
    return ENTITLEMENT_PRO if expiry > now_naive else ENTITLEMENT_FREE


def entitlement_effective_grants_pro(
    raw: object | None,
    expires_at: datetime | None = None,
    *,
    now: datetime | None = None,
) -> bool:
    """``entitlement_effective`` 的布尔面（调用面与 ``entitlement_grants_pro`` 对齐）。"""
    return entitlement_effective(raw, expires_at, now=now) == ENTITLEMENT_PRO


def request_tier_label(tier: str | None) -> str:
    """请求级 tier（llm_router ContextVar）→ 有界 metrics label。

    词表封闭：'free' | 'pro' | 'unknown'；None/未知值 → 'unknown'。
    """
    value = str(tier or "").strip().lower()
    if value in (ENTITLEMENT_FREE, ENTITLEMENT_PRO):
        return value
    return "unknown"
