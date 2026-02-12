"""
ToolResultExtractor - 从 LangGraph State 中提取工具结果

解决工具结果检索问题：从 final_state.messages 中提取 role='tool' 的消息
"""
import json
from typing import Any

from loguru import logger

from app.tools.base import ToolResult


class ToolResultExtractor:
    """从 LangGraph State 消息中提取工具结果"""

    def extract_from_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[ToolResult]:
        """
        从 LangGraph messages 列表中提取工具执行结果

        Args:
            messages: LangGraph state.messages 列表
                     每个消息格式: {"role": "tool", "content": "...", "tool_call_id": "...", ...}

        Returns:
            List[ToolResult]: 提取的工具结果列表
        """
        results = []

        for msg in messages:
            # 跳过非工具消息
            if msg.get("role") != "tool":
                continue

            try:
                result = self._parse_tool_message(msg)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse tool message: {e}")

        logger.info(f"Extracted {len(results)} tool results from {len(messages)} messages")
        return results

    def _parse_tool_message(self, msg: dict[str, Any]) -> ToolResult | None:
        """
        解析单个工具消息为 ToolResult

        Args:
            msg: 单个 LangGraph 消息

        Returns:
            ToolResult 或 None
        """
        content = msg.get("content", "")
        tool_name = msg.get("name", "") or msg.get("tool_name", "")
        tool_call_id = msg.get("tool_call_id", "") or msg.get("id", "")

        if not tool_name:
            return None

        # 尝试解析 content 为 JSON
        content_data = self._parse_content(content)

        # 判断成功/失败
        success, error_message, error_type = self._determine_success(content_data)

        # 构建 ToolResult
        return ToolResult(
            success=success,
            tool_name=tool_name,
            tool_call_id=tool_call_id if tool_call_id else None,
            data=content_data if success else None,
            error_message=error_message,
            error_type=error_type,
        )

    def _parse_content(self, content: Any) -> dict[str, Any]:
        """解析消息内容"""
        if isinstance(content, dict):
            return content

        if isinstance(content, str):
            # 尝试解析 JSON
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
                return {"result": parsed}
            except (json.JSONDecodeError, TypeError):
                # 非 JSON 字符串
                return {"raw": content}

        return {"raw": str(content)}

    def _determine_success(
        self, content_data: dict[str, Any]
    ) -> tuple[bool, str | None, str | None]:
        """
        判断工具执行是否成功

        Returns:
            (success, error_message, error_type)
        """
        # 检查显式的 success 字段
        if "success" in content_data:
            if content_data["success"] is False:
                return (
                    False,
                    content_data.get("error_message") or content_data.get("error") or content_data.get("message"),
                    content_data.get("error_type"),
                )
            return (True, None, None)

        # 检查 error 字段
        if "error" in content_data:
            error = content_data["error"]
            if error:
                return (
                    False,
                    str(error),
                    content_data.get("error_type") or "unknown_error",
                )

        # 检查 error_message 字段
        if "error_message" in content_data and content_data["error_message"]:
            return (
                False,
                content_data["error_message"],
                content_data.get("error_type") or "error",
            )

        # 检查特定的错误模式
        raw = content_data.get("raw", "")
        if isinstance(raw, str):
            error_keywords = ["error:", "exception:", "failed:", "traceback"]
            if any(kw in raw.lower() for kw in error_keywords):
                return (False, raw[:500], "execution_error")

        # 默认视为成功
        return (True, None, None)

    def extract_tool_call_summary(
        self, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        提取工具调用摘要

        Args:
            messages: LangGraph state.messages 列表

        Returns:
            摘要信息包含:
            - total_calls: 总调用次数
            - successful_calls: 成功次数
            - failed_calls: 失败次数
            - tools_used: 使用的工具列表
            - success_rate: 成功率
        """
        results = self.extract_from_messages(messages)

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        tools_used = list({r.tool_name for r in results})

        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": failed,
            "tools_used": tools_used,
            "success_rate": successful / total if total > 0 else 1.0,
        }
