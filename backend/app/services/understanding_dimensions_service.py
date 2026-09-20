"""D-03 · Understanding 五维每日聚合服务（真实表取数 + 行为锚点冻结）。

职责（与 core 契约、calibration service 的分工）：
- 本服务：从既有生产表取数 → 调 core 纯函数算五维 → 同窗行为锚点 →
  每用户每日幂等 upsert 落 ``understanding_dimension_daily``。
- ``app/core/understanding_dimensions.py``：公式与缺失语义（冻结，无 I/O）。
- ``app/services/understanding_calibration_service.py``：锚点重算对齐 + 离线
  校准 + 漂移检测。

数据源（全部既有表，零新真源；dev 实测 2026-09-20 只读盘点见模块尾注）：
- aurora_judgment_records → coverage（确定性 Stage20 judge，非 LLM 自评）
- context_pack_runs(memory_counts) → correctness 分母（注入 ≥1 记忆的使用机会）
- memory_corrections(action 分区, core 契约冻结) → correctness/scope/freshness/utility
- unresolved_conflicts → correctness 冲突面
- memory 三表（preference/goal/episodic）created_at → freshness lag
- chat_messages(role=user) → coverage 行为锚点（重复提问率的归一化沿用
  ``understanding_depth_metric_service`` 的既有语义，不另立真源）

窗口语义：metric_date = D 的行按**滚动 window_days（默认 7）窗口**
[D-window_days+1 00:00, D+1 00:00) 计算（UTC，DB naive-UTC 规范）。
维度样本稀疏（memory_reference/scope 面 live 0 行）→ 滚动窗是 unknown 减少
虚假抖动的最小手段；样本量仍逐维记录在 detail 里，缺就是 unknown。

无活动规则：窗口内五类输入全为空（无 judgment、无 pack run、无 correction、
无 conflict、无 user 消息）→ 不落行（与既有 understanding_depth_daily 一致）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.understanding_dimensions import (
    ALL_DIMENSIONS,
    CORRECTNESS_NEGATIVE_ACTIONS,
    FRESHNESS_STATE_CHANGE_ACTIONS,
    SCOPE_FEEDBACK_ACTIONS,
    SCOPE_NEGATIVE_ACTIONS,
    UTILITY_DECISIVE_ACTIONS,
    UTILITY_POSITIVE_ACTIONS,
    DimensionName,
    DimensionValue,
    compute_correctness,
    compute_coverage,
    compute_freshness,
    compute_scope_precision,
    compute_utility,
)
from app.models.aurora_stage20 import AuroraJudgmentRecord, UnresolvedConflict
from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryGoal, MemoryPreference
from app.models.understanding_dimensions import UnderstandingDimensionDaily
from app.services.understanding_depth_metric_service import (
    SHORT_MESSAGE_MIN_LEN,
    _normalize_message,
    normalize_memory_counts,
)

DEFAULT_WINDOW_DAYS = 7

#: memory_type 字符串 → ORM 模型（memory_corrections.memory_type 的读侧映射）。
_MEMORY_TYPE_MODELS: dict[str, type] = {
    "preference": MemoryPreference,
    "goal": MemoryGoal,
    "episodic": EpisodicMemory,
}


@dataclass
class WindowInputs:
    """一个滚动窗的全部原始输入（可重放；golden/测试与生产共用此结构）。"""

    context_scores: list[float] = field(default_factory=list)
    task_scores: list[float] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    usage_opportunities: int = 0
    correctness_negatives: int = 0
    unresolved_conflicts: int = 0
    scope_feedback_total: int = 0
    scope_negatives: int = 0
    lag_days: list[float] = field(default_factory=list)
    utility_accepted: int = 0
    utility_corrected: int = 0
    utility_denied: int = 0
    user_messages: list[str] = field(default_factory=list)

    @property
    def has_any_activity(self) -> bool:
        return bool(
            self.context_scores
            or self.usage_opportunities
            or self.correctness_negatives
            or self.unresolved_conflicts
            or self.scope_feedback_total
            or self.lag_days
            or self.utility_accepted
            or self.utility_corrected
            or self.utility_denied
            or self.user_messages
        )


def window_bounds(day: date_type, window_days: int = DEFAULT_WINDOW_DAYS) -> tuple[datetime, datetime]:
    """滚动窗口 UTC 边界：[D-window_days+1 00:00, D+1 00:00)。"""
    end = datetime(day.year, day.month, day.day) + timedelta(days=1)
    start = end - timedelta(days=max(1, int(window_days)))
    return start, end


def dimensions_from_inputs(inputs: WindowInputs) -> dict[str, DimensionValue]:
    """core 纯函数的批量入口：WindowInputs → 五维（键 = ALL_DIMENSIONS 顺序）。"""
    values = {
        DimensionName.COVERAGE.value: compute_coverage(
            context_scores=inputs.context_scores,
            task_scores=inputs.task_scores,
            missing_dimensions=inputs.missing_dimensions,
        ),
        DimensionName.CORRECTNESS.value: compute_correctness(
            usage_opportunities=inputs.usage_opportunities,
            negative_corrections=inputs.correctness_negatives,
            unresolved_conflicts=inputs.unresolved_conflicts,
        ),
        DimensionName.SCOPE_PRECISION.value: compute_scope_precision(
            scope_feedback_total=inputs.scope_feedback_total,
            scope_negative=inputs.scope_negatives,
        ),
        DimensionName.FRESHNESS.value: compute_freshness(lag_days_samples=inputs.lag_days),
        DimensionName.UTILITY.value: compute_utility(
            accepted=inputs.utility_accepted,
            corrected=inputs.utility_corrected,
            denied=inputs.utility_denied,
        ),
    }
    return {dim.value: values[dim.value] for dim in ALL_DIMENSIONS}  # 键序按 ALL_DIMENSIONS 冻结


def repeat_question_rate(messages: list[str]) -> float | None:
    """重复提问率（与 understanding_depth_metric_service 同语义，锚点专用）。

    返回 None = 窗口内无可判定消息（锚点 insufficient 的诚实态）。
    """
    normalized = [_normalize_message(msg) for msg in messages]
    eligible = [text for text in normalized if len(text) > SHORT_MESSAGE_MIN_LEN]
    if not eligible:
        return None
    seen: dict[str, int] = {}
    for text in eligible:
        seen[text] = seen.get(text, 0) + 1
    duplicates = sum(count - 1 for count in seen.values() if count > 1)
    return duplicates / len(eligible)


def anchors_from_inputs(inputs: WindowInputs) -> dict[str, dict]:
    """行为锚点：维度值应与之对齐的外部可观察行为量。

    - coverage 锚点 = 1 − 重复提问率（独立行为流：真懂用户的系统不该被反复
      问同一问题）。无判定消息 → value=None（insufficient）。
    - correctness / scope_precision / freshness / utility 是行为定义维：锚点 =
      同一公式在**取数时点**原始数据上的重算值。校准服务在**检测时点**再重算
      一次并与落行值比对 → 捕获 late-arriving 数据 / 落行后被篡改 / 公式漂移。
    """
    anchors: dict[str, dict] = {}
    rate = repeat_question_rate(inputs.user_messages)
    anchors[DimensionName.COVERAGE.value] = {
        "anchor_value": None if rate is None else round(max(0.0, 1.0 - rate), 4),
        "anchor_samples": len(inputs.user_messages),
        "method": "1 - repeat_question_rate(chat_messages)",
    }
    recomputed = dimensions_from_inputs(inputs)
    for dim in (
        DimensionName.CORRECTNESS,
        DimensionName.SCOPE_PRECISION,
        DimensionName.FRESHNESS,
        DimensionName.UTILITY,
    ):
        entry = recomputed[dim.value]
        anchors[dim.value] = {
            "anchor_value": entry.value,
            "anchor_samples": entry.samples,
            "method": "dimension formula recomputed from raw tables at collect time",
        }
    return anchors


class UnderstandingDimensionsService:
    """五维每日聚合（Celery 每日触发；也可带 day 重算补齐历史）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 取数（真实表；每个查询都带 user_id 隔离）
    # ------------------------------------------------------------------

    async def collect_window_inputs(
        self,
        *,
        user_id: UUID,
        day: date_type,
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> WindowInputs:
        start, end = window_bounds(day, window_days)
        inputs = WindowInputs()

        # coverage：确定性 sufficiency judge 落行
        judgments = await self.db.execute(
            select(
                AuroraJudgmentRecord.context_sufficiency_score,
                AuroraJudgmentRecord.task_sufficiency_score,
                AuroraJudgmentRecord.task_missing_dimensions,
                AuroraJudgmentRecord.context_missing_dimensions,
            ).where(
                AuroraJudgmentRecord.user_id == user_id,
                AuroraJudgmentRecord.created_at >= start,
                AuroraJudgmentRecord.created_at < end,
            )
        )
        for ctx_score, task_score, task_missing, ctx_missing in judgments.all():
            inputs.context_scores.append(float(ctx_score or 0.0))
            inputs.task_scores.append(float(task_score or 0.0))
            for seq in (task_missing, ctx_missing):
                if isinstance(seq, list):
                    inputs.missing_dimensions.extend(str(x) for x in seq if x)

        # correctness 分母：注入 ≥1 条记忆的 context pack run（模型被使用的次数）
        runs = await self.db.execute(
            select(ContextPackRun.memory_counts).where(
                ContextPackRun.user_id == user_id,
                ContextPackRun.created_at >= start,
                ContextPackRun.created_at < end,
            )
        )
        inputs.usage_opportunities = sum(1 for row in runs.scalars().all() if normalize_memory_counts(row) > 0)

        # corrections 动作分区（core 契约冻结的封闭集）
        corrections = await self.db.execute(
            select(
                MemoryCorrection.memory_type,
                MemoryCorrection.memory_id,
                MemoryCorrection.action,
                MemoryCorrection.created_at,
            ).where(
                MemoryCorrection.user_id == user_id,
                MemoryCorrection.created_at >= start,
                MemoryCorrection.created_at < end,
            )
        )
        state_change_rows: list[tuple[str, UUID, datetime]] = []
        for memory_type, memory_id, action, created_at in corrections.all():
            action_str = str(action or "")
            if action_str in CORRECTNESS_NEGATIVE_ACTIONS:
                inputs.correctness_negatives += 1
            if action_str in SCOPE_FEEDBACK_ACTIONS:
                inputs.scope_feedback_total += 1
                if action_str in SCOPE_NEGATIVE_ACTIONS:
                    inputs.scope_negatives += 1
            if action_str in UTILITY_DECISIVE_ACTIONS:
                if action_str in UTILITY_POSITIVE_ACTIONS:
                    inputs.utility_accepted += 1
                elif action_str == "memory_reference_corrected":
                    inputs.utility_corrected += 1
                else:
                    inputs.utility_denied += 1
            if action_str in FRESHNESS_STATE_CHANGE_ACTIONS:
                state_change_rows.append((str(memory_type or ""), memory_id, created_at))

        # correctness 冲突面：窗口内出现的未解决冲突
        conflicts = await self.db.execute(
            select(UnresolvedConflict.id).where(
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.created_at >= start,
                UnresolvedConflict.created_at < end,
            )
        )
        inputs.unresolved_conflicts = len(conflicts.all())

        # freshness lag：状态变更型纠正 → 被改记录旧状态存活天数
        if state_change_rows:
            created_by_model: dict[type, dict[UUID, datetime]] = {}
            for model in _MEMORY_TYPE_MODELS.values():
                ids = {
                    memory_id for m_type, memory_id, _ in state_change_rows if _MEMORY_TYPE_MODELS.get(m_type) is model
                }
                if not ids:
                    continue
                rows = await self.db.execute(select(model.id, model.created_at).where(model.id.in_(ids)))
                created_by_model[model] = dict(rows.all())
            for memory_type, memory_id, corrected_at in state_change_rows:
                model = _MEMORY_TYPE_MODELS.get(memory_type)
                if model is None:
                    continue
                record_created = created_by_model.get(model, {}).get(memory_id)
                if record_created is None or corrected_at is None:
                    continue
                lag = (corrected_at - record_created).total_seconds() / 86400.0
                inputs.lag_days.append(lag)

        # coverage 行为锚点输入：user 消息原文
        messages = await self.db.execute(
            select(ChatMessage.content).where(
                ChatMessage.user_id == user_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end,
                ChatMessage.deleted_at.is_(None),
            )
        )
        inputs.user_messages = [str(text or "") for text in messages.scalars().all()]

        return inputs

    # ------------------------------------------------------------------
    # 每日聚合 + 幂等落行
    # ------------------------------------------------------------------

    async def compute_daily_for_user(
        self,
        *,
        user_id: UUID,
        day: date_type,
        window_days: int = DEFAULT_WINDOW_DAYS,
    ) -> dict[str, dict] | None:
        """计算并 upsert 单用户单日五维；窗口无任何活动返回 None（不落行）。"""
        inputs = await self.collect_window_inputs(user_id=user_id, day=day, window_days=window_days)
        if not inputs.has_any_activity:
            return None

        dimensions = dimensions_from_inputs(inputs)
        anchors = anchors_from_inputs(inputs)
        payload = {dim.value: dimensions[dim.value].to_dict() for dim in ALL_DIMENSIONS}

        existing = (
            await self.db.execute(
                select(UnderstandingDimensionDaily).where(
                    UnderstandingDimensionDaily.user_id == user_id,
                    UnderstandingDimensionDaily.metric_date == day,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(
                UnderstandingDimensionDaily(
                    user_id=user_id,
                    metric_date=day,
                    dimensions=payload,
                    anchors=anchors,
                    window_days=window_days,
                )
            )
        else:
            existing.dimensions = payload
            existing.anchors = anchors
            existing.window_days = window_days
        await self.db.commit()
        return payload

    async def compute_daily_all(
        self,
        *,
        day: date_type,
        window_days: int = DEFAULT_WINDOW_DAYS,
        limit: int = 2000,
    ) -> dict[str, int]:
        """对窗口内有活动的用户全量计算（Celery beat 每日触发）。"""
        start, end = window_bounds(day, window_days)
        user_ids: set[UUID] = set()

        for stmt in (
            select(AuroraJudgmentRecord.user_id).where(
                AuroraJudgmentRecord.created_at >= start, AuroraJudgmentRecord.created_at < end
            ),
            select(ContextPackRun.user_id).where(ContextPackRun.created_at >= start, ContextPackRun.created_at < end),
            select(MemoryCorrection.user_id).where(
                MemoryCorrection.created_at >= start, MemoryCorrection.created_at < end
            ),
            select(ChatMessage.user_id).where(
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end,
                ChatMessage.deleted_at.is_(None),
            ),
        ):
            result = await self.db.execute(stmt)
            user_ids.update(row for row in result.scalars().all() if row)

        computed = 0
        skipped = 0
        for user_id in sorted(user_ids)[:limit]:
            try:
                if await self.compute_daily_for_user(user_id=user_id, day=day, window_days=window_days) is None:
                    skipped += 1
                else:
                    computed += 1
            except Exception as exc:  # 单用户失败不阻断整批
                logger.warning(f"understanding-dimensions daily compute failed for {user_id}: {exc}")
                skipped += 1
        return {"active_users": len(user_ids), "computed": computed, "skipped": skipped}

    async def get_latest_row(self, *, user_id: UUID) -> UnderstandingDimensionDaily | None:
        result = await self.db.execute(
            select(UnderstandingDimensionDaily)
            .where(UnderstandingDimensionDaily.user_id == user_id)
            .order_by(UnderstandingDimensionDaily.metric_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
