"""
Core: infra
Phase: reinforce
Stage: O-07

O-07 · cost/WVPL 单位价值成本指标（OBSERVABILITY 面板「cost/WVPL」的数据源）。

口径（冻结声明，变更需过 reviewer）：
- **分子**：当日各成本类目（llm/rag/aurora/glm_batch）估算支出之和，读
  ``cost_controller`` 的既有 Redis 日计数（``cost:daily:{category}:{date}``）——
  不建第二套成本账。
- **分母**：D-06 北极星 WVPL 事实 JSON 的 ``north_star.loops_total``（7 日
  窗口、三腿全确定性、有界扫描）——不重算 loop 口径。
- **比值**：``cost_per_wvpl = 当日总支出 / 7 日 WVPL loop 数``。这是一个
  **异窗口比值**（日成本 / 周价值），用于趋势告警而非精确单位经济：分母
  周内相对平稳，分子突增（失控 batch/provider 重试风暴，FIX-49 那类）会
  立即推高比值——正是 O-07 要的可观测失控信号。精确单位经济走周批报表。
- loops=0（新部署/无价值循环）时比值无定义：gauge 不写（保留上次值），
  快照如实置 ``ratio=None``，不伪造 0。
- 零模型参与（与 D-06 同纪律）：纯确定性聚合，模块不 import 任何 LLM 基础设施。

刷新入口：``app/workers/cost_wvpl_worker.refresh_cost_wvpl_metrics``（celery
beat 每日一次，low_priority 车道）；``refresh_cost_wvpl_snapshot`` 也可被
运维脚本直接 await。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from prometheus_client import Counter, Gauge

from app.core.cost_controller import CostCategory, get_budget_breaker
from app.core.metrics import get_or_create_metric

COST_DAILY_ALL_USD = get_or_create_metric(
    Gauge,
    "sparkle_cost_daily_all_usd",
    "Today's estimated spend summed across all cost categories (USD)",
)

WVPL_LOOPS_CURRENT = get_or_create_metric(
    Gauge,
    "sparkle_wvpl_loops_current",
    "WVPL loops_total from the latest D-06 north-star fact (7-day window)",
)

COST_PER_WVPL_USD = get_or_create_metric(
    Gauge,
    "sparkle_cost_per_wvpl_usd",
    "Daily estimated spend (USD) per WVPL loop; unit-value cost trend signal",
)

COST_WVPL_REFRESH_FAILURES_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_cost_wvpl_refresh_failures_total",
    "cost/WVPL metric refresh failures by stage",
    ["stage"],
)

#: O-07 · cost/WVPL 指标口径版本（分子/分母/窗口任一变更需 bump）。
COST_WVPL_METRIC_VERSION = "cost_wvpl.v1"


def compute_cost_per_wvpl(daily_spend_usd: float, wvpl_loops: int | None) -> float | None:
    """纯比值计算（分母无效/为零 → None；负分母按脏数据 → None）。确定性可单测。"""
    if wvpl_loops is None or wvpl_loops <= 0:
        return None
    if daily_spend_usd < 0:
        return None
    return daily_spend_usd / float(wvpl_loops)


async def _daily_spend_all_categories() -> float:
    breaker = get_budget_breaker()
    total = 0.0
    for category in CostCategory:
        try:
            total += await breaker.read_daily_spend(category)
        except Exception:  # noqa: BLE001 — 单类目读失败不拖垮整个快照
            logger.opt(exception=True).debug("cost_wvpl: daily spend read failed for {}", category)
    return total


async def refresh_cost_wvpl_snapshot(db: Any, *, as_of: datetime | None = None) -> dict[str, Any]:
    """刷新 cost/WVPL gauge 并返回事实快照（可审计；失败按 stage 计数）。

    db 为 SQLAlchemy AsyncSession（WVPL fact 走 D-06 只读查询，有界扫描）。
    """
    daily_spend = await _daily_spend_all_categories()
    COST_DAILY_ALL_USD.set(daily_spend)

    from app.services.north_star_wvpl_service import NorthStarWvplService

    try:
        fact = await NorthStarWvplService(db).build_fact(as_of=as_of)
    except Exception as exc:  # noqa: BLE001 — 分母面失败如实计数，不写脏 gauge
        COST_WVPL_REFRESH_FAILURES_TOTAL.labels(stage="wvpl_fact").inc()
        logger.warning("cost_wvpl: WVPL fact build failed; ratio gauge not updated: {!r}", exc)
        return {
            "version": COST_WVPL_METRIC_VERSION,
            "daily_spend_usd": daily_spend,
            "wvpl_loops": None,
            "cost_per_wvpl_usd": None,
            "error": "wvpl_fact_failed",
        }

    wvpl_loops = fact.get("north_star", {}).get("loops_total")
    wvpl_loops = int(wvpl_loops) if isinstance(wvpl_loops, (int, float)) else None
    ratio = compute_cost_per_wvpl(daily_spend, wvpl_loops)
    if wvpl_loops is not None:
        WVPL_LOOPS_CURRENT.set(wvpl_loops)
    if ratio is not None:
        COST_PER_WVPL_USD.set(ratio)

    return {
        "version": COST_WVPL_METRIC_VERSION,
        "daily_spend_usd": daily_spend,
        "wvpl_loops": wvpl_loops,
        "cost_per_wvpl_usd": ratio,
        "as_of": (as_of or datetime.now(UTC)).strftime("%Y-%m-%d"),
    }
