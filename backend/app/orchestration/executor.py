from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import ValidationError

from app.config import settings
from app.core.business_metrics import COMPENSATION_TRIGGERED
from app.core.event_bus import event_bus
from app.core.event_types import (
    TOOL_EXECUTION_COMPLETED,
    TOOL_EXECUTION_FAILED,
    TOOL_EXECUTION_STARTED,
    TOOL_EXECUTION_TIMED_OUT,
)
from app.core.llm_secure_io import refresh_llm_safety_mode, sanitize_exception_message
from app.core.metrics import TOOL_EXECUTION_COUNT
from app.db.session import AsyncSessionLocal
from app.services.tool_history_service import ToolHistoryService
from app.tools.base import TOOL_RUNTIME_CONTEXT_KEY, ToolResult
from app.tools.registry import tool_registry

if TYPE_CHECKING:
    from app.orchestration.schemas import ExecutablePlan, ToolCallSpec


@dataclass
class StepResult:
    """Result of executing a single DAG step."""

    step_id: str
    tool_name: str
    tool_result: ToolResult
    duration_ms: int = 0
    output_key: str | None = None
    output_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanExecutionResult:
    """Aggregate result of executing an entire plan via DAG layers."""

    plan_id: str
    step_results: list[StepResult] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    execution_layers_completed: int = 0
    total_layers: int = 0
    aborted: bool = False
    abort_reason: str | None = None


