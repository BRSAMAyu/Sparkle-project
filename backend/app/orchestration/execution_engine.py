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

from google.protobuf import struct_pb2
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent_persona import build_agent_persona
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.core.business_metrics import (
    EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL,
)
from app.core.metrics import (
    RESPONSE_FALLBACK_GENERATED_TOTAL,
    SESSION_FEEDBACK_VISIBLE_HINT_TOTAL,
    TOKEN_USAGE,
)
from app.core.task_manager import task_manager
from app.gen.agent.v1 import agent_service_pb2
from app.models.execution_intent import ExecutionIntentStatus
from app.models.galaxy import KnowledgeNode
from app.orchestration.agent_memory import AgentMemoryService
from app.orchestration.agent_activity import emit_agent_activity, emit_agent_turn
from app.orchestration.chat_modes import CHAT_MODE_STANDARD
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
from app.services.execution_service import ExecutionService
from app.services.llm_service import llm_service
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService

_LANGGRAPH_PLANNER_TIMEOUT_SECONDS = 10.0
_OPENCLAW_CHAT_CONTROL_EXPLICIT_HINTS = (
    "openclaw",
    "通过 openclaw",
    "用 openclaw",
    "在我的电脑上",
    "在我电脑上",
    "在我的设备上",
    "on my computer",
    "on my device",
)
_OPENCLAW_CHAT_CONTROL_ACTION_HINTS = (
    "打开",
    "运行",
    "执行",
    "检查",
    "查看",
    "搜索",
    "读取",
    "列出",
    "打开一下",
    "帮我打开",
    "帮我运行",
    "帮我执行",
    "帮我检查",
    "帮我查看",
    "帮我搜索",
    "open ",
    "run ",
    "execute ",
    "check ",
    "inspect ",
    "search ",
    "list ",
    "show ",
)
_OPENCLAW_CHAT_CONTROL_DEVICE_HINTS = (
    "电脑",
    "设备",
    "本机",
    "本地",
    "浏览器",
    "网页",
    "网站",
    "终端",
    "命令行",
    "仓库",
    "repo",
    "repository",
    "git",
    "workspace",
    "文件",
    "文件夹",
    "目录",
    "shell",
    "terminal",
    "browser",
)
_OPENCLAW_CHAT_CONTROL_EXPLANATION_HINTS = (
    "什么是",
    "什么意思",
    "解释",
    "介绍",
    "讲讲",
    "为什么",
    "怎么",
    "what is",
    "explain",
    "why ",
    "how ",
)


