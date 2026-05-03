"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Multi-agent mode workflow adapter.

This module upgrades non-standard chat modes from prompt-only behavior to
full planning/execution workflows while keeping backward-compatible entrypoints.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.core.agent_profiles import AgentRole, TaskType
from app.core.i18n import I18n
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_STANDARD,
    CHAT_MODE_STUDY_PLAN,
)
from app.orchestration.mode_workflow_config import get_workflow_config
from app.orchestration.prompts import build_system_prompt
from app.orchestration.schemas import StateSnapshot
from app.orchestration.step_feedback_collector import StepFeedbackCollector
from app.services.llm_service import get_configured_llm_service, llm_service
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator

if TYPE_CHECKING:
    from app.orchestration.orchestrator import ChatOrchestrator


class MultiAgentWorkflowAdapter:
    """Mode workflow adapter that reuses planner/executor/validator pipeline."""

    def __init__(self, orchestrator: ChatOrchestrator):
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
        result_holder: dict[str, Any] | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        result_holder = result_holder if result_holder is not None else {}
        config = get_workflow_config(chat_mode)
        user_context = context_data.get("user_context") or {}
        locale = user_context.get("language", "en")

        if not config:
            async for chunk in self._fallback_simple_stream(
                message=message,
                chat_mode=chat_mode,
                context_data=context_data,
                locale=locale,
            ):
                yield chunk
            return

        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details=I18n.t("workflow.analyzing", locale=locale),
                active_agent=agent_service_pb2.ORCHESTRATOR,
            )
        )

        snapshot = StateSnapshot(
            user_id=user_id,
            session_id=session_id,
            context_versions={"tasks": "v0"},
        )
        try:
            plan = await asyncio.wait_for(
                self.orchestrator.lang_graph_planner.plan(
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
                    locale=locale,
                ),
                timeout=10.0,
            )
        except TimeoutError:
            logger.warning(
                "LangGraph planner timed out in multi-agent adapter for session {}; using fallback",
                session_id,
            )
            plan = self.orchestrator.lang_graph_planner.build_fallback_plan(
                message=message,
                snapshot=snapshot,
                user_id=user_id,
                session_id=session_id,
                rationale="Planner timeout in multi-agent adapter, synthesized fallback",
            )

        plan = self._apply_tool_policy(plan, config, context_data)
        result_holder["collaboration_mode"] = plan.collaboration_mode
        result_holder["agents_involved"] = list(plan.agents_involved or [])
        result_holder["tool_calls_count"] = len(plan.tool_calls or [])

        if not plan.tool_calls:
            async for chunk in self._fallback_simple_stream(
                message=message,
                chat_mode=chat_mode,
                context_data=context_data,
                extra_notice=I18n.t("workflow.fallback_notice", locale=locale),
                locale=locale,
            ):
                yield chunk
            yield agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP)
            return

        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details=I18n.t("workflow.executing", locale=locale, count=len(plan.tool_calls)),
                active_agent=agent_service_pb2.ORCHESTRATOR,
            )
        )

        execution_result = await self.orchestrator.tool_executor.execute_plan(
            plan=plan,
            user_id=user_id,
            db_session=context_data.get("db_session"),
        )

        db_session = context_data.get("db_session")
        validation_result = await self._validate_plan(
            plan=plan,
            execution_result=execution_result,
            user_id=user_id,
            db_session=db_session,
        )
        summary_text = self._format_execution_summary(execution_result, validation_result, locale=locale)
        result_holder["execution_summary"] = summary_text
        await self._publish_feedback(
            plan=plan,
            execution_result=execution_result,
            validation_result=validation_result,
            user_id=user_id,
            session_id=session_id,
            db_session=db_session,
        )

        async for chunk in self._stream_synthesis_response(
            chat_mode=chat_mode,
            user_message=message,
            execution_result=execution_result,
            validation_result=validation_result,
            execution_summary=summary_text,
            synthesis_template=config.synthesis_template,
            context_data=context_data,
            locale=locale,
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

    async def _validate_plan(self, plan, execution_result, user_id: str, db_session=None):
        record_service = None
        if db_session is not None:
            record_service = PlanExecutionRecordService(db_session)
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
        db_session=None,
    ) -> None:
        if db_session is None:
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

            replanner = AdaptiveReplanner(db_session, redis=self.orchestrator.redis)
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
        execution_summary: str,
        synthesis_template: str,
        context_data: dict[str, Any],
        locale: str = "en",
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        summary = execution_summary
        synthesis_role = self._resolve_synthesis_agent_role(chat_mode)
        synthesis_task_type = self._resolve_synthesis_task_type(chat_mode)
        synthesis_llm = await self._resolve_synthesis_llm(synthesis_role, synthesis_task_type)
        prompt_version = str(context_data.get("prompt_version") or "v1")
        conversation_context = context_data.get("conversation_context")
        if not isinstance(conversation_context, dict):
            conversation_context = {"messages": []}
        user_context = context_data.get("user_context")
        if not isinstance(user_context, dict):
            user_context = {}
        plan_context = context_data.get("plan_context")
        if not isinstance(plan_context, dict):
            plan_context = None

        base_system_prompt = build_system_prompt(
            user_context=user_context,
            conversation_history=conversation_context,
            prompt_version=prompt_version,
            agent_role=synthesis_role,
            plan_context=plan_context,
            session_feedback_instruction=str(context_data.get("session_feedback_instruction") or ""),
            dual_core_instruction=str(context_data.get("dual_core_prompt_instruction") or ""),
            context_focus=context_data.get("context_focus") or user_context.get("context_focus"),
            context_briefing_note=str(
                context_data.get("context_briefing_note") or user_context.get("context_briefing_note") or ""
            ),
            chat_mode=chat_mode,
            spine_response_directive=context_data.get("spine_response_directive"),
            spine_chronicle_summary=context_data.get("spine_chronicle_summary"),
            spine_fatigue_context=context_data.get("spine_fatigue_context"),
        )
        document_context = str(
            context_data.get("document_context") or user_context.get("document_context") or ""
        ).strip()
        if document_context:
            base_system_prompt += f"\n\n## Retrieved Documents\n{document_context}"
        synthesis_guidance = synthesis_template or self._default_synthesis_prompt(chat_mode, locale=locale)
        validation_issues = getattr(validation_result, "issues", None) or []
        validation_summary = (
            f"validation_status={validation_result.validation_status}, "
            f"quality_score={validation_result.quality_score:.2f}, "
            f"aborted={validation_result.aborted}"
        )
        answer_experts = context_data.get("answer_experts")
        answer_expert_instruction = ""
        if isinstance(answer_experts, list) and answer_experts:
            experts_text = "、".join(str(item) for item in answer_experts if str(item).strip())
            answer_expert_instruction = "\n" + I18n.t("synthesis.expert_contribution", locale=locale, experts=experts_text)

        if validation_issues:
            validation_summary += "\nissues=" + " | ".join(str(issue) for issue in validation_issues[:5])

        system_prompt = (
            f"{base_system_prompt}\n\n"
            f"{I18n.t('synthesis.multi_agent_constraints', locale=locale)}\n"
            f"{synthesis_guidance}\n\n"
            f"{I18n.t('synthesis.refer_to_points', locale=locale)}\n"
            f"{I18n.t('synthesis.fact_based', locale=locale)}\n"
            f"{I18n.t('synthesis.consistency', locale=locale)}\n"
            f"{I18n.t('synthesis.deviation', locale=locale)}"
            f"{answer_expert_instruction}\n\n"
            f"{I18n.t('synthesis.executed_results', locale=locale)}\n"
            f"{summary}\n\n"
            f"{I18n.t('synthesis.execution_quality', locale=locale)}\n"
            f"{validation_summary}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in self._recent_conversation_messages(conversation_context):
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        first_chunk = True
        emitted_content = False
        selection_getter = getattr(synthesis_llm, "get_current_selection", None)
        selection = selection_getter() if callable(selection_getter) else None
        model_name = selection.config.model_name if selection else getattr(synthesis_llm, "default_model", "")
        async for chunk in synthesis_llm.stream_chat(messages=messages, model=None, temperature=0.5):
            if not chunk:
                continue
            if first_chunk:
                yield agent_service_pb2.ChatResponse(
                    metadata={
                        "synthesis_agent_role": str(synthesis_role.value),
                        "synthesis_model": model_name,
                    },
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.GENERATING,
                        details=I18n.t("workflow.synthesizing", locale=locale),
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    ),
                )
                first_chunk = False
            emitted_content = True
            yield agent_service_pb2.ChatResponse(delta=chunk)
        if not emitted_content:
            if first_chunk:
                yield agent_service_pb2.ChatResponse(
                    metadata={
                        "synthesis_agent_role": str(synthesis_role.value),
                        "synthesis_model": model_name,
                    },
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.GENERATING,
                        details=I18n.t("workflow.synthesizing", locale=locale),
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    ),
                )
            fallback_text = I18n.t("workflow.fallback_summary", locale=locale, summary=summary)
            yield agent_service_pb2.ChatResponse(delta=fallback_text)

    @staticmethod
    def _recent_conversation_messages(conversation_context: dict[str, Any], limit: int = 6) -> list[dict[str, str]]:
        messages = conversation_context.get("messages", [])
        if not isinstance(messages, list):
            return []

        normalized_messages: list[dict[str, str]] = []
        for msg in messages[-limit:]:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "")).strip().lower()
            if role not in {"user", "assistant", "system"}:
                continue
            content = str(msg.get("content", "") or "").strip()
            if not content:
                continue
            normalized_messages.append({"role": role, "content": content})
        return normalized_messages

    @staticmethod
    def _resolve_synthesis_agent_role(chat_mode: str) -> AgentRole:
        mapping = {
            CHAT_MODE_DEEP_ANALYSIS: AgentRole.DEEP_ANALYST,
            CHAT_MODE_STUDY_PLAN: AgentRole.STUDY_PLANNER,
            CHAT_MODE_ERROR_DIAGNOSIS: AgentRole.ERROR_ANALYST,
        }
        return mapping.get(chat_mode, AgentRole.ORCHESTRATOR)

    @staticmethod
    def _resolve_synthesis_task_type(chat_mode: str) -> TaskType:
        mapping = {
            CHAT_MODE_DEEP_ANALYSIS: TaskType.DEEP_REASONING,
            CHAT_MODE_STUDY_PLAN: TaskType.TASK_DECOMPOSITION,
            CHAT_MODE_ERROR_DIAGNOSIS: TaskType.ERROR_DIAGNOSIS,
        }
        return mapping.get(chat_mode, TaskType.COLLABORATION)

    async def _resolve_synthesis_llm(self, agent_role: AgentRole, task_type: TaskType):
        if self.llm_service is not llm_service:
            return self.llm_service
        return await get_configured_llm_service(agent_role, task_type)

    def _format_execution_summary(self, execution_result, validation_result, locale: str = "en") -> str:
        lines = []
        for sr in execution_result.step_results:
            success_text = "Success" if locale == "en" else "成功"
            fail_text = "Failure" if locale == "en" else "失败"
            status = success_text if sr.tool_result.success else fail_text
            data_text = ""
            if sr.output_data:
                data_text = str(sr.output_data)
            elif sr.tool_result.data:
                data_text = str(sr.tool_result.data)
            elif sr.tool_result.error_message:
                data_text = sr.tool_result.error_message
            lines.append(f"- [{status}] {sr.tool_name}: {data_text}")

        lines.append(
            I18n.t(
                "workflow.validation_status",
                locale=locale,
                status=validation_result.validation_status,
                score=f"{validation_result.quality_score:.2f}",
                aborted=validation_result.aborted,
            )
        )
        if validation_result.issues:
            issues_text = " | ".join(validation_result.issues[:5])
            lines.append(I18n.t("workflow.main_issues", locale=locale, issues=issues_text))
        return "\n".join(lines)

    def _default_synthesis_prompt(self, chat_mode: str, locale: str = "en") -> str:
        prompts = {
            CHAT_MODE_DEEP_ANALYSIS: I18n.t("synthesis.deep_analysis", locale=locale),
            CHAT_MODE_STUDY_PLAN: I18n.t("synthesis.study_plan", locale=locale),
            CHAT_MODE_ERROR_DIAGNOSIS: I18n.t("synthesis.error_diagnosis", locale=locale),
        }
        return prompts.get(chat_mode, I18n.t("synthesis.default", locale=locale))

    async def _fallback_simple_stream(
        self,
        *,
        message: str,
        chat_mode: str,
        context_data: dict[str, Any],
        extra_notice: str | None = None,
        locale: str = "en",
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        preamble = extra_notice or ""
        synthesis_role = self._resolve_synthesis_agent_role(chat_mode)
        synthesis_task_type = self._resolve_synthesis_task_type(chat_mode)
        synthesis_llm = await self._resolve_synthesis_llm(synthesis_role, synthesis_task_type)
        conversation_context = context_data.get("conversation_context")
        if not isinstance(conversation_context, dict):
            conversation_context = {"messages": []}
        user_context = context_data.get("user_context")
        if not isinstance(user_context, dict):
            user_context = {}
        plan_context = context_data.get("plan_context")
        if not isinstance(plan_context, dict):
            plan_context = None

        base_prompt = build_system_prompt(
            user_context=user_context,
            conversation_history=conversation_context,
            prompt_version=str(context_data.get("prompt_version") or "v1"),
            agent_role=synthesis_role,
            plan_context=plan_context,
            session_feedback_instruction=str(context_data.get("session_feedback_instruction") or ""),
            dual_core_instruction=str(context_data.get("dual_core_prompt_instruction") or ""),
            context_focus=context_data.get("context_focus") or user_context.get("context_focus"),
            context_briefing_note=str(
                context_data.get("context_briefing_note") or user_context.get("context_briefing_note") or ""
            ),
            chat_mode=chat_mode,
            spine_response_directive=context_data.get("spine_response_directive"),
            spine_chronicle_summary=context_data.get("spine_chronicle_summary"),
            spine_fatigue_context=context_data.get("spine_fatigue_context"),
        )
        document_context = str(
            context_data.get("document_context") or user_context.get("document_context") or ""
        ).strip()
        if document_context:
            base_prompt += f"\n\n## Retrieved Documents\n{document_context}"

        mode_fallback_header = "## Mode Fallback Explanation" if locale == "en" else "## 模式回退说明"
        mode_fallback_text = (
            f"You are currently in {chat_mode} mode, but no executable plan was formed this round."
            if locale == "en"
            else f"你当前处于 {chat_mode} 模式，但本轮未形成可执行计划。"
        )

        system = f"{base_prompt}\n\n{mode_fallback_header}\n{mode_fallback_text}"
        if preamble:
            system += f"\n{preamble}"

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        messages.extend(self._recent_conversation_messages(conversation_context))
        messages.append({"role": "user", "content": message})

        async for chunk in synthesis_llm.stream_chat(messages=messages, model=None, temperature=0.6):
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
    orchestrator: ChatOrchestrator,
    chat_mode: str,
    message: str,
    user_id: str,
    session_id: str,
    context_data: dict[str, Any],
    stream_callback,
    result_holder: dict[str, Any] | None = None,
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
        result_holder=result_holder,
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
