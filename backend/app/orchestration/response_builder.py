"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio, contextlib, json, time, uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import (
    ACTIVE_SESSIONS,
    AI_RESPONSE_TOTAL_DURATION,
    REQUEST_LATENCY,
    RESPONSE_FALLBACK_GENERATED_TOTAL,
    SESSION_FEEDBACK_VISIBLE_HINT_TOTAL,
)
from app.core.business_metrics import COLLABORATION_LATENCY
from app.core.task_manager import task_manager
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.agent_scoring import AgentScoringService
from app.orchestration.schemas import ExecutablePlan, RouteDecision
from app.orchestration.session_feedback import SessionFeedbackSignal, apply_session_feedback_visible_prefix
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.orchestration.utilization_metrics import build_stage9_utilization_metrics
from app.orchestration.ux_envelope import ux_envelope_builder


class ResponseBuilderMixin:
    """Mixin providing response-building and cleanup helpers for the Orchestrator."""

    @staticmethod
    def _capability_selection_metadata(context_data: dict[str, Any]) -> dict[str, str]:
        situation_brief = context_data.get("situation_brief")
        capability_selection_report = context_data.get("capability_selection_report")
        if not isinstance(capability_selection_report, dict) and isinstance(situation_brief, dict):
            capability_selection_report = situation_brief.get("capability_selection")
        if not isinstance(capability_selection_report, dict):
            return {}

        metadata = {
            "capability_selection_report": json.dumps(capability_selection_report, ensure_ascii=False),
        }
        summary_payload = capability_selection_report.get("summary")
        if isinstance(summary_payload, dict) and summary_payload:
            metadata["capability_selection_summary"] = json.dumps(summary_payload, ensure_ascii=False)
        why_this_path = str(
            context_data.get("why_this_path")
            or capability_selection_report.get("why_this_path")
            or ""
        ).strip()
        if why_this_path:
            metadata["why_this_path"] = why_this_path
        return metadata

    @staticmethod
    def _semantic_control_trace_metadata(context_data: dict[str, Any]) -> dict[str, str]:
        situation_brief = context_data.get("situation_brief")
        if not isinstance(situation_brief, dict):
            return {}
        semantic_control = situation_brief.get("semantic_control")
        if not isinstance(semantic_control, dict) or not semantic_control:
            return {}

        trace_payload = {
            "selected_terms": list(semantic_control.get("selected_terms") or []),
            "rendered_doctrine_summary": dict(semantic_control.get("rendered_doctrine_summary") or {}),
            "response_contract": dict(semantic_control.get("response_contract") or {}),
            "compliance_expectations": dict(semantic_control.get("compliance_expectations") or {}),
        }
        observed_payload = ResponseBuilderMixin._semantic_control_observed_payload(context_data)
        if observed_payload:
            trace_payload.update(observed_payload)
        return {
            "semantic_control_trace": json.dumps(trace_payload, ensure_ascii=False),
        }

    @staticmethod
    def _semantic_control_observed_payload(context_data: dict[str, Any]) -> dict[str, Any]:
        compliance = context_data.get("semantic_control_compliance")
        if not isinstance(compliance, dict):
            return {}
        checks = compliance.get("checks")
        if not isinstance(checks, dict) or not checks:
            return {}
        return {
            "observed_compliance_flags": dict(checks),
            "observed_compliance_source": "plan_quality_gate",
        }

    def _extract_response_outcome_stats(self, final_state: WorkflowState | None) -> dict[str, int]:
        if final_state is None:
            return {"task_count": 0, "plan_count": 0, "execution_count": 0}

        seen_entity_keys: set[str] = set()
        task_count = 0
        plan_count = 0
        execution_count = 0

        def visit(value: Any) -> None:
            nonlocal task_count, plan_count, execution_count
            if isinstance(value, dict):
                if "entity_card" in value and isinstance(value["entity_card"], dict):
                    visit(value["entity_card"])
                entity_type = str(value.get("entity_type") or "").strip().lower()
                entity_id = str(value.get("entity_id") or "").strip()
                schema_version = str(value.get("schema_version") or "").strip()
                if entity_type and schema_version:
                    entity_key = f"{entity_type}:{entity_id or id(value)}"
                    if entity_key not in seen_entity_keys:
                        seen_entity_keys.add(entity_key)
                        if entity_type == "task":
                            task_count += 1
                        elif entity_type == "plan":
                            plan_count += 1
                        if value.get("primary_action") or value.get("secondary_actions"):
                            execution_count += 1
                for nested in value.values():
                    visit(nested)
                return
            if isinstance(value, list):
                for item in value:
                    visit(item)

        visit(final_state.messages)
        visit(final_state.context_data)
        return {
            "task_count": task_count,
            "plan_count": plan_count,
            "execution_count": execution_count,
        }

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
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ) -> tuple[agent_service_pb2.ChatResponse, dict[str, Any]]:
        full_response = ""
        for msg in reversed(final_state.messages):
            if msg["role"] == "assistant":
                full_response = msg["content"]
                break
        used_fallback_response = False
        if not full_response or not full_response.strip():
            full_response = self._build_nonempty_fallback_response(
                final_state=final_state, executable_plan=executable_plan
            )
            used_fallback_response = True
            RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="standard_empty_final").inc()

        llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
        run_ledger = final_state.context_data.get("run_ledger")
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
            "session_id": session_id,  # Include session_id for conversation continuity
            "preference_version": (user_context_payload or {}).get("preference_version", 0),
            "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
            "experiment_cohort": (user_context_payload or {}).get("experiment_cohort", ""),
        }
        generation_model_key = str(
            final_state.context_data.get("generation_model_key")
            or final_state.context_data.get("model_used")
            or "default"
        )
        generation_model_tier = str(
            final_state.context_data.get("generation_model_tier")
            or final_state.context_data.get("final_synthesis_model_tier")
            or final_state.context_data.get("first_touch_model_tier")
            or ""
        )
        reasoning_mode = str(final_state.context_data.get("reasoning_mode") or "balanced")
        chat_mode = str(final_state.context_data.get("chat_mode") or "standard")
        response_metadata["generation_model_key"] = generation_model_key
        response_metadata["generation_model_tier"] = generation_model_tier
        response_metadata["reasoning_mode"] = reasoning_mode
        response_metadata["chat_mode"] = chat_mode
        if used_fallback_response:
            response_metadata["response_fallback"] = "generated"
        final_state.context_data["response_fallback_used"] = used_fallback_response
        final_state.context_data["response_outcome_stats"] = self._extract_response_outcome_stats(final_state)
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
            agents_involved = [str(agent).strip() for agent in executable_plan.agents_involved if str(agent).strip()]
        if not agents_involved:
            selected_experts_for_primary = final_state.context_data.get("selected_experts")
            if isinstance(selected_experts_for_primary, list):
                agents_involved = [
                    str(agent).strip()
                    for agent in selected_experts_for_primary
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
                    agents_involved = [str(agent).strip() for agent in trace_agents if str(agent).strip()]
        if not agents_involved:
            fallback_primary = str(final_state.context_data.get("next_step") or "").strip() or "study_buddy"
            agents_involved = [fallback_primary]
        if agents_involved:
            response_metadata["agents_involved"] = json.dumps(
                agents_involved,
                ensure_ascii=False,
            )
            response_metadata["primary_agent"] = agents_involved[0]
            if executable_plan and getattr(executable_plan, "collaboration_mode", None):
                response_metadata["collaboration_mode"] = executable_plan.collaboration_mode
            collaboration_narrative = (
                getattr(executable_plan, "collaboration_narrative", None) if executable_plan is not None else None
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
        answer_experts = final_state.context_data.get("answer_experts")
        if isinstance(answer_experts, list) and answer_experts:
            response_metadata["answer_experts"] = json.dumps(
                [str(expert) for expert in answer_experts],
                ensure_ascii=False,
            )
        routing_preview = final_state.context_data.get("routing_preview")
        if isinstance(routing_preview, dict) and routing_preview:
            response_metadata["routing_preview"] = json.dumps(
                routing_preview,
                ensure_ascii=False,
            )
        doc_retrieval_meta = final_state.context_data.get("document_context_retrieval")
        if isinstance(doc_retrieval_meta, dict) and doc_retrieval_meta.get("context_receipt"):
            response_metadata["context_receipt"] = json.dumps(
                doc_retrieval_meta["context_receipt"],
                ensure_ascii=False,
            )
        roundtable_turns = final_state.context_data.get("roundtable_turns")
        if isinstance(roundtable_turns, list) and roundtable_turns:
            response_metadata["roundtable_turns"] = json.dumps(
                roundtable_turns,
                ensure_ascii=False,
            )
        tool_results = ToolResultExtractor().extract_from_messages(final_state.messages)
        for tool_result in tool_results:
            if not tool_result.success or not isinstance(tool_result.data, dict):
                continue
            tool_payload = tool_result.data
            if isinstance(tool_payload.get("data"), dict):
                tool_payload = tool_payload["data"]
            if tool_result.tool_name == "launch_prediction":
                response_metadata["open_theater"] = "true"
                if tool_payload.get("deep_link"):
                    response_metadata["deep_link"] = str(tool_payload["deep_link"])
                response_metadata["prediction_preview"] = json.dumps(
                    {
                        "prediction_id": str(tool_payload.get("prediction_id") or ""),
                        "topic": str(tool_payload.get("topic") or ""),
                        "target_node_id": str(tool_payload.get("target_node_id") or ""),
                        "paths": list(tool_payload.get("paths") or []),
                    },
                    ensure_ascii=False,
                )
                if tool_payload.get("source_chat_session_id"):
                    response_metadata["source_chat_session_id"] = str(tool_payload["source_chat_session_id"])
            if tool_result.tool_name == "run_quick_simulation":
                response_metadata["open_simulation"] = "true"
                if tool_payload.get("deep_link"):
                    response_metadata["simulation_deep_link"] = str(tool_payload["deep_link"])
                response_metadata["simulation_preview"] = json.dumps(
                    {
                        "session_id": str(tool_payload.get("session_id") or ""),
                        "scenario_key": str(tool_payload.get("scenario_key") or ""),
                        "topic": str(tool_payload.get("topic") or ""),
                        "participants": list(tool_payload.get("participants") or []),
                        "round_preview": list(tool_payload.get("round_preview") or []),
                        "insight_summary": str(tool_payload.get("insight_summary") or ""),
                    },
                    ensure_ascii=False,
                )
                if tool_payload.get("source_chat_session_id"):
                    response_metadata["source_chat_session_id"] = str(tool_payload["source_chat_session_id"])
            if tool_result.tool_name == "generate_learning_report":
                response_metadata["open_report"] = "true"
                if tool_payload.get("deep_link"):
                    response_metadata["report_deep_link"] = str(tool_payload["deep_link"])
                preview_payload = (
                    dict(tool_payload.get("report_preview") or {})
                    if isinstance(tool_payload.get("report_preview"), dict)
                    else {}
                )
                preview_payload.setdefault("report_id", str(tool_payload.get("report_id") or ""))
                response_metadata["report_preview"] = json.dumps(
                    preview_payload,
                    ensure_ascii=False,
                )
                if tool_payload.get("quality_mode"):
                    response_metadata["bridge_quality_mode"] = str(tool_payload["quality_mode"])
                if tool_payload.get("source_chat_session_id"):
                    response_metadata["source_chat_session_id"] = str(tool_payload["source_chat_session_id"])
        if run_ledger is not None:
            agent_ids = []
            for source in (agents_involved, selected_experts, answer_experts):
                if not isinstance(source, list):
                    continue
                for agent_id in source:
                    label = str(agent_id).strip()
                    if label and label not in agent_ids:
                        agent_ids.append(label)
            for agent_id in agent_ids:
                await run_ledger.record_event(
                    event_type="agent_completed",
                    label=f"{agent_id} 已参与本轮编排",
                    workflow_stage="collaboration",
                    metadata={
                        "agent_id": agent_id,
                        "display_name": agent_id,
                        "description": "参与本轮回答生成与协作",
                        "status": "completed",
                        "collaboration_mode": (
                            getattr(executable_plan, "collaboration_mode", "") if executable_plan else ""
                        ),
                    },
                    emit_snapshot=False,
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
                context_pack_meta = (focused_memory.get("context_pack") or {}).get("metadata") or {}
                semantic_meta = context_pack_meta.get("semantic_gating")
            if semantic_meta:
                response_metadata["context_semantic_gating"] = json.dumps(semantic_meta, ensure_ascii=False)
        situation_brief = final_state.context_data.get("situation_brief")
        if isinstance(situation_brief, dict):
            response_metadata["situation_brief"] = json.dumps(situation_brief, ensure_ascii=False)
            summary = str(situation_brief.get("summary") or "").strip()
            if summary:
                response_metadata["situation_brief_summary"] = summary
            decision_context = situation_brief.get("decision_context")
            if isinstance(decision_context, dict):
                response_metadata["residual_decision_context"] = json.dumps(decision_context, ensure_ascii=False)
        response_metadata.update(self._semantic_control_trace_metadata(final_state.context_data))
        response_metadata.update(self._capability_selection_metadata(final_state.context_data))
        strategy_state = final_state.context_data.get("user_strategy_state")
        if isinstance(strategy_state, dict):
            response_metadata["user_strategy_state"] = json.dumps(strategy_state, ensure_ascii=False)
        understanding_depth = (
            (user_context_payload or {}).get("understanding_depth") if isinstance(user_context_payload, dict) else None
        )
        if isinstance(understanding_depth, dict):
            response_metadata["understanding_depth"] = json.dumps(understanding_depth, ensure_ascii=False)
        returning_context = (
            (user_context_payload or {}).get("returning_context") if isinstance(user_context_payload, dict) else None
        )
        if isinstance(returning_context, dict):
            response_metadata["returning_after_silence"] = json.dumps(returning_context, ensure_ascii=False)

        focused_memory = final_state.context_data.get("focused_memory")
        context_pack_meta = {}
        if isinstance(focused_memory, dict):
            context_pack_meta = (focused_memory.get("context_pack") or {}).get("metadata") or {}
        if run_ledger is not None:
            evidence_avg = context_pack_meta.get("evidence_score_avg")
            if evidence_avg is None:
                evidence_avg = context_pack_meta.get("evidence_score")
            await run_ledger.record_event(
                event_type="context_pack_built",
                label="上下文证据完成注入",
                workflow_stage="context",
                metadata={
                    "context_pack_id": str(context_pack_meta.get("pack_id") or context_pack_meta.get("id") or ""),
                    "focus_mode": str((final_state.context_data.get("context_focus") or {}).get("focus_mode") or ""),
                    "context_briefing_note": str(final_state.context_data.get("context_briefing_note") or ""),
                    "preferences": len(dict((focused_memory or {}).get("preferences") or {})),
                    "goals": len(list((focused_memory or {}).get("active_goals") or [])),
                    "episodic": len(list((focused_memory or {}).get("episodic_memories") or [])),
                    "evidence_score_avg": evidence_avg,
                    "situation_brief_confidence": (
                        ((final_state.context_data.get("situation_brief") or {}).get("sparkle_self_state") or {}).get(
                            "confidence_estimate"
                        )
                        if isinstance(final_state.context_data.get("situation_brief"), dict)
                        else None
                    ),
                },
                emit_snapshot=False,
            )
            semantic_control = (
                ((final_state.context_data.get("situation_brief") or {}).get("semantic_control") or {})
                if isinstance(final_state.context_data.get("situation_brief"), dict)
                else {}
            )
            if isinstance(semantic_control, dict) and semantic_control:
                metadata = {
                    "selected_terms": list(semantic_control.get("selected_terms") or []),
                    "rendered_doctrine_summary": dict(semantic_control.get("rendered_doctrine_summary") or {}),
                    "response_contract": dict(semantic_control.get("response_contract") or {}),
                    "compliance_expectations": dict(semantic_control.get("compliance_expectations") or {}),
                }
                metadata.update(self._semantic_control_observed_payload(final_state.context_data))
                await run_ledger.record_event(
                    event_type="semantic_control_attached",
                    label="语义控制层已附着",
                    workflow_stage="orchestration",
                    metadata=metadata,
                    emit_snapshot=False,
                )

        execution_validation = await self._validate_plan_execution(
            executable_plan=executable_plan,
            active_db=active_db,
            final_state=final_state,
            user_id=user_id,
            session_id=session_id,
        )
        task_context = self._derive_task_context_for_execution(
            task_context=final_state.context_data.get("task_context"),
            plan_context=plan_context or final_state.context_data.get("plan_context"),
            user_context_payload=user_context_payload,
        )
        execution_suggestion = await self._detect_execution_suggestion(
            user_message=self._extract_latest_user_message(final_state.messages),
            assistant_response=full_response,
            task_context=task_context,
            cognitive_context=(user_context_payload or {}).get("cognitive_context")
            if isinstance(user_context_payload, dict)
            else None,
            user_id=user_id,
            session_id=session_id,
            active_db=active_db,
        )
        if execution_suggestion:
            execution_validation = dict(execution_validation or {})
            execution_validation["execution_suggestion"] = execution_suggestion
        if execution_validation:
            response_metadata["execution_validation"] = execution_validation
        if execution_suggestion:
            response_metadata["execution_suggestion"] = execution_suggestion

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
        utilization_metrics = build_stage9_utilization_metrics(
            user_context_payload=user_context_payload,
            context_data=final_state.context_data,
            response_metadata=response_metadata,
            full_response=full_response,
        )
        final_state.context_data["utilization_metrics"] = utilization_metrics
        response_metadata["utilization_metrics"] = json.dumps(utilization_metrics, ensure_ascii=False)

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

        if run_ledger is not None:
            estimated_cost = 0.0
            model_key = str(
                final_state.context_data.get("generation_model_key")
                or final_state.context_data.get("model_used")
                or "default"
            )
            if self.token_tracker and total_prompt_tokens > 0:
                try:
                    estimated_cost = await self.token_tracker.estimate_cost(
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                        model=model_key,
                    )
                except Exception:
                    estimated_cost = 0.0
            await run_ledger.record_event(
                event_type="response_streamed",
                label="回答已完成",
                workflow_stage="response",
                metadata={
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                    "total_tokens": total_prompt_tokens + total_completion_tokens,
                    "estimated_cost_usd": estimated_cost,
                    "finish_reason": "stop",
                    "fallback_used": bool(used_fallback_response),
                },
            )
            response_metadata["run_ledger_summary"] = run_ledger.to_metadata_payload()

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

        # Spine: inject UserVisibleReceipt and StaleStateGuard card for Flutter UI
        if getattr(self, "redis", None) is not None:
            try:
                from app.signals.spine_orchestrator import SpineOrchestrator
                _spine = SpineOrchestrator(self.redis)
                _latest_receipt = await _spine.get_latest_receipt(user_id)
                if _latest_receipt:
                    _receipt_actions = list(_latest_receipt.actions or [])
                    _correctable = "correct" in _receipt_actions
                    response_metadata["spine_receipt"] = json.dumps({
                        "receipt_id": _latest_receipt.receipt_id,
                        "trigger": _latest_receipt.receipt_type,
                        "summary": _latest_receipt.message,
                        "correctable": _correctable,
                        "correction_options": (
                            ["这个判断不准确", "我不同意这个调整", "继续，先看看效果"]
                            if _correctable else []
                        ),
                    }, ensure_ascii=False)
                _community_hint = await _spine.get_latest_community_hint(user_id)
                if _community_hint:
                    response_metadata["spine_community_hint"] = json.dumps(
                        _community_hint, ensure_ascii=False
                    )
                _ux_warning = await _spine.get_ux_risk_warning(user_id)
                if _ux_warning:
                    response_metadata["spine_ux_warning"] = json.dumps(
                        _ux_warning, ensure_ascii=False
                    )
                _goal_arb = await _spine.get_goal_arbitration_summary(user_id)
                if _goal_arb:
                    response_metadata["spine_goal_arbitration"] = json.dumps(
                        _goal_arb, ensure_ascii=False
                    )
            except Exception:
                pass

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
            session_id=session_id,
        )
        return final_response, final_response_data

    @staticmethod
    def _extract_latest_user_message(messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content") or "")
        return ""

    @staticmethod
    def _estimate_text_tokens(text: str) -> int:
        normalized = "".join(str(text or "").split())
        if not normalized:
            return 0
        return max(1, int(round(len(normalized) * 0.9)))

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
        final_state: WorkflowState | None = None,
        chat_mode_hint: str | None = None,
        reasoning_mode_hint: str | None = None,
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

        if self.token_tracker:
            try:
                context_data = final_state.context_data if final_state is not None else {}
                model_key = str(context_data.get("generation_model_key") or context_data.get("model_used") or "default")
                model_tier = str(
                    context_data.get("generation_model_tier")
                    or context_data.get("final_synthesis_model_tier")
                    or context_data.get("first_touch_model_tier")
                    or ""
                )
                reasoning_mode = str(context_data.get("reasoning_mode") or "balanced")
                if not reasoning_mode.strip():
                    reasoning_mode = str(reasoning_mode_hint or "balanced")
                chat_mode = str(context_data.get("chat_mode") or "standard")
                if not chat_mode.strip():
                    chat_mode = str(chat_mode_hint or "standard")
                fallback_used = bool(context_data.get("response_fallback_used") or False)
                outcome_stats = context_data.get("response_outcome_stats") or self._extract_response_outcome_stats(
                    final_state
                )
                success = final_state is not None
                AI_RESPONSE_TOTAL_DURATION.labels(
                    chat_mode=chat_mode or "standard",
                    reasoning_mode=reasoning_mode or "balanced",
                    model_tier=model_tier or "unknown",
                ).observe(latency)
                prompt_tokens = total_prompt_tokens
                completion_tokens = total_completion_tokens
                if final_state is not None and prompt_tokens <= 0 and completion_tokens <= 0:
                    prompt_tokens = self._estimate_text_tokens(
                        self._extract_latest_user_message(final_state.messages),
                    )
                    assistant_text = ""
                    for msg in reversed(final_state.messages):
                        if msg.get("role") == "assistant":
                            assistant_text = str(msg.get("content") or "")
                            break
                    completion_tokens = self._estimate_text_tokens(assistant_text)
                estimated_cost = await self.token_tracker.estimate_cost(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=model_key,
                )
                await task_manager.spawn(
                    self.token_tracker.record_usage(
                        user_id=user_id,
                        session_id=session_id,
                        request_id=request_id,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        model=model_key,
                        cost=estimated_cost,
                        reasoning_mode=reasoning_mode,
                        model_tier=model_tier,
                        chat_mode=chat_mode,
                        timing_stats={
                            "total_duration_ms": int(round(latency * 1000)),
                        },
                        success=success,
                        fallback_used=fallback_used,
                        outcome_stats=outcome_stats,
                        utilization_metrics=context_data.get("utilization_metrics")
                        if isinstance(context_data.get("utilization_metrics"), dict)
                        else None,
                    ),
                    task_name="token_usage_record",
                    user_id=str(user_id),
                )
                logger.info(
                    f"Token usage recorded for user {user_id}: "
                    f"{prompt_tokens} + {completion_tokens} = "
                    f"{prompt_tokens + completion_tokens} tokens, "
                    f"est. cost: ${estimated_cost:.6f}"
                )
            except Exception as e:
                logger.error(f"Failed to record token usage: {e}")
