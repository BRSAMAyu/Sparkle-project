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


# ── Budget Circuit Breaker ─────────────────────────────────────────────


class BudgetCircuitBreaker:
    """Per-category daily budget enforcement.

    When a category exceeds its daily budget, operations in that category
    are either downgraded (e.g., L3→L1) or blocked entirely.
    """

    _BUDGET_KEY = "cost:daily:{category}:{date}"

    def __init__(
        self,
        budgets: dict[CostCategory, float] | None = None,
    ):
        self._budgets = budgets or {
            CostCategory.LLM: 10.0,
            CostCategory.RAG: 2.0,
            CostCategory.AURORA: 5.0,
        }
        for cat, amount in self._budgets.items():
            COST_DAILY_BUDGET_USD.labels(category=cat).set(amount)

    def get_budget(self, category: CostCategory) -> float:
        return self._budgets.get(category, 0.0)

    def _get_redis(self):
        from app.core.cache import cache_service
        return cache_service.redis

    async def _get_daily_spend(self, category: CostCategory) -> float:
        redis = self._get_redis()
        if redis is None:
            return 0.0
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        key = self._BUDGET_KEY.format(category=category, date=date_key)
        try:
            raw = await redis.get(key)
            return float(raw) if raw else 0.0
        except Exception:
            logger.debug("cost_controller: failed to read daily spend", exc_info=True)
            return 0.0

    async def record_spend(self, category: CostCategory, amount_usd: float, operation: str = "") -> None:
        """Record a cost spend and update daily counter."""
        if amount_usd <= 0:
            return
        COST_ESTIMATED_TOTAL.labels(category=category, operation=operation).inc(amount_usd)
        try:
            redis = self._get_redis()
            if redis is None:
                return
            date_key = datetime.now(UTC).strftime("%Y-%m-%d")
            key = self._BUDGET_KEY.format(category=category, date=date_key)
            await redis.incrbyfloat(key, amount_usd)
            await redis.expire(key, 48 * 3600)

            current = await self._get_daily_spend(category)
            COST_DAILY_SPEND_USD.labels(category=category).set(current)
        except Exception:
            logger.debug("cost_controller: failed to record spend", exc_info=True)

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


async def is_aurora_within_budget(tier: str = "l3_full_core") -> bool:
    """Check budget and trip circuit breaker if over. Returns True if within budget."""
    within = await get_budget_breaker().check_budget(CostCategory.AURORA)
    if not within:
        await get_budget_breaker().check_and_trip(CostCategory.AURORA)
    return within
