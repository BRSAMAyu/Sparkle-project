"""
Agent 错误处理器
实现自我修正和人机协作
"""
from typing import Dict, Any, Optional, List
import json
from app.tools.base import ToolResult
from app.tools.registry import tool_registry


class AgentErrorHandler:
    """
    Agent 错误处理器
    实现工具调用失败后的自我修正机制
    """

    MAX_RETRY_COUNT = 2  # 最大重试次数

    async def handle_tool_error(
        self,
        llm_service: Any,
        tool_result: ToolResult,
        original_request: Dict[str, Any],
        retry_count: int = 0,
        user_id: str = None,
        db_session: Any = None
    ) -> ToolResult:
        """
        处理工具执行错误，尝试自我修正

        Args:
            llm_service: LLM 服务实例
            tool_result: 失败的工具执行结果
            original_request: 原始工具调用请求
            retry_count: 当前重试次数
            user_id: 用户 ID
            db_session: 数据库会话

        Returns:
            ToolResult: 修正后的执行结果或原始错误
        """
        # 超过最大重试次数，返回原始错误
        if retry_count >= self.MAX_RETRY_COUNT:
            return tool_result

        # 构建修正提示
        correction_prompt = self._build_correction_prompt(
            tool_result,
            original_request
        )

        try:
            # 让 LLM 分析错误并生成修正后的调用
            retry_response = await llm_service.chat_with_tools(
                system_prompt=self._get_correction_system_prompt(),
                user_message=correction_prompt,
                tools=tool_registry.get_openai_tools_schema()
            )

            # 如果 LLM 提供了修正后的工具调用
            if retry_response.tool_calls:
                from app.orchestration.executor import ToolExecutor
                executor = ToolExecutor()

                # 执行修正后的调用
                corrected_result = await executor.execute_tool_call(
                    tool_name=retry_response.tool_calls[0]["function"]["name"],
                    arguments=json.loads(retry_response.tool_calls[0]["function"]["arguments"]),
                    user_id=user_id,
                    db_session=db_session
                )

                # 如果修正后仍然失败，递归重试
                if not corrected_result.success:
                    return await self.handle_tool_error(
                        llm_service=llm_service,
                        tool_result=corrected_result,
                        original_request=retry_response.tool_calls[0],
                        retry_count=retry_count + 1,
                        user_id=user_id,
                        db_session=db_session
                    )

                return corrected_result

            # LLM 无法提供修正方案，返回原始错误
            return tool_result

        except Exception as e:
            # 修正过程出错，返回原始错误并附加修正失败信息
            tool_result.suggestion = f"{tool_result.suggestion or ''}\n自动修正失败: {str(e)}"
            return tool_result

    def _build_correction_prompt(
        self,
        tool_result: ToolResult,
        original_request: Dict[str, Any]
    ) -> str:
        """
        构建错误修正提示

        Args:
            tool_result: 失败的工具执行结果
            original_request: 原始请求

        Returns:
            str: 修正提示文本
        """
        original_params = {}
        if "function" in original_request:
            try:
                original_params = json.loads(
                    original_request["function"].get("arguments", "{}")
                )
            except (json.JSONDecodeError, KeyError):
                original_params = original_request.get("function", {}).get("arguments", {})

        prompt = f"""工具调用失败，需要你分析错误原因并修正参数后重新调用。

**失败的工具**: {tool_result.tool_name}

**错误信息**: {tool_result.error_message}

**建议**: {tool_result.suggestion or '无'}

**原始参数**:
```json
{json.dumps(original_params, ensure_ascii=False, indent=2)}
```

请分析错误原因，并使用修正后的参数重新调用工具。如果无法修正，请说明原因。
"""
        return prompt

    def _get_correction_system_prompt(self) -> str:
        """
        获取错误修正的 System Prompt

        Returns:
            str: System Prompt
        """
        return """你是一个工具调用修正助手。

**你的任务**:
1. 分析工具调用失败的原因
2. 根据错误信息和建议修正参数
3. 使用修正后的参数重新调用工具

**修正原则**:
- 仔细阅读错误信息和建议
- 检查参数格式是否正确
- 检查必填参数是否缺失
- 检查参数值是否符合规范
- 如果是 ID 类错误，建议先用查询工具确认 ID 是否存在

**注意**:
- 只修正明确可以修正的错误
- 如果错误无法通过修正参数解决（如权限问题、资源不存在等），不要尝试调用工具
- 修正后的参数必须符合工具的 Schema 定义
"""

    async def handle_batch_errors(
        self,
        llm_service: Any,
        tool_results: list[ToolResult],
        original_requests: list[Dict[str, Any]],
        user_id: str = None,
        db_session: Any = None
    ) -> list[ToolResult]:
        """
        批量处理工具执行错误

        Args:
            llm_service: LLM 服务实例
            tool_results: 工具执行结果列表
            original_requests: 原始请求列表
            user_id: 用户 ID
            db_session: 数据库会话

        Returns:
            list[ToolResult]: 处理后的结果列表
        """
        corrected_results = []

        for i, result in enumerate(tool_results):
            if not result.success and i < len(original_requests):
                # 尝试修正失败的工具调用
                corrected = await self.handle_tool_error(
                    llm_service=llm_service,
                    tool_result=result,
                    original_request=original_requests[i],
                    retry_count=0,
                    user_id=user_id,
                    db_session=db_session
                )
                corrected_results.append(corrected)
            else:
                # 成功的调用直接保留
                corrected_results.append(result)

        return corrected_results

    def should_retry(self, tool_result: ToolResult) -> bool:
        """
        判断是否应该重试

        Args:
            tool_result: 工具执行结果

        Returns:
            bool: 是否应该重试
        """
        # 不重试的情况：
        # 1. 权限错误
        # 2. 资源不存在且无法通过修正参数解决
        # 3. 参数类型错误但无法推断正确类型

        if not tool_result.error_message:
            return False

        error_msg = tool_result.error_message.lower()

        # 权限错误不重试
        if any(keyword in error_msg for keyword in ['permission', 'unauthorized', '权限', '未授权']):
            return False

        # 参数验证错误可以重试
        if any(keyword in error_msg for keyword in ['validation', 'invalid', '验证失败', '无效']):
            return True

        # 资源不存在可以重试（可能是 ID 错误）
        if any(keyword in error_msg for keyword in ['not found', 'does not exist', '不存在', '未找到']):
            return True

        # 默认尝试重试
        return True