class ToolExecutor:
    """
    工具执行器
    负责解析 LLM 的工具调用请求并执行
    """

    @staticmethod
    async def _notify_execution_observer(execution_observer: Any | None, payload: dict[str, Any]) -> None:
        if not execution_observer:
            return
        result = execution_observer(payload)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _tool_timeout_seconds(tool: Any) -> float:
        timeout = getattr(tool, "timeout_seconds", None)
        if timeout is None:
            timeout = getattr(settings, "TOOL_EXECUTION_TIMEOUT_SECONDS", 120.0)
        try:
            timeout_value = float(timeout)
        except (TypeError, ValueError):
            timeout_value = 120.0
        return timeout_value if timeout_value > 0 else 120.0

    @staticmethod
    async def _publish_tool_event(event_type: str, payload: dict[str, Any]) -> None:
        try:
            await event_bus.publish(
                event_type,
                {
                    "event_type": event_type,
                    **payload,
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to publish tool execution event {event_type}: {exc}")

    @staticmethod
    def _dump_params(validated_params: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        if hasattr(validated_params, "model_dump"):
            try:
                dumped = validated_params.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        if hasattr(validated_params, "__dict__"):
            try:
                dumped = dict(validated_params)
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        return fallback

    @staticmethod
    def _quote_bareword_values(raw: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            prefix, token, suffix = match.groups()
            if token in {"true", "false", "null"}:
                return f"{prefix}{token}{suffix}"
            return f'{prefix}"{token}"{suffix}'

        return re.sub(r"(:\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*[,}])", _replace, raw)

    @classmethod
    def _coerce_arguments(cls, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if raw is None:
            return {}
        if not isinstance(raw, str):
            return {}

        text = raw.strip()
        if not text:
            return {}

        candidates = [
            text,
            text.replace("'", '"'),
            cls._quote_bareword_values(text),
            cls._quote_bareword_values(text.replace("'", '"')),
        ]
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        logger.warning(f"Failed to parse tool call arguments as JSON: {text}")
        return {"_raw": text}

    @staticmethod
    def _session_info_mapping(db_session: Any) -> dict[str, Any] | None:
        sync_session = getattr(db_session, "sync_session", None)
        info = getattr(sync_session, "info", None)
        if isinstance(info, dict):
            return info
        info = getattr(db_session, "info", None)
        if isinstance(info, dict):
            return info
        return None

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None = None,
        tool_call_id: str | None = None,
        compensation_call: dict[str, Any] | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        执行单个工具调用并记录执行历史

        Args:
            tool_name: 工具名称
            arguments: LLM 提供的参数（JSON）
            user_id: 用户 ID
            db_session: 数据库会话
            progress_callback: 进度回调
            tool_call_id: 工具调用 ID

        Returns:
            ToolResult: 执行结果
        """
        await refresh_llm_safety_mode()
        if db_session is None:
            async with AsyncSessionLocal() as session:
                return await self._execute_tool_call_with_session(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=user_id,
                    db_session=session,
                    progress_callback=progress_callback,
                    tool_call_id=tool_call_id,
                    owns_session=True,
                    compensation_call=compensation_call,
                    runtime_context=runtime_context,
                )

        return await self._execute_tool_call_with_session(
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            db_session=db_session,
            progress_callback=progress_callback,
            tool_call_id=tool_call_id,
            owns_session=False,
            compensation_call=compensation_call,
            runtime_context=runtime_context,
        )

    async def _execute_tool_call_with_session(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        db_session: Any,
        progress_callback: Any | None,
        tool_call_id: str | None,
        owns_session: bool,
        compensation_call: dict[str, Any] | None,
        runtime_context: dict[str, Any] | None,
    ) -> ToolResult:
        tool = tool_registry.get_tool(tool_name)
        session_info = self._session_info_mapping(db_session)
        previous_runtime_context = session_info.get(TOOL_RUNTIME_CONTEXT_KEY) if session_info is not None else None
        if session_info is not None and runtime_context:
            session_info[TOOL_RUNTIME_CONTEXT_KEY] = dict(runtime_context)

        try:
            if not tool:
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="not_found").inc()
                error_result = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=f"未知工具: {tool_name}",
                    suggestion="请检查工具名称是否正确",
                )
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "error_message": error_result.error_message,
                        "error_type": "ToolNotFound",
                        "timestamp": self._utcnow_iso(),
                    },
                )
                await self._record_tool_execution(
                    db_session,
                    user_id,
                    tool_name,
                    False,
                    error_message=f"未知工具: {tool_name}",
                    error_type="ToolNotFound",
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                return error_result

            try:
                validated_params = tool.parameters_schema(**arguments)
            except ValidationError as e:
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="validation_error").inc()
                validation_error = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=sanitize_exception_message(
                        f"参数验证失败: {str(e)}",
                        fallback="参数验证失败，请检查输入格式。",
                    ),
                    suggestion="请检查参数格式是否正确",
                )
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "error_message": validation_error.error_message,
                        "error_type": "ValidationError",
                        "timestamp": self._utcnow_iso(),
                    },
                )
                await self._record_tool_execution(
                    db_session,
                    user_id,
                    tool_name,
                    False,
                    error_message=f"参数验证失败: {str(e)}",
                    error_type="ValidationError",
                    input_args=arguments,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                return validation_error

            start_time = time.time()
            executed_tool = False
            compensation_spec = self._parse_compensation_call(compensation_call)
            timeout_seconds = self._tool_timeout_seconds(tool)

            await self._publish_tool_event(
                TOOL_EXECUTION_STARTED,
                {
                    "user_id": str(user_id),
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "timeout_seconds": timeout_seconds,
                    "timestamp": self._utcnow_iso(),
                },
            )

            try:
                executed_tool = True
                if getattr(tool, "is_long_running", False) and progress_callback:
                    execution_coro = tool.execute(
                        validated_params,
                        user_id,
                        db_session,
                        tool_call_id=tool_call_id,
                        progress_callback=progress_callback,
                    )
                else:
                    execution_coro = tool.execute(
                        validated_params,
                        user_id,
                        db_session,
                        tool_call_id=tool_call_id,
                    )
                result = await asyncio.wait_for(execution_coro, timeout=timeout_seconds)
                if result.tool_call_id is None:
                    result.tool_call_id = tool_call_id
                if not result.success:
                    result.error_message = sanitize_exception_message(result.error_message)
                    if result.suggestion:
                        result.suggestion = sanitize_exception_message(
                            result.suggestion,
                            fallback="请稍后重试。",
                        )

                execution_time_ms = int((time.time() - start_time) * 1000)
                TOOL_EXECUTION_COUNT.labels(
                    tool_name=tool_name,
                    status="success" if result.success else "failed",
                ).inc()

                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=result.success,
                    execution_time_ms=execution_time_ms,
                    error_message=result.error_message,
                    tool_category=getattr(tool, "category", None),
                    input_args=self._dump_params(validated_params, arguments),
                    output_summary=result.suggestion or str(result.data)[:200] if result.data else None,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)

                if not result.success:
                    await self._publish_tool_event(
                        TOOL_EXECUTION_FAILED,
                        {
                            "user_id": str(user_id),
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "duration_ms": execution_time_ms,
                            "error_message": result.error_message,
                            "error_type": result.error_type,
                            "timestamp": self._utcnow_iso(),
                        },
                    )
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_failed",
                    )
                else:
                    await self._publish_tool_event(
                        TOOL_EXECUTION_COMPLETED,
                        {
                            "user_id": str(user_id),
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "duration_ms": execution_time_ms,
                            "success": True,
                            "timestamp": self._utcnow_iso(),
                        },
                    )

                return result
            except TimeoutError:
                execution_time_ms = int((time.time() - start_time) * 1000)
                timeout_message = f"工具执行超时（>{timeout_seconds:.0f}s）"
                logger.error(f"Tool execution timeout: {tool_name} after {timeout_seconds}s")
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="timeout").inc()
                await self._safe_rollback(db_session)
                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=False,
                    execution_time_ms=execution_time_ms,
                    error_message=timeout_message,
                    error_type="TimeoutError",
                    input_args=self._dump_params(validated_params, arguments),
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                await self._publish_tool_event(
                    TOOL_EXECUTION_TIMED_OUT,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "duration_ms": execution_time_ms,
                        "timeout_seconds": timeout_seconds,
                        "error_message": timeout_message,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                if executed_tool:
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_timeout",
                    )
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=timeout_message,
                    error_type="TimeoutError",
                    suggestion="请稍后重试，或缩小本次工具执行范围",
                )
            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                safe_error = sanitize_exception_message(str(e))
                logger.error(f"Tool execution error: {tool_name} - {str(e)}", exc_info=True)
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="error").inc()
                await self._safe_rollback(db_session)
                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=False,
                    execution_time_ms=execution_time_ms,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    input_args=arguments,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "duration_ms": execution_time_ms,
                        "error_message": safe_error,
                        "error_type": type(e).__name__,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                if executed_tool:
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_exception",
                    )
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=safe_error,
                    error_type=type(e).__name__,
                    suggestion="请稍后重试或联系支持",
                )
        finally:
            if session_info is not None:
                if previous_runtime_context is None:
                    session_info.pop(TOOL_RUNTIME_CONTEXT_KEY, None)
                else:
                    session_info[TOOL_RUNTIME_CONTEXT_KEY] = previous_runtime_context

    async def _record_tool_execution(
        self,
        db_session: Any,
        user_id: str,
        tool_name: str,
        success: bool,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        tool_category: str | None = None,
        input_args: dict[str, Any] | None = None,
        output_summary: str | None = None,
        use_separate_session: bool = False,
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
        # 转换user_id为UUID（如果需要）
        try:
            user_id_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        except ValueError:
            logger.warning(f"Invalid user_id for history recording: {user_id}")
            return

        if use_separate_session:
            async with AsyncSessionLocal() as history_session:
                try:
                    history_service = ToolHistoryService(history_session)
                    await history_service.record_tool_execution(
                        user_id=user_id_uuid,
                        tool_name=tool_name,
                        success=success,
                        execution_time_ms=execution_time_ms,
                        error_message=error_message,
                        error_type=error_type,
                        tool_category=tool_category,
                        input_args=input_args,
                        output_summary=output_summary,
                    )
                    await history_session.commit()
                except Exception as e:
                    await history_session.rollback()
                    logger.warning(f"Failed to record tool execution history: {e}")
            return

        try:
            history_service = ToolHistoryService(db_session)
            await history_service.record_tool_execution(
                user_id=user_id_uuid,
                tool_name=tool_name,
                success=success,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                error_type=error_type,
                tool_category=tool_category,
                input_args=input_args,
                output_summary=output_summary,
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

    def _parse_compensation_call(self, compensation_call: dict[str, Any] | None) -> tuple[str, dict[str, Any]] | None:
        if not compensation_call or not isinstance(compensation_call, dict):
            return None
        tool_name = compensation_call.get("name") or compensation_call.get("tool_name") or compensation_call.get("tool")
        args = (
            compensation_call.get("params") or compensation_call.get("arguments") or compensation_call.get("args") or {}
        )
        if not tool_name:
            return None
        if isinstance(args, str):
            args = self._coerce_arguments(args)
        if not isinstance(args, dict):
            args = {}
        return tool_name, args

    async def _maybe_execute_compensation(
        self,
        *,
        compensation_spec: tuple[str, dict[str, Any]] | None,
        user_id: str,
        db_session: Any,
        owns_session: bool,
        reason: str,
    ) -> None:
        if not compensation_spec:
            return
        tool_name, arguments = compensation_spec
        COMPENSATION_TRIGGERED.labels(reason=reason).inc()
        try:
            await self._execute_tool_call_with_session(
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                db_session=db_session,
                progress_callback=None,
                tool_call_id=None,
                owns_session=owns_session,
                compensation_call=None,
            )
        except Exception as e:
            logger.warning(f"Compensation tool failed: {tool_name} - {e}")

    async def execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        user_id: str,
        db_session: Any | None,
        runtime_context: dict[str, Any] | None = None,
    ) -> list[ToolResult]:
        """
        批量执行工具调用（按顺序）

        Args:
            tool_calls: 工具调用列表，格式为 OpenAI function_call

        Returns:
            List[ToolResult]: 执行结果列表
        """
        results = []
        for call in tool_calls:
            arguments = self._coerce_arguments(call["function"].get("arguments"))
            result = await self.execute_tool_call(
                tool_name=call["function"]["name"],
                arguments=arguments,
                user_id=user_id,
                db_session=db_session,
                tool_call_id=call.get("id"),
                compensation_call=(call.get("compensation_call") or call.get("function", {}).get("compensation_call")),
                runtime_context=runtime_context,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # DAG-aware plan execution
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan: ExecutablePlan,
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None = None,
        execution_observer: Any | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> PlanExecutionResult:
        """Execute an ExecutablePlan respecting DAG layer ordering.

        Steps within a layer run concurrently (asyncio.gather).
        Output from earlier steps is propagated to dependent steps
        via ``output_key`` → parameter substitution.

        If a *required* step fails, execution is aborted and remaining
        layers are skipped.

        Falls back to sequential execution when no ``execution_order``
        is defined (backward compatible).
        """
        layers = plan.get_execution_layers()
        result = PlanExecutionResult(
            plan_id=plan.plan_id,
            total_layers=len(layers),
        )

        # Shared output store: step_id -> output_data
        output_store: dict[str, dict[str, Any]] = {}

        for layer_idx, layer in enumerate(layers):
            if not layer:
                continue

            # Resolve parameter placeholders from output_store
            resolved_layer = self._resolve_layer_params(layer, output_store)
            layer_number = layer_idx + 1

            await self._notify_execution_observer(
                execution_observer,
                {
                    "event": "layer_start",
                    "layer_index": layer_idx,
                    "layer_number": layer_number,
                    "total_layers": len(layers),
                    "step_ids": [tc.id for tc in resolved_layer],
                    "tool_names": [tc.name for tc in resolved_layer],
                },
            )

            # Execute steps within this layer concurrently
            step_results = await asyncio.gather(
                *(
                    self._execute_step(
                        tc,
                        user_id,
                        db_session,
                        progress_callback,
                        runtime_context=runtime_context,
                    )
                    for tc in resolved_layer
                ),
                return_exceptions=True,
            )

            # Process results
            layer_aborted = False
            for tc, sr in zip(resolved_layer, step_results, strict=False):
                if isinstance(sr, BaseException):
                    sr = StepResult(
                        step_id=tc.id,
                        tool_name=tc.name,
                        tool_result=ToolResult(
                            success=False,
                            tool_name=tc.name,
                            error_message=str(sr),
                        ),
                    )

                result.step_results.append(sr)
                result.tool_results.append(sr.tool_result)

                await self._notify_execution_observer(
                    execution_observer,
                    {
                        "event": "step_completed",
                        "layer_index": layer_idx,
                        "layer_number": layer_number,
                        "step_id": sr.step_id,
                        "tool_name": sr.tool_name,
                        "success": sr.tool_result.success,
                        "duration_ms": sr.duration_ms,
                    },
                )

                # Store output for downstream steps
                if sr.output_key and sr.tool_result.success:
                    output_store[sr.step_id] = sr.output_data

                # Check required step failure
                criteria = tc.success_criteria
                is_required = criteria.required if criteria else True
                if not sr.tool_result.success and is_required:
                    layer_aborted = True

            result.execution_layers_completed = layer_idx + 1

            await self._notify_execution_observer(
                execution_observer,
                {
                    "event": "layer_end",
                    "layer_index": layer_idx,
                    "layer_number": layer_number,
                    "total_layers": len(layers),
                    "aborted": layer_aborted,
                    "completed_steps": len(resolved_layer),
                },
            )

            if layer_aborted:
                result.aborted = True
                result.abort_reason = f"Required step failed in layer {layer_idx}"
                logger.warning(
                    "Plan {} aborted at layer {}: required step failed",
                    plan.plan_id,
                    layer_idx,
                )
                await self._notify_execution_observer(
                    execution_observer,
                    {
                        "event": "execution_aborted",
                        "layer_index": layer_idx,
                        "layer_number": layer_number,
                        "reason": result.abort_reason,
                    },
                )
                break

        await self._notify_execution_observer(
            execution_observer,
            {
                "event": "execution_end",
                "plan_id": plan.plan_id,
                "total_layers": len(layers),
                "layers_completed": result.execution_layers_completed,
                "aborted": result.aborted,
                "abort_reason": result.abort_reason,
                "steps_total": len(result.step_results),
            },
        )

        return result

    async def _execute_step(
        self,
        spec: ToolCallSpec,
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None,
        runtime_context: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute a single ToolCallSpec and return StepResult."""
        start = time.time()
        tool_result = await self.execute_tool_call(
            tool_name=spec.name,
            arguments=spec.params,
            user_id=user_id,
            db_session=db_session,
            progress_callback=progress_callback,
            tool_call_id=spec.id,
            compensation_call=spec.compensation_call,
            runtime_context=runtime_context,
        )
        duration_ms = int((time.time() - start) * 1000)

        # Extract output_data from result for downstream propagation
        output_data: dict[str, Any] = {}
        if spec.output_key and tool_result.success and tool_result.data:
            if isinstance(tool_result.data, dict):
                output_data = tool_result.data
            else:
                output_data = {"_value": tool_result.data}

        return StepResult(
            step_id=spec.id,
            tool_name=spec.name,
            tool_result=tool_result,
            duration_ms=duration_ms,
            output_key=spec.output_key,
            output_data=output_data,
        )

    @staticmethod
    def _resolve_layer_params(
        layer: list[ToolCallSpec],
        output_store: dict[str, dict[str, Any]],
    ) -> list[ToolCallSpec]:
        """Substitute placeholder params with outputs from completed steps.

        If a step's param value matches a pattern like
        ``"$ref:step_id:key"`` or is exactly ``"$ref:step_id"``,
        replace it with the corresponding value from output_store.
        Also handles the common case where ``depends_on`` lists a step
        whose output contains the needed ID (e.g. plan_id, task_id).
        """
        if not output_store:
            return layer

        for tc in layer:
            for dep_id in tc.depends_on:
                if dep_id not in output_store:
                    continue
                dep_output = output_store[dep_id]
                # Auto-inject matching keys from dependency output
                for param_key, param_val in list(tc.params.items()):
                    # Explicit $ref placeholder
                    if isinstance(param_val, str) and param_val.startswith("$ref:"):
                        parts = param_val.split(":", 2)
                        ref_step = parts[1] if len(parts) > 1 else ""
                        ref_key = parts[2] if len(parts) > 2 else param_key
                        if ref_step == dep_id and ref_key in dep_output:
                            tc.params[param_key] = dep_output[ref_key]
                    # Auto-fill: if param value looks like a placeholder
                    # (empty or __pending__) and dep has the key
                    elif param_val in ("", "__pending__") and param_key in dep_output:
                        tc.params[param_key] = dep_output[param_key]

        return layer
