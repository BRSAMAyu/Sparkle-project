"""D-03 · Understanding 校准服务测试：行为对齐 + 离线校准 + 漂移检测（注入漂移必红）。

验收面：
- 离线校准：coverage 仿射拟合的误差量化（mae_before > mae_after）与安全回退
  （拟合不优 → 恒等，校准永不把误差变大）；
- 漂移检测：落行后篡改 daily 行 → 红；落行后 late-arriving 原始数据 → 红；
  未篡改且行为稳定 → 不红。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.aurora_stage20 import AuroraJudgmentRecord
from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.memory import MemoryCorrection, MemoryPreference
from app.models.understanding_dimensions import UnderstandingDimensionDaily
from app.services.understanding_calibration_service import (
    AffineMap,
    UnderstandingCalibrationService,
    apply_coverage_calibration,
    fit_affine_map,
)
from app.services.understanding_dimensions_service import UnderstandingDimensionsService

METRIC_DAY = datetime(2026, 9, 19).date()


def _ts(day_offset: float) -> datetime:
    return datetime(2026, 9, 19, 12) + timedelta(days=day_offset)


# ---------------------------------------------------------------------------
# fit_affine_map 纯函数
# ---------------------------------------------------------------------------


def test_fit_insufficient_pairs_returns_identity():
    result = fit_affine_map([(1.0, 0.5), (0.8, 0.4)])
    assert result.applied is False
    assert (result.a, result.b) == (1.0, 0.0)
    assert result.method == "insufficient_pairs"


def test_fit_no_improvement_keeps_identity():
    # 完全对齐：拟合没有改进空间 → 恒等（校准永不把误差变大）。
    result = fit_affine_map([(x, x) for x in (0.2, 0.4, 0.6, 0.8)])
    assert result.applied is False
    assert result.method == "identity_no_improvement"
    assert result.mae_before == pytest.approx(0.0)


def test_fit_constant_offset_with_clamp():
    # stored 恒 1.0、anchor 恒 0.7：var_x=0 → 只拟 b=-0.3，clamp 到 -0.25。
    result = fit_affine_map([(1.0, 0.7)] * 4)
    assert result.applied is True
    assert result.b == pytest.approx(-0.25)
    assert result.mae_before == pytest.approx(0.3)
    assert result.mae_after == pytest.approx(0.05)
    assert result.apply(1.0) == pytest.approx(0.75)


def test_fit_slope_with_bounds():
    # stored [0.2,0.4,0.6,0.8] vs anchor [0.35,0.55,0.75,0.95]：OLS a=1, b=0.15。
    result = fit_affine_map([(0.2, 0.35), (0.4, 0.55), (0.6, 0.75), (0.8, 0.95)])
    assert result.applied is True
    assert result.a == pytest.approx(1.0, abs=1e-6)
    assert result.b == pytest.approx(0.15, abs=1e-6)
    assert result.mae_after < result.mae_before


def test_affine_map_apply_clamps_to_unit_interval():
    assert AffineMap(a=2.0, b=0.5).apply(0.6) == pytest.approx(1.0)
    assert AffineMap(a=0.5, b=-0.25).apply(0.1) == pytest.approx(0.0)


def test_apply_coverage_calibration_from_dict():
    assert apply_coverage_calibration(0.8, {"a": 1.0, "b": -0.25}) == pytest.approx(0.55)
    assert apply_coverage_calibration(0.8, None) == pytest.approx(0.8)
    assert apply_coverage_calibration(0.8, {"a": "bad", "b": 0.0}) == pytest.approx(0.8)  # 防御性回退


# ---------------------------------------------------------------------------
# 端到端：构造多日 daily 行 → 校准/漂移
# ---------------------------------------------------------------------------


async def _seed_series(db, user_id, *, judge_score: float = 1.0, dup_rate_denominator: int | None = None):
    """铺 10 天数据：judgments + pack runs + chat（可控重复率）。"""
    for offset in range(-10, 1):
        for _ in range(3):
            db.add(
                AuroraJudgmentRecord(
                    user_id=user_id,
                    task_sufficiency_score=judge_score,
                    task_missing_dimensions=[],
                    context_sufficiency_score=judge_score,
                    context_missing_dimensions=[],
                    computed_at=_ts(offset),
                    created_at=_ts(offset),
                    updated_at=_ts(offset),
                )
            )
        db.add(
            ContextPackRun(
                user_id=user_id,
                intent="chat",
                budgets={},
                token_usage={},
                memory_counts={"preferences": 2},
                created_at=_ts(offset),
                updated_at=_ts(offset),
            )
        )
    if dup_rate_denominator:
        # 每天都铺消息（保证每个 daily 行的滚动窗内都有锚点输入）：
        # 每日 10 条：固定短语 P×3（跨日重复）+ 当日唯一短语×7。
        # 7 天窗内：eligible=70，P 计 21 份 → 20 份重复 → rate=2/7 → anchor=5/7。
        for offset in range(-10, 1):
            for i in range(10):
                content = "帮我规划一周复习安排" if i < 3 else f"今天聊聊别的话题{offset}_{i}"
                db.add(
                    ChatMessage(
                        user_id=user_id,
                        session_id=uuid4(),
                        role=MessageRole.USER,
                        content=content,
                        created_at=_ts(offset),
                        updated_at=_ts(offset),
                    )
                )
    await db.commit()


async def _compute_rows(service: UnderstandingDimensionsService, user_id, *, days: int = 4):
    for back in range(days - 1, -1, -1):
        await service.compute_daily_for_user(user_id=user_id, day=METRIC_DAY - timedelta(days=back))


async def _tamper_latest_row(db, user_id, *, dim: str, value: float):
    row = (
        await db.execute(
            select(UnderstandingDimensionDaily)
            .where(UnderstandingDimensionDaily.user_id == user_id)
            .order_by(UnderstandingDimensionDaily.metric_date.desc())
            .limit(1)
        )
    ).scalar_one()
    payload = dict(row.dimensions)
    entry = dict(payload[dim])
    entry["value"] = value
    entry["status"] = "ok"
    payload[dim] = entry
    row.dimensions = payload
    await db.commit()


async def test_calibration_quantifies_error_before_and_after(db_session, test_user):
    """coverage judge 恒 1.0、行为锚 5/7 → 拟合把 MAE 2/7 降到 1/28，且检测不红。"""
    dims_service = UnderstandingDimensionsService(db_session)
    await _seed_series(db_session, test_user.id, judge_score=1.0, dup_rate_denominator=10)
    await _compute_rows(dims_service, test_user.id)

    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)

    cov_map = report["coverage_map"]
    assert cov_map["applied"] is True, cov_map
    # 恒等误差 |1 − 5/7| = 2/7；拟合 b=-2/7 被 clamp 到 -0.25 → 0.75 vs 5/7 = 1/28。
    assert cov_map["mae_before"] == pytest.approx(2 / 7, abs=1e-3)
    assert cov_map["mae_after"] == pytest.approx(1 / 28, abs=1e-3)
    assert cov_map["mae_after"] < cov_map["mae_before"]  # 误差量化：校准后更小
    # 校准后 coverage 与行为锚对齐 → 不红
    assert report["dimensions"]["coverage"]["status"] != "drift"
    assert report["overall_status"] != "red"
    # 运行已持久化
    latest = await calib.latest_run(user_id=test_user.id)
    assert latest is not None and latest.coverage_map["applied"] is True


async def test_uncalibrated_systematic_gap_reads_as_drift(db_session, test_user):
    """未校准且存在系统性 gap（拟合对数不足）→ 检测器红。

    构造：行为锚 5/7 与 stored coverage 1.0 恒差 2/7，但只有 2 行（< 拟合门槛 3）
    → map=identity → 最近窗误差 2/7 > 0.15 门 → coverage=drift, overall=red。
    """
    dims_service = UnderstandingDimensionsService(db_session)
    await _seed_series(db_session, test_user.id, judge_score=1.0, dup_rate_denominator=10)
    await _compute_rows(dims_service, test_user.id, days=2)  # 2 行 < COVERAGE_FIT_MIN_PAIRS

    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)
    assert report["coverage_map"]["applied"] is False
    assert report["dimensions"]["coverage"]["status"] == "drift"
    assert report["dimensions"]["coverage"]["recent_error"] == pytest.approx(2 / 7, abs=1e-3)
    assert report["overall_status"] == "red"


async def test_tampered_daily_row_goes_red(db_session, test_user):
    """验收（变异必红）：落行后篡改 correctness → 重算锚点不一致 → 红。"""
    dims_service = UnderstandingDimensionsService(db_session)
    await _seed_series(db_session, test_user.id)
    await _compute_rows(dims_service, test_user.id)
    # 篡改最新行：correctness 实为 1.0（0 负定/10 使用），改写为 0.1。
    await _tamper_latest_row(db_session, test_user.id, dim="correctness", value=0.1)

    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)
    entry = report["dimensions"]["correctness"]
    assert entry["status"] == "drift"
    # 最近 3 行（D-2, D-1, D）中只有被篡改的最新行有误差 0.9 → 均值 0.3。
    assert entry["recent_error"] == pytest.approx(0.3, abs=1e-3)
    assert report["overall_status"] == "red"


async def test_late_arriving_data_goes_red(db_session, test_user):
    """验收（真实漂移语义）：落行后窗口内补进 5 条 reject → correctness 锚点
    从 1.0 掉到 0.0，与落行值 1.0 差 1.0 → 红。"""
    dims_service = UnderstandingDimensionsService(db_session)
    await _seed_series(db_session, test_user.id)
    await _compute_rows(dims_service, test_user.id)

    pref = MemoryPreference(
        user_id=test_user.id,
        pref_key=f"pref_{uuid4().hex[:8]}",
        pref_value={"v": 1},
        version=1,
        created_at=_ts(-1),
        updated_at=_ts(-1),
    )
    db_session.add(pref)
    await db_session.flush()
    for _ in range(5):
        db_session.add(
            MemoryCorrection(
                user_id=test_user.id,
                memory_type="preference",
                memory_id=pref.id,
                action="reject",
                created_at=_ts(-1),
                updated_at=_ts(-1),
            )
        )
    await db_session.commit()

    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)
    entry = report["dimensions"]["correctness"]
    assert entry["status"] == "drift"
    # 最近 3 行（D-2 无误差, D-1 与 D 的窗含 late 数据 → 各 1.0）→ 均值 2/3。
    assert entry["recent_error"] == pytest.approx(2 / 3, abs=1e-3)
    assert report["overall_status"] == "red"


async def test_stable_series_stays_green(db_session, test_user):
    """无篡改、无 late 数据、行为与度量一致 → 任何维都不红。"""
    dims_service = UnderstandingDimensionsService(db_session)
    await _seed_series(db_session, test_user.id)
    await _compute_rows(dims_service, test_user.id)

    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)
    assert report["overall_status"] != "red"
    for dim, entry in report["dimensions"].items():
        assert entry["status"] != "drift", (dim, entry)


async def test_no_rows_report_is_insufficient_not_red(db_session, test_user):
    calib = UnderstandingCalibrationService(db_session)
    report = await calib.run_for_user(user_id=test_user.id)
    assert report["row_count"] == 0
    assert report["overall_status"] == "insufficient"
    assert all(e["status"] == "insufficient" for e in report["dimensions"].values())
    latest = await calib.latest_run(user_id=test_user.id)
    assert latest is not None  # insufficient 也落痕（审计面）
