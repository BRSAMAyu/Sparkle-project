from __future__ import annotations

import asyncio, contextlib, json, time, uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import ACTIVE_SESSIONS, REQUEST_LATENCY, RESPONSE_FALLBACK_GENERATED_TOTAL, SESSION_FEEDBACK_VISIBLE_HINT_TOTAL
from app.core.business_metrics import COLLABORATION_LATENCY
from app.core.task_manager import task_manager
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.agent_scoring import AgentScoringService
from app.orchestration.schemas import ExecutablePlan, RouteDecision
from app.orchestration.session_feedback import SessionFeedbackSignal, apply_session_feedback_visible_prefix
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.ux_envelope import ux_envelope_builder


class ResponseBuilderMixin:
    """Mixin providing response-building and cleanup helpers for the Orchestrator."""

    async def _build_final_response(
        self,
        *,
        final_state: WorkflowState,
        executable_plan: ExecutablePlan | None,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        route_decision: RouteDecision,
        plan_switched: bool,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
    ) -> tuple[agent_service_pb2.ChatResponse, dict[str, Any]]:
        full_response = ""
        for msg in reversed(final_state.messages):
            if msg["role"] == "assistant":
                full_response = msg["content"]
                break
        used_fallback_response = False
        if not full_response or not full_response.strip():
            full_response = self._build_nonempty_fallback_response(final_state=final_state, executable_plan=executable_plan)
            used_fallback_response = True
            RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="standard_empty_final").inc()

        llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
        session_feedback_signal = final_state.context_data.get("session_feedback_signal")
        full_response, session_adaptation_visible = apply_session_feedback_visible_prefix(
            full_response,
            session_feedback_signal,
        )
        parsed_session_signal = SessionFeedbackSignal.from_dict(session_feedback_signal)
        if parsed_session_signal and session_adaptation_visible and parsed_session_signal.applies_adaptation:
            SESSION_FEEDBACK_VISIBLE_HINT_TOTAL.labels(
                signal_type=parsed_session_signal.signal_type,
            ).inc()
        response_metadata = {
            "response_id": response_id,
            "trace_id": trace_id,
            "preference_version": (user_context_payload or {}).get("preference_version", 0),
            "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
            "experiment_cohort": (user_context_payload or {}).get("experiment_cohort", ""),
        }
        if used_fallback_response:
            response_metadata["response_fallback"] = "generated"
        if route_decision and "sprint" in route_decision.reason.lower():
            response_metadata["switch_to_sprint"] = True
        if plan_switched and plan_id:
            response_metadata["plan_switched"] = True
            response_metadata["switched_to_plan_id"] = str(plan_id)
        expert_metadata = final_state.context_data.get("expert_routing_metadata")
        if isinstance(expert_metadata, dict):
            response_metadata.update(expert_metadata)
        agents_involved = []
        if executable_plan and executable_plan.agents_involved:
            agents_involved = [
                str(agent).strip()
                for agent in executable_plan.agents_involved
                if str(agent).strip()
            ]
        if not agents_involved and isinstance(user_context_payload, dict):
            raw_trace = user_context_payload.get("orchestration_trace")
            if isinstance(raw_trace, str) and raw_trace:
                try:
                    raw_trace = json.loads(raw_trace)
                except Exception:
                    raw_trace = None
            if isinstance(raw_trace, dict):
                trace_agents = raw_trace.get("agents")
                if isinstance(trace_agents, list):
                    agents_involved = [
                        str(agent).strip()
                        for agent in trace_agents
                        if str(agent).strip()
                    ]
        if agents_involved:
            response_metadata["agents_involved"] = json.dumps(
                agents_involved,
                ensure_ascii=False,
            )
            if executable_plan and getattr(executable_plan, "collaboration_mode", None):
                response_metadata["collaboration_mode"] = executable_plan.collaboration_mode
            collaboration_narrative = (
                getattr(executable_plan, "collaboration_narrative", None)
                if executable_plan is not None
                else None
            )
            if collaboration_narrative:
                response_metadata["collaboration_narrative"] = str(collaboration_narrative)
            if self.redis:
                try:
                    route_intent = self._extract_route_intent(route_decision.reason)
                    scoring_service = AgentScoringService(self.redis)
                    await scoring_service.bind_response_to_recent_records(
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        agents=agents_involved,
                        intent_type=route_intent,
                    )
                    await scoring_service.store_response_agent_mapping(
                        response_id=response_id,
                        user_id=user_id,
                        session_id=session_id,
                        agents=agents_involved,
                        intent_type=route_intent,
                        workflow_id=workflow_id,
                    )
                except Exception as exc:
                    logger.debug(f"Failed to persist agent response mapping: {exc}")
        selected_experts = final_state.context_data.get("selected_experts")
        if isinstance(selected_experts, list) and selected_experts:
            response_metadata["selected_experts"] = json.dumps(
                [str(expert) for expert in selected_experts],
                ensure_ascii=False,
            )
        if parsed_session_signal is not None:
            response_metadata["session_feedback_signal"] = json.dumps(
                parsed_session_signal.to_dict(),
                ensure_ascii=False,
            )
        if final_state.context_data.get("session_adaptation"):
            response_metadata["session_adaptation"] = json.dumps(
                final_state.context_data["session_adaptation"],
                ensure_ascii=False,
            )
        if final_state.context_data.get("conversation_rhythm"):
            response_metadata["conversation_rhythm"] = json.dumps(
                final_state.context_data["conversation_rhythm"],
                ensure_ascii=False,
            )
        response_metadata["session_adaptation_visible"] = "true" if session_adaptation_visible else "false"
        if settings.ENABLE_CONTEXT_FOCUS_METADATA:
            context_focus = final_state.context_data.get("context_focus")
            if context_focus:
                response_metadata["context_focus"] = json.dumps(context_focus, ensure_ascii=False)
                response_metadata["context_section_weights"] = json.dumps(
                    dict(context_focus.get("section_weights") or {}),
                    ensure_ascii=False,
                )
            briefing_note = str(final_state.context_data.get("context_briefing_note") or "").strip()
            if briefing_note:
                response_metadata["context_briefing_note"] = briefing_note
            focused_memory = final_state.context_data.get("focused_memory")
            if isinstance(focused_memory, dict):
                summary = {
                    "preferences": len(dict(focused_memory.get("preferences") or {})),
                    "goals": len(list(focused_memory.get("active_goals") or [])),
                    "episodic": len(list(focused_memory.get("episodic_memories") or [])),
                }
                response_metadata["focused_memory_summary"] = json.dumps(summary, ensure_ascii=False)
                context_pack_meta = ((focused_memory.get("context_pack") or {}).get("metadata") or {})
                semantic_meta = context_pack_meta.get("semantic_gating")
            if semantic_meta:
                response_metadata["context_semantic_gating"] = json.dumps(semantic_meta, ensure_ascii=False)
        understanding_depth = (user_context_payload or {}).get("understanding_depth") if isinstance(user_context_payload, dict) else None
        if isinstance(understanding_depth, dict):
            response_metadata["understanding_depth"] = json.dumps(understanding_depth, ensure_ascii=False)
        returning_context = (user_context_payload or {}).get("returning_context") if isinstance(user_context_payload, dict) else None
        if isinstance(returning_context, dict):
            response_metadata["returning_after_silence"] = json.dumps(returning_context, ensure_ascii=False)

        execution_validation = await self._validate_plan_execution(
            executable_plan=executable_plan,
            active_db=active_db,
            final_state=final_state,
            user_id=user_id,
            session_id=session_id,
        )
        if execution_validation:
            response_metadata["execution_validation"] = execution_validation

        await self._hydrate_evolution_context(final_state=final_state, user_id=user_id)
        ux_envelope = await ux_envelope_builder.build(
            user_message=self._extract_latest_user_message(final_state.messages),
            full_response=full_response,
            final_state=final_state,
            executable_plan=executable_plan,
            route_decision=route_decision,
            include_references=bool(final_state.context_data.get("include_references")),
            file_ids=list(final_state.context_data.get("file_ids") or []),
            execution_validation=execution_validation,
            conversation_context=final_state.context_data.get("conversation_context"),
            plan_context=final_state.context_data.get("plan_context"),
            user_context_payload=user_context_payload,
        )
        response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))

        await self._persist_assistant_message(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            full_response=full_response,
        )
        await self._record_decision(
            active_db=active_db,
            user_id=user_id,
            user_context_payload=user_context_payload,
            llm_profile_meta=llm_profile_meta,
            full_response=full_response,
        )

        final_response_data = {
            "message": full_response,
            "tool_results": [],
            "metadata": response_metadata,
        }

        # Phase 1-D: Cognitive Feedback Loop — when user views behavior patterns,
        # boost confidence of viewed patterns (positive reinforcement signal).
        if executable_plan and executable_plan.tool_calls:
            prism_viewed = any(tc.name == "get_user_behavior_patterns" for tc in executable_plan.tool_calls)
            if prism_viewed and active_db and user_id:
                try:
                    from app.services.cognitive_service import CognitiveService
                    cognitive_svc = CognitiveService(active_db)
                    patterns = await cognitive_svc.get_user_patterns(uuid.UUID(user_id), min_confidence=0.5)
                    for p in patterns[:5]:
                        new_conf = min(1.0, float(p.confidence_score or 0.5) + 0.03)
                        p.confidence_score = new_conf
                    await active_db.flush()
                except Exception as e:
                    logger.debug(f"Cognitive feedback loop flush skipped: {e}")

        final_response = agent_service_pb2.ChatResponse(
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
        return final_response, final_response_data

    @staticmethod
    def _extract_latest_user_message(messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content") or "")
        return ""

    def _build_nonempty_fallback_response(
        self,
        *,
        final_state: WorkflowState,
        executable_plan: ExecutablePlan | None,
    ) -> str:
        plan_result = final_state.context_data.get("plan_execution_result")
        success_count = 0
        failed_count = 0
        failed_tools: list[str] = []
        if plan_result is not None and hasattr(plan_result, "step_results"):
            for step in getattr(plan_result, "step_results", []) or []:
                tool_result = getattr(step, "tool_result", None)
                tool_name = getattr(step, "tool_name", "unknown_tool")
                if getattr(tool_result, "success", False):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_tools.append(str(tool_name))

        if success_count > 0 or failed_count > 0:
            summary_parts = [f"已完成执行：成功 {success_count} 项"]
            if failed_count > 0:
                summary_parts.append(f"失败 {failed_count} 项")
            detail = "，".join(summary_parts)
            if failed_tools:
                failed_preview = "、".join(failed_tools[:3])
                detail += f"。失败工具：{failed_preview}"
            detail += "。如果你希望，我可以基于当前结果继续细化下一步行动。"
            return detail

        if executable_plan and executable_plan.tool_calls:
            tool_names = [tc.name for tc in executable_plan.tool_calls[:3]]
            tool_list = "、".join(tool_names)
            return f"我已生成并执行任务流程（{tool_list}）。当前结果未形成完整文本答案，你可以让我继续输出详细结论或下一步计划。"

        return "我已经完成本轮处理，但结果文本为空。请告诉我你希望我优先输出：结论摘要、执行细节，或下一步行动计划。"

    async def _cleanup(
        self,
        *,
        lock_acquired: bool,
        lock_renewal_task: asyncio.Task | None,
        lock_renewal_stop: asyncio.Event | None,
        session_id: str,
        request_id: str,
        start_time: float,
        user_id: str,
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ) -> None:
        ACTIVE_SESSIONS.dec()
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(module="orchestration", method="process_stream").observe(latency)
        COLLABORATION_LATENCY.labels(workflow_type="standard_chat").observe(latency)

        if lock_renewal_task and lock_renewal_stop:
            try:
                await self.state_manager.stop_lock_renewal(lock_renewal_task, lock_renewal_stop)
            except Exception as e:
                logger.warning(f"Failed to stop lock renewal: {e}")

        if lock_acquired:
            await self._release_session_lock(session_id, request_id)

        if self.token_tracker and total_prompt_tokens > 0:
            try:
                estimated_cost = await self.token_tracker.estimate_cost(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    model="gpt-4",
                )
                await task_manager.spawn(
                    self.token_tracker.record_usage(
                        user_id=user_id,
                        session_id=session_id,
                        request_id=request_id,
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                        model="gpt-4",
                        cost=estimated_cost,
                    ),
                    task_name="token_usage_record",
                    user_id=str(user_id),
                )
                logger.info(
                    f"Token usage recorded for user {user_id}: "
                    f"{total_prompt_tokens} + {total_completion_tokens} = "
                    f"{total_prompt_tokens + total_completion_tokens} tokens, "
                    f"est. cost: ${estimated_cost:.6f}"
                )
            except Exception as e:
                logger.error(f"Failed to record token usage: {e}")
