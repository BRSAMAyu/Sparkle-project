"""自我 7 日锚视图（D-COMM-1 · 排行榜 P1 债务 #3 裁决落地）。

裁决（v3-output/D-COMMUNITY/DESIGN.md §3.2 + KNOWN_CODE_DEBT_LEDGER P1 #3）：
- 全站综合榜保持 D17 隐藏（「打击中尾生」反面模式，DESIGN §2.2），不新增产品入口；
- 只挂「自我历史对比」视图：本人近 7 日每日冲刺完成度 / 掌握度增量序列，
  只跟自己的历史比（零社交伤害）；后续 D-COMM-4 小队双视图榜复用本面。

数据源（复用既有面，不新造聚合口径）：
- 冲刺完成度 = sprint 任务账本（app/services/sprint_task_ledger.py，BP-4
  单一事实源）按 completed_at 落日分布；账本条件复用 sprint_ledger_condition，
  完成判定与账本同源（status == COMPLETED——abandon 路径也会写 completed_at，
  见 task_service.py:1238，故状态过滤不可省）；
- 掌握度增量 = study_records（galaxy 掌握度事件流，galaxy/stats_service 与
  error_book_mastery_sync_service 写入）按日 SUM(mastery_delta)。state_aggregator
  的 learning_state 是 prompt 侧即时快照、无按日历史，故按日增量读其底层事实面。

语义（诚实数据，D20）：
- 窗口固定 7 天（UTC 日界，含今天），无数据的天如实补零，不内插不估算；
- has_any_data=False 表示窗口内完全无任何记录（空态），全零曲线必须是真零；
- 时区：与账本/学习记录存储一致按 UTC 落日；本地化日界属展示层职责。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import date as _date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus
from app.schemas.leaderboard import SelfAnchorDayPoint, SelfAnchorViewResponse
from app.services.sprint_task_ledger import sprint_ledger_condition

WINDOW_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _day_index(window_start: _date, at: datetime) -> int | None:
    """落日 → 窗口内下标（0=窗口首日）；窗口外返回 None（防御未来/乱序时间戳）。"""
    day = at.date() if at.tzinfo is None else at.astimezone(UTC).date()
    offset = (day - window_start).days
    if 0 <= offset < WINDOW_DAYS:
        return offset
    return None


class LeaderboardSelfAnchorService:
    """自我 7 日锚视图取数（只读，无缓存、无新聚合口径）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_self_anchor_view(self, user_id: UUID) -> SelfAnchorViewResponse:
        window_end = _utcnow().date()
        window_start = window_end - timedelta(days=WINDOW_DAYS - 1)
        window_start_dt = datetime.combine(window_start, datetime.min.time())

        completed: list[int] = [0] * WINDOW_DAYS
        mastery: list[float] = [0.0] * WINDOW_DAYS

        # 冲刺完成度：任务账本（用户全域 + 非软删）按完成日落日
        task_rows = await self.db.execute(
            select(Task.completed_at).where(
                sprint_ledger_condition(user_id),
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= window_start_dt,
            )
        )
        for (completed_at,) in task_rows:
            idx = _day_index(window_start, completed_at)
            if idx is not None:
                completed[idx] += 1

        # 掌握度增量：study_records 事件流按日求和（与既有消费面同口径，只读）
        record_rows = await self.db.execute(
            select(StudyRecord.created_at, StudyRecord.mastery_delta).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= window_start_dt,
            )
        )
        for created_at, mastery_delta in record_rows:
            idx = _day_index(window_start, created_at)
            if idx is not None and mastery_delta:
                mastery[idx] += float(mastery_delta)

        series = [
            SelfAnchorDayPoint(
                date=window_start + timedelta(days=i),
                tasks_completed=completed[i],
                mastery_delta=round(mastery[i], 4),
            )
            for i in range(WINDOW_DAYS)
        ]
        has_any_data = any(v > 0 for v in completed) or any(v > 0 for v in mastery)
        return SelfAnchorViewResponse(
            window_start=window_start,
            window_end=window_end,
            series=series,
            total_tasks_completed=sum(completed),
            total_mastery_delta=round(sum(mastery), 4),
            has_any_data=has_any_data,
        )
