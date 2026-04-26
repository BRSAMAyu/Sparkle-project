"""
Tool Execution Fallback Strategies - 工具执行降级策略

P1 Improvement: Provides multi-level fallback strategies when tool execution fails.
"""
from __future__ import annotations
import json
from typing import Any

from app.core.i18n import I18n
from loguru import logger


class ToolExecutionFallback:
    """工具执行降级策略处理器

    当工具调用失败时，提供多级降级策略：
    1. 尝试备用工具
    2. 使用规则生成响应
    3. 让 LLM 基于知识库回答
    4. 返回友好的错误消息
    """

    # 工具降级映射
    FALLBACK_TOOLS = {
        "get_user_behavior_patterns": "behavior_patterns_fallback",
        "translate": "translation_fallback",
        "suggest_focus_session": "focus_session_fallback",
        "create_task": "task_creation_fallback",
        "create_plan": "plan_creation_fallback",
    }

    @staticmethod
    async def handle_tool_failure(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
        stream_callback: Any | None = None,
    ) -> str:
        """处理工具调用失败，返回降级响应

        Args:
            tool_name: 失败的工具名称
            error_message: 错误消息
            user_id: 用户ID
            db_session: 数据库会话
            redis_client: Redis客户端
            stream_callback: 流式回调（可选）

        Returns:
            str: 降级响应文本
        """
        logger.warning(f"Tool '{tool_name}' failed, attempting fallback: {error_message}")

        # 策略 1: 检查备用工具
        fallback_method_name = ToolExecutionFallback.FALLBACK_TOOLS.get(tool_name)
        if fallback_method_name:
            fallback_method = getattr(ToolExecutionFallback, f"_{fallback_method_name}", None)
            if fallback_method:
                try:
                    result = await fallback_method(
                        tool_name=tool_name,
                        error_message=error_message,
                        user_id=user_id,
                        db_session=db_session,
                        redis_client=redis_client,
                    )
                    if result:
                        return result
                except Exception as e:
                    logger.error(f"Fallback method '{fallback_method_name}' failed: {e}")

        # 策略 4: 默认错误响应
        return await ToolExecutionFallback._default_fallback(tool_name, error_message)

    @staticmethod
    async def _behavior_patterns_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """Prism 工具降级：返回基于对话历史的简单分析"""
        try:
            # 从 Redis 缓存中获取用户的基本统计信息
            if redis_client and user_id:
                # 获取用户任务完成统计
                stats_key = f"user_stats:{user_id}"
                stats = await redis_client.get(stats_key)

                if stats:
                    stats_data = json.loads(stats)
                    total_tasks = stats_data.get("total_tasks", 0)
                    completed_tasks = stats_data.get("completed_tasks", 0)
                    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                    advice = I18n.t("tool_fallback.behavior_patterns_advice_high", locale="zh") if completion_rate > 70 else I18n.t("tool_fallback.behavior_patterns_advice_low", locale="zh")
                    response = I18n.t("tool_fallback.behavior_patterns_success", locale="zh", total=total_tasks, completed=completed_tasks, rate=completion_rate, advice=advice)
                    return response

            # 如果没有统计数据，返回通用提示
            return I18n.t("tool_fallback.behavior_patterns_no_data", locale="zh")
        except Exception as e:
            logger.error(f"Behavior patterns fallback failed: {e}")
            return None

    @staticmethod
    async def _translation_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """翻译工具降级：提示用户使用其他方式"""
        return I18n.t("tool_fallback.translation_unavailable", locale="zh")

    @staticmethod
    async def _focus_session_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """专注时段建议降级：提供通用建议"""
        return I18n.t("tool_fallback.focus_session_unavailable", locale="zh")

    @staticmethod
    async def _task_creation_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """任务创建降级：提供手动创建指引"""
        return I18n.t("tool_fallback.task_creation_unavailable", locale="zh")

    @staticmethod
    async def _plan_creation_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """计划创建降级：提供手动创建指引"""
        return I18n.t("tool_fallback.plan_creation_unavailable", locale="zh")

    @staticmethod
    async def _default_fallback(tool_name: str, error_message: str) -> str:
        """默认降级策略"""
        return I18n.t("tool_fallback.default_fallback", locale="zh", tool=tool_name, error=error_message)


class FallbackToolResult:
    """降级工具结果封装

    用于在工具失败时返回结构化的降级响应
    """

    @staticmethod
    def create_fallback_result(
        tool_name: str,
        fallback_message: str,
        original_error: str,
    ) -> dict[str, Any]:
        """创建降级工具结果

        Args:
            tool_name: 原始工具名称
            fallback_message: 降级消息
            original_error: 原始错误

        Returns:
            Dict: 工具结果字典
        """
        return {
            "success": True,  # 降级成功，不是完全失败
            "tool_name": tool_name,
            "fallback": True,
            "data": {
                "message": fallback_message,
                "original_error": original_error,
                "fallback_type": "degraded_response"
            },
            "error_message": None,
            "suggestion": "如需完整功能，请稍后再试"
        }
