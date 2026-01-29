"""
Tool Execution Fallback Strategies - 工具执行降级策略

P1 Improvement: Provides multi-level fallback strategies when tool execution fails.
"""
import json
from typing import Any

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

                    response = f"""基于你的学习记录，我发现以下初步模式：

📊 **学习统计**
- 总任务数：{total_tasks}
- 已完成：{completed_tasks}
- 完成率：{completion_rate:.1f}%

💡 **初步建议**
{ "- 你的任务完成率较高，保持良好的学习节奏" if completion_rate > 70 else "- 建议尝试将复杂任务分解为更小的步骤" }

*注：这是基于简单统计的分析。继续学习后，认知棱镜会提供更精准的行为模式分析。*
"""
                    return response

            # 如果没有统计数据，返回通用提示
            return """暂无足够的数据进行行为分析。

认知棱镜需要收集更多学习数据才能准确分析你的行为模式。建议你：
- 继续完成学习任务
- 使用专注模式记录学习过程
- 让系统观察你的学习习惯

随着数据积累，认知棱镜会越来越准确地了解你的学习模式。
"""
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
        return """抱歉，翻译服务暂时不可用。

你可以尝试：
- 使用浏览器扩展（如沉浸式翻译）
- 使用翻译APP（如DeepL、Google翻译）
- 稍后再试

我们正在努力恢复服务。"""

    @staticmethod
    async def _focus_session_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """专注时段建议降级：提供通用建议"""
        return """抱歉，专注时段建议服务暂时不可用。

通用建议：
- 🎯 番茄工作法：25分钟专注 + 5分钟休息
- ⏰ 选择精力最好的时间段学习
- 📱 将手机调至勿扰模式
- 💧 准备水杯，避免中断

稍后可再次请求个性化的专注时段建议。"""

    @staticmethod
    async def _task_creation_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """任务创建降级：提供手动创建指引"""
        return """抱歉，自动创建任务功能暂时不可用。

你可以手动创建任务：
1. 打开任务列表
2. 点击"添加任务"
3. 填写任务详情

或者稍后再试自动创建功能。"""

    @staticmethod
    async def _plan_creation_fallback(
        tool_name: str,
        error_message: str,
        user_id: str,
        db_session: Any,
        redis_client: Any,
    ) -> str | None:
        """计划创建降级：提供手动创建指引"""
        return """抱歉，自动创建计划功能暂时不可用。

你可以手动创建计划：
1. 打开计划页面
2. 点击"创建计划"
3. 设置学习目标和时间安排

或者稍后再试自动创建功能。"""

    @staticmethod
    async def _default_fallback(tool_name: str, error_message: str) -> str:
        """默认降级策略"""
        return f"""抱歉，{tool_name} 功能暂时不可用。

错误详情：{error_message}

建议：
- 稍后再试
- 检查网络连接
- 如问题持续，请联系客服

我们正在努力恢复服务。"""


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
