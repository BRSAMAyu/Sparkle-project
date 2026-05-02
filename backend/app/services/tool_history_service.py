"""
Tool History Service - 工具执行历史记录和学习服务

提供以下功能:
1. 记录工具执行结果
2. 计算工具成功率
3. 支持路由器的偏好学习
4. 性能监控
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import Integer, and_, desc, event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.core.event_types import TOOL_HISTORY_RECORDED, TOOL_USAGE_EVENT
from app.models.tool_history import ToolSuccessRateView, UserToolHistory, UserToolPreference


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_AFTER_COMMIT_TASKS_KEY = "tool_history_after_commit_tasks"

CONTEXT_AWARE_TOOL_NAMES = frozenset(
    {
        "breathing",
        "calculator",
        "translator",
        "vocabulary_lookup",
        "notes",
        "flash_capsule",
    }
)

TOOL_DISPLAY_NAMES = {
    "breathing": "呼吸练习",
    "calculator": "计算器",
    "translator": "翻译器",
    "vocabulary_lookup": "词汇查询",
    "notes": "快速笔记",
    "flash_capsule": "闪念胶囊",
}


@event.listens_for(AsyncSession.sync_session_class, "after_commit")
def _run_tool_history_after_commit_tasks(session) -> None:
    callbacks: list[Callable[[], Awaitable[None]]] = session.info.pop(_AFTER_COMMIT_TASKS_KEY, [])
    if not callbacks:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("Skipping tool history after-commit callbacks because no event loop is running")
        return

    for callback in callbacks:
        loop.create_task(callback())


@event.listens_for(AsyncSession.sync_session_class, "after_rollback")
@event.listens_for(AsyncSession.sync_session_class, "after_soft_rollback")
def _clear_tool_history_after_commit_tasks(session, *_args) -> None:
    session.info.pop(_AFTER_COMMIT_TASKS_KEY, None)


class ToolHistoryService:
    """工具历史记录服务"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    def _enqueue_after_commit(self, callback: Callable[[], Awaitable[None]]) -> None:
        callbacks = self.db_session.sync_session.info.setdefault(_AFTER_COMMIT_TASKS_KEY, [])
        callbacks.append(callback)

    async def record_tool_execution(
        self,
        user_id: uuid.UUID,
        tool_name: str,
        success: bool,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        tool_category: str | None = None,
        context_snapshot: dict[str, Any] | None = None,
        input_args: dict[str, Any] | None = None,
        output_summary: str | None = None,
    ) -> UserToolHistory:
        """
        记录工具执行结果

        Args:
            user_id: 用户ID
            tool_name: 工具名称
            success: 是否成功
            execution_time_ms: 执行时间（毫秒）
            error_message: 错误信息
            error_type: 错误类型
            tool_category: 工具类别
            context_snapshot: 执行时的上下文快照
            input_args: 输入参数
            output_summary: 输出摘要

        Returns:
            UserToolHistory: 创建的历史记录对象
        """
        try:
            record = UserToolHistory(
                user_id=user_id,
                tool_name=tool_name,
                success=success,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                error_type=error_type,
                tool_category=tool_category,
                context_snapshot=context_snapshot,
                input_args=input_args,
                output_summary=output_summary,
            )

            self.db_session.add(record)
            await self.db_session.flush()
            self._enqueue_after_commit(
                lambda: self._publish_tool_history_event(
                    history_id=record.id,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=success,
                    tool_category=tool_category,
                )
            )

            logger.info(
                f"Recorded tool execution: user={user_id}, tool={tool_name}, "
                f"success={success}, time={execution_time_ms}ms"
            )

            return record

        except Exception as e:
            logger.error(f"Failed to record tool execution: {e}")
            raise

    async def _publish_tool_history_event(
        self,
        *,
        history_id: int,
        user_id: uuid.UUID,
        tool_name: str,
        success: bool,
        tool_category: str | None,
    ) -> None:
        payload = {
            "user_id": str(user_id),
            "tool_history_id": history_id,
            "tool_name": tool_name,
            "success": success,
            "tool_category": tool_category,
        }
        await event_bus.publish(
            TOOL_HISTORY_RECORDED,
            {
                **payload,
                "event_type": TOOL_HISTORY_RECORDED,
                "tool_usage_event": True,
            },
        )
        if tool_name in CONTEXT_AWARE_TOOL_NAMES:
            await event_bus.publish(
                TOOL_USAGE_EVENT,
                {
                    **payload,
                    "event_type": TOOL_USAGE_EVENT,
                },
            )

    async def get_recent_context_effects(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 4,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return prompt-safe summaries of recent client-side tool usage."""
        since = _utcnow() - timedelta(hours=hours)
        query = (
            select(UserToolHistory)
            .where(
                and_(
                    UserToolHistory.user_id == user_id,
                    UserToolHistory.success.is_(True),
                    UserToolHistory.tool_name.in_(CONTEXT_AWARE_TOOL_NAMES),
                    UserToolHistory.created_at >= since,
                )
            )
            .order_by(desc(UserToolHistory.created_at))
            .limit(limit)
        )
        result = await self.db_session.execute(query)
        records = list(result.scalars().all())
        return [self._context_effect_payload(record) for record in records]

    async def delete_client_context_effect(self, *, user_id: uuid.UUID, record_id: int) -> bool:
        """Delete a user-owned client tool event when the user opts out after save."""
        record = await self.db_session.get(UserToolHistory, record_id)
        if record is None or record.user_id != user_id:
            return False
        await self.db_session.delete(record)
        await self.db_session.flush()
        return True

    @classmethod
    def _context_effect_payload(cls, record: UserToolHistory) -> dict[str, Any]:
        context = record.context_snapshot or {}
        return {
            "tool_history_id": record.id,
            "tool_name": record.tool_name,
            "label": TOOL_DISPLAY_NAMES.get(record.tool_name, record.tool_name),
            "used_at": record.created_at.isoformat() if record.created_at else None,
            "summary": cls._safe_context_summary(record.tool_name, context, record.output_summary),
            "privacy_note": cls._privacy_note(record.tool_name),
        }

    @classmethod
    def _safe_context_summary(
        cls,
        tool_name: str,
        context: dict[str, Any],
        output_summary: str | None,
    ) -> str:
        if tool_name == "breathing":
            duration = context.get("duration_minutes") or 0
            pattern = str(context.get("pattern") or "呼吸练习").strip()
            return f"完成 {duration} 分钟{pattern}"
        if tool_name == "calculator":
            complexity = str(context.get("complexity") or "simple").strip()
            return f"完成一次{complexity}复杂度计算"
        if tool_name == "translator":
            source = str(context.get("source_language") or "auto").strip()
            target = str(context.get("target_language") or "").strip()
            text_length = context.get("text_length")
            pair = f"{source}->{target}" if target else source
            length_text = (
                f"，原文约 {int(text_length)} 字符" if isinstance(text_length, int) and text_length > 0 else ""
            )
            return f"完成 {pair} 翻译{length_text}"
        if tool_name == "vocabulary_lookup":
            term = str(context.get("lookup_term") or "").strip()
            return f"查询词汇 {term}" if term else "完成一次词汇查询"
        if tool_name == "notes":
            char_count = context.get("char_count")
            line_count = context.get("line_count")
            details = []
            if isinstance(char_count, int) and char_count > 0:
                details.append(f"{char_count} 字")
            if isinstance(line_count, int) and line_count > 0:
                details.append(f"{line_count} 行")
            suffix = f"（{', '.join(details)}）" if details else ""
            return f"同步快速笔记到认知棱镜{suffix}"
        if tool_name == "flash_capsule":
            subject = str(context.get("subject") or "").strip()
            error_type = str(context.get("error_type") or "").strip()
            details = "，".join(item for item in (subject, error_type) if item)
            return f"保存闪念胶囊{f'（{details}）' if details else ''}"
        return str(output_summary or "完成一次工具使用").strip()

    @staticmethod
    def _privacy_note(tool_name: str) -> str:
        if tool_name in {"calculator", "translator", "notes", "flash_capsule"}:
            return "只保存安全摘要，不保存原始内容。"
        return "只用于衔接下一轮对话。"

    async def get_tool_success_rate(self, user_id: uuid.UUID, tool_name: str, days: int = 30) -> float:
        """
        获取特定工具的成功率（过去N天）

        Args:
            user_id: 用户ID
            tool_name: 工具名称
            days: 时间范围（天）

        Returns:
            成功率 (0-100)
        """
        since = _utcnow() - timedelta(days=days)

        query = select(
            func.count(UserToolHistory.id).label("total"),
            func.sum(func.cast(UserToolHistory.success, Integer)).label("success_count"),
        ).where(
            and_(
                UserToolHistory.user_id == user_id,
                UserToolHistory.tool_name == tool_name,
                UserToolHistory.created_at >= since,
            )
        )

        result = await self.db_session.execute(query)
        row = result.first()

        if not row or row[0] == 0:
            return 0.0

        total = row[0]
        success_count = row[1] or 0

        return (success_count / total) * 100

    async def get_user_preferred_tools(
        self, user_id: uuid.UUID, limit: int = 10, days: int = 30
    ) -> list[UserToolPreference]:
        """
        获取用户偏好的工具列表（按成功率和使用频率排序）

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            days: 时间范围（天）

        Returns:
            UserToolPreference列表
        """
        since = _utcnow() - timedelta(days=days)

        query = (
            select(
                UserToolHistory.tool_name,
                func.count(UserToolHistory.id).label("usage_count"),
                func.sum(func.cast(UserToolHistory.success, Integer)).label("success_count"),
                func.avg(UserToolHistory.execution_time_ms).label("avg_time_ms"),
                func.max(UserToolHistory.created_at).label("last_used_at"),
            )
            .where(and_(UserToolHistory.user_id == user_id, UserToolHistory.created_at >= since))
            .group_by(UserToolHistory.tool_name)
            .order_by(desc("success_count"), desc("usage_count"))
            .limit(limit)
        )

        results = await self.db_session.execute(query)
        rows = results.fetchall()

        preferences = []
        for row in rows:
            tool_name = row.tool_name
            usage_count = row.usage_count
            success_count = row.success_count or 0

            success_rate = (success_count / usage_count * 100) if usage_count > 0 else 0.0

            # 偏好分数: 成功率(70%) + 使用频率归一化(30%)
            frequency_score = min(usage_count / 10, 1.0)  # 归一化到0-1
            preference_score = (success_rate / 100 * 0.7) + (frequency_score * 0.3)

            pref = UserToolPreference(
                user_id=user_id,
                tool_name=tool_name,
                preference_score=preference_score,
                last_30d_success_rate=success_rate,
                last_30d_usage=usage_count,
            )
            preferences.append(pref)

        return preferences

    async def get_tool_statistics(self, user_id: uuid.UUID, tool_name: str, days: int = 30) -> ToolSuccessRateView:
        """
        获取工具统计信息

        Args:
            user_id: 用户ID
            tool_name: 工具名称
            days: 时间范围（天）

        Returns:
            ToolSuccessRateView: 统计视图
        """
        since = _utcnow() - timedelta(days=days)

        query = (
            select(
                UserToolHistory.tool_name,
                func.count(UserToolHistory.id).label("usage_count"),
                func.sum(func.cast(UserToolHistory.success, Integer)).label("success_count"),
                func.avg(UserToolHistory.execution_time_ms).label("avg_time_ms"),
                func.max(UserToolHistory.created_at).label("last_used_at"),
            )
            .where(
                and_(
                    UserToolHistory.user_id == user_id,
                    UserToolHistory.tool_name == tool_name,
                    UserToolHistory.created_at >= since,
                )
            )
            .group_by(UserToolHistory.tool_name)
        )

        result = await self.db_session.execute(query)
        row = result.first()

        if not row:
            return ToolSuccessRateView(
                tool_name=tool_name, success_rate=0.0, usage_count=0, avg_time_ms=0.0, last_used_at=None
            )

        usage_count = row.usage_count
        success_count = row.success_count or 0
        success_rate = (success_count / usage_count * 100) if usage_count > 0 else 0.0

        return ToolSuccessRateView(
            tool_name=tool_name,
            success_rate=success_rate,
            usage_count=usage_count,
            avg_time_ms=row.avg_time_ms or 0.0,
            last_used_at=row.last_used_at,
        )

    async def get_recent_failed_tools(self, user_id: uuid.UUID, limit: int = 5) -> list[dict[str, Any]]:
        """
        获取用户最近失败的工具

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            最近失败的工具列表
        """
        query = (
            select(UserToolHistory)
            .where(and_(UserToolHistory.user_id == user_id, UserToolHistory.success.is_(False)))
            .order_by(desc(UserToolHistory.created_at))
            .limit(limit)
        )

        results = await self.db_session.execute(query)
        records = results.scalars().all()

        return [record.to_dict() for record in records]

    async def update_user_satisfaction(
        self, record_id: int, satisfaction_rating: int, was_helpful: bool
    ) -> UserToolHistory | None:
        """
        更新用户对工具执行结果的反馈

        Args:
            record_id: 历史记录ID
            satisfaction_rating: 满意度评分 (1-5)
            was_helpful: 是否有帮助

        Returns:
            更新后的历史记录对象
        """
        query = select(UserToolHistory).where(UserToolHistory.id == record_id)
        result = await self.db_session.execute(query)
        record = result.scalars().first()

        if record:
            record.user_satisfaction = satisfaction_rating
            record.was_helpful = was_helpful
            await self.db_session.flush()
            logger.info(f"Updated satisfaction for tool history {record_id}")

        return record

    async def cleanup_old_records(self, days: int = 90) -> int:
        """
        清理N天前的旧记录（可选的日常维护任务）

        Args:
            days: 保留天数

        Returns:
            删除的记录数
        """
        cutoff_date = _utcnow() - timedelta(days=days)

        query = select(UserToolHistory).where(UserToolHistory.created_at < cutoff_date)

        results = await self.db_session.execute(query)
        records = results.scalars().all()

        count = len(records)
        for record in records:
            await self.db_session.delete(record)

        logger.info(f"Cleaned up {count} old tool history records")
        return count
