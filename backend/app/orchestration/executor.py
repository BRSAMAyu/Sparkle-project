from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from app.tools.registry import tool_registry
from app.tools.base import ToolResult

class ToolExecutor:
    """
    工具执行器
    负责解析 LLM 的工具调用请求并执行
    """
    
    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        db_session: Any,
        progress_callback: Optional[Any] = None
    ) -> ToolResult:
        """
        执行单个工具调用
        
        Args:
            tool_name: 工具名称
            arguments: LLM 提供的参数（JSON）
            user_id: 用户 ID
            db_session: 数据库会话
            
        Returns:
            ToolResult: 执行结果
        """
        tool = tool_registry.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"未知工具: {tool_name}",
                suggestion="请检查工具名称是否正确"
            )
        
        # 验证参数
        try:
            validated_params = tool.parameters_schema(**arguments)
        except ValidationError as e:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"参数验证失败: {str(e)}",
                suggestion="请检查参数格式是否正确"
            )
        
        # 执行工具
        # 如果工具有 is_long_running 属性，可以传递进度回调
        if getattr(tool, "is_long_running", False) and progress_callback:
            result = await tool.execute(validated_params, user_id, db_session, progress_callback=progress_callback)
        else:
            result = await tool.execute(validated_params, user_id, db_session)
        return result
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        user_id: str,
        db_session: Any
    ) -> List[ToolResult]:
        """
        批量执行工具调用（按顺序）
        
        Args:
            tool_calls: 工具调用列表，格式为 OpenAI function_call
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        results = []
        for call in tool_calls:
            result = await self.execute_tool_call(
                tool_name=call["function"]["name"],
                arguments=call["function"]["arguments"] if isinstance(call["function"]["arguments"], dict) else json.loads(call["function"]["arguments"]),
                user_id=user_id,
                db_session=db_session
            )
            results.append(result)
        return results

import json