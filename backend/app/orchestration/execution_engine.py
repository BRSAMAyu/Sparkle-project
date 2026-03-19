"""ExecutionEngineMixin — execution, planning, and tool-handling methods for ChatOrchestrator."""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    COLLABORATION_LATENCY,
    COLLABORATION_SUCCESS,
    EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL,
    HITL_REQUESTED,
)
from app.core.metrics import (
    ACTIVE_SESSIONS,
    REQUEST_COUNT,
    RESPONSE_FALLBACK_GENERATED_TOTAL,
    SESSION_FEEDBACK_VISIBLE_HINT_TOTAL,
    TOKEN_USAGE,
)
from app.core.pending_actions import pending_actions_store
from app.core.task_manager import task_manager
from app.gen.agent.v1 import agent_service_pb2
from app.models.galaxy import KnowledgeNode
from app.orchestration.agent_memory import AgentMemoryService
from app.orchestration.agent_scoring import AgentScoringService
from app.orchestration.chat_modes import CHAT_MODE_STANDARD, is_expert_chat_mode
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.mode_workflow_config import get_mode_strategy, get_workflow_config
from app.orchestration.multi_agent_adapter import execute_multi_agent_workflow
from app.orchestration.orchestration_trace import OrchestrationTrace
from app.orchestration.persona_aware_planner import PersonaAwarePlanner
from app.orchestration.plan_review_service import ReviewDecision, plan_review_service
from app.orchestration.schemas import ExecutablePlan, RouteDecision, StateSnapshot
from app.orchestration.session_feedback import (
    SessionFeedbackSignal,
    apply_session_feedback_visible_prefix,
    build_session_feedback_instruction,
)
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.transparency_data_generator import StepType, TransparencyDataGenerator
from app.orchestration.ux_envelope import ux_envelope_builder
from app.services.llm_service import llm_service
from app.services.system_update_service import SystemUpdateService, build_system_update


