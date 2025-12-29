import json
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from loguru import logger

from app.tools.registry import tool_registry
from app.tools.base import ToolResult
from app.services.tool_history_service import ToolHistoryService
from app.db.session import AsyncSessionLocal


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
        db_session: Optional[Any],
        progress_callback: Optional[Any] = None
    ) -> ToolResult:
        """
        执行单个工具调用并记录执行历史

        Args:
            tool_name: 工具名称
            arguments: LLM 提供的参数（JSON）
            user_id: 用户 ID
            db_session: 数据库会话
            progress_callback: 进度回调

        Returns:
            ToolResult: 执行结果
        """
        if db_session is None:
            async with AsyncSessionLocal() as session:
                return await self._execute_tool_call_with_session(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=user_id,
                    db_session=session,
                    progress_callback=progress_callback,
                    owns_session=True
                )

        return await self._execute_tool_call_with_session(
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            db_session=db_session,
            progress_callback=progress_callback,
            owns_session=False
        )

    async def _execute_tool_call_with_session(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        db_session: Any,
        progress_callback: Optional[Any],
        owns_session: bool
    ) -> ToolResult:
        tool = tool_registry.get_tool(tool_name)

        if not tool:
            error_result = ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"未知工具: {tool_name}",
                suggestion="请检查工具名称是否正确"
            )
            # 记录失败
            await self._record_tool_execution(
                db_session, user_id, tool_name, False,
                error_message=f"未知工具: {tool_name}",
                error_type="ToolNotFound",
                use_separate_session=not owns_session
            )
            await self._commit_if_owned(db_session, owns_session)
            return error_result

        # 验证参数
        try:
            validated_params = tool.parameters_schema(**arguments)
        except ValidationError as e:
            validation_error = ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"参数验证失败: {str(e)}",
                suggestion="请检查参数格式是否正确"
            )
            # 记录参数验证失败
            await self._record_tool_execution(
                db_session, user_id, tool_name, False,
                error_message=f"参数验证失败: {str(e)}",
                error_type="ValidationError",
                input_args=arguments,
                use_separate_session=not owns_session
            )
            await self._commit_if_owned(db_session, owns_session)
            return validation_error

        # 记录执行开始时间
        start_time = time.time()

        try:
            # 执行工具
            if getattr(tool, "is_long_running", False) and progress_callback:
                result = await tool.execute(validated_params, user_id, db_session, progress_callback=progress_callback)
            else:
                result = await tool.execute(validated_params, user_id, db_session)

            # 计算执行时间
            execution_time_ms = int((time.time() - start_time) * 1000)

            # 记录执行成功
            await self._record_tool_execution(
                db_session=db_session,
                user_id=user_id,
                tool_name=tool_name,
                success=result.success,
                execution_time_ms=execution_time_ms,
                error_message=result.error_message,
                tool_category=getattr(tool, "category", None),
                input_args=dict(validated_params) if hasattr(validated_params, '__dict__') else arguments,
                output_summary=result.suggestion or str(result.data)[:200] if result.data else None,
                use_separate_session=not owns_session
            )
            await self._commit_if_owned(db_session, owns_session)

            return result

        except Exception as e:
            # 计算执行时间
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(f"Tool execution error: {tool_name} - {str(e)}", exc_info=True)
            await self._safe_rollback(db_session)

            # 记录执行异常
            await self._record_tool_execution(
                db_session=db_session,
                user_id=user_id,
                tool_name=tool_name,
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=str(e),
                error_type=type(e).__name__,
                input_args=arguments,
                use_separate_session=not owns_session
            )
            await self._commit_if_owned(db_session, owns_session)

            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"工具执行异常: {str(e)}",
                suggestion="请稍后重试或联系支持"
            )

    async def _record_tool_execution(
        self,
        db_session: Any,
        user_id: str,
        tool_name: str,
        success: bool,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        tool_category: Optional[str] = None,
        input_args: Optional[Dict[str, Any]] = None,
        output_summary: Optional[str] = None,
        use_separate_session: bool = False
    ) -> None:
        """
        记录工具执行到数据库

        Args:
            db_session: 数据库会话
            user_id: 用户ID
            tool_name: 工具名称
            success: 是否成功
            execution_time_ms: 执行时间（毫秒）
            error_message: 错误信息
            error_type: 错误类型
            tool_category: 工具类别
            input_args: 输入参数
            output_summary: 输出摘要
        """
        # 转换user_id为int（如果需要）
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id

        if use_separate_session:
            async with AsyncSessionLocal() as history_session:
                try:
                    history_service = ToolHistoryService(history_session)
                    await history_service.record_tool_execution(
                        user_id=user_id_int,
                        tool_name=tool_name,
                        success=success,
                        execution_time_ms=execution_time_ms,
                        error_message=error_message,
                        error_type=error_type,
                        tool_category=tool_category,
                        input_args=input_args,
                        output_summary=output_summary
                    )
                    await history_session.commit()
                except Exception as e:
                    await history_session.rollback()
                    logger.warning(f"Failed to record tool execution history: {e}")
            return

        try:
            history_service = ToolHistoryService(db_session)
            await history_service.record_tool_execution(
                user_id=user_id_int,
                tool_name=tool_name,
                success=success,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                error_type=error_type,
                tool_category=tool_category,
                input_args=input_args,
                output_summary=output_summary
            )
            await db_session.flush()
        except Exception as e:
            logger.warning(f"Failed to record tool execution history: {e}")
            await self._safe_rollback(db_session)

    async def _commit_if_owned(self, db_session: Any, owns_session: bool) -> None:
        if not owns_session:
            return
        try:
            await db_session.commit()
        except Exception as e:
            logger.warning(f"Failed to commit tool execution session: {e}")
            await self._safe_rollback(db_session)

    async def _safe_rollback(self, db_session: Any) -> None:
        if not db_session or not hasattr(db_session, "rollback"):
            return
        try:
            await db_session.rollback()
        except Exception as e:
            logger.warning(f"Failed to rollback tool execution session: {e}")
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        user_id: str,
        db_session: Optional[Any]
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
