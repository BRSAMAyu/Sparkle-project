"""D-03 · Understanding 五维校准：行为对齐 + 离线校准 + 漂移检测。

三层机制（全部确定性、无 LLM）：

1. **行为锚点对齐**（``UnderstandingDimensionsService.anchors_from_inputs``）：
   每个维度有外部可观察行为锚点 —— coverage 锚 = 1 − 重复提问率（独立行为流）；
   行为定义四维（correctness/scope/freshness/utility）锚 = 公式在取数时点原始
   数据上的重算值。
2. **离线校准（coverage 仿射重标定）**：coverage 是唯一由 judge 分数表述的维度，
   可能系统性高/低估行为实况 → 在校准窗上对 (stored_coverage, anchor) 做最小二乘
   仿射拟合（有界 a∈[0.5,2.0]、b∈[-0.25,0.25]），拟合 MAE 不优于恒等映射则不
   应用（安全回退 identity）。行为定义四维**不做拟合**——它们由行为直接定义，
   对自身行为拟合是循环论证；它们的「校准」= 下面的漂移检测（一致性校准）。
3. **漂移检测**（验收：注入漂移 → 检测器红）：
   - 最近 K 行：**检测时点**从原始表重算锚点，与落行值比对 → 捕获落行后被篡改、
     late-arriving 数据、公式/代码漂移；
   - 基线行（更早行）：用落行时冻结的锚点（compute-time 一致性面）；
   - drift ⟺ recent_error > max(DRIFT_ABS_THRESHOLD, baseline_error + DRIFT_DELTA)。

误差量化（验收：校准前后度量误差）：coverage 报 mae_before（恒等映射下
|stored − anchor| 均值）与 mae_after（拟合映射下），applied=False 时两者相等。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.understanding_dimensions import ALL_DIMENSIONS, DimensionName
from app.models.understanding_dimensions import UnderstandingCalibrationRun, UnderstandingDimensionDaily
from app.services.understanding_dimensions_service import (
    DEFAULT_WINDOW_DAYS,
    UnderstandingDimensionsService,
    anchors_from_inputs,
)

CALIBRATION_WINDOW_ROWS = 14
"""参与离线校准/漂移基线的最近 daily 行数上限。"""

DRIFT_RECENT_ROWS = 3
"""漂移检测的「最近窗」行数（这些行做检测时点锚点重算）。"""

DRIFT_ABS_THRESHOLD = 0.15
"""绝对漂移门：最近窗平均误差超过此值即红（与基线无关）。"""

DRIFT_DELTA = 0.10
"""相对漂移门：最近窗误差比基线平均高出此值即红。"""

COVERAGE_FIT_MIN_PAIRS = 3
"""仿射拟合最少样本对（不足 → identity 不应用）。"""

COVERAGE_A_BOUNDS: tuple[float, float] = (0.5, 2.0)
COVERAGE_B_BOUNDS: tuple[float, float] = (-0.25, 0.25)

#: 行为定义维（恒等校准——不做拟合，理由见模块 docstring）。
BEHAVIOR_DEFINED_DIMS: tuple[DimensionName, ...] = (
    DimensionName.CORRECTNESS,
    DimensionName.SCOPE_PRECISION,
    DimensionName.FRESHNESS,
    DimensionName.UTILITY,
)


class CalibrationStatus(StrEnum):
    ALIGNED = "aligned"
    DRIFT = "drift"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class AffineMap:
    """仿射重标定 map：display = clamp(a * x + b, 0, 1)。恒等时 a=1, b=0。"""

    a: float = 1.0
    b: float = 0.0
    applied: bool = False
    fitted_pairs: int = 0
    mae_before: float | None = None
    mae_after: float | None = None
    method: str = "identity"

    def apply(self, x: float) -> float:
        return min(1.0, max(0.0, self.a * float(x) + self.b))

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": round(self.a, 4),
            "b": round(self.b, 4),
            "applied": self.applied,
            "fitted_pairs": self.fitted_pairs,
            "mae_before": None if self.mae_before is None else round(self.mae_before, 4),
            "mae_after": None if self.mae_after is None else round(self.mae_after, 4),
            "method": self.method,
        }


def fit_affine_map(pairs: list[tuple[float, float]]) -> AffineMap:
    """对 (stored, anchor) 对做有界最小二乘仿射拟合（纯函数，无 numpy）。

    安全规则：拟合结果（含 clamp 到界内）必须严格优于恒等映射的 MAE 才 applied；
    否则返回恒等 map（校准永不把误差变大——单调安全）。
    """
    n = len(pairs)
    if n < COVERAGE_FIT_MIN_PAIRS:
        return AffineMap(applied=False, fitted_pairs=n, method="insufficient_pairs")

    xs = [float(x) for x, _ in pairs]
    ys = [float(y) for _, y in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)

    def mae_of(a: float, b: float) -> float:
        return sum(abs(a * x + b - y) for x, y in zip(xs, ys, strict=True)) / n

    mae_identity = mae_of(1.0, 0.0)
    if var_x < 1e-12:
        # stored 全部相同（judge 恒定输出）：只能拟 b（平移截距）。
        a_raw, b_raw = 1.0, mean_y - mean_x
    else:
        cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        a_raw = cov_xy / var_x
        b_raw = mean_y - a_raw * mean_x

    a = min(COVERAGE_A_BOUNDS[1], max(COVERAGE_A_BOUNDS[0], a_raw))
    b = min(COVERAGE_B_BOUNDS[1], max(COVERAGE_B_BOUNDS[0], b_raw))
    mae_fitted = mae_of(a, b)
    if mae_fitted < mae_identity - 1e-9:
        return AffineMap(
            a=a,
            b=b,
            applied=True,
            fitted_pairs=n,
            mae_before=mae_identity,
            mae_after=mae_fitted,
            method="bounded_ols",
        )
    return AffineMap(
        applied=False,
        fitted_pairs=n,
        mae_before=mae_identity,
        mae_after=mae_identity,
        method="identity_no_improvement",
    )


def _row_dim_value(row: UnderstandingDimensionDaily, dim: DimensionName) -> float | None:
    entry = (row.dimensions or {}).get(dim.value) or {}
    if entry.get("status") != "ok":
        return None
    value = entry.get("value")
    return None if value is None else float(value)


def _stored_anchor(row: UnderstandingDimensionDaily, dim: DimensionName) -> float | None:
    entry = (row.anchors or {}).get(dim.value) or {}
    value = entry.get("anchor_value")
    return None if value is None else float(value)


class UnderstandingCalibrationService:
    """离线校准 + 漂移检测（Celery 每日触发；结果落 understanding_calibration_runs）。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dimensions_service = UnderstandingDimensionsService(db)

    # ------------------------------------------------------------------
    # 校准主入口
    # ------------------------------------------------------------------

    async def run_for_user(
        self,
        *,
        user_id: UUID,
        as_of: date_type | None = None,
        window_rows: int = CALIBRATION_WINDOW_ROWS,
    ) -> dict[str, Any]:
        """跑一次校准并落 ``understanding_calibration_runs``，返回报告 dict。"""
        rows = (
            (
                await self.db.execute(
                    select(UnderstandingDimensionDaily)
                    .where(UnderstandingDimensionDaily.user_id == user_id)
                    .order_by(UnderstandingDimensionDaily.metric_date.desc())
                    .limit(window_rows)
                )
            )
            .scalars()
            .all()
        )
        rows = list(reversed(rows))  # metric_date 升序

        report: dict[str, Any] = {"row_count": len(rows), "dimensions": {}}

        if not rows:
            report["dimensions"] = {dim.value: self._insufficient("no daily rows") for dim in ALL_DIMENSIONS}
            report["coverage_map"] = AffineMap().to_dict()
            report["overall_status"] = "insufficient"
            await self._persist(user_id=user_id, report=report)
            return report

        # ---- coverage：离线仿射拟合（stored vs 落行时冻结的行为锚点）----
        coverage_pairs: list[tuple[float, float]] = []
        for row in rows:
            stored = _row_dim_value(row, DimensionName.COVERAGE)
            anchor = _stored_anchor(row, DimensionName.COVERAGE)
            if stored is not None and anchor is not None:
                coverage_pairs.append((stored, anchor))
        coverage_map = fit_affine_map(coverage_pairs)
        report["coverage_map"] = coverage_map.to_dict()

        # ---- 漂移检测：最近 K 行做检测时点锚点重算，基线用冻结锚点 ----
        recent_rows = rows[-DRIFT_RECENT_ROWS:]
        baseline_rows = rows[:-DRIFT_RECENT_ROWS]

        recomputed_anchors = await self._recompute_anchors(user_id=user_id, rows=recent_rows)

        for dim in ALL_DIMENSIONS:
            report["dimensions"][dim.value] = self._drift_for_dimension(
                dim=dim,
                coverage_map=coverage_map,
                recent_rows=recent_rows,
                recent_anchors=recomputed_anchors,
                baseline_rows=baseline_rows,
            )

        drift_any = any(entry["status"] == CalibrationStatus.DRIFT.value for entry in report["dimensions"].values())
        aligned_any = any(entry["status"] == CalibrationStatus.ALIGNED.value for entry in report["dimensions"].values())
        report["overall_status"] = "red" if drift_any else ("green" if aligned_any else "insufficient")
        await self._persist(user_id=user_id, report=report)
        return report

    # ------------------------------------------------------------------
    # 内部构件
    # ------------------------------------------------------------------

    def _insufficient(self, reason: str) -> dict[str, Any]:
        return {
            "status": CalibrationStatus.INSUFFICIENT.value,
            "recent_error": None,
            "baseline_error": None,
            "n": 0,
            "reason": reason,
        }

    def _drift_for_dimension(
        self,
        *,
        dim: DimensionName,
        coverage_map: AffineMap,
        recent_rows: list[UnderstandingDimensionDaily],
        recent_anchors: dict[date_type, dict[str, dict]],
        baseline_rows: list[UnderstandingDimensionDaily],
    ) -> dict[str, Any]:
        # 最近窗误差：stored（coverage 用校准后值）vs 检测时点重算锚点。
        recent_errors: list[float] = []
        for row in recent_rows:
            stored = _row_dim_value(row, dim)
            anchor_entry = recent_anchors.get(row.metric_date, {}).get(dim.value) or {}
            anchor = anchor_entry.get("anchor_value")
            if stored is None or anchor is None:
                continue
            comparable = coverage_map.apply(stored) if dim is DimensionName.COVERAGE else stored
            recent_errors.append(abs(comparable - float(anchor)))

        # 基线误差：coverage 用 stored vs 冻结行为锚点；行为定义维的冻结锚点与
        # 落行值同源同算（基线误差恒 0，见模块 docstring——其漂移语义是绝对门）。
        baseline_errors: list[float] = []
        if dim is DimensionName.COVERAGE:
            for row in baseline_rows:
                stored = _row_dim_value(row, dim)
                anchor = _stored_anchor(row, dim)
                if stored is not None and anchor is not None:
                    baseline_errors.append(abs(coverage_map.apply(stored) - anchor))

        if not recent_errors:
            return self._insufficient("no comparable (stored, anchor) pairs in recent window")

        recent_error = sum(recent_errors) / len(recent_errors)
        baseline_error = (sum(baseline_errors) / len(baseline_errors)) if baseline_errors else 0.0
        threshold = max(DRIFT_ABS_THRESHOLD, baseline_error + DRIFT_DELTA)
        status = CalibrationStatus.DRIFT if recent_error > threshold else CalibrationStatus.ALIGNED
        return {
            "status": status.value,
            "recent_error": round(recent_error, 4),
            "baseline_error": round(baseline_error, 4),
            "threshold": round(threshold, 4),
            "n": len(recent_errors),
        }

    async def _recompute_anchors(
        self,
        *,
        user_id: UUID,
        rows: list[UnderstandingDimensionDaily],
    ) -> dict[date_type, dict[str, dict]]:
        """检测时点重算：对每行按其 (metric_date, window_days) 从原始表重新取数。"""
        out: dict[date_type, dict[str, dict]] = {}
        for row in rows:
            try:
                inputs = await self.dimensions_service.collect_window_inputs(
                    user_id=user_id,
                    day=row.metric_date,
                    window_days=row.window_days or DEFAULT_WINDOW_DAYS,
                )
                out[row.metric_date] = anchors_from_inputs(inputs)
            except Exception:  # 单行重算失败 → 该行无锚点（漂移面退化为 insufficient）
                out[row.metric_date] = {}
        return out

    async def _persist(self, *, user_id: UUID, report: dict[str, Any]) -> None:
        self.db.add(
            UnderstandingCalibrationRun(
                user_id=user_id,
                ran_at=datetime.utcnow(),
                window_days=CALIBRATION_WINDOW_ROWS,
                coverage_map=report.get("coverage_map") or {},
                drift_report=report.get("dimensions") or {},
                overall_status=str(report.get("overall_status") or "insufficient"),
            )
        )
        await self.db.commit()

    async def latest_run(self, *, user_id: UUID) -> UnderstandingCalibrationRun | None:
        result = await self.db.execute(
            select(UnderstandingCalibrationRun)
            .where(UnderstandingCalibrationRun.user_id == user_id)
            .order_by(UnderstandingCalibrationRun.ran_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


def apply_coverage_calibration(value: float, coverage_map_dict: dict[str, Any] | None) -> float:
    """把持久化的 coverage_map dict 作用到展示值（API 面用；缺 map = 恒等）。"""
    if not coverage_map_dict:
        return float(value)
    try:
        a = float(coverage_map_dict.get("a", 1.0))
        b = float(coverage_map_dict.get("b", 0.0))
    except (TypeError, ValueError):
        return float(value)
    if not math.isfinite(a) or not math.isfinite(b):
        return float(value)
    return min(1.0, max(0.0, a * float(value) + b))
