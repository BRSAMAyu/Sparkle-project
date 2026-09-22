"""
Worker: cost/WVPL 指标日刷新（O-07 · backend/app/workers 车道）。

Celery beat 每日调 ``refresh_cost_wvpl_metrics``（low_priority 车道）：把
当日成本（cost_controller 日计数）与 D-06 WVPL 北极星 loop 数的比值刷进
Prometheus gauge（OBSERVABILITY「cost/WVPL」面板数据源）。模式与
cleanup_worker 同构：sync celery task → ``asyncio.run`` 包 async 实现；
失败只计数告警，绝不影响其它任务。
"""

# rule-bj: exempt 已运行时接线——app/core/celery_app.py 以字符串引用本模块（:78 Celery include / :184 low_priority 队列路由 / :1024 beat 日程），AST 导入图看不见字符串引用

from __future__ import annotations

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="refresh_cost_wvpl_metrics", ignore_result=True)
def refresh_cost_wvpl_metrics() -> dict:
    """每日刷新 cost/WVPL gauge（纯确定性聚合，零 LLM 参与）。"""
    from app.core.cost_wvpl_metrics import refresh_cost_wvpl_snapshot
    from app.db.session import AsyncSessionLocal

    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            return await refresh_cost_wvpl_snapshot(db)

    try:
        snapshot = asyncio.run(_run())
    except Exception:  # noqa: BLE001 — 指标刷新失败不进重试风暴（低价值高频率任务）
        logger.exception("cost_wvpl refresh failed (gauge retains last values)")
        from app.core.cost_wvpl_metrics import COST_WVPL_REFRESH_FAILURES_TOTAL

        COST_WVPL_REFRESH_FAILURES_TOTAL.labels(stage="task").inc()
        return {"ok": False}
    logger.info(
        "cost_wvpl refreshed: spend=${:.4f} loops={} ratio={}",
        snapshot.get("daily_spend_usd") or 0.0,
        snapshot.get("wvpl_loops"),
        snapshot.get("cost_per_wvpl_usd"),
    )
    return {"ok": True, "snapshot": snapshot}
