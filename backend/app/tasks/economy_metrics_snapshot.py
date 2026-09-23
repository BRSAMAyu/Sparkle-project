"""Photon economy daily metrics snapshot (PHOTON-TUNE, D-MONETIZE audit §1.6-5/R5).

经济健康仪表三指标——日铸币量 / 日消耗量 / 活跃用户人均余额：

- 真源 = ``photon_transaction_history`` 审计流水（PHOTON-CALIBRATION §⑤ 登记
  的数据钩子），零新埋点：收入-消耗方向合计直接从流水重放，余额取
  ``users.photon_balance``；
- 「活跃用户」= 统计窗口（前一个已关闭的 UTC 自然日）内至少有一笔光子流水
  的用户——经济活跃的诚实口径，不依赖登录埋点；
- 空窗口（零活跃）仪表置 0 并在返回值如实报告 active_users=0，不造默认值；
- 告警阈值占位：settings.PHOTON_ECONOMY_ALERT_*（默认 0=静默，只记仪表），
  超限走 loguru 告警日志，alertmanager 接线后续卡接此日志面即可；
- 结构沿用 SESSION-GC 先例（user_session_cleanup）：``@shared_task`` +
  ``get_db_context`` + ``asyncio.run`` 驱动协程；仪表置值是幂等 Gauge
  （任务重试不会重复累计，区别于 Counter）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from celery import shared_task
from loguru import logger
from sqlalchemy import case, func, select

from app.config import settings
from app.core.time_utils import utcnow as _utcnow
from app.db.session import get_db_context


def _closed_utc_day_window() -> tuple[datetime, datetime, str]:
    """前一个已关闭的 UTC 自然日 [start, end) 与 ISO 日期标注。"""
    today = _utcnow().date()
    day = today - timedelta(days=1)
    start = datetime.combine(day, datetime.min.time())
    end = datetime.combine(today, datetime.min.time())
    return start, end, day.isoformat()


@shared_task(
    name="tasks.economy_metrics_snapshot",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def economy_metrics_snapshot():
    """
    放置经济仪表三指标（前一个已关闭 UTC 日窗口）。

    每日低峰执行（beat: photon-economy-metrics-daily，low_priority 车道）。
    """
    logger.info("Starting photon economy metrics snapshot")

    try:
        with get_db_context() as db:
            snapshot = asyncio.run(_economy_metrics_snapshot(db))
    except Exception as e:
        logger.error("Photon economy metrics snapshot failed: {}", str(e))
        return {"status": "error", "message": str(e)}

    if snapshot["status"] != "success":
        return snapshot

    _set_economy_gauges(snapshot)
    alerts = _evaluate_alert_thresholds(snapshot)
    for alert in alerts:
        # 告警占位面：阈值默认 0（静默）；>0 后超限在此出告警日志，
        # alertmanager/值班接线后续卡消费该日志或直连指标即可。
        logger.warning("PHOTON-ECONOMY ALERT: {}", alert)

    logger.info(
        "Photon economy metrics snapshot done (day={} mint={} burn={} active_users={} avg_balance={:.2f})",
        snapshot["day"],
        snapshot["daily_mint"],
        snapshot["daily_burn"],
        snapshot["active_users"],
        snapshot["avg_balance_per_active_user"],
    )
    return {**snapshot, "alerts": alerts}


async def _economy_metrics_snapshot(db) -> dict:
    """从审计流水重放前一个已关闭 UTC 日的经济三指标。"""
    from app.models.shop import PhotonTransactionHistory
    from app.models.user import User

    start, end, day = _closed_utc_day_window()

    direction = await db.execute(
        select(
            func.coalesce(func.sum(case(
                (PhotonTransactionHistory.amount > 0, PhotonTransactionHistory.amount), else_=0
            )), 0),
            func.coalesce(func.sum(case(
                (PhotonTransactionHistory.amount < 0, -PhotonTransactionHistory.amount), else_=0
            )), 0),
            func.count(func.distinct(PhotonTransactionHistory.user_id)),
        ).where(
            PhotonTransactionHistory.created_at >= start,
            PhotonTransactionHistory.created_at < end,
        )
    )
    mint, burn, active_users = direction.one()
    active_users = int(active_users or 0)

    avg_balance = 0.0
    if active_users > 0:
        active_user_ids = (
            select(PhotonTransactionHistory.user_id)
            .where(
                PhotonTransactionHistory.created_at >= start,
                PhotonTransactionHistory.created_at < end,
            )
            .distinct()
        ).scalar_subquery()
        avg_result = await db.execute(
            select(func.coalesce(func.avg(User.photon_balance), 0)).where(User.id.in_(active_user_ids))
        )
        avg_balance = float(avg_result.scalar_one() or 0)

    return {
        "status": "success",
        "day": day,
        "daily_mint": int(mint or 0),
        "daily_burn": int(burn or 0),
        "active_users": active_users,
        "avg_balance_per_active_user": round(avg_balance, 2),
    }


def _set_economy_gauges(snapshot: dict) -> None:
    """三仪表置值（Gauge 幂等，失败不影响快照结果）。"""
    try:
        from app.core.metrics import (
            PHOTON_ECONOMY_AVG_BALANCE_PER_ACTIVE_USER,
            PHOTON_ECONOMY_DAILY_BURN,
            PHOTON_ECONOMY_DAILY_MINT,
        )

        PHOTON_ECONOMY_DAILY_MINT.set(snapshot["daily_mint"])
        PHOTON_ECONOMY_DAILY_BURN.set(snapshot["daily_burn"])
        PHOTON_ECONOMY_AVG_BALANCE_PER_ACTIVE_USER.set(snapshot["avg_balance_per_active_user"])
    except Exception as e:  # noqa: BLE001 — 可观测面绝不阻塞快照任务本身
        logger.warning("photon economy metrics gauge set failed: {}", e)


def _evaluate_alert_thresholds(snapshot: dict) -> list[str]:
    """告警阈值占位（settings 默认 0=静默）：超限返回告警文案列表。"""
    alerts: list[str] = []
    mint_max = int(settings.PHOTON_ECONOMY_ALERT_DAILY_MINT_MAX)
    burn_max = int(settings.PHOTON_ECONOMY_ALERT_DAILY_BURN_MAX)
    balance_max = int(settings.PHOTON_ECONOMY_ALERT_AVG_BALANCE_MAX)

    if mint_max > 0 and snapshot["daily_mint"] > mint_max:
        alerts.append(
            f"daily_mint={snapshot['daily_mint']} exceeds threshold {mint_max} "
            f"(day={snapshot['day']}; R1/R2 mint-anomaly precursor, audit §1.6-5)"
        )
    if burn_max > 0 and snapshot["daily_burn"] > burn_max:
        alerts.append(
            f"daily_burn={snapshot['daily_burn']} exceeds threshold {burn_max} "
            f"(day={snapshot['day']})"
        )
    if balance_max > 0 and snapshot["avg_balance_per_active_user"] > balance_max:
        alerts.append(
            f"avg_balance_per_active_user={snapshot['avg_balance_per_active_user']} "
            f"exceeds threshold {balance_max} (day={snapshot['day']}; stockpile inflation precursor)"
        )
    return alerts
