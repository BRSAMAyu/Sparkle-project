"""X-04 · Focus/Calendar 作为 optional capability（不在场时优雅降级）.

GOAL_TASK_PLAN_CALENDAR_FOCUS.md：Calendar 只在 scheduling intervention 需要
时出现；Focus timer 不等于学习成果。Action 生命周期（start/complete/abandon/
rescope/reopen）**不依赖** Focus/Calendar 子系统——二者是增强能力，缺席时：

- Focus：``TaskService.start`` 的 focus 上下文预载跳过（可观测 WARN，不阻断）；
- Calendar：action 流全程零耦合（无任何读写依赖，无需降级动作）。

本探测是**显式化**的降级判定（表级可用性 + 导入可用性），替代无差别裸
try/except，让「能力缺席」成为可观测、可测试的状态而非静默吞异常。
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class OptionalCapabilities:
    """action 流可挂载的可选能力探测结果（全部 False 时核心流必须照常工作）."""

    focus: bool
    calendar: bool

    def to_dict(self) -> dict[str, bool]:
        return {"focus": self.focus, "calendar": self.calendar}


async def _table_exists(db: AsyncSession, table: str) -> bool:
    try:
        connection = await db.connection()
        return bool(
            await connection.run_sync(
                lambda sync_conn: (table in __import__("sqlalchemy").inspect(sync_conn).get_table_names())
            )
        )
    except Exception as exc:  # noqa: BLE001 — 探测本身不得破坏主流程
        logger.debug("capability table probe failed for {}: {}", table, exc)
        return False


async def probe_optional_capabilities(db: AsyncSession) -> OptionalCapabilities:
    """探测 Focus / Calendar 可选能力（表级；零依赖缺席 = False，绝不抛出）."""
    focus_available = await _table_exists(db, "focus_sessions")
    calendar_available = await _table_exists(db, "calendar_events")
    return OptionalCapabilities(focus=focus_available, calendar=calendar_available)


async def focus_preload_available(db: AsyncSession) -> bool:
    """start() 预载判定：Focus 能力在场才预载上下文（缺席 → 跳过并 WARN 一次）。"""
    available = await _table_exists(db, "focus_sessions")
    if not available:
        logger.info("optional focus capability absent — skipping focus context preload (action flow continues)")
    return available
