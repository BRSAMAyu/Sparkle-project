"""PHOTON-TUNE · 经济仪表三指标日快照（D-MONETIZE 审计 §1.6-5）。

钉住：方向合计（日铸币/日消耗）真源=photon_transaction_history 审计流水；
活跃用户=窗口内有光子流水者；空窗口诚实置零不造默认值；告警阈值占位
（settings 默认 0=静默，>0 超限出告警文案）。
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.models.shop import PhotonTransactionHistory
from app.models.user import User
from app.tasks.economy_metrics_snapshot import (
    _closed_utc_day_window,
    _economy_metrics_snapshot,
    _evaluate_alert_thresholds,
    _set_economy_gauges,
)


async def _seed_user(db, username: str, photon_balance: int = 0) -> User:
    user = User(username=username, email=f"{username}@test.local", hashed_password="x",
                photon_balance=photon_balance)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_tx(db, user: User, amount: int, balance_before: int, balance_after: int, created_at) -> None:
    db.add(
        PhotonTransactionHistory(
            id=str(uuid4()),
            user_id=user.id,
            transaction_type="grant_daily_first" if amount > 0 else "purchase",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            source="photon-tune-test",
            created_at=created_at,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_snapshot_direction_sums_active_users_and_avg_balance(db_session, monkeypatch):
    start, end, day = _closed_utc_day_window()
    noon = start + timedelta(hours=12)
    assert start < noon < end

    alice = await _seed_user(db_session, "econ_alice", photon_balance=300)
    bob = await _seed_user(db_session, "econ_bob", photon_balance=100)
    # 窗口外的一笔（窗口结束后，不应计入）
    stale = await _seed_user(db_session, "econ_stale", photon_balance=9999)

    await _seed_tx(db_session, alice, +30, 270, 300, noon)  # mint
    await _seed_tx(db_session, alice, -50, 350, 300, noon)  # burn
    await _seed_tx(db_session, bob, -20, 120, 100, noon)  # burn
    await _seed_tx(db_session, stale, +1, 9998, 9999, end + timedelta(hours=1))  # 窗口外

    snapshot = await _economy_metrics_snapshot(db_session)

    assert snapshot["status"] == "success"
    assert snapshot["day"] == day
    assert snapshot["daily_mint"] == 30
    assert snapshot["daily_burn"] == 70
    assert snapshot["active_users"] == 2
    assert snapshot["avg_balance_per_active_user"] == 200.0  # (300+100)/2，不含 stale


@pytest.mark.asyncio
async def test_snapshot_empty_window_reports_honest_zero(db_session):
    """空数据诚实空态：零活跃置零，不造默认值（FLEET-BRIEF §四.4）。"""
    snapshot = await _economy_metrics_snapshot(db_session)
    assert snapshot["daily_mint"] == 0
    assert snapshot["daily_burn"] == 0
    assert snapshot["active_users"] == 0
    assert snapshot["avg_balance_per_active_user"] == 0.0


@pytest.mark.asyncio
async def test_gauges_set_from_snapshot(db_session):
    snapshot = await _economy_metrics_snapshot(db_session)
    snapshot["daily_mint"] = 42
    snapshot["daily_burn"] = 24
    snapshot["avg_balance_per_active_user"] = 12.5
    _set_economy_gauges(snapshot)

    assert REGISTRY.get_sample_value("sparkle_photon_economy_daily_mint") == 42.0
    assert REGISTRY.get_sample_value("sparkle_photon_economy_daily_burn") == 24.0
    assert REGISTRY.get_sample_value("sparkle_photon_economy_avg_balance_per_active_user") == 12.5


def test_alert_thresholds_default_silent():
    """默认 0=静默不响（告警占位纪律）。"""
    snapshot = {
        "day": "2026-09-21",
        "daily_mint": 10**9,
        "daily_burn": 10**9,
        "avg_balance_per_active_user": 10**9,
    }
    assert _evaluate_alert_thresholds(snapshot) == []


def test_alert_thresholds_fire_when_configured(monkeypatch):
    """阈值 >0 且超限 → 告警文案；未超限不响。"""
    monkeypatch.setattr(settings, "PHOTON_ECONOMY_ALERT_DAILY_MINT_MAX", 100)
    monkeypatch.setattr(settings, "PHOTON_ECONOMY_ALERT_DAILY_BURN_MAX", 0)
    monkeypatch.setattr(settings, "PHOTON_ECONOMY_ALERT_AVG_BALANCE_MAX", 5000)

    alerts = _evaluate_alert_thresholds(
        {"day": "2026-09-21", "daily_mint": 101, "daily_burn": 999999, "avg_balance_per_active_user": 4999}
    )
    assert len(alerts) == 1
    assert "daily_mint=101" in alerts[0]

    alerts_all = _evaluate_alert_thresholds(
        {"day": "2026-09-21", "daily_mint": 101, "daily_burn": 1, "avg_balance_per_active_user": 5001}
    )
    assert len(alerts_all) == 2
