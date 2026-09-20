"""D-03 · Understanding 五维每日度量与校准运行持久化模型。

两张表，均由 Celery 每日任务离线聚合写入（读模型，无在线写路径）：

- ``understanding_dimension_daily``：每用户每日一行，五维值 + 当窗行为锚点
  （anchor——校准/漂移检测的输入在落行时一并冻结，可重放）。
- ``understanding_calibration_runs``：离线校准运行记录（coverage 仿射重标定
  map、校准前后误差、各维漂移状态快照）——审计与「校准前后误差量化」证据面。

数据源全部为既有生产表（aurora_judgment_records / memory_corrections /
unresolved_conflicts / context_pack_runs / chat_messages），无新真源。
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, Date, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class UnderstandingDimensionDaily(BaseModel):
    __tablename__ = "understanding_dimension_daily"

    user_id = Column(GUID(), nullable=False, index=True)
    metric_date = Column(Date, nullable=False)
    # 五维结果（understanding.dimensions.v1）：
    # {<dim>: {status, value, samples, provenance, detail}}，键序 = ALL_DIMENSIONS。
    dimensions = Column(JSONBCompat, nullable=False, default=dict)
    # 落行时同窗计算的行为锚点（漂移检测的对齐基准，与维度值同窗冻结）：
    # {<dim>: {anchor_value, anchor_samples}}（unknown 锚点 value=null）。
    anchors = Column(JSONBCompat, nullable=False, default=dict)
    # 聚合窗口天数（滚动窗口，默认 7；重放/审计需要知道行是按什么窗算的）。
    window_days = Column(Integer, nullable=False, default=7)
    schema_version = Column(String(64), nullable=False, default="understanding.dimensions.v1")

    __table_args__ = (
        UniqueConstraint("user_id", "metric_date", name="uq_understanding_dimension_daily_user_date"),
        Index("idx_understanding_dimension_daily_date", "metric_date"),
    )


class UnderstandingCalibrationRun(BaseModel):
    __tablename__ = "understanding_calibration_runs"

    user_id = Column(GUID(), nullable=False, index=True)
    ran_at = Column(DateTime, nullable=False)
    # 校准窗（天）：从最近可用 daily 行回溯参与拟合的行数窗口。
    window_days = Column(Integer, nullable=False, default=14)
    # coverage 仿射重标定 map（其余维度恒等——行为定义维，拟合即循环论证）：
    # {a, b, method, fitted_pairs, mae_before, mae_after, applied}
    coverage_map = Column(JSONBCompat, nullable=False, default=dict)
    # 各维漂移检测快照：
    # {<dim>: {status: aligned|drift|insufficient, recent_error, baseline_error, n}}
    drift_report = Column(JSONBCompat, nullable=False, default=dict)
    # 汇总红/绿（任一维 drift → red）。
    overall_status = Column(String(16), nullable=False, default="insufficient")
    schema_version = Column(String(64), nullable=False, default="understanding.dimensions.v1")

    __table_args__ = (Index("idx_understanding_calibration_runs_user_ran_at", "user_id", "ran_at"),)
