"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Multi-agent mode workflow adapter.

This module upgrades non-standard chat modes from prompt-only behavior to
full planning/execution workflows while keeping backward-compatible entrypoints.
"""

from __future__ import annotations


import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.core.agent_profiles import AgentRole, TaskType
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
        result_holder: dict[str, Any] | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        result_holder = result_holder if result_holder is not None else {}
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
        result_holder["collaboration_mode"] = plan.collaboration_mode
        result_holder["agents_involved"] = list(plan.agents_involved or [])
        result_holder["tool_calls_count"] = len(plan.tool_calls or [])

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
            db_session=context_data.get("db_session"),
        )

        db_session = context_data.get("db_session")
        validation_result = await self._validate_plan(
            plan=plan,
            execution_result=execution_result,
            user_id=user_id,
            db_session=db_session,
        )
        summary_text = self._format_execution_summary(execution_result, validation_result)
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
        )
        synthesis_guidance = synthesis_template or self._default_synthesis_prompt(chat_mode)
        validation_issues = getattr(validation_result, "issues", None) or []
        validation_summary = (
            f"validation_status={validation_result.validation_status}, "
            f"quality_score={validation_result.quality_score:.2f}, "
            f"aborted={validation_result.aborted}"
        )
        answer_experts = context_data.get("answer_experts")
        answer_expert_instruction = ""
        if isinstance(answer_experts, list) and answer_experts:
            answer_expert_instruction = (
                "\n4. 最终综合时优先吸收以下专家视角并明确其贡献："
                + "、".join(str(item) for item in answer_experts if str(item).strip())
            )
        if validation_issues:
            validation_summary += "\nissues=" + " | ".join(str(issue) for issue in validation_issues[:5])

        system_prompt = (
            f"{base_system_prompt}\n\n"
            "## 多Agent综合约束\n"
            f"{synthesis_guidance}\n\n"
            "请同时参考以下要点：\n"
            "1. 最终回答必须以已执行完成的工具结果为事实基础。\n"
            "2. 保留用户画像、历史上下文、当前计划上下文的一致性。\n"
            "3. 如果执行结果与用户期待有偏差，要明确指出边界与下一步。"
            f"{answer_expert_instruction}\n\n"
            "## 已验证的执行结果摘要\n"
            f"{summary}\n\n"
            "## 执行质量验证\n"
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
                        details="正在合成最终结果...",
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    )
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
                        details="正在合成最终结果...",
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    )
                )
            fallback_text = (
                "已完成多Agent执行，以下是结构化摘要：\n"
                f"{summary}\n\n"
                "如需我继续输出完整报告，请告诉我你关注的重点。"
            )
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
        )
        system = (
            f"{base_prompt}\n\n"
            f"## 模式回退说明\n你当前处于 {chat_mode} 模式，但本轮未形成可执行计划。"
        )
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
    orchestrator: "ChatOrchestrator",
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