class ExecutionEngineMixin:
    """Mixin providing execution, planning, and tool-handling methods for ChatOrchestrator."""

    async def _maybe_short_circuit_bridge_tool(
        self,
        *,
        active_tools: list[str],
        user_message: str,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        active_db: AsyncSession | None,
    ) -> list[agent_service_pb2.ChatResponse] | None:
        bridge_tool_name = next(
            (
                tool_name
                for tool_name in ("launch_prediction", "run_quick_simulation", "generate_learning_report")
                if tool_name in active_tools
            ),
            None,
        )
        if bridge_tool_name is None or not str(user_message or "").strip():
            return None

        if bridge_tool_name == "launch_prediction":
            arguments = {
                "topic": user_message,
                "source_chat_session_id": session_id,
            }
        elif bridge_tool_name == "run_quick_simulation":
            arguments = {
                "seed_topic": user_message,
                "source_chat_session_id": session_id,
            }
        else:
            arguments = {
                "section_limit": 4,
                "delivery_mode": "chat_bridge",
                "source_chat_session_id": session_id,
            }

        result = await self.tool_executor.execute_tool_call(
            tool_name=bridge_tool_name,
            arguments=arguments,
            user_id=user_id,
            db_session=active_db,
            tool_call_id=f"bridge_{bridge_tool_name}_{uuid.uuid4().hex[:12]}",
            runtime_context={
                "session_id": session_id,
                "redis_client": getattr(self, "redis", None),
            },
        )
        if not result.success or not isinstance(result.data, dict):
            return None

        full_response = self._bridge_tool_response_text(
            tool_name=bridge_tool_name,
            payload=result.data,
        )
        metadata = self._bridge_tool_response_metadata(
            tool_name=bridge_tool_name,
            payload=result.data,
            response_id=response_id,
            trace_id=trace_id,
            session_id=session_id,
        )

        await self._persist_assistant_message(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            full_response=full_response,
        )
        await self._cache_response(
            session_id,
            request_id,
            {
                "message": full_response,
                "full_text": full_response,
                "tool_results": [result.model_dump()],
                "metadata": metadata,
            },
        )

        now = int(datetime.now().timestamp())
        return [
            agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=now,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    details="正在准备可视化预览",
                    current_agent_name="Sparkle AI",
                ),
            ),
            agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=now,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                metadata={str(k): str(v) for k, v in metadata.items()},
                full_text=full_response,
                finish_reason=agent_service_pb2.STOP,
            ),
        ]

    @staticmethod
    def _bridge_tool_response_text(*, tool_name: str, payload: dict[str, Any]) -> str:
        if tool_name == "launch_prediction":
            topic = str(payload.get("topic") or "当前主题").strip()
            target_name = str(payload.get("target_name") or topic).strip() or topic
            return f"我已经为你准备好“{target_name}”的知识推演预览，点开卡片就能查看路径、风险和采纳入口。"
        if tool_name == "run_quick_simulation":
            topic = str(payload.get("topic") or "当前主题").strip()
            scenario_key = str(payload.get("scenario_key") or "study_group").strip() or "study_group"
            return f"我已经为“{topic}”准备了一个 {scenario_key} 学习仿真预览，点开卡片就能直接进入模拟。"
        preview = payload.get("report_preview") if isinstance(payload.get("report_preview"), dict) else {}
        summary = str((preview or {}).get("summary") or "点开卡片就能查看学习表现、薄弱点和下一步建议。").strip()
        return f"我已经整理出一份最新学习报告，{summary}"

    @staticmethod
    def _bridge_tool_response_metadata(
        *,
        tool_name: str,
        payload: dict[str, Any],
        response_id: str,
        trace_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "response_id": response_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "bridge_execution_mode": "short_circuit",
        }
        if tool_name == "launch_prediction":
            metadata["open_theater"] = "true"
            if payload.get("deep_link"):
                metadata["deep_link"] = str(payload["deep_link"])
            metadata["prediction_preview"] = json.dumps(
                {
                    "prediction_id": str(payload.get("prediction_id") or ""),
                    "topic": str(payload.get("topic") or ""),
                    "target_node_id": str(payload.get("target_node_id") or ""),
                    "target_name": str(payload.get("target_name") or ""),
                    "paths": list(payload.get("paths") or []),
                },
                ensure_ascii=False,
            )
            metadata["bridge_cost_tier"] = "low"
            metadata["bridge_quality_mode"] = "preview"
        elif tool_name == "run_quick_simulation":
            metadata["open_simulation"] = "true"
            if payload.get("deep_link"):
                metadata["simulation_deep_link"] = str(payload["deep_link"])
            metadata["simulation_preview"] = json.dumps(
                {
                    "session_id": str(payload.get("session_id") or ""),
                    "topic": str(payload.get("topic") or ""),
                    "scenario_key": str(payload.get("scenario_key") or ""),
                    "participants": list(payload.get("participants") or []),
                    "round_preview": list(payload.get("round_preview") or []),
                    "insight_summary": str(payload.get("insight_summary") or ""),
                },
                ensure_ascii=False,
            )
            metadata["bridge_cost_tier"] = "low"
            metadata["bridge_quality_mode"] = "preview"
        else:
            metadata["open_report"] = "true"
            if payload.get("deep_link"):
                metadata["report_deep_link"] = str(payload["deep_link"])
            metadata["report_preview"] = json.dumps(
                {
                    "report_id": str(payload.get("report_id") or ""),
                    **(
                        dict(payload.get("report_preview") or {})
                        if isinstance(payload.get("report_preview"), dict)
                        else {}
                    ),
                },
                ensure_ascii=False,
            )
            metadata["bridge_cost_tier"] = "low"
            metadata["bridge_quality_mode"] = str(payload.get("quality_mode") or "instant_preview")
        if payload.get("source_chat_session_id"):
            metadata["source_chat_session_id"] = str(payload["source_chat_session_id"])
        return metadata

    async def _maybe_short_circuit_openclaw_chat_control(
        self,
        *,
        active_tools: list[str],
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        active_db: AsyncSession | None,
    ) -> list[agent_service_pb2.ChatResponse] | None:
        responses = [
            response
            async for response in self._stream_openclaw_chat_control(
                active_tools=active_tools,
                user_message=user_message,
                request_extra_context=request_extra_context,
                user_id=user_id,
                session_id=session_id,
                response_id=response_id,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                active_db=active_db,
            )
        ]
        return responses or None

    async def _stream_openclaw_chat_control(
        self,
        *,
        active_tools: list[str],
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        active_db: AsyncSession | None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        del active_tools
        if active_db is None:
            return

        normalized_message = str(user_message or "").strip()
        if not normalized_message:
            return
        if not self._looks_like_openclaw_chat_control_request(
            message=normalized_message,
            request_extra_context=request_extra_context or {},
        ):
            return

        try:
            user_uuid = uuid.UUID(str(user_id))
        except Exception:
            logger.debug("Skipping OpenClaw chat control short-circuit due to invalid user_id: {}", user_id)
            return

        service = ExecutionService(db=active_db, redis=self.redis)
        queue: asyncio.Queue[agent_service_pb2.ChatResponse | object] = asyncio.Queue()
        sentinel = object()
        live_state: dict[str, Any] = {
            "current_step": "正在连接你的 OpenClaw",
            "recent_output": [],
            "progress_hint": 0.2,
        }

        await queue.put(
            self._build_openclaw_progress_response(
                response_id=response_id,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                live_state=live_state,
            )
        )

        async def stream_sink(event_type: str, payload: dict[str, Any]) -> None:
            response = self._build_openclaw_progress_response(
                response_id=response_id,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                live_state=self._apply_openclaw_progress_event(
                    live_state=live_state,
                    event_type=event_type,
                    payload=payload,
                ),
            )
            await queue.put(response)

        async def run_chat_control() -> None:
            try:
                intent, record = await service.handoff_chat_control(
                    session_id=session_id,
                    user_id=user_uuid,
                    message=normalized_message,
                    request_id=request_id,
                    stream_sink=stream_sink,
                )
                assistant_text, tool_payload = self._build_openclaw_chat_control_payload(
                    message=normalized_message,
                    intent=intent,
                    record=record,
                )
                metadata = {
                    "response_id": response_id,
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "openclaw_chat_control": "true",
                    "openclaw_intent_id": str(intent.id),
                    "openclaw_record_id": str(record.id) if record else "",
                    "openclaw_status": intent.status.value,
                }
                await self._persist_assistant_message(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    full_response=assistant_text,
                )
                await self._cache_response(
                    session_id,
                    request_id,
                    {
                        "message": assistant_text,
                        "full_text": assistant_text,
                        "tool_results": [tool_payload],
                        "metadata": metadata,
                    },
                )
                for response in self._openclaw_chat_control_responses(
                    response_id=response_id,
                    request_id=request_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    prompt_version=prompt_version,
                    metadata=metadata,
                    assistant_text=assistant_text,
                    tool_payload=tool_payload,
                ):
                    await queue.put(response)
            except Exception as exc:
                logger.warning("OpenClaw chat control short-circuit failed: {}", exc)
                fallback = await service.build_manual_fallback(
                    user_id=user_uuid,
                    goal=normalized_message,
                    error_category="connection_unavailable",
                    error_message=str(exc),
                    target_env=service._infer_chat_control_target_env(normalized_message),
                )
                assistant_text, tool_payload = self._build_openclaw_chat_control_error_payload(
                    message=normalized_message,
                    error_message=str(exc),
                    fallback=fallback,
                )
                metadata = {
                    "response_id": response_id,
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "openclaw_chat_control": "true",
                    "openclaw_status": "failed",
                }
                await self._persist_assistant_message(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    full_response=assistant_text,
                )
                await self._cache_response(
                    session_id,
                    request_id,
                    {
                        "message": assistant_text,
                        "full_text": assistant_text,
                        "tool_results": [tool_payload],
                        "metadata": metadata,
                    },
                )
                for response in self._openclaw_chat_control_responses(
                    response_id=response_id,
                    request_id=request_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    prompt_version=prompt_version,
                    metadata=metadata,
                    assistant_text=assistant_text,
                    tool_payload=tool_payload,
                ):
                    await queue.put(response)
            finally:
                await queue.put(sentinel)

        worker = asyncio.create_task(run_chat_control())
        try:
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                yield item
        finally:
            with contextlib.suppress(Exception):
                await worker

    def _looks_like_openclaw_chat_control_request(
        self,
        *,
        message: str,
        request_extra_context: dict[str, Any],
    ) -> bool:
        if bool(request_extra_context.get("openclaw_chat_control")):
            return True

        normalized = str(message or "").strip().lower()
        if not normalized:
            return False
        if any(hint in normalized for hint in _OPENCLAW_CHAT_CONTROL_EXPLICIT_HINTS):
            return True
        if any(hint in normalized for hint in _OPENCLAW_CHAT_CONTROL_EXPLANATION_HINTS):
            return False

        has_action = any(hint in normalized for hint in _OPENCLAW_CHAT_CONTROL_ACTION_HINTS)
        has_device = any(hint in normalized for hint in _OPENCLAW_CHAT_CONTROL_DEVICE_HINTS)
        return has_action and has_device

    def _build_openclaw_chat_control_payload(
        self,
        *,
        message: str,
        intent,
        record,
    ) -> tuple[str, dict[str, Any]]:
        status = intent.status.value if intent and intent.status else "unknown"
        error_message = str(
            (record.error_message if record else None) or (intent.error_message if intent else None) or ""
        ).strip()
        parsed_output = record.parsed_output if record and isinstance(record.parsed_output, dict) else None
        output_text = self._extract_openclaw_output_text(record.raw_response if record else {})
        approval = (
            (record.raw_response or {}).get("approval") if record and isinstance(record.raw_response, dict) else {}
        )
        approval = approval if isinstance(approval, dict) else {}
        recovery = ((intent.policy or {}).get("error_recovery") or {}) if intent else {}
        recovery = recovery if isinstance(recovery, dict) else {}
        result_preview = parsed_output or self._build_openclaw_preview(
            output_text=output_text,
            approval=approval,
            error_message=error_message,
        )
        waiting_approval = intent.status == ExecutionIntentStatus.WAITING_APPROVAL

        if waiting_approval:
            assistant_text = "我已经把这条请求交给你的 OpenClaw 了，当前在等待你确认后继续执行。"
            summary = "OpenClaw 已接手这条请求，确认后会继续在你的设备上执行。"
            next_action = "确认以继续执行，或忽略这次请求"
        elif intent.status in {ExecutionIntentStatus.SUCCEEDED, ExecutionIntentStatus.PARTIAL}:
            assistant_text = "我已经通过你的 OpenClaw 执行了这条请求，结果卡片里可以直接展开查看。"
            summary = self._truncate_openclaw_summary(output_text) or "OpenClaw 已返回结果。"
            next_action = "继续查看结果，或直接发下一条控制指令"
        else:
            manual_only = recovery.get("manual_only") is True
            suggestion = str(recovery.get("suggestion") or "").strip()
            assistant_text = (
                "这次没能直接通过 OpenClaw 完成，但我已经把可继续推进的办法整理好了。"
                if manual_only
                else f"我尝试调用你的 OpenClaw，但这次执行没有成功：{error_message or '请稍后再试。'}"
            )
            summary = suggestion or error_message or "这次执行没有成功完成。"
            next_action = "按手动步骤继续" if manual_only else "补充更明确的指令，或稍后重试"

        tool_result_id = str(record.id) if record else str(intent.id)
        widget_data = {
            "title": "OpenClaw 正等待确认" if waiting_approval else "OpenClaw 执行结果",
            "summary": summary,
            "status": status,
            "tool_result_id": tool_result_id,
            "execution_id": str(intent.id),
            "record_id": str(record.id) if record else None,
            "executor": "openclaw",
            "target_env": intent.target_env.value if intent.target_env else "general",
            "next_action": next_action,
            "error_message": error_message or None,
            "requires_confirmation": waiting_approval,
            "approval_requested": int(record.approval_requested or 0) if record else 0,
            "source_message": message,
            "result_preview": result_preview,
            "impact_summary": "这次结果来自用户自己的 OpenClaw 远程执行链路。",
            "manual_steps": [item for item in list(recovery.get("manual_steps") or []) if isinstance(item, dict)],
            "error_suggestion": (
                {
                    "suggestion": recovery.get("suggestion"),
                    "recommended_action": recovery.get("recommended_action"),
                    "retry_success_rate": recovery.get("retry_success_rate"),
                    "recent_similar_failures": recovery.get("recent_similar_failures"),
                }
                if recovery
                else None
            ),
            "retry_action": recovery.get("retry_action") if isinstance(recovery.get("retry_action"), dict) else None,
        }
        tool_data = {
            "intent_id": str(intent.id),
            "record_id": str(record.id) if record else None,
            "status": status,
            "requires_confirmation": waiting_approval,
            "parsed_output": parsed_output,
            "output_text": output_text,
            "approval": approval or None,
            "error_recovery": recovery or None,
        }
        return assistant_text, {
            "tool_name": "openclaw.chat_control",
            "success": intent.status
            in {
                ExecutionIntentStatus.WAITING_APPROVAL,
                ExecutionIntentStatus.SUCCEEDED,
                ExecutionIntentStatus.PARTIAL,
            },
            "data": tool_data,
            "error_message": error_message,
            "suggestion": next_action,
            "widget_type": "execution_summary",
            "widget_data": widget_data,
            "tool_call_id": tool_result_id,
        }

    def _build_openclaw_chat_control_error_payload(
        self,
        *,
        message: str,
        error_message: str,
        fallback: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        error_id = f"openclaw-error-{uuid.uuid4().hex[:12]}"
        fallback = fallback if isinstance(fallback, dict) else {}
        assistant_text = (
            "我没能直接连上你的 OpenClaw，但我已经把手动执行步骤整理好了。"
            if fallback.get("manual_only") is True
            else f"这条请求更像是 OpenClaw 远程控制，但当前没有执行成功：{error_message}"
        )
        tool_payload = {
            "tool_name": "openclaw.chat_control",
            "success": False,
            "data": {
                "status": "degraded" if fallback.get("manual_only") is True else "failed",
                "requires_confirmation": False,
                "source_message": message,
                "error_recovery": fallback or None,
            },
            "error_message": error_message,
            "suggestion": str(fallback.get("suggestion") or "先检查 OpenClaw 连接状态，再重试这条请求"),
            "widget_type": "execution_summary",
            "widget_data": {
                "title": (
                    "OpenClaw 已切到手动协作" if fallback.get("manual_only") is True else "OpenClaw 远程控制未完成"
                ),
                "summary": str(fallback.get("suggestion") or error_message),
                "status": "degraded" if fallback.get("manual_only") is True else "failed",
                "tool_result_id": error_id,
                "executor": "openclaw",
                "next_action": "按手动步骤继续" if fallback.get("manual_only") is True else "确认连接状态后重试",
                "error_message": error_message,
                "requires_confirmation": False,
                "source_message": message,
                "manual_steps": [item for item in list(fallback.get("manual_steps") or []) if isinstance(item, dict)],
                "error_suggestion": (
                    {
                        "suggestion": fallback.get("suggestion"),
                        "recommended_action": fallback.get("recommended_action"),
                        "retry_success_rate": fallback.get("retry_success_rate"),
                    }
                    if fallback
                    else None
                ),
                "retry_action": (
                    fallback.get("retry_action") if isinstance(fallback.get("retry_action"), dict) else None
                ),
            },
            "tool_call_id": error_id,
        }
        return assistant_text, tool_payload

    def _build_openclaw_progress_response(
        self,
        *,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        live_state: dict[str, Any],
    ) -> agent_service_pb2.ChatResponse:
        metadata = {
            "execution_progress": json.dumps(
                {
                    "current_step": str(live_state.get("current_step") or ""),
                    "recent_output": list(live_state.get("recent_output") or []),
                    "progress_hint": live_state.get("progress_hint"),
                },
                ensure_ascii=False,
            ),
            "openclaw_live": "true",
        }
        return agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            metadata=metadata,
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details=self._format_openclaw_live_details(live_state),
                current_agent_name="Sparkle AI",
            ),
        )

    def _apply_openclaw_progress_event(
        self,
        *,
        live_state: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        next_state = dict(live_state)
        recent_output = list(next_state.get("recent_output") or [])
        message = str(payload.get("message") or "").strip()
        if event_type == "execution_lifecycle":
            next_state["current_step"] = message or next_state.get("current_step") or "OpenClaw 正在处理中"
            next_state["progress_hint"] = payload.get("progress_hint", next_state.get("progress_hint"))
        elif event_type == "execution_tool_call":
            next_state["current_step"] = message or "OpenClaw 正在调用工具"
            next_state["progress_hint"] = payload.get("progress_hint", next_state.get("progress_hint"))
        elif event_type == "execution_delta":
            text = str(payload.get("text") or "").strip()
            if text:
                recent_output.append(text)
            next_state["progress_hint"] = payload.get("progress_hint", next_state.get("progress_hint"))
        elif event_type == "execution_approval":
            next_state["current_step"] = message or "OpenClaw 正在等待确认"
            next_state["progress_hint"] = payload.get("progress_hint", next_state.get("progress_hint"))
        if message and event_type != "execution_delta":
            recent_output.append(message)
        next_state["recent_output"] = recent_output[-4:]
        return next_state

    @staticmethod
    def _format_openclaw_live_details(live_state: dict[str, Any]) -> str:
        current_step = str(live_state.get("current_step") or "").strip()
        recent_output = [str(item).strip() for item in list(live_state.get("recent_output") or []) if str(item).strip()]
        if not recent_output:
            return current_step or "正在连接你的 OpenClaw"
        return "\n".join([current_step or "正在执行中", *recent_output[-3:]])

    def _openclaw_chat_control_responses(
        self,
        *,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        metadata: dict[str, Any],
        assistant_text: str,
        tool_payload: dict[str, Any],
    ) -> list[agent_service_pb2.ChatResponse]:
        now = int(datetime.now().timestamp())
        data_struct = struct_pb2.Struct()
        if isinstance(tool_payload.get("data"), dict):
            data_struct.update(tool_payload["data"])
        widget_struct = struct_pb2.Struct()
        if isinstance(tool_payload.get("widget_data"), dict):
            widget_struct.update(tool_payload["widget_data"])
        return [
            agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=now,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                    details="正在连接用户的 OpenClaw",
                    current_agent_name="Sparkle AI",
                ),
            ),
            agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=now,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                tool_result=agent_service_pb2.ToolResultPayload(
                    tool_name=str(tool_payload.get("tool_name") or "openclaw.chat_control"),
                    success=bool(tool_payload.get("success")),
                    data=data_struct,
                    error_message=str(tool_payload.get("error_message") or ""),
                    suggestion=str(tool_payload.get("suggestion") or ""),
                    widget_type=str(tool_payload.get("widget_type") or "execution_summary"),
                    widget_data=widget_struct,
                    tool_call_id=str(tool_payload.get("tool_call_id") or ""),
                ),
            ),
            agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=now,
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                metadata={str(k): str(v) for k, v in metadata.items()},
                full_text=assistant_text,
                finish_reason=agent_service_pb2.STOP,
            ),
        ]

    @staticmethod
    def _extract_openclaw_output_text(raw_response: dict[str, Any]) -> str:
        if not isinstance(raw_response, dict):
            return ""
        output = raw_response.get("output") or []
        if isinstance(output, str):
            return output.strip()
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            for block in item.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "output_text" and str(block.get("text") or "").strip():
                    parts.append(str(block["text"]).strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _build_openclaw_preview(
        *,
        output_text: str,
        approval: dict[str, Any],
        error_message: str,
    ) -> dict[str, Any]:
        if output_text:
            return {"text": output_text}
        command = str(approval.get("command") or "").strip()
        cwd = str(approval.get("cwd") or "").strip()
        if command or cwd:
            preview = {}
            if command:
                preview["command"] = command
            if cwd:
                preview["cwd"] = cwd
            return preview
        if error_message:
            return {"text": error_message}
        return {"text": "OpenClaw 已接手，但暂时没有返回可展示的文本结果。"}

    @staticmethod
    def _truncate_openclaw_summary(output_text: str, limit: int = 160) -> str:
        normalized = " ".join(str(output_text or "").split()).strip()
        if not normalized:
            return ""
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1].rstrip()}…"

    async def _emit_roundtable_preview(
        self,
        *,
        executable_plan: ExecutablePlan | None,
        user_message: str,
        stream_callback,
        state: WorkflowState,
        active_db: AsyncSession | None = None,
        user_id: str | None = None,
    ) -> None:
        if executable_plan is None or stream_callback is None:
            return
        agent_ids = [str(agent).strip() for agent in list(executable_plan.agents_involved or []) if str(agent).strip()]
        if len(agent_ids) < 2:
            return

        turns: list[dict[str, Any]] = []
        references = self._resolve_roundtable_reference_ids(executable_plan=executable_plan, state=state)
        for index, agent_id in enumerate(agent_ids):
            preview = self._build_agent_turn_preview(
                agent_id=agent_id,
                user_message=user_message,
                executable_plan=executable_plan,
                turn_index=index,
                user_id=user_id,
            )
            await emit_agent_activity(
                stream_callback,
                agent_id=agent_id,
                status="active",
                metadata={
                    "phase": "analysis",
                    "collaboration_mode": executable_plan.collaboration_mode,
                    "turn_index": index,
                },
            )
            turn_payload = await emit_agent_turn(
                stream_callback,
                agent_id=agent_id,
                turn_index=index,
                content=preview,
                turn_type="analysis",
                references=references,
                metadata={
                    "collaboration_mode": executable_plan.collaboration_mode,
                },
            )
            turns.append(turn_payload)
            await emit_agent_activity(
                stream_callback,
                agent_id=agent_id,
                status="completed",
                result_summary=preview,
                metadata={
                    "phase": "analysis",
                    "collaboration_mode": executable_plan.collaboration_mode,
                    "turn_index": index,
                },
            )
        if turns:
            state.context_data["roundtable_turns"] = turns
            if active_db is not None and user_id:
                await self._write_roundtable_graph_updates(
                    active_db=active_db,
                    user_id=user_id,
                    turns=turns,
                    executable_plan=executable_plan,
                    state=state,
                )

    def _build_agent_turn_preview(
        self,
        *,
        agent_id: str,
        user_message: str,
        executable_plan: ExecutablePlan,
        turn_index: int,
        user_id: str | None = None,
    ) -> str:
        topic = str(user_message or "").strip()
        topic = topic[:42] + "..." if len(topic) > 42 else topic
        narrative = str(executable_plan.collaboration_narrative or "").strip()
        resolved_role = self._resolve_agent_role(agent_id)
        profile = agent_profile_registry.get_profile(resolved_role)
        persona = build_agent_persona(
            agent_role=resolved_role,
            user_context={"user_id": user_id or "anonymous"},
            profile=profile,
        )
        style_hint = f"{persona.communication_style}、{persona.teaching_style}"
        if agent_id == "galaxy_guide":
            return f"我会用{style_hint}的方式，先把“{topic}”的知识依赖关系梳理清楚。"
        if agent_id == "deep_analyst":
            return f"我会用{style_hint}的方式，沿着最容易混淆的分歧点拆解“{topic}”，把核心判断依据讲透。"
        if agent_id == "exam_oracle":
            return f"我会用{style_hint}的方式，把“{topic}”放到考试与得分场景里，优先定位最容易失分的环节。"
        if agent_id == "time_tutor":
            return f"我会用{style_hint}的方式，从学习节奏和投入成本看“{topic}”，判断怎样安排更容易真正学会。"
        if agent_id == "error_analyst":
            return f"我会用{style_hint}的方式，先从常见错因逆推“{topic}”，看看哪些误区最值得提前规避。"
        if agent_id == "math_agent":
            return f"我会用{style_hint}的方式，把“{topic}”里的关键公式、推导和计算路径压缩成一条可执行主线。"
        if agent_id == "code_agent":
            return f"我会用{style_hint}的方式，如果“{topic}”需要落到实现层面，先指出最关键的数据结构和步骤约束。"
        if agent_id == "study_buddy":
            return f"我会用{style_hint}的方式，把“{topic}”先翻译成更好吸收的学习语言，确保你能跟得上后面的讨论。"
        if narrative:
            return narrative
        return f"我会用{style_hint}的方式，从自己的专长视角切入“{topic}”，补上这轮协作里最关键的一块。"

    def _resolve_agent_role(self, agent_id: str) -> AgentRole:
        normalized = str(agent_id or "").strip().lower()
        alias_map = {
            "math_expert": AgentRole.MATH_AGENT,
            "code_expert": AgentRole.CODE_AGENT,
            "writing_expert": AgentRole.WRITING_AGENT,
            "science_expert": AgentRole.SCIENCE_AGENT,
            "search_expert": AgentRole.SEARCH_AGENT,
        }
        if normalized in alias_map:
            return alias_map[normalized]
        with contextlib.suppress(ValueError):
            return AgentRole(normalized)
        return AgentRole.GENERATION

    def _resolve_roundtable_reference_ids(
        self,
        *,
        executable_plan: ExecutablePlan,
        state: WorkflowState,
    ) -> list[str]:
        candidates: list[str] = []
        for source in (
            state.context_data.get("plan_context"),
            state.context_data.get("focused_memory"),
            state.context_data.get("conversation_context"),
            getattr(executable_plan, "context", None),
        ):
            self._collect_node_ids_from_payload(source, candidates)
        deduped: list[str] = []
        for item in candidates:
            if item not in deduped:
                deduped.append(item)
        return deduped[:4]

    def _collect_node_ids_from_payload(self, payload: Any, sink: list[str]) -> None:
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key or "").lower()
                if normalized_key in {
                    "node_id",
                    "target_node_id",
                    "source_node_id",
                } and isinstance(value, str):
                    with contextlib.suppress(ValueError):
                        sink.append(str(uuid.UUID(value)))
                elif normalized_key in {
                    "focus_node_ids",
                    "related_node_ids",
                    "source_ids",
                    "references",
                } and isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            with contextlib.suppress(ValueError):
                                sink.append(str(uuid.UUID(item)))
                else:
                    self._collect_node_ids_from_payload(value, sink)
            return
        if isinstance(payload, list):
            for item in payload:
                self._collect_node_ids_from_payload(item, sink)

    async def _write_roundtable_graph_updates(
        self,
        *,
        active_db: AsyncSession,
        user_id: str,
        turns: list[dict[str, Any]],
        executable_plan: ExecutablePlan,
        state: WorkflowState,
    ) -> None:
        user_uuid = uuid.UUID(str(user_id))
        structure = GraphStructureEvolutionService(active_db)
        all_node_ids: list[str] = []
        for turn in turns:
            refs = [str(item) for item in list(turn.get("references") or []) if str(item).strip()]
            for ref in refs:
                with contextlib.suppress(ValueError):
                    normalized = str(uuid.UUID(ref))
                    if normalized not in all_node_ids:
                        all_node_ids.append(normalized)
        if not all_node_ids:
            all_node_ids = self._resolve_roundtable_reference_ids(executable_plan=executable_plan, state=state)

        for node_id in all_node_ids:
            node_uuid = uuid.UUID(node_id)
            with contextlib.suppress(Exception):
                await structure.record_engagement(user_id=user_uuid, node_id=node_uuid, minutes=1)
            with contextlib.suppress(Exception):
                await structure.tag_node_signal(node_uuid, "signal:expert_discussion", active=True)

        relation_candidates: list[tuple[str, str, str]] = []
        for turn in turns:
            refs = [str(item) for item in list(turn.get("references") or []) if str(item).strip()]
            normalized_refs: list[str] = []
            for ref in refs:
                with contextlib.suppress(ValueError):
                    normalized_refs.append(str(uuid.UUID(ref)))
            if len(normalized_refs) >= 2:
                relation_candidates.append(
                    (
                        normalized_refs[0],
                        normalized_refs[1],
                        str(turn.get("content") or ""),
                    )
                )

        for source_id, target_id, text in relation_candidates:
            relation_type = self._infer_roundtable_relation_type(text)
            if not relation_type:
                continue
            with contextlib.suppress(Exception):
                await structure.upsert_relation(
                    source_id=uuid.UUID(source_id),
                    target_id=uuid.UUID(target_id),
                    relation_type=relation_type,
                    default_strength=0.18,
                    created_by="expert_discussion",
                )

    @staticmethod
    def _infer_roundtable_relation_type(text: str) -> str | None:
        content = str(text or "")
        mapping = (
            (("前置", "依赖", "基础"), "prerequisite"),
            (("解释", "说明"), "explains"),
            (("支持", "印证"), "supports"),
            (("对立", "相反", "矛盾"), "contradicts"),
        )
        for keywords, relation_type in mapping:
            if any(keyword in content for keyword in keywords):
                return relation_type
        return None

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

    @staticmethod
    def _attach_quality_report_context(*, state: Any, quality_report: dict[str, Any] | None) -> None:
        quality_report = quality_report if isinstance(quality_report, dict) else {}
        metadata_expectations = quality_report.get("metadata_expectations")
        metadata_expectations = metadata_expectations if isinstance(metadata_expectations, dict) else {}
        semantic_control_compliance = metadata_expectations.get("semantic_control")
        if not isinstance(semantic_control_compliance, dict) or not semantic_control_compliance:
            return
        context_data = getattr(state, "context_data", None)
        if isinstance(context_data, dict):
            context_data["semantic_control_compliance"] = semantic_control_compliance

    async def _get_tools_schema(self, active_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """Get tools from dynamic registry, optionally filtered by request-scoped allowlist."""
        try:
            requested_tools = [
                tool_name.strip() for tool_name in (active_tools or []) if tool_name and tool_name.strip()
            ]
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
    ) -> tuple[TransparencyDataGenerator, typing.Callable]:
        """Prepare transparency tracking, tools schema, and initial status.

        Returns (transparency_generator, emit_transparency_event).
        """

        transparency_enabled = bool(settings.TRANSPARENCY_MODE_ENABLED and settings.TRANSPARENCY_MODE_DEFAULT)
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
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(state=agent_service_pb2.AgentStatus.THINKING)
            )
        )

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
        return [text[idx : idx + chunk_size] for idx in range(0, len(text), chunk_size)]

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
            final_state=WorkflowState(
                messages=conversation_history,
                context_data={
                    "chat_mode": CHAT_MODE_STANDARD,
                    "conversation_context": conversation_context,
                    "include_references": False,
                    "file_ids": [],
                },
            ),
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
        update_responses, _, _, _, _, _, _ = await self._drain_system_updates(user_id)
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
        *,
        state: WorkflowState,
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
            "effective_companion_state": state.context_data.get("effective_companion_state"),
            "relationship_profile": state.context_data.get("relationship_profile"),
            "companion_state_recent_revisions": state.context_data.get("companion_state_recent_revisions"),
            "soul_runtime_context": state.context_data.get("soul_runtime_context"),
            "soul_runtime_debug": state.context_data.get("soul_runtime_debug"),
            "db_session": active_db,
            "prompt_version": prompt_version,
            "workflow_id": workflow_id,
            "session_feedback_signal": session_feedback_signal,
            "session_feedback_instruction": build_session_feedback_instruction(session_feedback_signal),
            "session_adaptation": session_adaptation_context,
            "context_focus": (user_context_payload or {}).get("context_focus"),
            "context_briefing_note": (user_context_payload or {}).get("context_briefing_note"),
            # C-03-FIX: Pass Spine directives to multi-agent adapter
            "spine_response_directive": state.context_data.get("spine_response_directive"),
            "spine_chronicle_summary": state.context_data.get("spine_chronicle_summary"),
            "spine_fatigue_context": state.context_data.get("spine_fatigue_context"),
            # Dual-core routing prompt instruction (structured adjustments text)
            "dual_core_prompt_instruction": state.context_data.get("dual_core_prompt_instruction"),
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
                response.workflow_id = response.workflow_id or workflow_id
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
                    situation_brief = None
                    if isinstance(user_context_payload, dict):
                        context_focus = user_context_payload.get("context_focus")
                        briefing_note = str(user_context_payload.get("context_briefing_note") or "").strip()
                        focused_memory = user_context_payload.get("focused_memory")
                        situation_brief = user_context_payload.get("situation_brief")
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
                        semantic_meta = ((focused_memory.get("context_pack") or {}).get("metadata") or {}).get(
                            "semantic_gating"
                        )
                        if semantic_meta:
                            response_metadata["context_semantic_gating"] = json.dumps(semantic_meta, ensure_ascii=False)
                    if isinstance(situation_brief, dict):
                        response_metadata["situation_brief"] = json.dumps(situation_brief, ensure_ascii=False)
                        summary = str(situation_brief.get("summary") or "").strip()
                        if summary:
                            response_metadata["situation_brief_summary"] = summary
                        decision_context = situation_brief.get("decision_context")
                        if isinstance(decision_context, dict):
                            response_metadata["residual_decision_context"] = json.dumps(
                                decision_context,
                                ensure_ascii=False,
                            )
                    strategy_state = user_context_payload.get("user_strategy_state") if isinstance(user_context_payload, dict) else None
                    if isinstance(strategy_state, dict):
                        response_metadata["user_strategy_state"] = json.dumps(strategy_state, ensure_ascii=False)
                understanding_depth = (
                    (user_context_payload or {}).get("understanding_depth")
                    if isinstance(user_context_payload, dict)
                    else None
                )
                if isinstance(understanding_depth, dict):
                    response_metadata["understanding_depth"] = json.dumps(understanding_depth, ensure_ascii=False)
                returning_context = (
                    (user_context_payload or {}).get("returning_context")
                    if isinstance(user_context_payload, dict)
                    else None
                )
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
        state.context_data.update(
            {
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
            }
        )

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
        use_synthesized_fallback = False

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
            use_synthesized_fallback = True

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
            if isinstance(user_context_payload, dict):
                situation_brief = user_context_payload.get("situation_brief")
                if isinstance(situation_brief, dict):
                    planning_strategy = situation_brief.get("planning_strategy")
                    if isinstance(planning_strategy, dict) and planning_strategy:
                        planning_constraints["planning_strategy"] = planning_strategy

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
                            + ("，并需要热身任务来降低启动成本。" if persona_constraints.require_warmup_task else "。")
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

            if use_synthesized_fallback:
                executable_plan = self.lang_graph_planner.build_fallback_plan(
                    message=user_message,
                    snapshot=snapshot,
                    user_id=user_id,
                    session_id=session_id,
                    rationale=f"LangGraph circuit open, synthesized fallback: {reason}",
                    plan_version=1,
                )
            else:
                try:
                    locale = user_context_payload.get("profile", {}).get("identity", {}).get("language", "en")
                    executable_plan = await asyncio.wait_for(
                        self.lang_graph_planner.plan(
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
                            locale=locale,
                        ),
                        timeout=_LANGGRAPH_PLANNER_TIMEOUT_SECONDS,
                    )
                except TimeoutError:
                    logger.warning(
                        "LangGraph planner timed out after {}s for session {}; using synthesized fallback",
                        _LANGGRAPH_PLANNER_TIMEOUT_SECONDS,
                        session_id,
                    )
                    executable_plan = self.lang_graph_planner.build_fallback_plan(
                        message=user_message,
                        snapshot=snapshot,
                        user_id=user_id,
                        session_id=session_id,
                        rationale=(
                            f"Planner timeout after {_LANGGRAPH_PLANNER_TIMEOUT_SECONDS:.0f}s, " "synthesized fallback"
                        ),
                        plan_version=1,
                    )
                    use_synthesized_fallback = True

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

            rendered_plan_artifact = self.lang_graph_planner.pop_rendered_plan_artifact(session_id)
            if rendered_plan_artifact and isinstance(user_context_payload, dict):
                user_context_payload["rendered_plan_artifact"] = rendered_plan_artifact
                state.context_data["rendered_plan_artifact"] = rendered_plan_artifact

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
                        if not (
                            mode_step.metadata.get("required_agents") or mode_step.metadata.get("preferred_agents")
                        ):
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
                await stream_callback(
                    agent_service_pb2.ChatResponse(delta=f"\n\n⚠️ 服务暂时不可用: {', '.join(preflight['blocked_by'])}")
                )
                await self.langgraph_breaker.on_failure("preflight_blocked")
                return route_decision, executable_plan, snapshot, True

            if executable_plan and route_decision.execution_mode in ["langgraph", "hybrid"]:
                synthesized_fallback = "synthesized fallback" in str(executable_plan.rationale or "").lower()
                if synthesized_fallback:
                    logger.info(
                        "Skipping LLM plan review for synthesized fallback plan {} to keep planning degradations executable",
                        executable_plan.plan_id,
                    )
                    state.context_data["plan_review"] = {
                        "decision": ReviewDecision.APPROVED.value,
                        "confidence": executable_plan.confidence,
                        "alignment_score": executable_plan.confidence,
                        "alignment_summary": "Fallback plan auto-approved to preserve end-to-end execution.",
                        "reasoning_source": "rule_skip_synthesized_fallback",
                        "plan_id": executable_plan.plan_id,
                    }
                else:
                    review_started_at = time.perf_counter()
                    review_result = await plan_review_service.review_plan(
                        plan=executable_plan,
                        user_message=user_message,
                        user_context={
                            **(user_context_payload or {}),
                            "plan_context": plan_context or (user_context_payload or {}).get("plan_context"),
                            "mode_strategy": state.context_data.get("mode_strategy"),
                            "rendered_plan_artifact": state.context_data.get("rendered_plan_artifact"),
                        },
                    )
                    if orchestration_trace is not None:
                        alignment_score = review_result.alignment_score
                        decision_label = str(review_result.decision or "unknown")
                        alignment_text = (
                            f"{alignment_score:.2f}" if isinstance(alignment_score, (int, float)) else "未知"
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
                        normalized_plan_id = uuid.UUID(str(plan_id))
                        await feedback_service.append_review_feedback(
                            user_id=uuid.UUID(user_id),
                            plan_id=normalized_plan_id,
                            review_result=review_result,
                            user_decision=None,
                        )
                        review_feedback_entry = review_result.review_feedback_entry or {}
                        if review_feedback_entry:
                            plan_state_service = PlanStateService(active_db, self.redis)
                            plan_state = await plan_state_service.get_plan_state(
                                uuid.UUID(user_id),
                                normalized_plan_id,
                            )
                            existing_review_log = []
                            if plan_state and isinstance(plan_state.facts, dict):
                                raw_log = plan_state.facts.get("review_feedback_log")
                                if isinstance(raw_log, list):
                                    existing_review_log = [item for item in raw_log if isinstance(item, dict)]
                            existing_review_log.append(review_feedback_entry)
                            await plan_state_service.upsert_plan_state(
                                user_id=uuid.UUID(user_id),
                                plan_id=normalized_plan_id,
                                patch={
                                    "feedback_log": review_feedback_entry,
                                    "facts": {
                                        "review_feedback_log": existing_review_log[-10:],
                                    },
                                },
                            )
                        logger.info(f"Review feedback written for plan {plan_id}")

                    quality_report = review_result.quality_report or {}
                    self._attach_quality_report_context(state=state, quality_report=quality_report)
                    quality_decision = str(quality_report.get("decision") or "").strip()
                    if quality_decision == "ask_more":
                        situation_brief = (user_context_payload or {}).get("situation_brief")
                        decision_context = situation_brief.get("decision_context") if isinstance(situation_brief, dict) else {}
                        clarification_questions = [
                            str(item).strip()
                            for item in (decision_context.get("strategic_clarification_questions") or [])
                            if str(item).strip()
                        ] if isinstance(decision_context, dict) else []
                        question = clarification_questions[0] if clarification_questions else "我还缺哪个关键信息，才能把计划做得更靠谱？"
                        clarification_delta = (
                            "\n\n⚠️ 这轮我先不把计划当成强计划发出去。\n\n"
                            f"- 我需要先确认：{question}\n\n"
                            "你告诉我这个信息后，我会按同一目标继续收紧并重做计划。"
                        )
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                delta=clarification_delta,
                                metadata={
                                    "requires_clarification": "true",
                                    "clarification_source": "phase_b_quality_gate",
                                    "review_decision": review_result.decision,
                                    "quality_decision": quality_decision,
                                    "review_id": review_result.review_id,
                                    "plan_id": review_result.plan_id,
                                },
                            )
                        )
                        state.context_data["plan_review"] = review_result.to_dict()
                        logger.info(
                            "Plan %s bounced to clarification by Phase B quality gate",
                            executable_plan.plan_id,
                        )
                        return route_decision, executable_plan, snapshot, True

                    review_requires_user_action = review_result.decision in [
                        ReviewDecision.REJECTED.value,
                        ReviewDecision.REQUIRES_CONFIRMATION.value,
                        ReviewDecision.NEEDS_MODIFICATION.value,
                    ]
                    planning_keywords = (
                        "计划",
                        "学习计划",
                        "任务卡",
                        "制定",
                        "安排",
                        "路径",
                        "复习",
                    )
                    route_reason_text = str(getattr(route_decision, "reason", "") or "").lower()
                    should_force_minimal_execution = (
                        review_requires_user_action
                        and len(executable_plan.tool_calls) > 2
                        and (
                            "plan" in route_reason_text
                            or any(keyword in str(user_message or "") for keyword in planning_keywords)
                        )
                    )
                    if should_force_minimal_execution:
                        logger.warning(
                            "Plan {} review={} for planning request; degrading to synthesized executable fallback",
                            executable_plan.plan_id,
                            review_result.decision,
                        )
                        executable_plan = self.lang_graph_planner.build_fallback_plan(
                            message=user_message,
                            snapshot=snapshot,
                            user_id=user_id,
                            session_id=session_id,
                            rationale=(
                                "Review-gated complex plan degraded to synthesized fallback "
                                f"after decision={review_result.decision}"
                            ),
                            plan_version=1,
                        )
                        state.context_data["plan_review"] = {
                            "decision": ReviewDecision.APPROVED.value,
                            "confidence": executable_plan.confidence,
                            "alignment_score": executable_plan.confidence,
                            "alignment_summary": (
                                "复杂规划已自动降级为可直接执行的最小计划链，" "以确保聊天内能稳定产出计划卡与任务卡。"
                            ),
                            "reasoning_source": "review_degraded_to_synthesized_fallback",
                            "plan_id": executable_plan.plan_id,
                            "original_review_decision": review_result.decision,
                            "original_review_id": review_result.review_id,
                        }

                    if review_requires_user_action and not should_force_minimal_execution:
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
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                delta=review_delta,
                                metadata=review_metadata,
                            )
                        )
                        state.context_data["plan_review"] = review_result.to_dict()
                        state.context_data["pending_review_action_id"] = action_id
                        logger.info(
                            f"Plan {executable_plan.plan_id} requires user review: "
                            f"{review_result.decision} (action_id={action_id})"
                        )
                        return route_decision, executable_plan, snapshot, True

                    state.context_data["plan_review"] = review_result.to_dict()
                    logger.info(
                        f"Plan {executable_plan.plan_id} auto-approved: " f"confidence={review_result.confidence}"
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
            await self._emit_roundtable_preview(
                executable_plan=executable_plan,
                user_message=user_message,
                stream_callback=stream_callback,
                state=state,
                active_db=active_db,
                user_id=user_id,
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
            await stream_callback(agent_service_pb2.ChatResponse(delta=f"\n\n⚠️ 规划失败，使用直接模式: {str(e)}"))
            route_decision.execution_mode = "direct"
            return route_decision, executable_plan, snapshot, False
