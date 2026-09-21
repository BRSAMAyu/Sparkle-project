"""
Core: infra
Phase: adapt
Stage: T6.4.2-4 — RAG/Aurora cost monitoring + budget circuit breaker

Unified cost tracking for all AI operations (LLM, RAG, Aurora) with
per-category daily budgets and circuit breaker that downgrades or
blocks expensive operations when daily budget is exceeded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from loguru import logger
from prometheus_client import Counter, Gauge

# ── Prometheus Metrics ─────────────────────────────────────────────────

COST_ESTIMATED_TOTAL = Counter(
    "sparkle_cost_estimated_usd_total",
    "Estimated cost in USD by category and operation",
    ["category", "operation"],
)

#: O-07 · Redis 故障期间预算核算进入进程内有界降级的计数（>0 即降级生效中，
#: 运维应同时关注网关 ``sparkle_quota_local_fallback_active``——同一故障域）。
COST_BUDGET_REDIS_FALLBACK_TOTAL = Counter(
    "sparkle_cost_budget_redis_fallback_total",
    "Budget accounting entered process-local bounded fallback (Redis unavailable) by category",
    ["category"],
)

COST_DAILY_BUDGET_USD = Gauge(
    "sparkle_cost_daily_budget_usd",
    "Configured daily budget in USD by category",
    ["category"],
)

COST_DAILY_SPEND_USD = Gauge(
    "sparkle_cost_daily_spend_usd",
    "Current daily spend in USD by category",
    ["category"],
)

BUDGET_CIRCUIT_TRIPS = Counter(
    "sparkle_budget_circuit_trips_total",
    "Budget circuit breaker trips by category",
    ["category"],
)


class CostCategory(StrEnum):
    LLM = "llm"
    RAG = "rag"
    AURORA = "aurora"
    # E-06：batch 认知车道独立预算桶。batch 工作负载（reflection/profile
    # aggregation/analytics 的异步 LLM）的支出计入此处，与前台 LLM 桶隔离：
    # batch 不占前台预算，前台预算熔断也不误杀 batch 车道。
    GLM_BATCH = "glm_batch"


# ── Budget Utilization Gauge ───────────────────────────────────────────

BUDGET_UTILIZATION = Gauge(
    "sparkle_budget_utilization_ratio",
    "Current daily budget utilization ratio (0.0-1.0+) by category",
    ["category"],
)

# ── Spend Rate Tracker ─────────────────────────────────────────────────

SPEND_RATE_USD_PER_HOUR = Gauge(
    "sparkle_spend_rate_usd_per_hour",
    "Estimated hourly spend rate in USD by category",
    ["category"],
)


# ── Default Pricing (USD per 1K units) ─────────────────────────────────

_RAG_PRICING: dict[str, float] = {
    "pgvector_search": 0.0001,
    "graphrag_retrieve": 0.0002,
    "redis_hybrid": 0.00005,
    "embedding_generate": 0.0001,
}

_AURORA_PRICING: dict[str, float] = {
    "l0_rule": 0.0,
    "l1_light": 0.0001,
    "l2_mid": 0.001,
    "l3_full_core": 0.005,
    "l4_async": 0.01,
}

# LLM pricing per 1K tokens, keyed by model tier (matches LLMRouter tiers).
# Input tokens are typically cheaper than output tokens; we use a blended rate
# per 1K total tokens for simplicity.
_LLM_TIER_PRICING_PER_1K: dict[str, float] = {
    "free": 0.0,
    "free_fast": 0.00005,
    "fast": 0.0002,
    "standard": 0.0005,
    "plus": 0.0015,
    "pro": 0.003,
    "reasoning": 0.008,
    "max": 0.015,
    "top": 0.02,
    "glm_batch": 0.0001,
    "specialist": 0.003,
}


# ── Budget Circuit Breaker ─────────────────────────────────────────────


class BudgetCircuitBreaker:
    """Per-category daily budget enforcement.

    When a category exceeds its daily budget, operations in that category
    are either downgraded (e.g., L3→L1) or blocked entirely.

    O-07 · Redis 有界降级（``COST_BUDGET_REDIS_FALLBACK_ENABLED``，默认开）：
    Redis 读/写失败或缺失时，预算核算退回**进程内保守累计值**继续闸门——
    降级期间成本仍有上界（per-process），不再是无界 fail-open；Redis 恢复
    后自动清零回落到 Redis 真值。与网关 GW-P2-4 ``QuotaLocalFallback`` 同
    设计语言：实例本地有界兜底 + 降级期显式指标（``COST_BUDGET_REDIS_FALLBACK_TOTAL``）。
    已知近似（如实声明）：降级期本地累计的支出在 Redis 恢复后不回填
    （incrbyfloat 当时已失败），恢复后的 Redis 计数只含恢复后支出——低估
    幅度以降级时长为界，方向保守（闸门宁严不松）。
    """

    _BUDGET_KEY = "cost:daily:{category}:{date}"
    _SPEND_RATE_KEY = "cost:spend_rate:{category}"
    _SPEND_WINDOW = 3600  # 1-hour rolling window for rate estimation

    def __init__(
        self,
        budgets: dict[CostCategory, float] | None = None,
    ):
        if budgets is not None:
            self._budgets = budgets
        else:
            from app.config import settings as _settings

            self._budgets = {
                CostCategory.LLM: float(getattr(_settings, "LLM_DAILY_BUDGET_USD", 10.0) or 10.0),
                CostCategory.RAG: float(getattr(_settings, "RAG_DAILY_BUDGET_USD", 2.0) or 2.0),
                CostCategory.AURORA: float(getattr(_settings, "AURORA_DAILY_BUDGET_USD", 5.0) or 5.0),
                CostCategory.GLM_BATCH: float(getattr(_settings, "BATCH_LANE_DAILY_BUDGET_USD", 0.5) or 0.5),
            }
        for cat, amount in self._budgets.items():
            COST_DAILY_BUDGET_USD.labels(category=cat).set(amount)
        # O-07 · 有界降级状态：进程内保守累计（仅降级期累计）+ 降级中类别集合。
        self._local_spend: dict[CostCategory, float] = {}
        self._redis_degraded: set[CostCategory] = set()

    # -- O-07 · 有界降级内部状态机 ----------------------------------------

    @staticmethod
    def _fallback_enabled() -> bool:
        from app.config import settings as _settings

        return bool(getattr(_settings, "COST_BUDGET_REDIS_FALLBACK_ENABLED", True))

    def _enter_degraded(self, category: CostCategory) -> None:
        if category not in self._redis_degraded:
            self._redis_degraded.add(category)
            COST_BUDGET_REDIS_FALLBACK_TOTAL.labels(category=category).inc()
            logger.warning(
                "cost_controller: Redis unavailable for {} budget accounting -> "
                "process-local bounded fallback (ceiling still enforced)",
                category,
            )

    def _exit_degraded(self, category: CostCategory) -> None:
        if category in self._redis_degraded:
            self._redis_degraded.discard(category)
            self._local_spend.pop(category, None)
            logger.info("cost_controller: Redis recovered for {} budget accounting -> redis truth restored", category)

    def _local_total(self, category: CostCategory) -> float:
        return float(self._local_spend.get(category, 0.0))

    def get_budget(self, category: CostCategory) -> float:
        return self._budgets.get(category, 0.0)

    def _get_redis(self):
        from app.core.cache import cache_service

        return cache_service.redis

    async def _get_daily_spend(self, category: CostCategory) -> float:
        redis = self._get_redis()
        if redis is None:
            if self._fallback_enabled():
                self._enter_degraded(category)
                return self._local_total(category)
            return 0.0
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        key = self._BUDGET_KEY.format(category=category, date=date_key)
        try:
            raw = await redis.get(key)
        except Exception:
            logger.debug("cost_controller: failed to read daily spend", exc_info=True)
            if self._fallback_enabled():
                self._enter_degraded(category)
                return self._local_total(category)
            return 0.0
        self._exit_degraded(category)
        return float(raw) if raw else 0.0

    def daily_spend(self, category: CostCategory) -> float:
        """进程内同步快照（本地累计面；Redis 真值请用 ``read_daily_spend``）。"""
        return self._local_total(category)

    async def read_daily_spend(self, category: CostCategory) -> float:
        """公开只读：当日支出（Redis 真值；故障时为本地保守累计值）。"""
        return await self._get_daily_spend(category)

    async def record_spend(self, category: CostCategory, amount_usd: float, operation: str = "") -> None:
        """Record a cost spend and update daily counter."""
        if amount_usd <= 0:
            return
        COST_ESTIMATED_TOTAL.labels(category=category, operation=operation).inc(amount_usd)
        redis = self._get_redis()
        if redis is None:
            if self._fallback_enabled():
                # O-07 · 有界降级：无 Redis 时本地保守累计（成本上限仍被执行）。
                self._enter_degraded(category)
                self._local_spend[category] = self._local_total(category) + float(amount_usd)
            return
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        key = self._BUDGET_KEY.format(category=category, date=date_key)
        try:
            await redis.incrbyfloat(key, amount_usd)
            await redis.expire(key, 48 * 3600)
        except Exception:
            logger.debug("cost_controller: failed to record spend", exc_info=True)
            if self._fallback_enabled():
                self._enter_degraded(category)
                self._local_spend[category] = self._local_total(category) + float(amount_usd)
            return
        self._exit_degraded(category)

        current = await self._get_daily_spend(category)
        COST_DAILY_SPEND_USD.labels(category=category).set(current)

        budget = self._budgets.get(category, 0.0)
        if budget > 0:
            BUDGET_UTILIZATION.labels(category=category).set(current / budget)

        # Estimate hourly spend rate via rolling window
        rate_key = self._SPEND_RATE_KEY.format(category=category)
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        window_start = now_ms - (self._SPEND_WINDOW * 1000)
        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zadd(rate_key, {f"{now_ms}:{operation}": amount_usd})
            pipe.zrangebyscore(rate_key, window_start, now_ms, withscores=True)
            results = await pipe.execute()
        except Exception:
            # 支率窗口失败不影响预算闸门（已记上的支出不受影响）
            logger.debug("cost_controller: failed to update spend rate window", exc_info=True)
            return
        window_total = sum(float(s) for _, s in results[2]) if results[2] else amount_usd
        hourly_rate = (window_total / self._SPEND_WINDOW) * 3600.0
        SPEND_RATE_USD_PER_HOUR.labels(category=category).set(hourly_rate)
        await redis.expire(rate_key, max(self._SPEND_WINDOW * 3, 7200))

    async def check_budget(self, category: CostCategory) -> bool:
        """Return True if category is within daily budget."""
        budget = self._budgets.get(category, 0.0)
        if budget <= 0:
            return True
        spend = await self._get_daily_spend(category)
        return spend < budget

    async def check_and_trip(self, category: CostCategory) -> bool:
        """Check budget and record trip if exceeded. Returns True if over budget."""
        within = await self.check_budget(category)
        if not within:
            BUDGET_CIRCUIT_TRIPS.labels(category=category).inc()
            logger.warning(
                "Budget circuit breaker tripped: category={} spend=${:.2f} > budget=${:.2f}",
                category, await self._get_daily_spend(category), self._budgets.get(category, 0),
            )
        return not within


# ── Module-level helpers ────────────────────────────────────────────────

_budget_breaker: BudgetCircuitBreaker | None = None


def get_budget_breaker() -> BudgetCircuitBreaker:
    global _budget_breaker
    if _budget_breaker is None:
        _budget_breaker = BudgetCircuitBreaker()
    return _budget_breaker


async def record_rag_cost(operation: str, units: int = 1) -> float:
    """Record estimated RAG retrieval cost."""
    cost = _RAG_PRICING.get(operation, 0.0001) * units
    breaker = get_budget_breaker()
    await breaker.record_spend(CostCategory.RAG, cost, operation=operation)
    return cost


async def record_aurora_cost(tier: str) -> float:
    """Record estimated Aurora tier execution cost."""
    cost = _AURORA_PRICING.get(tier, 0.001)
    breaker = get_budget_breaker()
    await breaker.record_spend(CostCategory.AURORA, cost, operation=tier)
    return cost


async def is_rag_within_budget() -> bool:
    return await get_budget_breaker().check_budget(CostCategory.RAG)


async def record_llm_cost(model_key: str, prompt_tokens: int, completion_tokens: int, source: str = "chat") -> float:
    """Record estimated LLM call cost based on model tier and token counts."""
    # Resolve tier from model key; default to "standard"
    tier = "standard"
    if model_key:
        model_lower = model_key.lower()
        for tier_key in _LLM_TIER_PRICING_PER_1K:
            if tier_key in model_lower:
                tier = tier_key
                break
    price_per_1k = _LLM_TIER_PRICING_PER_1K.get(tier, 0.0005)
    cost = (prompt_tokens + completion_tokens) / 1000.0 * price_per_1k
    breaker = get_budget_breaker()
    await breaker.record_spend(CostCategory.LLM, cost, operation=f"{source}/{model_key or 'unknown'}")
    return cost


async def is_llm_within_budget() -> bool:
    """Check if LLM daily budget is still available. Returns True if within budget."""
    return await get_budget_breaker().check_budget(CostCategory.LLM)


async def is_aurora_within_budget(tier: str = "l3_full_core") -> bool:
    """Check budget and trip circuit breaker if over. Returns True if within budget."""
    within = await get_budget_breaker().check_budget(CostCategory.AURORA)
    if not within:
        await get_budget_breaker().check_and_trip(CostCategory.AURORA)
    return within