class ExecutionEngineMixin:
    """Mixin providing execution, planning, and tool-handling methods for ChatOrchestrator."""

    def _format_review_message(self, review_result) -> str:
        """Format plan review result as user-friendly message"""
        from app.orchestration.plan_review_service import ReviewDecision

        decision = review_result.decision
        comments = review_result.comments

        # Header based on decision
        if decision == ReviewDecision.REJECTED.value:
            header = "🚫 计划未通过审查"
        elif decision == ReviewDecision.NEEDS_MODIFICATION.value:
            header = "⚠️ 计划需要修改"
        elif decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            header = "🔍 需要确认计划"
        else:
            header = "✅ 计划已通过审查"

        lines = [f"\n\n{header}"]

        # Add comments by severity
        critical_comments = [c for c in comments if c.severity == "critical"]
        warning_comments = [c for c in comments if c.severity == "warning"]
        info_comments = [c for c in comments if c.severity == "info"]

        if critical_comments:
            lines.append("\n**严重问题:**")
            for c in critical_comments:
                lines.append(f"- {c.message}")
                if c.suggested_fix:
                    lines.append(f"  建议: {c.suggested_fix}")

        if warning_comments:
            lines.append("\n**警告:**")
            for c in warning_comments[:3]:  # Limit warnings
                lines.append(f"- {c.message}")

        if info_comments and decision != ReviewDecision.REJECTED.value:
            lines.append("\n**建议:**")
            for c in info_comments[:2]:  # Limit info comments
                lines.append(f"- {c.message}")

        # Add confidence indicator
        if review_result.confidence > 0:
            confidence_pct = int(review_result.confidence * 100)
            lines.append(f"\n置信度: {confidence_pct}%")

        # Add footer based on decision
        if decision == ReviewDecision.REJECTED.value:
            lines.append("\n请重新描述您的需求，我将为您重新规划。")
        elif decision == ReviewDecision.NEEDS_MODIFICATION.value:
            lines.append("\n请在下方补充说明修改要求，我将重新规划。")
        elif decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            lines.append("\n请确认是否执行此计划。")

        return "\n".join(lines)

    async def _get_tools_schema(self, active_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """Get tools from dynamic registry, optionally filtered by request-scoped allowlist."""
        try:
            requested_tools = [tool_name.strip() for tool_name in (active_tools or []) if tool_name and tool_name.strip()]
            if not requested_tools:
                return dynamic_tool_registry.get_openai_tools_schema()

            tools_by_name = {tool.name: tool for tool in dynamic_tool_registry.get_all_tools()}
            filtered_tools: list[dict[str, Any]] = []
            unknown_tools: list[str] = []
            seen: set[str] = set()
            for tool_name in requested_tools:
                if tool_name in seen:
                    continue
                seen.add(tool_name)
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    unknown_tools.append(tool_name)
                    continue
                filtered_tools.append(tool.to_openai_schema())

            if unknown_tools:
                logger.warning(f"Ignoring unknown active_tools: {unknown_tools}")

            return filtered_tools
        except Exception as e:
            logger.error(f"Failed to get tools schema: {e}")
            return []

    async def _prepare_runtime_context(
        self,
        state: WorkflowState,
        request_id: str,
        response_id: str,
        active_tools: list[str],
        stream_callback,
        tracer,
    ) -> tuple[TransparencyDataGenerator, "typing.Callable"]:
        """Prepare transparency tracking, tools schema, and initial status.

        Returns (transparency_generator, emit_transparency_event).
        """
        import typing

        transparency_enabled = bool(
            settings.TRANSPARENCY_MODE_ENABLED and settings.TRANSPARENCY_MODE_DEFAULT
        )
        transparency_generator = TransparencyDataGenerator(
            request_id=request_id or response_id,
            enabled=transparency_enabled,
        )

        async def emit_transparency_event(event: dict[str, Any] | None) -> None:
            if not event:
                return
            try:
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        metadata={
                            "event_type": "transparency",
                            "event_payload": json.dumps(event, ensure_ascii=False),
                        }
                    )
                )
            except Exception as exc:
                logger.debug(f"Failed to emit transparency event: {exc}")

        # Load tools with transparency step
        tools_step = transparency_generator.create_step(
            name="加载工具配置",
            step_type=StepType.PLANNING,
            agent_type="ORCHESTRATOR",
            metadata={"phase": "tools_schema"},
        )
        transparency_generator.start_step(tools_step)
        await emit_transparency_event(transparency_generator.get_step_event())
        with tracer.start_as_current_span("orchestrator.get_tools"):
            tools = await self._get_tools_schema(active_tools=active_tools)
        transparency_generator.complete_step(
            tools_step,
            metadata={"tool_count": len(tools), "requested_tool_count": len(active_tools)},
        )
        await emit_transparency_event(transparency_generator.get_step_event())
        run_ledger = state.context_data.get("run_ledger")
        if run_ledger is not None:
            await run_ledger.record_event(
                event_type="runtime_context_ready",
                label="运行上下文准备完成",
                workflow_stage="context",
                metadata={
                    "tool_count": len(tools),
                    "requested_tool_count": len(active_tools),
                },
                emit_snapshot=False,
            )

        # Emit initial thinking status
        await stream_callback(agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING
            )
        ))

        # Inject tools into state
        state.context_data["tools_schema"] = tools
        state.context_data["active_tools"] = list(active_tools)

        return transparency_generator, emit_transparency_event

    @staticmethod
    def _coerce_tool_result_payload(raw_result_json: str) -> Any:
        if not raw_result_json:
            return {}
        try:
            return json.loads(raw_result_json)
        except json.JSONDecodeError:
            return {"raw_result": raw_result_json}

    @staticmethod
    def _iter_text_chunks(text: str, chunk_size: int = 240) -> list[str]:
        if not text:
            return []
        return [text[idx:idx + chunk_size] for idx in range(0, len(text), chunk_size)]

    async def _continue_after_tool_result(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        tr = request.tool_result
        conversation_history = self._build_routing_history(conversation_context)
        tool_result = {
            "tool_call_id": tr.tool_call_id,
            "tool_name": tr.tool_name,
            "result": self._coerce_tool_result_payload(tr.result_json),
            "success": not tr.is_error,
            "is_error": bool(tr.is_error),
            "error_message": tr.error_message,
        }

        try:
            llm_response = await llm_service.continue_with_tool_results(
                conversation_history=conversation_history,
                tool_results=[tool_result],
            )
        except Exception as exc:
            logger.error(f"Tool result continuation failed: {exc}", exc_info=True)
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                error=agent_service_pb2.Error(
                    message=f"工具结果续跑失败: {exc}",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_INTERNAL,
                ),
                finish_reason=agent_service_pb2.ERROR,
            )
            return

        full_response = (llm_response.content or "").strip()
        if not full_response:
            full_response = "工具执行已完成，但没有生成补充说明。请继续告诉我下一步需要处理什么。"
            RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="tool_result_empty_final").inc()

        yield agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details=f"正在整合工具结果：{tr.tool_name}",
                current_agent_name="Sparkle AI",
            ),
        )

        for chunk in self._iter_text_chunks(full_response):
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                delta=chunk,
            )

        await self._persist_assistant_message(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            full_response=full_response,
        )
        llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
        await self._record_decision(
            active_db=active_db,
            user_id=user_id,
            user_context_payload=user_context_payload,
            llm_profile_meta=llm_profile_meta,
            full_response=full_response,
        )

        response_metadata = {
            "response_id": response_id,
            "trace_id": trace_id,
            "tool_continuation": "true",
            "tool_name": tr.tool_name,
            "tool_error": str(bool(tr.is_error)).lower(),
            "preference_version": (user_context_payload or {}).get("preference_version", 0),
            "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
            "experiment_cohort": (user_context_payload or {}).get("experiment_cohort", ""),
        }
        ux_envelope = await ux_envelope_builder.build(
            user_message=self._extract_latest_user_message(conversation_history),
            full_response=full_response,
            final_state=WorkflowState(messages=conversation_history, context_data={
                "chat_mode": CHAT_MODE_STANDARD,
                "conversation_context": conversation_context,
                "include_references": False,
                "file_ids": [],
            }),
            executable_plan=None,
            route_decision=RouteDecision(
                execution_mode="direct",
                reason="tool_continuation",
                risk_level="low",
            ),
            include_references=False,
            file_ids=[],
            execution_validation=None,
            conversation_context=conversation_context,
            plan_context=None,
            user_context_payload=user_context_payload,
        )
        response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))
        final_response_data = {
            "message": full_response,
            "tool_results": [tool_result],
            "metadata": response_metadata,
        }
        await self._cache_response(session_id, request_id, final_response_data)
        update_responses, _, _, _, _, _ = await self._drain_system_updates(user_id)
        for update_resp in update_responses:
            yield update_resp

        yield agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            metadata={str(k): str(v) for k, v in response_metadata.items()},
            full_text=full_response,
            finish_reason=agent_service_pb2.STOP,
        )

    async def _handle_multi_agent_mode(
        self,
        chat_mode: str,
        user_message: str,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        start_time: float,
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        active_db: AsyncSession | None,
        workflow_id: str,
        prompt_version: str,
        stream_callback,
        session_feedback_signal: dict[str, Any] | None = None,
        session_adaptation_context: dict[str, Any] | None = None,
        result_holder: dict[str, Any] | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """Handle non-standard chat modes (multi-agent workflows).

        Yields ChatResponse items directly; caller should ``return`` after iteration.
        """
        logger.info(f"Routing to multi-agent workflow: {chat_mode}")
        result_holder = result_holder if result_holder is not None else {}
        multi_agent_context = {
            "user_id": user_id,
            "session_id": session_id,
            "user_context": user_context_payload,
            "conversation_context": conversation_context,
            "plan_context": plan_context,
            "db_session": active_db,
            "prompt_version": prompt_version,
            "workflow_id": workflow_id,
            "session_feedback_signal": session_feedback_signal,
            "session_feedback_instruction": build_session_feedback_instruction(session_feedback_signal),
            "session_adaptation": session_adaptation_context,
            "context_focus": (user_context_payload or {}).get("context_focus"),
            "context_briefing_note": (user_context_payload or {}).get("context_briefing_note"),
        }
        full_text_parts: list[str] = []
        full_text_override = ""
        metadata_map: dict[str, str] = {}
        had_error = False
        mode_config = get_workflow_config(chat_mode)

        try:
            response_count = 0
            agents = list(mode_config.collaboration_agents) if mode_config else []
            collaboration_mode = mode_config.collaboration_mode if mode_config else "single"
            if agents and collaboration_mode != "single":
                await self.observability.log_collaboration_start(
                    user_id=user_id,
                    session_id=session_id,
                    agents=agents,
                    mode=collaboration_mode,
                )
            if settings.ENABLE_MODE_WORKFLOW_V2:
                response_stream = self.multi_agent_adapter.execute_mode_workflow(
                    chat_mode=chat_mode,
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    context_data=multi_agent_context,
                    stream_callback=stream_callback,
                    result_holder=result_holder,
                )
            else:
                response_stream = execute_multi_agent_workflow(
                    orchestrator=self,
                    chat_mode=chat_mode,
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    context_data=multi_agent_context,
                    stream_callback=stream_callback,
                    result_holder=result_holder,
                )

            async for response in response_stream:
                response.response_id = response_id
                response.created_at = int(datetime.now().timestamp())
                response.request_id = request_id
                response.trace_id = response.trace_id or trace_id
                response.workflow_id = f"multi_agent_{chat_mode}"
                response.prompt_version = response.prompt_version or prompt_version
                response_count += 1
                content_type = response.WhichOneof("content")
                logger.info(
                    f"[Orchestrator] Multi-agent response #{response_count}: "
                    f"type={content_type}, delta_len={len(response.delta) if response.delta else 0}"
                )
                if response.delta:
                    full_text_parts.append(response.delta)
                if response.full_text:
                    full_text_override = response.full_text
                if response.metadata:
                    for k, v in response.metadata.items():
                        metadata_map[str(k)] = str(v)
                if response.finish_reason == agent_service_pb2.ERROR or response.HasField("error"):
                    had_error = True
                yield response

            logger.info(f"[Orchestrator] Multi-agent workflow completed with {response_count} responses")
            await self._update_state(session_id, "DONE", "Multi-agent workflow completed")
            final_text = full_text_override or "".join(full_text_parts)
            parsed_session_signal = SessionFeedbackSignal.from_dict(session_feedback_signal)
            if not had_error and (not final_text or not final_text.strip()):
                execution_summary = str(result_holder.get("execution_summary", "")).strip()
                if execution_summary:
                    final_text = (
                        "执行已完成，以下是关键结果摘要：\n"
                        f"{execution_summary}\n\n"
                        "如需我继续，我可以进一步输出完整分析与下一步计划。"
                    )
                    metadata_map["response_fallback"] = "mode_execution_summary"
                    RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="mode_empty_final").inc()
            final_text, session_adaptation_visible = apply_session_feedback_visible_prefix(
                final_text,
                session_feedback_signal,
            )
            if parsed_session_signal and session_adaptation_visible and parsed_session_signal.applies_adaptation:
                SESSION_FEEDBACK_VISIBLE_HINT_TOTAL.labels(
                    signal_type=parsed_session_signal.signal_type,
                ).inc()
            if not had_error and final_text:
                await self._persist_assistant_message(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    full_response=final_text,
                )
                llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
                await self._record_decision(
                    active_db=active_db,
                    user_id=user_id,
                    user_context_payload=user_context_payload,
                    llm_profile_meta=llm_profile_meta,
                    full_response=final_text,
                )
                response_metadata = {
                    "response_id": response_id,
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "prompt_version": prompt_version,
                    "session_adaptation_visible": "true" if session_adaptation_visible else "false",
                    "experiment_cohort": (user_context_payload or {}).get("experiment_cohort", ""),
                    **metadata_map,
                }
                if parsed_session_signal is not None:
                    response_metadata["session_feedback_signal"] = json.dumps(
                        parsed_session_signal.to_dict(),
                        ensure_ascii=False,
                    )
                if session_adaptation_context:
                    response_metadata["session_adaptation"] = json.dumps(
                        session_adaptation_context,
                        ensure_ascii=False,
                    )
                if isinstance(result_holder.get("conversation_rhythm"), dict):
                    response_metadata["conversation_rhythm"] = json.dumps(
                        result_holder["conversation_rhythm"],
                        ensure_ascii=False,
                    )
                if settings.ENABLE_CONTEXT_FOCUS_METADATA:
                    context_focus = None
                    briefing_note = ""
                    focused_memory = None
                    if isinstance(user_context_payload, dict):
                        context_focus = user_context_payload.get("context_focus")
                        briefing_note = str(user_context_payload.get("context_briefing_note") or "").strip()
                        focused_memory = user_context_payload.get("focused_memory")
                    if context_focus:
                        response_metadata["context_focus"] = json.dumps(context_focus, ensure_ascii=False)
                        response_metadata["context_section_weights"] = json.dumps(
                            dict(context_focus.get("section_weights") or {}),
                            ensure_ascii=False,
                        )
                    if briefing_note:
                        response_metadata["context_briefing_note"] = briefing_note
                    if isinstance(focused_memory, dict):
                        summary = {
                            "preferences": len(dict(focused_memory.get("preferences") or {})),
                            "goals": len(list(focused_memory.get("active_goals") or [])),
                            "episodic": len(list(focused_memory.get("episodic_memories") or [])),
                        }
                        response_metadata["focused_memory_summary"] = json.dumps(summary, ensure_ascii=False)
                        semantic_meta = (((focused_memory.get("context_pack") or {}).get("metadata") or {}).get("semantic_gating"))
                        if semantic_meta:
                            response_metadata["context_semantic_gating"] = json.dumps(semantic_meta, ensure_ascii=False)
                understanding_depth = (user_context_payload or {}).get("understanding_depth") if isinstance(user_context_payload, dict) else None
                if isinstance(understanding_depth, dict):
                    response_metadata["understanding_depth"] = json.dumps(understanding_depth, ensure_ascii=False)
                returning_context = (user_context_payload or {}).get("returning_context") if isinstance(user_context_payload, dict) else None
                if isinstance(returning_context, dict):
                    response_metadata["returning_after_silence"] = json.dumps(returning_context, ensure_ascii=False)
                result_holder["final_response_data"] = {
                    "message": final_text,
                    "full_text": final_text,
                    "tool_results": [],
                    "metadata": response_metadata,
                }
            tool_calls_count = int(result_holder.get("tool_calls_count", 0))
            if agents and collaboration_mode != "single":
                await self.observability.log_collaboration_end(
                    user_id=user_id,
                    session_id=session_id,
                    agents=agents,
                    mode=collaboration_mode,
                    tool_calls_count=tool_calls_count,
                    latency_ms=(time.time() - start_time) * 1000.0,
                )

        except Exception as e:
            logger.error(f"Multi-agent workflow error: {e}")
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message=f"多Agent协作模式执行失败: {str(e)}",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_INTERNAL,
                ),
                finish_reason=agent_service_pb2.ERROR,
            )

    def _inject_state_dependencies(
        self,
        state: WorkflowState,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        stream_callback,
        tools_schema: list[dict[str, Any]],
        transparency_generator: TransparencyDataGenerator,
        emit_transparency_event,
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        file_ids: list[str],
        include_references: bool,
        workflow_id: str,
        prompt_version: str,
        run_ledger=None,
    ) -> None:
        """Inject all runtime dependencies into the workflow state."""
        if active_db:
            state.context_data["db_session"] = active_db
        state.context_data.update({
            "user_id": user_id,
            "session_id": session_id,
            "stream_callback": stream_callback,
            "tools_schema": tools_schema,
            "transparency_generator": transparency_generator,
            "emit_transparency_event": emit_transparency_event,
            "redis_client": self.redis,
            "user_context": user_context_payload,
            "conversation_context": conversation_context,
            "plan_context": plan_context,
            "file_ids": file_ids,
            "include_references": include_references,
            "workflow_id": workflow_id,
            "prompt_version": prompt_version,
            "run_ledger": run_ledger,
        })

    async def _execute_graph(
        self,
        *,
        state: WorkflowState,
        user_id: str,
        queue: asyncio.Queue,
        result_holder: dict[str, Any],
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        logger.info("🚀 Launching StateGraph Execution")
        graph_task = await task_manager.spawn(
            self.graph.invoke(state),
            task_name="orchestrator_graph",
            user_id=str(user_id),
        )

        total_prompt_tokens = 0
        total_completion_tokens = 0

        while not graph_task.done() or not queue.empty():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.1)
                if item.HasField("usage"):
                    total_prompt_tokens = item.usage.prompt_tokens
                    total_completion_tokens = item.usage.completion_tokens
                    if self.token_tracker:
                        TOKEN_USAGE.labels(model="gpt-4", type="prompt").inc(total_prompt_tokens)
                        TOKEN_USAGE.labels(model="gpt-4", type="completion").inc(total_completion_tokens)
                yield item
                queue.task_done()
            except TimeoutError:
                if graph_task.done():
                    break

        if graph_task.done():
            exc = graph_task.exception()
            if exc:
                raise exc
            result_holder["final_state"] = graph_task.result()
            result_holder["total_prompt_tokens"] = total_prompt_tokens
            result_holder["total_completion_tokens"] = total_completion_tokens

    async def _plan_and_validate(
        self,
        *,
        route_decision: RouteDecision,
        user_message: str,
        user_id: str,
        session_id: str,
        active_db: AsyncSession | None,
        plan_id: uuid.UUID | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        stream_callback,
        state: WorkflowState,
        user_context_payload: dict[str, Any] | None,
        orchestration_trace: OrchestrationTrace | None = None,
    ) -> tuple[RouteDecision, ExecutablePlan | None, StateSnapshot | None, bool]:
        executable_plan = None
        snapshot = None

        if route_decision.execution_mode not in ["langgraph", "hybrid"]:
            return route_decision, executable_plan, snapshot, False

        logger.info(f"Using LangGraph planner for {route_decision.execution_mode} mode")
        allow, reason = await self.langgraph_breaker.allow_request()
        if not allow:
            logger.warning(f"LangGraph blocked by circuit breaker: {reason}")
            await self.observability.log_circuit_state_change(
                circuit_name="langgraph_planner",
                old_state="open",
                new_state="open",
                reason=reason,
            )
            await stream_callback(agent_service_pb2.ChatResponse(
                delta="\n\n⚠️ 智能规划暂时不可用，使用标准模式"
            ))
            route_decision.execution_mode = "direct"
            return route_decision, executable_plan, snapshot, False

        try:
            snapshot = await self.snapshot_manager.create_snapshot(
                user_id=user_id,
                session_id=session_id,
                db_session=active_db,
            )
            conversation_history = []
            if conversation_context:
                conversation_history = conversation_context.get("messages", [])
            plan_id_str = str(plan_id) if plan_id else None

            execution_feedback = await self._load_recent_execution_feedback(
                active_db=active_db,
                user_id=user_id,
                plan_id=plan_id_str,
            )
            planning_constraints = {}
            if isinstance(plan_context, dict) and isinstance(plan_context.get("constraints"), dict):
                planning_constraints = dict(plan_context.get("constraints") or {})
            weak_knowledge_node_ids = planning_constraints.get("weak_knowledge_node_ids") or []
            if weak_knowledge_node_ids and active_db:
                resolved_nodes: list[dict[str, Any]] = []
                normalized_ids: list[uuid.UUID] = []
                for node_id in weak_knowledge_node_ids[:5]:
                    with contextlib.suppress(Exception):
                        normalized_ids.append(uuid.UUID(str(node_id)))
                if normalized_ids:
                    nodes_result = await active_db.execute(
                        select(KnowledgeNode).where(KnowledgeNode.id.in_(normalized_ids))
                    )
                    for node in nodes_result.scalars().all():
                        resolved_nodes.append(
                            {
                                "id": str(node.id),
                                "name": node.name,
                                "description": (node.description or "")[:160],
                            }
                        )
                if resolved_nodes:
                    planning_constraints["weak_knowledge_nodes"] = resolved_nodes

            chat_mode = str(state.context_data.get("chat_mode", CHAT_MODE_STANDARD))
            mode_strategy = get_mode_strategy(chat_mode)
            mode_config = get_workflow_config(chat_mode)
            route_intent = self._extract_route_intent(route_decision.reason)
            if route_intent:
                planning_constraints["route_intent"] = route_intent
            if mode_strategy and mode_strategy.collaboration_mode != "auto":
                planning_constraints["collaboration_mode"] = mode_strategy.collaboration_mode
            if mode_strategy and mode_strategy.required_agents:
                planning_constraints["required_agents"] = list(mode_strategy.required_agents)
            if mode_strategy and mode_strategy.preferred_agents:
                planning_constraints["preferred_agents"] = list(mode_strategy.preferred_agents)
            if mode_strategy and mode_strategy.excluded_agents:
                planning_constraints["excluded_agents"] = list(mode_strategy.excluded_agents)
            if mode_strategy and mode_strategy.output_structure:
                planning_constraints["required_output_structure"] = list(mode_strategy.output_structure)

            # Phase 1-B: Inject Cognitive Policy Signals
            if isinstance(user_context_payload, dict):
                insights = user_context_payload.get("cognitive_insights", {})
                if isinstance(insights, dict) and insights.get("policy_signals"):
                    signals = insights.get("policy_signals")
                    if isinstance(signals, list) and signals:
                        planning_constraints["cognitive_policy_signals"] = signals

            persona_constraints = None
            if active_db is not None:
                persona_started_at = time.perf_counter()
                persona_constraints = await PersonaAwarePlanner(active_db, self.redis).build_constraints(
                    user_id=user_id,
                    user_context_payload=user_context_payload,
                    plan_context=plan_context,
                    plan_id=plan_id_str,
                )
                planning_constraints["persona_constraints"] = persona_constraints.to_planning_constraints()
                persona_summary = (
                    f"完成率{persona_constraints.recent_completion_rate:.0%}，"
                    f"偏好{persona_constraints.preferred_task_size}任务，"
                    f"最大专注{persona_constraints.max_session_minutes}分钟"
                    + ("，需要热身任务" if persona_constraints.require_warmup_task else "")
                )
                state.context_data["persona_constraints_summary"] = persona_summary
                if isinstance(user_context_payload, dict):
                    user_context_payload["persona_constraints_summary"] = persona_summary
                if persona_constraints.weak_knowledge_nodes:
                    planning_constraints["insert_prerequisite_review"] = True
                    if "weak_knowledge_nodes" not in planning_constraints:
                        planning_constraints["weak_knowledge_nodes"] = [
                            {"name": item} for item in persona_constraints.weak_knowledge_nodes
                        ]
                if orchestration_trace is not None:
                    orchestration_trace.add_step(
                        step_id="persona",
                        label="画像约束",
                        decision=(
                            f"完成率 {persona_constraints.recent_completion_rate:.0%}，"
                            f"{persona_constraints.preferred_task_size} 任务优先"
                        ),
                        reason=(
                            f"根据你的画像，当前最大专注时长约 {persona_constraints.max_session_minutes} 分钟，"
                            f"时间倍率 {persona_constraints.time_multiplier:.2f}"
                            + (
                                "，并需要热身任务来降低启动成本。"
                                if persona_constraints.require_warmup_task
                                else "。"
                            )
                        ),
                        metadata={
                            "recent_completion_rate": round(persona_constraints.recent_completion_rate, 4),
                            "preferred_task_size": persona_constraints.preferred_task_size,
                            "max_session_minutes": persona_constraints.max_session_minutes,
                            "time_multiplier": round(persona_constraints.time_multiplier, 2),
                            "require_warmup_task": persona_constraints.require_warmup_task,
                            "weak_knowledge_nodes": list(persona_constraints.weak_knowledge_nodes[:5]),
                        },
                        duration_ms=self._roundtrip_ms(persona_started_at),
                    )
                    self._sync_orchestration_trace(
                        state=state,
                        orchestration_trace=orchestration_trace,
                        user_context_payload=user_context_payload,
                    )

            selected_experts = state.context_data.get("selected_experts", [])
            state_overrides: dict[str, Any] = {}
            if isinstance(selected_experts, list) and selected_experts:
                cleaned = [str(expert).strip() for expert in selected_experts if str(expert).strip()]
                if cleaned:
                    state_overrides["next_step"] = cleaned[0]
                    state_overrides["collaboration_agents"] = cleaned
                    state_overrides["collaboration_mode"] = "sequential"
                    state_overrides["collaboration_order"] = [
                        {"agent": expert, "task": user_message} for expert in cleaned
                    ]
                    state_overrides["collaboration_index"] = 0
            elif mode_strategy:
                required = [str(agent).strip() for agent in mode_strategy.required_agents if str(agent).strip()]
                preferred = [str(agent).strip() for agent in mode_strategy.preferred_agents if str(agent).strip()]
                ordered_agents = required or preferred
                if ordered_agents:
                    state_overrides["next_step"] = ordered_agents[0]
                    state_overrides["collaboration_agents"] = ordered_agents
                    if mode_strategy.collaboration_mode != "auto":
                        state_overrides["collaboration_mode"] = mode_strategy.collaboration_mode
                    state_overrides["collaboration_order"] = [
                        {"agent": agent, "task": user_message} for agent in ordered_agents
                    ]
                    state_overrides["collaboration_index"] = 0

            executable_plan = await self.lang_graph_planner.plan(
                message=user_message,
                snapshot=snapshot,
                user_id=user_id,
                session_id=session_id,
                conversation_history=conversation_history,
                plan_id=plan_id_str,
                execution_feedback=execution_feedback,
                mode_config=mode_config,
                mode_strategy=mode_strategy,
                persona_constraints=persona_constraints,
                state_overrides=state_overrides or None,
                planning_constraints=planning_constraints or None,
                stream_callback=stream_callback,
            )

            if self.redis and isinstance(user_context_payload, dict) and executable_plan is not None:
                agent_ids = [
                    str(agent).strip()
                    for agent in (getattr(executable_plan, "agents_involved", []) or [])
                    if str(agent).strip()
                ]
                if agent_ids:
                    try:
                        memory_context = await AgentMemoryService(self.redis).get_multi_agent_prompt_context(
                            agent_ids=agent_ids,
                            user_id=user_id,
                        )
                        if memory_context:
                            state.context_data["agent_memory_context"] = memory_context
                            user_context_payload["agent_memory_context"] = memory_context
                    except Exception as exc:
                        logger.debug(f"Failed to hydrate agent memory context: {exc}")

            collaboration_narrative = (
                executable_plan.collaboration_narrative
                if executable_plan and getattr(executable_plan, "collaboration_narrative", None)
                else None
            )
            if collaboration_narrative:
                state.context_data["collaboration_narrative"] = collaboration_narrative
                if isinstance(user_context_payload, dict):
                    user_context_payload["collaboration_narrative"] = collaboration_narrative
                existing_context = state.context_data.get("user_context")
                if isinstance(existing_context, dict):
                    existing_context["collaboration_narrative"] = collaboration_narrative

            if orchestration_trace is not None and executable_plan is not None:
                mode_step = orchestration_trace.latest_step("mode_strategy")
                if mode_step is not None:
                    actual_agents = [
                        str(agent).strip()
                        for agent in (getattr(executable_plan, "agents_involved", []) or [])
                        if str(agent).strip()
                    ]
                    if actual_agents:
                        mode_step.metadata["agents_involved"] = actual_agents
                        if not (mode_step.metadata.get("required_agents") or mode_step.metadata.get("preferred_agents")):
                            mode_step.metadata["required_agents"] = actual_agents
                        self._sync_orchestration_trace(
                            state=state,
                            orchestration_trace=orchestration_trace,
                            user_context_payload=user_context_payload,
                        )

            await self.observability.log_langgraph_plan(
                user_id=user_id,
                session_id=session_id,
                plan_id=executable_plan.plan_id,
                plan_data={
                    "agents_involved": executable_plan.agents_involved,
                    "collaboration_mode": executable_plan.collaboration_mode,
                    "tool_calls_count": len(executable_plan.tool_calls),
                    "confidence": executable_plan.confidence,
                    "rationale": executable_plan.rationale,
                },
            )

            logger.info(
                f"LangGraph plan generated: {len(executable_plan.tool_calls)} tool calls, "
                f"confidence={executable_plan.confidence}, "
                f"collaboration={executable_plan.collaboration_mode}, "
                f"agents={executable_plan.agents_involved}"
            )

            current_versions = await self._load_context_versions(user_id)
            conflict = await self.version_conflict_service.check_all_conflicts(
                plan=executable_plan,
                snapshot=snapshot,
                current_context_versions=current_versions,
                user_id=uuid.UUID(user_id),
            )
            if conflict.has_conflict:
                logger.warning(
                    "Version conflict detected: type=%s domains=%s",
                    conflict.conflict_type,
                    conflict.conflicted_domains,
                )
                plan_uuid = uuid.UUID(plan_id_str) if plan_id_str else None

                async def _replan_callback():
                    new_snapshot = await self.snapshot_manager.create_snapshot(
                        user_id=user_id,
                        session_id=session_id,
                        db_session=active_db,
                    )
                    nonlocal snapshot
                    snapshot = new_snapshot
                    return await self.lang_graph_planner.replan(
                        message=user_message,
                        snapshot=new_snapshot,
                        user_id=user_id,
                        session_id=session_id,
                        previous_plan=executable_plan,
                        conflict_info=conflict.to_dict(),
                        plan_id=plan_id_str,
                        execution_feedback=execution_feedback,
                    )

                resolution = await self.version_conflict_service.resolve_conflict(
                    conflict_result=conflict,
                    original_plan=executable_plan,
                    user_id=uuid.UUID(user_id),
                    session_id=session_id,
                    user_message=user_message,
                    plan_id=plan_uuid,
                    replan_callback=_replan_callback,
                )
                if resolution.requires_hitl:
                    await self._stream_hitl_escalation(
                        conflict=conflict,
                        executable_plan=executable_plan,
                        snapshot=snapshot,
                        user_id=str(user_id),
                        stream_callback=stream_callback,
                    )
                    return route_decision, executable_plan, snapshot, True
                if resolution.success and resolution.new_plan:
                    executable_plan = resolution.new_plan
                else:
                    await self._stream_discard_notice(stream_callback)
                    await self.observability.log_validation_failed(
                        user_id=user_id,
                        session_id=session_id,
                        plan_id=executable_plan.plan_id,
                        failure_reason="Version conflict discard",
                    )
                    await self.langgraph_breaker.on_failure("version_conflict_discard")
                    return route_decision, executable_plan, snapshot, True

            validation_result = await self.grounding_validator.validate_plan(
                plan=executable_plan,
                snapshot=snapshot,
                db_session=active_db,
                user_id=user_id,
            )
            if not validation_result.is_valid:
                logger.warning(
                    "LangGraph validation failed, falling back to direct mode: %s",
                    validation_result.failure_reason,
                )
                await self.observability.log_validation_failed(
                    user_id=user_id,
                    session_id=session_id,
                    plan_id=executable_plan.plan_id,
                    failure_reason=validation_result.failure_reason,
                )
                await self.langgraph_breaker.on_failure("validation_failed")
                route_decision.execution_mode = "direct"
                return route_decision, None, snapshot, False
            if validation_result.warnings:
                state.context_data["knowledge_readiness_warnings"] = validation_result.warnings
                for warning in validation_result.warnings[:3]:
                    message = str(warning.get("message") or "").strip()
                    if message and f"knowledge_warning:{message}" not in executable_plan.risk_flags:
                        executable_plan.risk_flags.append(f"knowledge_warning:{message}")
                first_warning = validation_result.warnings[0]
                warning_message = str(first_warning.get("message") or "").strip()
                if warning_message:
                    existing_rationale = (executable_plan.rationale or "").strip()
                    suffix = f" 知识前置提醒：{warning_message}。"
                    if suffix.strip() not in existing_rationale:
                        executable_plan.rationale = f"{existing_rationale}{suffix}".strip()

            preflight = await self.grounding_validator.preflight_check(
                plan=executable_plan,
                user_id=user_id,
            )
            if not preflight["is_ready"]:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 服务暂时不可用: {', '.join(preflight['blocked_by'])}"
                ))
                await self.langgraph_breaker.on_failure("preflight_blocked")
                return route_decision, executable_plan, snapshot, True

            if executable_plan and route_decision.execution_mode in ["langgraph", "hybrid"]:
                review_started_at = time.perf_counter()
                review_result = await plan_review_service.review_plan(
                    plan=executable_plan,
                    user_message=user_message,
                    user_context={
                        **(user_context_payload or {}),
                        "plan_context": plan_context or (user_context_payload or {}).get("plan_context"),
                        "mode_strategy": state.context_data.get("mode_strategy"),
                    },
                )
                if orchestration_trace is not None:
                    alignment_score = review_result.alignment_score
                    decision_label = str(review_result.decision or "unknown")
                    alignment_text = (
                        f"{alignment_score:.2f}"
                        if isinstance(alignment_score, (int, float))
                        else "未知"
                    )
                    orchestration_trace.add_step(
                        step_id="plan_review",
                        label="计划审查",
                        decision=f"审查结果 {decision_label}，对齐度 {alignment_text}",
                        reason=(
                            review_result.alignment_summary
                            or review_result.user_facing_reason
                            or "系统已根据当前画像、风险和执行可行性完成审查。"
                        ),
                        confidence=review_result.confidence,
                        metadata={
                            "decision": review_result.decision,
                            "alignment_score": review_result.alignment_score,
                            "alignment_summary": review_result.alignment_summary or "",
                            "review_id": review_result.review_id,
                            "reasoning_source": review_result.reasoning_source or "",
                        },
                        duration_ms=self._roundtrip_ms(review_started_at),
                    )
                    self._sync_orchestration_trace(
                        state=state,
                        orchestration_trace=orchestration_trace,
                        user_context_payload=user_context_payload,
                    )
                if (
                    settings.ENABLE_PERCEPTIBLE_INTELLIGENCE
                    and settings.ENABLE_PLAN_REASONING_SUMMARY
                    and review_result.decision == ReviewDecision.APPROVED.value
                    and review_result.reasoning_summary
                ):
                    try:
                        await SystemUpdateService(getattr(self, "redis", None)).enqueue(
                            user_id,
                            build_system_update(
                                update_type="plan_reasoning",
                                category="evolution",
                                title="这次计划这样安排，是有依据的",
                                description=review_result.reasoning_summary,
                                priority="low",
                                metadata={
                                    "evolution_kind": "plan_reasoning",
                                    "headline": "这次计划这样安排，是有依据的",
                                    "reasoning_summary": review_result.reasoning_summary,
                                    "reasoning_details": review_result.reasoning_details or [],
                                    "reasoning_source": review_result.reasoning_source or "",
                                    "persona_strategy_mapping": review_result.persona_strategy_mapping or [],
                                    "alignment_score": review_result.alignment_score,
                                    "alignment_summary": review_result.alignment_summary or "",
                                    "evidence_summary": "；".join(
                                        detail.get("evidence", "")
                                        for detail in (review_result.reasoning_details or [])
                                        if isinstance(detail, dict) and detail.get("evidence")
                                    ),
                                    "plan_id": review_result.plan_id,
                                },
                            ),
                        )
                        EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL.labels(kind="plan_reasoning").inc()
                    except Exception as exc:
                        logger.warning(f"Failed to enqueue plan reasoning summary: {exc}")
                if plan_id:
                    from app.services.plan_feedback_service import get_plan_feedback_service
                    from app.services.plan_state_service import PlanStateService

                    feedback_service = get_plan_feedback_service(active_db, self.redis)
                    await feedback_service.append_review_feedback(
                        user_id=uuid.UUID(user_id),
                        plan_id=uuid.UUID(plan_id),
                        review_result=review_result,
                        user_decision=None,
                    )
                    review_feedback_entry = review_result.review_feedback_entry or {}
                    if review_feedback_entry:
                        plan_state_service = PlanStateService(active_db, self.redis)
                        plan_state = await plan_state_service.get_plan_state(
                            uuid.UUID(user_id),
                            uuid.UUID(plan_id),
                        )
                        existing_review_log = []
                        if plan_state and isinstance(plan_state.facts, dict):
                            raw_log = plan_state.facts.get("review_feedback_log")
                            if isinstance(raw_log, list):
                                existing_review_log = [item for item in raw_log if isinstance(item, dict)]
                        existing_review_log.append(review_feedback_entry)
                        await plan_state_service.upsert_plan_state(
                            user_id=uuid.UUID(user_id),
                            plan_id=uuid.UUID(plan_id),
                            patch={
                                "feedback_log": review_feedback_entry,
                                "facts": {
                                    "review_feedback_log": existing_review_log[-10:],
                                },
                            },
                        )
                    logger.info(f"Review feedback written for plan {plan_id}")

                if review_result.decision in [
                    ReviewDecision.REJECTED.value,
                    ReviewDecision.REQUIRES_CONFIRMATION.value,
                    ReviewDecision.NEEDS_MODIFICATION.value,
                ]:
                    action_id = await plan_review_service.store_review_result(
                        review=review_result,
                        user_id=str(user_id),
                    )
                    review_data_dict = review_result.to_dict()
                    review_data_dict["action_id"] = action_id
                    review_metadata = {
                        "requires_review": "true",
                        "review_action_id": action_id,
                        "review_decision": review_result.decision,
                        "review_id": review_result.review_id,
                        "plan_id": review_result.plan_id,
                        "review_data": json.dumps(review_data_dict),
                    }
                    review_delta = self._format_review_message(review_result)
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=review_delta,
                        metadata=review_metadata,
                    ))
                    state.context_data["plan_review"] = review_result.to_dict()
                    state.context_data["pending_review_action_id"] = action_id
                    logger.info(
                        f"Plan {executable_plan.plan_id} requires user review: "
                        f"{review_result.decision} (action_id={action_id})"
                    )
                    return route_decision, executable_plan, snapshot, True

                state.context_data["plan_review"] = review_result.to_dict()
                logger.info(
                    f"Plan {executable_plan.plan_id} auto-approved: "
                    f"confidence={review_result.confidence}"
                )

            state.context_data["executable_plan"] = executable_plan
            state.context_data["snapshot"] = snapshot
            await self.langgraph_breaker.on_success()

            plan_summary = self.lang_graph_planner.get_plan_summary(executable_plan)
            logger.info(f"Plan ready for execution: {plan_summary}")
            if executable_plan.collaboration_mode != "single":
                await self.observability.log_collaboration_start(
                    user_id=user_id,
                    session_id=session_id,
                    agents=executable_plan.agents_involved,
                    mode=executable_plan.collaboration_mode,
                )

            asyncio.create_task(
                self.shadow_predictor.predict_and_record(
                    user_message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    actual_decision=route_decision,
                    actual_plan=executable_plan,
                )
            )
            return route_decision, executable_plan, snapshot, False
        except Exception as e:
            logger.error(f"LangGraph planning error: {e}", exc_info=True)
            await self.langgraph_breaker.on_failure(str(e))
            await stream_callback(agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 规划失败，使用直接模式: {str(e)}"
            ))
            route_decision.execution_mode = "direct"
            return route_decision, executable_plan, snapshot, False
