"""
Multi-agent mode workflow adapter.

This module upgrades non-standard chat modes from prompt-only behavior to
full planning/execution workflows while keeping backward-compatible entrypoints.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_STANDARD,
    CHAT_MODE_STUDY_PLAN,
)
from app.orchestration.mode_workflow_config import get_workflow_config
from app.orchestration.schemas import StateSnapshot
from app.orchestration.step_feedback_collector import StepFeedbackCollector
from app.services.llm_service import llm_service
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator

if TYPE_CHECKING:
    from app.orchestration.orchestrator import ChatOrchestrator


class MultiAgentWorkflowAdapter:
    """Mode workflow adapter that reuses planner/executor/validator pipeline."""

    def __init__(self, orchestrator: "ChatOrchestrator"):
        self.orchestrator = orchestrator
        self.logger = logger
        self.llm_service = llm_service

    async def execute_mode_workflow(
        self,
        chat_mode: str,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        config = get_workflow_config(chat_mode)
        if not config:
            async for chunk in self._fallback_simple_stream(
                message=message,
                chat_mode=chat_mode,
                context_data=context_data,
            ):
                yield chunk
            return

        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="正在分析并规划任务...",
                active_agent=agent_service_pb2.ORCHESTRATOR,
            )
        )

        snapshot = StateSnapshot(
            user_id=user_id,
            session_id=session_id,
            context_versions={"tasks": "v0"},
        )
        plan = await self.orchestrator.lang_graph_planner.plan(
            message=message,
            snapshot=snapshot,
            user_id=user_id,
            session_id=session_id,
            conversation_history=context_data.get("conversation_context", {}).get("messages", []),
            execution_feedback=None,
            mode_config=config,
            state_overrides={
                "planning_mode": "langgraph",
                "_planning_mode": True,
            },
        )

        plan = self._apply_tool_policy(plan, config, context_data)

        if not plan.tool_calls:
            async for chunk in self._fallback_simple_stream(
                message=message,
                chat_mode=chat_mode,
                context_data=context_data,
                extra_notice="本轮未生成可执行工具计划，已回退为模式化回答。",
            ):
                yield chunk
            yield agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP)
            return

        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details=f"正在执行 {len(plan.tool_calls)} 个任务...",
                active_agent=agent_service_pb2.ORCHESTRATOR,
            )
        )

        execution_result = await self.orchestrator.tool_executor.execute_plan(
            plan=plan,
            user_id=user_id,
            db_session=self.orchestrator.db_session,
        )

        validation_result = await self._validate_plan(plan, execution_result, user_id)
        await self._publish_feedback(
            plan=plan,
            execution_result=execution_result,
            validation_result=validation_result,
            user_id=user_id,
            session_id=session_id,
        )

        async for chunk in self._stream_synthesis_response(
            chat_mode=chat_mode,
            user_message=message,
            execution_result=execution_result,
            validation_result=validation_result,
            synthesis_template=config.synthesis_template,
        ):
            yield chunk

        yield agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP)

    def _apply_tool_policy(self, plan, config, context_data: dict[str, Any]):
        allow_record = bool(context_data.get("error_record_confirmed", False))
        if config.tool_policy.get("allow_record_error_without_confirmation", False):
            allow_record = True
        if allow_record:
            return plan

        filtered_calls = [tc for tc in plan.tool_calls if tc.name != "record_error"]
        if len(filtered_calls) != len(plan.tool_calls):
            self.logger.info("[ModeWorkflow] record_error removed by confirmation gate")
        plan.tool_calls = filtered_calls
        plan.total_steps = len(filtered_calls)
        if plan.execution_order:
            valid_ids = {tc.id for tc in filtered_calls}
            plan.execution_order = [[sid for sid in layer if sid in valid_ids] for layer in plan.execution_order]
            plan.execution_order = [layer for layer in plan.execution_order if layer]
        return plan

    async def _validate_plan(self, plan, execution_result, user_id: str):
        record_service = None
        if self.orchestrator.db_session is not None:
            record_service = PlanExecutionRecordService(self.orchestrator.db_session)
        validator = PlanExecutionValidator(record_service=record_service)
        try:
            user_uuid = uuid.UUID(str(user_id))
        except ValueError:
            user_uuid = None
        return await validator.validate_plan_execution(
            plan=plan,
            plan_result=execution_result,
            user_id=user_uuid,
        )

    async def _publish_feedback(
        self,
        *,
        plan,
        execution_result,
        validation_result,
        user_id: str,
        session_id: str,
    ) -> None:
        if self.orchestrator.db_session is None:
            return
        try:
            collector = StepFeedbackCollector()
            feedback = collector.collect(
                plan=plan,
                plan_result=execution_result,
                validation_result=validation_result,
                user_id=user_id,
                session_id=session_id,
            )
            from app.orchestration.adaptive_replanner import AdaptiveReplanner

            replanner = AdaptiveReplanner(self.orchestrator.db_session, redis=self.orchestrator.redis)
            await replanner.on_plan_execution_completed(
                user_id=uuid.UUID(str(user_id)),
                plan_id=uuid.UUID(str(plan.plan_id)),
                feedback=feedback,
            )
        except Exception as e:
            self.logger.warning(f"[ModeWorkflow] Failed to publish feedback: {e}")

    async def _stream_synthesis_response(
        self,
        *,
        chat_mode: str,
        user_message: str,
        execution_result,
        validation_result,
        synthesis_template: str,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        summary = self._format_execution_summary(execution_result, validation_result)
        system_prompt = synthesis_template or self._default_synthesis_prompt(chat_mode)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"用户原始请求:\n{user_message}\n\n"
                    f"执行结果摘要:\n{summary}\n\n"
                    "请基于以上执行结果给出最终回答。"
                ),
            },
        ]

        first_chunk = True
        async for chunk in self.llm_service.stream_chat(messages=messages, model=None, temperature=0.5):
            if not chunk:
                continue
            if first_chunk:
                yield agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.GENERATING,
                        details="正在合成最终结果...",
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    )
                )
                first_chunk = False
            yield agent_service_pb2.ChatResponse(delta=chunk)

    def _format_execution_summary(self, execution_result, validation_result) -> str:
        lines = []
        for sr in execution_result.step_results:
            status = "成功" if sr.tool_result.success else "失败"
            data_text = ""
            if sr.output_data:
                data_text = str(sr.output_data)
            elif sr.tool_result.data:
                data_text = str(sr.tool_result.data)
            elif sr.tool_result.error_message:
                data_text = sr.tool_result.error_message
            lines.append(f"- [{status}] {sr.tool_name}: {data_text}")

        lines.append(
            f"验证结果: status={validation_result.validation_status}, score={validation_result.quality_score:.2f}, "
            f"aborted={validation_result.aborted}"
        )
        if validation_result.issues:
            lines.append("主要问题: " + " | ".join(validation_result.issues[:5]))
        return "\n".join(lines)

    def _default_synthesis_prompt(self, chat_mode: str) -> str:
        prompts = {
            CHAT_MODE_DEEP_ANALYSIS: (
                "你是深度分析综合器。请输出：关键结论、证据链、反方与边界、应用建议。"
            ),
            CHAT_MODE_STUDY_PLAN: (
                "你是学习计划综合器。请输出：目标、里程碑、每周计划、每日执行模板、复盘机制。"
            ),
            CHAT_MODE_ERROR_DIAGNOSIS: (
                "你是错题诊断综合器。请输出：错误类型、根因分析、正确路径、针对性练习、复发预防。"
            ),
        }
        return prompts.get(chat_mode, "你是任务结果综合器。请基于执行结果输出清晰结论。")

    async def _fallback_simple_stream(
        self,
        *,
        message: str,
        chat_mode: str,
        context_data: dict[str, Any],
        extra_notice: str | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        preamble = extra_notice or ""
        system = (
            f"你是 {chat_mode} 模式助手。请提供结构化、可执行的回答。"
            f"\n{preamble}" if preamble else f"你是 {chat_mode} 模式助手。请提供结构化、可执行的回答。"
        )
        history = context_data.get("conversation_context", {}).get("messages", [])
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for msg in history[-6:]:
            content = msg.get("content", "")
            if not content:
                continue
            if msg.get("role") == "assistant":
                messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": "user", "content": content})
        messages.append({"role": "user", "content": message})

        async for chunk in self.llm_service.stream_chat(messages=messages, model=None, temperature=0.6):
            if chunk:
                yield agent_service_pb2.ChatResponse(delta=chunk)

    # -----------------------------------------------------------------
    # Backward-compatible methods (deprecated)
    # -----------------------------------------------------------------
    async def execute_progressive_exploration(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        async for resp in self.execute_mode_workflow(
            chat_mode=CHAT_MODE_DEEP_ANALYSIS,
            message=message,
            user_id=user_id,
            session_id=session_id,
            context_data=context_data,
            stream_callback=stream_callback,
        ):
            yield resp

    async def execute_task_decomposition(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        async for resp in self.execute_mode_workflow(
            chat_mode=CHAT_MODE_STUDY_PLAN,
            message=message,
            user_id=user_id,
            session_id=session_id,
            context_data=context_data,
            stream_callback=stream_callback,
        ):
            yield resp

    async def execute_error_diagnosis(
        self,
        message: str,
        user_id: str,
        session_id: str,
        context_data: dict[str, Any],
        stream_callback,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        async for resp in self.execute_mode_workflow(
            chat_mode=CHAT_MODE_ERROR_DIAGNOSIS,
            message=message,
            user_id=user_id,
            session_id=session_id,
            context_data=context_data,
            stream_callback=stream_callback,
        ):
            yield resp


async def execute_multi_agent_workflow(
    orchestrator: "ChatOrchestrator",
    chat_mode: str,
    message: str,
    user_id: str,
    session_id: str,
    context_data: dict[str, Any],
    stream_callback,
) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
    """Backward-compatible module function."""
    adapter = MultiAgentWorkflowAdapter(orchestrator=orchestrator)
    async for resp in adapter.execute_mode_workflow(
        chat_mode=chat_mode,
        message=message,
        user_id=user_id,
        session_id=session_id,
        context_data=context_data,
        stream_callback=stream_callback,
    ):
        yield resp


__all__ = [
    "CHAT_MODE_STANDARD",
    "CHAT_MODE_DEEP_ANALYSIS",
    "CHAT_MODE_STUDY_PLAN",
    "CHAT_MODE_ERROR_DIAGNOSIS",
    "MultiAgentWorkflowAdapter",
    "execute_multi_agent_workflow",
]
