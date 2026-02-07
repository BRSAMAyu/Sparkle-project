"""
State Change Notification Service

Sends detailed notifications for major state changes:
- Plan archived/restored/deleted
- User settings updated
- Memory cleanup

Integrates with WebSocket to deliver real-time notifications to clients.
"""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger

from app.core.websocket import get_ws_manager


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class StateNotificationService:
    """
    Service for sending state change notifications via WebSocket.

    Notifications are sent as metadata in delta messages, following the
    pattern established by PlanReviewWidgetEvent.
    """

    def __init__(self):
        self.ws_manager = get_ws_manager()

    async def notify_plan_archived(
        self,
        user_id: str,
        plan_name: str,
        plan_id: UUID,
        task_count_freed: int = 0,
        memory_count_removed: int = 0,
        new_primary_plan: str | None = None,
        intervention_level: str = "toast"
    ):
        """
        Send notification when a plan is archived.

        Args:
            user_id: User UUID
            plan_name: Name of the archived plan
            plan_id: Plan UUID
            task_count_freed: Number of tasks freed up
            memory_count_removed: Number of memory nodes removed
            new_primary_plan: Name of new primary plan (if applicable)
            intervention_level: toast | card | modal
        """
        change_id = str(uuid4())

        event_data = {
            "change_type": "plan_archived",
            "timestamp": _utcnow().isoformat(),
            "change_id": change_id,
            "plan_name": plan_name,
            "plan_id": str(plan_id),
            "task_count_freed": task_count_freed,
            "memory_count_removed": memory_count_removed,
            "new_primary_plan": new_primary_plan,
        }

        # Format user-friendly message
        message_parts = [
            f"✅ 已归档计划：{plan_name}"
        ]

        if task_count_freed > 0:
            message_parts.append(f"✓ 释放了 {task_count_freed} 个任务配额")

        if memory_count_removed > 0:
            message_parts.append(f"✓ 从记忆中移除 {memory_count_removed} 个知识点")

        if new_primary_plan:
            message_parts.append(f"✓ 新主计划：{new_primary_plan}")

        formatted_message = "\n".join(message_parts)

        await self._send_state_change_notification(
            user_id=user_id,
            change_type="plan_archived",
            change_data=event_data,
            formatted_message=formatted_message,
            intervention_level=intervention_level,
            priority="medium" if task_count_freed > 0 or memory_count_removed > 0 else "low"
        )

        logger.info(f"Sent plan_archived notification for plan {plan_id} to user {user_id}")

    async def notify_plan_restored(
        self,
        user_id: str,
        plan_name: str,
        plan_id: UUID,
        intervention_level: str = "toast"
    ):
        """
        Send notification when a plan is restored from archive.

        Args:
            user_id: User UUID
            plan_name: Name of the restored plan
            plan_id: Plan UUID
            intervention_level: toast | card | modal
        """
        change_id = str(uuid4())

        event_data = {
            "change_type": "plan_restored",
            "timestamp": _utcnow().isoformat(),
            "change_id": change_id,
            "plan_name": plan_name,
            "plan_id": str(plan_id),
        }

        formatted_message = f"🔄 已恢复计划：{plan_name}\n✓ 计划重新激活，可以继续学习"

        await self._send_state_change_notification(
            user_id=user_id,
            change_type="plan_restored",
            change_data=event_data,
            formatted_message=formatted_message,
            intervention_level=intervention_level,
            priority="low"
        )

        logger.info(f"Sent plan_restored notification for plan {plan_id} to user {user_id}")

    async def notify_plan_deleted(
        self,
        user_id: str,
        plan_name: str,
        plan_id: UUID,
        task_count_freed: int = 0,
        memory_count_removed: int = 0,
        intervention_level: str = "toast"
    ):
        """
        Send notification when a plan is permanently deleted.

        Args:
            user_id: User UUID
            plan_name: Name of the deleted plan
            plan_id: Plan UUID
            task_count_freed: Number of tasks freed up
            memory_count_removed: Number of memory nodes removed
            intervention_level: toast | card | modal
        """
        change_id = str(uuid4())

        event_data = {
            "change_type": "plan_deleted",
            "timestamp": _utcnow().isoformat(),
            "change_id": change_id,
            "plan_name": plan_name,
            "plan_id": str(plan_id),
            "task_count_freed": task_count_freed,
            "memory_count_removed": memory_count_removed,
        }

        message_parts = [
            f"🗑️ 已删除计划：{plan_name}"
        ]

        if task_count_freed > 0:
            message_parts.append(f"✓ 释放了 {task_count_freed} 个任务配额")

        if memory_count_removed > 0:
            message_parts.append(f"✓ 从记忆中移除 {memory_count_removed} 个知识点")

        formatted_message = "\n".join(message_parts)

        await self._send_state_change_notification(
            user_id=user_id,
            change_type="plan_deleted",
            change_data=event_data,
            formatted_message=formatted_message,
            intervention_level=intervention_level,
            priority="medium"
        )

        logger.info(f"Sent plan_deleted notification for plan {plan_id} to user {user_id}")

    async def notify_user_settings_updated(
        self,
        user_id: str,
        setting_field: str,
        old_value: Any,
        new_value: Any,
        impact_description: str | None = None,
        intervention_level: str = "toast"
    ):
        """
        Send notification when user settings are updated.

        Args:
            user_id: User UUID
            setting_field: Name of the setting field
            old_value: Previous value
            new_value: New value
            impact_description: Description of the impact (optional)
            intervention_level: toast | card | modal
        """
        change_id = str(uuid4())

        # Map field names to user-friendly labels
        field_labels = {
            "transparency_level": "透明度级别",
            "learning_pace": "学习节奏",
            "notification_frequency": "通知频率",
            "difficulty_preference": "难度偏好",
        }

        field_label = field_labels.get(setting_field, setting_field)

        event_data = {
            "change_type": "user_settings_updated",
            "timestamp": _utcnow().isoformat(),
            "change_id": change_id,
            "setting_field": setting_field,
            "field_label": field_label,
            "old_value": old_value,
            "new_value": new_value,
            "impact_description": impact_description,
        }

        message_parts = [
            f"⚙️ 设置已更新：{field_label}",
            f"旧值：{self._format_value(old_value)}",
            f"新值：{self._format_value(new_value)}",
        ]

        if impact_description:
            message_parts.append(f"\nℹ️ {impact_description}")

        formatted_message = "\n".join(message_parts)

        await self._send_state_change_notification(
            user_id=user_id,
            change_type="user_settings_updated",
            change_data=event_data,
            formatted_message=formatted_message,
            intervention_level=intervention_level,
            priority="low"
        )

        logger.info(f"Sent user_settings_updated notification for {setting_field} to user {user_id}")

    async def notify_memory_cleanup(
        self,
        user_id: str,
        memories_removed: int,
        space_freed_mb: float,
        intervention_level: str = "toast"
    ):
        """
        Send notification when memory cleanup is performed.

        Args:
            user_id: User UUID
            memories_removed: Number of memory nodes removed
            space_freed_mb: Amount of space freed in MB
            intervention_level: toast | card | modal
        """
        change_id = str(uuid4())

        event_data = {
            "change_type": "memory_cleanup",
            "timestamp": _utcnow().isoformat(),
            "change_id": change_id,
            "memories_removed": memories_removed,
            "space_freed_mb": space_freed_mb,
        }

        formatted_message = (
            f"🧹 记忆清理完成\n"
            f"✓ 移除了 {memories_removed} 个知识点\n"
            f"✓ 释放了 {space_freed_mb:.1f} MB 空间"
        )

        await self._send_state_change_notification(
            user_id=user_id,
            change_type="memory_cleanup",
            change_data=event_data,
            formatted_message=formatted_message,
            intervention_level=intervention_level,
            priority="low"
        )

        logger.info(f"Sent memory_cleanup notification to user {user_id}")

    async def _send_state_change_notification(
        self,
        user_id: str,
        change_type: str,
        change_data: dict[str, Any],
        formatted_message: str,
        intervention_level: str,
        priority: str
    ):
        """
        Internal method to send state change notification via WebSocket.

        The notification is sent as a delta message with metadata containing
        the state_change_event field.

        Args:
            user_id: User UUID
            change_type: Type of state change
            change_data: Complete event data
            formatted_message: User-friendly formatted message
            intervention_level: toast | card | modal
            priority: low | medium | high
        """
        message = {
            "type": "delta",
            "response_id": change_data.get("change_id"),
            "delta": "",  # Empty delta, content is in metadata
            "metadata": {
                "state_change_event": {
                    "change_type": change_type,
                    "timestamp": change_data["timestamp"],
                    "change_id": change_data["change_id"],
                    **change_data
                },
                "intervention_level": intervention_level,
                "priority": priority,
                "formatted_message": formatted_message,
            },
            "trace_id": change_data.get("change_id"),
        }

        await self.ws_manager.send_personal_message(message, user_id)

    def _format_value(self, value: Any) -> str:
        """
        Format a value for user display.

        Args:
            value: The value to format

        Returns:
            Formatted string representation
        """
        if value is None:
            return "未设置"

        if isinstance(value, bool):
            return "开启" if value else "关闭"

        if isinstance(value, (int, float)):
            return str(value)

        return str(value)


# Singleton instance
state_notification_service = StateNotificationService()
