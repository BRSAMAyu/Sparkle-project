from __future__ import annotations

import json
import uuid
from typing import Any

from google.protobuf import struct_pb2
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import CONTEXT_FOCUS_DECISION_TOTAL
from app.core.metrics import (
    SESSION_FEEDBACK_APPLIED_TOTAL,
    SESSION_FEEDBACK_CONFIDENCE_BUCKET,
    SESSION_FEEDBACK_DETECTED_TOTAL,
    SESSION_FEEDBACK_IGNORED_TOTAL,
)
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.context_focus import FocusedContextAssembler
from app.orchestration.retrieval_intent import RetrievalIntentBudgets, build_retrieval_decision
from app.orchestration.session_feedback import (
    SESSION_FEEDBACK_TTL_SECONDS,
    SessionAdaptationContext,
    SessionFeedbackSignal,
    analyze_conversation_rhythm,
    build_session_adaptation_context,
    detect_session_feedback_signal,
)
from app.orchestration.situation_brief import SituationBriefBuilder
from app.orchestration.soul_compiler import DEFAULT_COMPANION_STATE
from app.orchestration.statechart_engine import WorkflowState
from app.services.companion_state_service import CompanionStateService
from app.services.intervention_feedback_binding_service import InterventionFeedbackBindingService
from app.services.perceptible_intelligence_service import PerceptibleInsightService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.services.self_evolution_service import UnderstandingDepthService
from app.services.system_update_service import SystemUpdateService
from app.services.user_service import UserService
from app.services.user_strategy_state_service import UserStrategyStateService

SESSION_FEEDBACK_KEY_PREFIX = "session:feedback:"
CONTEXT_VERSION_KEY_PREFIX = "user:context:versions:"
CONTEXT_VERSION_TTL_SECONDS = 6 * 60 * 60
REALTIME_VERSION_DOMAINS = ("tasks", "plans", "focus", "progress", "prefs")


class SessionStateMixin:
    """Mixin providing session-state helpers extracted from Orchestrator."""

    @staticmethod
    def _copy_companion_runtime_keys(
        *,
        source_context: dict[str, Any] | None,
        target_context: dict[str, Any] | None,
    ) -> None:
        if not isinstance(source_context, dict) or not isinstance(target_context, dict):
            return
        for key in (
            "effective_companion_state",
            "companion_state_recent_revisions",
            "relationship_profile",
            "soul_runtime_context",
            "soul_runtime_debug",
        ):
            value = source_context.get(key)
            if value is not None:
                target_context[key] = value

    async def _hydrate_companion_runtime_context(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str | None,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState | None = None,
    ) -> dict[str, Any]:
        effective_companion_state: dict[str, Any]
        relationship_profile: dict[str, Any]
        recent_revisions: list[dict[str, Any]]

        if active_db is None:
            effective_companion_state = DEFAULT_COMPANION_STATE.to_dict()
            relationship_profile = {}
            recent_revisions = []
        else:
            service = CompanionStateService(active_db, getattr(self, "redis", None))
            user_uuid = uuid.UUID(str(user_id))
            effective_companion_state = await service.get_effective_state(
                user_uuid,
                plan_id=plan_id,
                session_id=session_id,
            )
            relationship_profile = await service.get_relationship_profile(user_uuid)
            recent_revisions = await service.get_recent_revisions(
                user_uuid,
                plan_id=plan_id,
                session_id=session_id,
            )

        payload = {
            "effective_companion_state": effective_companion_state,
            "relationship_profile": relationship_profile,
            "companion_state_recent_revisions": recent_revisions,
        }

        if isinstance(user_context_payload, dict):
            user_context_payload.update(payload)
        if state is not None:
            state.context_data.update(payload)
            existing_user_context = state.context_data.get("user_context")
            if isinstance(existing_user_context, dict):
                existing_user_context.update(payload)
        return payload

    @staticmethod
    def _build_system_update_prompt_context(updates: list[dict[str, Any]]) -> dict[str, Any]:
        proactive_opening_message = ""
        pending_observation = ""
        post_adaptation_question = ""
        active_interventions = InterventionFeedbackBindingService.extract_active_interventions_from_updates(updates)

        for update in updates:
            if not isinstance(update, dict):
                continue
            update_type = str(update.get("type") or "").strip()
            description = str(update.get("description") or "").strip()
            metadata = update.get("metadata") if isinstance(update.get("metadata"), dict) else {}
            evolution_kind = str(metadata.get("evolution_kind") or "").strip()

            if not proactive_opening_message and description and (
                update_type == "plan_adjusted_from_error"
                or evolution_kind in {"adjustment", "plan_reasoning", "progress_comparison"}
            ):
                proactive_opening_message = description

            if not pending_observation:
                if evolution_kind == "proactive_insight":
                    insight_text = str(metadata.get("insight_text") or "").strip()
                    if insight_text:
                        pending_observation = (
                            insight_text if "？" in insight_text or "?" in insight_text else f"{insight_text} 这和你的感受一致吗？"
                        )
                elif evolution_kind == "weekly_learning_report":
                    weekly_summary = str(metadata.get("weekly_summary") or "").strip()
                    if weekly_summary:
                        pending_observation = (
                            weekly_summary
                            if "？" in weekly_summary or "?" in weekly_summary
                            else f"{weekly_summary} 你也有这种感觉吗？"
                        )

            if not post_adaptation_question and (
                update_type == "plan_adjusted_from_error" or evolution_kind == "adjustment"
            ):
                node_name = str(metadata.get("node_name") or "").strip()
                if node_name:
                    post_adaptation_question = f"我把和「{node_name}」相关的安排提前了一些，这样调整对你来说合适吗？"
                else:
                    post_adaptation_question = "我刚微调了接下来的安排，这样的调整对你来说合适吗？"

        return {
            "proactive_opening_message": proactive_opening_message,
            "pending_observation": pending_observation,
            "post_adaptation_question": post_adaptation_question,
            "active_intervention_id": (
                str(active_interventions[0].get("intervention_id") or "").strip() if active_interventions else ""
            ),
            "active_interventions": active_interventions,
        }

    async def _drain_system_updates(
        self,
        user_id: str,
    ) -> tuple[
        list[agent_service_pb2.ChatResponse],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[str],
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, str],
    ]:
        updates = await SystemUpdateService(getattr(self, "redis", None)).drain(user_id, limit=20)
        responses: list[agent_service_pb2.ChatResponse] = []
        adaptation_records: list[dict[str, Any]] = []
        preference_learnings: list[dict[str, Any]] = []
        evolution_highlights: list[str] = []
        progress_snapshot: dict[str, Any] | None = None
        understanding_depth_update: dict[str, Any] | None = None
        visible_prompt_context = self._build_system_update_prompt_context(updates)
        for update in updates:
            if isinstance(update, dict):
                metadata = update.get("metadata") if isinstance(update.get("metadata"), dict) else {}
                update["seen_in_chat"] = True
                if isinstance(metadata, dict):
                    metadata["seen_in_chat"] = True
            metadata = update.get("metadata") if isinstance(update, dict) else None
            if isinstance(metadata, dict):
                if metadata.get("evolution_kind") == "adaptation_record" and isinstance(metadata.get("adaptation_record"), dict):
                    adaptation_records.append(metadata["adaptation_record"])
                if metadata.get("evolution_kind") == "preference_learning" and isinstance(metadata.get("preference_learning"), dict):
                    preference_learnings.append(metadata["preference_learning"])
                if metadata.get("evolution_kind") == "highlight" and metadata.get("highlight"):
                    evolution_highlights.append(str(metadata["highlight"]).strip())
                if metadata.get("evolution_kind") == "progress_snapshot" and isinstance(metadata.get("progress_snapshot"), dict):
                    progress_snapshot = metadata["progress_snapshot"]
                if metadata.get("evolution_kind") == "proactive_insight" and metadata.get("insight_text"):
                    evolution_highlights.append(str(metadata["insight_text"]).strip())
                if metadata.get("evolution_kind") == "weekly_learning_report" and metadata.get("weekly_summary"):
                    evolution_highlights.append(str(metadata["weekly_summary"]).strip())
                if metadata.get("evolution_kind") == "progress_comparison":
                    comparison = metadata.get("comparison")
                    if isinstance(comparison, dict) and comparison.get("delta_text"):
                        evolution_highlights.append(str(comparison["delta_text"]).strip())
                if metadata.get("evolution_kind") == "plan_reasoning" and metadata.get("reasoning_summary"):
                    evolution_highlights.append(str(metadata["reasoning_summary"]).strip())
                if metadata.get("evolution_kind") == "understanding_depth":
                    understanding_depth_update = {
                        **metadata,
                        "description": str(update.get("description") or "").strip(),
                    }
                    depth_payload = metadata.get("understanding_depth")
                    if isinstance(depth_payload, dict) and depth_payload.get("level"):
                        evolution_highlights.append(f"我对你的理解已提升到 {depth_payload['level']} 阶段。")
            if isinstance(update, dict) and str(update.get("description") or "").strip():
                update_type = str(update.get("type") or "").strip()
                if update_type == "plan_adjusted_from_error":
                    evolution_highlights.append(str(update["description"]).strip())
            widget_struct = struct_pb2.Struct()
            widget_struct.update(update)
            responses.append(
                agent_service_pb2.ChatResponse(
                    tool_result=agent_service_pb2.ToolResultPayload(
                        tool_name="system_update",
                        success=True,
                        widget_type="system_update",
                        widget_data=widget_struct,
                        tool_call_id="",
                    )
                )
            )
        if progress_snapshot:
            evolution_highlights = [*evolution_highlights[:2], *(progress_snapshot.get("highlights") or [])[:1]]
        return (
            responses,
            adaptation_records[:3],
            preference_learnings[:3],
            evolution_highlights[:3],
            progress_snapshot,
            understanding_depth_update,
            visible_prompt_context,
        )

    async def _attach_situation_brief(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        state: WorkflowState | None = None,
        session_feedback_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not isinstance(user_context_payload, dict):
            return user_context_payload

        existing_brief = user_context_payload.get("situation_brief")
        if isinstance(existing_brief, dict):
            decision_context = existing_brief.get("decision_context") if isinstance(existing_brief, dict) else None
            capability_selection = existing_brief.get("capability_selection") if isinstance(existing_brief, dict) else None
            if isinstance(decision_context, dict):
                user_context_payload["residual_decision_context"] = decision_context
            if isinstance(capability_selection, dict):
                user_context_payload["capability_selection"] = capability_selection

            if isinstance(state, WorkflowState):
                state.context_data["situation_brief"] = existing_brief
                if isinstance(decision_context, dict):
                    state.context_data["residual_decision_context"] = decision_context
                if isinstance(capability_selection, dict):
                    state.context_data["capability_selection_report"] = capability_selection
                    state.context_data["capability_selection_summary"] = capability_selection.get("summary", {})
                    state.context_data["why_this_path"] = str(capability_selection.get("why_this_path") or "").strip()
                    model_selection = capability_selection.get("model_selection")
                    if isinstance(model_selection, dict):
                        state.context_data["phase_d_forced_model_tier"] = str(
                            model_selection.get("preferred_tier") or ""
                        ).strip()
                existing_user_context = state.context_data.get("user_context")
                if isinstance(existing_user_context, dict):
                    existing_user_context["situation_brief"] = existing_brief
                    if isinstance(decision_context, dict):
                        existing_user_context["residual_decision_context"] = decision_context
                    if isinstance(capability_selection, dict):
                        existing_user_context["capability_selection"] = capability_selection
            return user_context_payload

        effective_progress_snapshot = None
        if isinstance(state, WorkflowState):
            existing_snapshot = state.context_data.get("progress_snapshot")
            if isinstance(existing_snapshot, dict):
                effective_progress_snapshot = existing_snapshot
        if effective_progress_snapshot is None and isinstance(user_context_payload.get("progress_snapshot"), dict):
            effective_progress_snapshot = user_context_payload.get("progress_snapshot")
        if effective_progress_snapshot is None and active_db is not None:
            try:
                effective_progress_snapshot = await ProgressNarrativeService(
                    active_db,
                    getattr(self, "redis", None),
                ).maybe_get_lightweight_snapshot(user_id)
            except Exception as exc:
                logger.warning(f"Failed to refresh lightweight progress snapshot for situation brief: {exc}")
                effective_progress_snapshot = None

        if isinstance(effective_progress_snapshot, dict):
            user_context_payload["progress_snapshot"] = effective_progress_snapshot
            if isinstance(state, WorkflowState):
                state.context_data["progress_snapshot"] = effective_progress_snapshot

        dual_core_snapshot = {}
        if isinstance(state, WorkflowState):
            decision = state.context_data.get("dual_core_decision")
            signals = state.context_data.get("dual_core_signal_snapshot")
            if isinstance(decision, dict):
                dual_core_snapshot["decision"] = decision
            if isinstance(signals, dict):
                dual_core_snapshot["signal_snapshot"] = signals
            prompt_instruction = str(state.context_data.get("dual_core_prompt_instruction") or "").strip()
            if prompt_instruction:
                dual_core_snapshot["prompt_instruction"] = prompt_instruction

        built_brief = await SituationBriefBuilder().build(
            user_context_payload=user_context_payload,
            plan_context=plan_context,
            focused_memory=(
                state.context_data.get("focused_memory")
                if isinstance(state, WorkflowState) and isinstance(state.context_data.get("focused_memory"), dict)
                else user_context_payload.get("focused_memory")
            ),
            context_briefing_note=(
                str(state.context_data.get("context_briefing_note") or "").strip()
                if isinstance(state, WorkflowState)
                else str(user_context_payload.get("context_briefing_note") or "").strip()
            ),
            visible_update_context=(
                state.context_data.get("visible_update_context")
                if isinstance(state, WorkflowState) and isinstance(state.context_data.get("visible_update_context"), dict)
                else {}
            ),
            dual_core_snapshot=dual_core_snapshot,
            session_feedback_signal=session_feedback_signal,
            progress_snapshot=effective_progress_snapshot,
            adaptation_records=(
                state.context_data.get("adaptation_records")
                if isinstance(state, WorkflowState) and isinstance(state.context_data.get("adaptation_records"), list)
                else user_context_payload.get("adaptation_records")
            ),
        )
        situation_brief = built_brief.to_dict()

        user_context_payload["situation_brief"] = situation_brief
        decision_context = situation_brief.get("decision_context") if isinstance(situation_brief, dict) else None
        capability_selection = situation_brief.get("capability_selection") if isinstance(situation_brief, dict) else None
        if isinstance(decision_context, dict):
            user_context_payload["residual_decision_context"] = decision_context
        if isinstance(capability_selection, dict):
            user_context_payload["capability_selection"] = capability_selection

        if isinstance(state, WorkflowState):
            state.context_data["situation_brief"] = situation_brief
            if isinstance(decision_context, dict):
                state.context_data["residual_decision_context"] = decision_context
            if isinstance(capability_selection, dict):
                state.context_data["capability_selection_report"] = capability_selection
                state.context_data["capability_selection_summary"] = capability_selection.get("summary", {})
                state.context_data["why_this_path"] = str(capability_selection.get("why_this_path") or "").strip()
                model_selection = capability_selection.get("model_selection")
                if isinstance(model_selection, dict):
                    state.context_data["phase_d_forced_model_tier"] = str(
                        model_selection.get("preferred_tier") or ""
                    ).strip()
            existing_user_context = state.context_data.get("user_context")
            if isinstance(existing_user_context, dict):
                existing_user_context["situation_brief"] = situation_brief
                if isinstance(decision_context, dict):
                    existing_user_context["residual_decision_context"] = decision_context
                if isinstance(capability_selection, dict):
                    existing_user_context["capability_selection"] = capability_selection

        return user_context_payload

    async def _attach_active_intervention_state(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState | None = None,
    ) -> dict[str, Any] | None:
        if active_db is None:
            return user_context_payload

        runtime_active_interventions: list[dict[str, Any]] = []
        if isinstance(state, WorkflowState):
            visible_update_context = state.context_data.get("visible_update_context")
            if isinstance(visible_update_context, dict):
                runtime_active_interventions = [
                    item
                    for item in (visible_update_context.get("active_interventions") or [])
                    if isinstance(item, dict)
                ]

        try:
            binding_service = InterventionFeedbackBindingService(active_db, getattr(self, "redis", None))
            resolved = await binding_service.resolve_active_interventions(
                user_id=uuid.UUID(str(user_id)),
                session_id=session_id,
                runtime_active_interventions=runtime_active_interventions,
                limit=3,
            )
            last_binding = await binding_service.get_last_feedback_binding(session_id)
        except Exception as exc:
            logger.warning(f"Failed to attach active intervention state: {exc}")
            return user_context_payload

        active_intervention_id = str(resolved[0].get("intervention_id") or "").strip() if resolved else ""
        if isinstance(user_context_payload, dict):
            user_context_payload["active_interventions"] = resolved
            if active_intervention_id:
                user_context_payload["active_intervention_id"] = active_intervention_id
            if last_binding:
                user_context_payload["last_feedback_binding"] = last_binding

        if isinstance(state, WorkflowState):
            state.context_data["active_interventions"] = resolved
            if active_intervention_id:
                state.context_data["active_intervention_id"] = active_intervention_id
            if last_binding:
                state.context_data["last_feedback_binding"] = last_binding
            existing_user_context = state.context_data.get("user_context")
            if isinstance(existing_user_context, dict):
                existing_user_context["active_interventions"] = resolved
                if active_intervention_id:
                    existing_user_context["active_intervention_id"] = active_intervention_id
                if last_binding:
                    existing_user_context["last_feedback_binding"] = last_binding

        return user_context_payload

    async def _attach_user_strategy_state(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str | None,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState | None = None,
    ) -> dict[str, Any] | None:
        if not isinstance(user_context_payload, dict) or active_db is None:
            return user_context_payload

        try:
            strategy_service = UserStrategyStateService(active_db, getattr(self, "redis", None))
            effective_state = await strategy_service.get_effective_state(
                uuid.UUID(str(user_id)),
                plan_id=plan_id,
                session_id=session_id,
            )
            recent_changes = await strategy_service.get_recent_changes(
                uuid.UUID(str(user_id)),
                plan_id=plan_id,
                session_id=session_id,
                limit=6,
            )
        except Exception as exc:
            logger.warning(f"Failed to attach user strategy state: {exc}")
            return user_context_payload

        user_context_payload["user_strategy_state"] = effective_state
        if recent_changes:
            user_context_payload["user_strategy_history"] = recent_changes

        if isinstance(state, WorkflowState):
            state.context_data["user_strategy_state"] = effective_state
            state.context_data["user_strategy_history"] = recent_changes
            existing_user_context = state.context_data.get("user_context")
            if isinstance(existing_user_context, dict):
                existing_user_context["user_strategy_state"] = effective_state
                if recent_changes:
                    existing_user_context["user_strategy_history"] = recent_changes

        return user_context_payload

    @staticmethod
    def _session_feedback_key(session_id: str) -> str:
        return f"{SESSION_FEEDBACK_KEY_PREFIX}{session_id}"

    @staticmethod
    def _extract_previous_message(
        conversation_context: dict[str, Any] | None,
        *,
        role: str,
    ) -> str:
        messages = (conversation_context or {}).get("messages") or []
        if not isinstance(messages, list):
            return ""
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").lower() != role:
                continue
            content = str(message.get("content") or "").strip()
            if content:
                return content
        return ""

    async def _load_session_adaptation_context(
        self,
        session_id: str,
    ) -> SessionAdaptationContext:
        if not self.redis or not session_id:
            return SessionAdaptationContext()
        try:
            raw = await self.redis.get(self._session_feedback_key(session_id))
            if not raw:
                return SessionAdaptationContext()
            payload = json.loads(raw)
            return SessionAdaptationContext.from_dict(payload)
        except Exception as e:
            logger.warning(f"Failed to load session adaptation context: {e}")
            return SessionAdaptationContext()

    async def _save_session_adaptation_context(
        self,
        session_id: str,
        context: SessionAdaptationContext,
    ) -> None:
        if not self.redis or not session_id:
            return
        try:
            await self.redis.setex(
                self._session_feedback_key(session_id),
                SESSION_FEEDBACK_TTL_SECONDS,
                json.dumps(context.to_dict(), ensure_ascii=False),
            )
        except Exception as e:
            logger.warning(f"Failed to save session adaptation context: {e}")

    async def _maybe_enqueue_perceptible_insight(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_message: str,
        user_context_payload: dict[str, Any] | None,
        plan_id: str | None,
        session_feedback_signal: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        if not active_db:
            return
        if not (settings.ENABLE_PERCEPTIBLE_INTELLIGENCE and settings.ENABLE_PROACTIVE_INSIGHTS):
            return
        try:
            service = PerceptibleInsightService(active_db, getattr(self, "redis", None))
            await service.maybe_enqueue_session_insight(
                user_id=user_id,
                user_message=user_message,
                context_focus=(user_context_payload or {}).get("context_focus") if isinstance(user_context_payload, dict) else None,
                plan_id=plan_id,
                progress_snapshot=(user_context_payload or {}).get("progress_snapshot") if isinstance(user_context_payload, dict) else None,
                session_feedback=session_feedback_signal,
                session_id=session_id,
                experiment_cohort=(user_context_payload or {}).get("experiment_cohort") if isinstance(user_context_payload, dict) else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to enqueue perceptible insight: {exc}")

    async def _maybe_enqueue_understanding_depth(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
    ) -> None:
        if not active_db or not settings.ENABLE_PERCEPTIBLE_INTELLIGENCE:
            return
        try:
            service = UnderstandingDepthService(active_db, getattr(self, "redis", None))
            await service.maybe_enqueue_upgrade(user_id=uuid.UUID(str(user_id)))
        except Exception as exc:
            logger.warning(f"Failed to enqueue understanding depth update: {exc}")

    async def _detect_session_feedback(
        self,
        *,
        session_id: str,
        user_message: str,
        conversation_context: dict[str, Any] | None,
    ) -> tuple[SessionFeedbackSignal | None, SessionAdaptationContext | None, dict[str, Any] | None]:
        if not settings.ENABLE_SESSION_FEEDBACK_ADAPTATION:
            return None, None, None
        if not str(user_message or "").strip():
            return None, None, None

        rhythm = analyze_conversation_rhythm(
            user_message=user_message,
            conversation_messages=(conversation_context or {}).get("messages"),
        )

        previous_assistant = self._extract_previous_message(conversation_context, role="assistant")
        if not previous_assistant:
            SESSION_FEEDBACK_IGNORED_TOTAL.labels(reason="no_previous_assistant").inc()
            if rhythm is None:
                return None, None, None
            existing_context = await self._load_session_adaptation_context(session_id)
            adaptation_context = build_session_adaptation_context(
                signal=None,
                existing_context=existing_context,
                conversation_rhythm=rhythm,
            )
            await self._save_session_adaptation_context(session_id, adaptation_context)
            return None, adaptation_context, rhythm

        previous_user = self._extract_previous_message(conversation_context, role="user")
        signal = detect_session_feedback_signal(
            user_message=user_message,
            previous_assistant_message=previous_assistant,
            previous_user_message=previous_user,
        )
        if signal is None:
            if rhythm is None:
                return None, None, None
            existing_context = await self._load_session_adaptation_context(session_id)
            adaptation_context = build_session_adaptation_context(
                signal=None,
                existing_context=existing_context,
                conversation_rhythm=rhythm,
            )
            await self._save_session_adaptation_context(session_id, adaptation_context)
            return None, adaptation_context, rhythm

        SESSION_FEEDBACK_DETECTED_TOTAL.labels(signal_type=signal.signal_type).inc()
        SESSION_FEEDBACK_CONFIDENCE_BUCKET.labels(
            signal_type=signal.signal_type,
            bucket=signal.confidence_bucket,
        ).inc()

        if signal.signal_type in {"mismatch", "simplify", "expand"} and not signal.applies_adaptation:
            SESSION_FEEDBACK_IGNORED_TOTAL.labels(reason="below_threshold").inc()

        if signal.applies_adaptation:
            SESSION_FEEDBACK_APPLIED_TOTAL.labels(signal_type=signal.signal_type).inc()

        existing_context = await self._load_session_adaptation_context(session_id)
        adaptation_context = build_session_adaptation_context(
            signal=signal,
            existing_context=existing_context,
            conversation_rhythm=rhythm,
        )
        await self._save_session_adaptation_context(session_id, adaptation_context)
        return signal, adaptation_context, rhythm

    async def _apply_context_focus_overlay(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_message: str,
        route_intent: str | None,
        plan_id: uuid.UUID | None,
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState | None = None,
        session_feedback_signal: dict[str, Any] | None = None,
        force_focus_mode: str | None = None,
    ) -> dict[str, Any] | None:
        user_context_payload = self._attach_retrieval_decision(
            user_context_payload=user_context_payload,
            state=state,
            user_message=user_message,
            route_intent=route_intent,
        )
        if not settings.ENABLE_CONTEXT_FOCUSING or not active_db or user_context_payload is None:
            return user_context_payload

        try:
            assembler = FocusedContextAssembler(active_db, self.redis)
            focus_decision, focused_memory, briefing_note = await assembler.assemble(
                user_id=uuid.UUID(str(user_id)),
                user_message=user_message,
                route_intent=route_intent,
                plan_id=plan_id,
                plan_context=plan_context,
                user_context_payload=user_context_payload,
                session_feedback_signal=session_feedback_signal,
                force_focus_mode=force_focus_mode,
            )
        except Exception as exc:
            logger.warning(f"Failed to apply context focus overlay: {exc}")
            return user_context_payload

        merged_context = dict(user_context_payload)
        merged_context["current_query"] = user_message
        merged_context["context_focus"] = focus_decision.to_dict()
        returning_context = merged_context.get("returning_context") if isinstance(merged_context, dict) else None
        if briefing_note:
            if isinstance(returning_context, dict) and returning_context.get("briefing_text"):
                merged_context["context_briefing_note"] = (
                    f"{str(returning_context.get('briefing_text') or '').strip()} {briefing_note}"
                ).strip()
            else:
                merged_context["context_briefing_note"] = briefing_note
        elif isinstance(returning_context, dict) and returning_context.get("briefing_text"):
            merged_context["context_briefing_note"] = str(returning_context.get("briefing_text") or "").strip()
        if focused_memory:
            merged_context["preferences"] = focused_memory.get("preferences", merged_context.get("preferences", {}))
            merged_context["active_goals"] = focused_memory.get("active_goals", [])
            merged_context["episodic_memories"] = focused_memory.get("episodic_memories", [])
            merged_context["focused_memory"] = focused_memory
            focused_pack = focused_memory.get("context_pack")
            if isinstance(focused_pack, dict):
                merged_context["context_pack"] = focused_pack

        CONTEXT_FOCUS_DECISION_TOTAL.labels(
            focus_mode=focus_decision.focus_mode,
            route_intent=str(focus_decision.route_intent or route_intent or "chat"),
        ).inc()

        if state is not None:
            state.context_data["user_context"] = merged_context
            state.context_data["context_focus"] = focus_decision.to_dict()
            state.context_data["focused_memory"] = focused_memory
            if merged_context.get("context_briefing_note"):
                state.context_data["context_briefing_note"] = merged_context.get("context_briefing_note")
            self._copy_companion_runtime_keys(source_context=state.context_data, target_context=merged_context)
        return merged_context

    @staticmethod
    def _attach_retrieval_decision(
        *,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState | None,
        user_message: str,
        route_intent: str | None,
    ) -> dict[str, Any] | None:
        if not isinstance(user_context_payload, dict):
            return user_context_payload

        decision = build_retrieval_decision(
            message=user_message,
            route_intent=route_intent,
            context=user_context_payload,
            aurora_doc_context_mode=str(getattr(settings, "AURORA_DOC_CONTEXT_MODE", "auto") or "auto"),
            budgets=RetrievalIntentBudgets(
                aggressive=int(getattr(settings, "AURORA_DOC_CONTEXT_AGGRESSIVE_BUDGET_TOKENS", 2200) or 2200),
                selective=int(getattr(settings, "AURORA_DOC_CONTEXT_SELECTIVE_BUDGET_TOKENS", 900) or 900),
                ambiguous=int(getattr(settings, "AURORA_DOC_CONTEXT_AMBIGUOUS_BUDGET_TOKENS", 500) or 500),
            ),
        )
        payload = dict(user_context_payload)
        decision_payload = decision.to_dict()
        payload["retrieval_decision"] = decision_payload
        payload["document_retrieval_decision"] = decision_payload

        if state is not None:
            state.context_data["retrieval_decision"] = decision_payload
            state.context_data["document_retrieval_decision"] = decision_payload

        logger.info(
            "Document retrieval decision: mode={} should_retrieve={} budget={} reason={}",
            decision.retrieval_mode,
            decision.should_retrieve,
            decision.budget_tokens,
            decision.reason,
        )
        return payload

    async def _update_state(self, session_id: str, state: str, details: str = ""):
        """Update FSM State in Redis with persistence"""
        if self.state_manager:
            await self.state_manager.update_state(
                session_id=session_id,
                state=state,
                details=details,
                request_id=None,  # Will be set in process_stream
                user_id=None
            )
        logger.info(f"Session {session_id} State: {state} ({details})")

    async def _check_idempotency(self, session_id: str, request_id: str) -> dict[str, Any] | None:
        """
        Check if request was already processed

        Returns:
            Optional[Dict]: Cached response if duplicate, None otherwise
        """
        if not self.state_manager or not request_id:
            return None

        return await self.state_manager.get_cached_response(session_id, request_id)

    async def _acquire_session_lock(self, session_id: str, request_id: str) -> bool:
        """Acquire distributed lock for session"""
        if not self.state_manager:
            return True

        return await self.state_manager.acquire_lock(session_id, request_id)

    async def _release_session_lock(self, session_id: str, request_id: str):
        """Release distributed lock"""
        if self.state_manager:
            await self.state_manager.release_lock(session_id, request_id)

    async def _cache_response(self, session_id: str, request_id: str, response_data: dict[str, Any]):
        """Cache response for idempotency"""
        if self.state_manager and request_id:
            await self.state_manager.cache_response(session_id, request_id, response_data)

    async def _load_context_versions(self, user_id: str) -> dict[str, str]:
        if not self.redis:
            return {}
        key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
        try:
            raw = await self.redis.get(key)
            if not raw:
                return {}
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load context versions: {e}")
        return {}

    async def _save_context_versions(self, user_id: str, versions: dict[str, str]) -> None:
        if not self.redis:
            return
        key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
        try:
            payload = json.dumps(versions, ensure_ascii=False)
            await self.redis.setex(key, CONTEXT_VERSION_TTL_SECONDS, payload)
        except Exception as e:
            logger.warning(f"Failed to save context versions: {e}")

    async def _self_heal_versions(
        self,
        user_id: str,
        overlay_versions: dict[str, str],
        db_session: AsyncSession | None,
    ) -> None:
        if not overlay_versions or not user_id:
            return

        previous = await self._load_context_versions(user_id)
        healed: list[str] = []

        for domain in REALTIME_VERSION_DOMAINS:
            new_v = overlay_versions.get(domain)
            if not new_v:
                continue
            old_v = previous.get(domain)
            if old_v == new_v:
                continue

            if domain == "prefs" and db_session:
                user_service = UserService(db_session, self.redis)
                await user_service.invalidate_user_cache(uuid.UUID(user_id))

            previous[domain] = new_v
            healed.append(f"{domain}:{old_v}->{new_v}")

        if healed:
            await self._save_context_versions(user_id, previous)
            logger.info("Context self-heal versions user=%s healed=%s", user_id, healed)

    async def _hydrate_evolution_context(
        self,
        *,
        final_state: WorkflowState,
        user_id: str,
    ) -> None:
        try:
            updates = await SystemUpdateService(getattr(self, "redis", None)).list_updates(user_id, limit=20)
            if not updates:
                return
            context_data = final_state.context_data
            adaptation_records = list(context_data.get("adaptation_records") or [])
            preference_learnings = list(context_data.get("preference_learnings") or [])
            evolution_highlights = list(context_data.get("evolution_highlights") or [])
            progress_snapshot = context_data.get("progress_snapshot")
            for update in updates:
                metadata = update.get("metadata") if isinstance(update, dict) else None
                if not isinstance(metadata, dict):
                    continue
                adaptation = metadata.get("adaptation_record")
                if metadata.get("evolution_kind") == "adaptation_record" and isinstance(adaptation, dict):
                    if adaptation not in adaptation_records:
                        adaptation_records.append(adaptation)
                pref = metadata.get("preference_learning")
                if metadata.get("evolution_kind") == "preference_learning" and isinstance(pref, dict):
                    if pref not in preference_learnings:
                        preference_learnings.append(pref)
                if metadata.get("evolution_kind") == "highlight" and metadata.get("highlight"):
                    highlight = str(metadata["highlight"]).strip()
                    if highlight and highlight not in evolution_highlights:
                        evolution_highlights.append(highlight)
                snapshot = metadata.get("progress_snapshot")
                if metadata.get("evolution_kind") == "progress_snapshot" and isinstance(snapshot, dict):
                    progress_snapshot = snapshot
                if metadata.get("evolution_kind") == "proactive_insight" and metadata.get("insight_text"):
                    highlight = str(metadata["insight_text"]).strip()
                    if highlight and highlight not in evolution_highlights:
                        evolution_highlights.append(highlight)
                if metadata.get("evolution_kind") == "weekly_learning_report" and metadata.get("weekly_summary"):
                    highlight = str(metadata["weekly_summary"]).strip()
                    if highlight and highlight not in evolution_highlights:
                        evolution_highlights.append(highlight)
                if metadata.get("evolution_kind") == "progress_comparison":
                    comparison = metadata.get("comparison")
                    if isinstance(comparison, dict) and comparison.get("delta_text"):
                        highlight = str(comparison["delta_text"]).strip()
                        if highlight and highlight not in evolution_highlights:
                            evolution_highlights.append(highlight)
                if metadata.get("evolution_kind") == "plan_reasoning" and metadata.get("reasoning_summary"):
                    highlight = str(metadata["reasoning_summary"]).strip()
                    if highlight and highlight not in evolution_highlights:
                        evolution_highlights.append(highlight)
            if progress_snapshot is None and hasattr(self, "db_session_factory"):
                async with self.db_session_factory() as db_session:
                    service = ProgressNarrativeService(db_session, getattr(self, "redis", None))
                    progress_snapshot = await service.maybe_get_lightweight_snapshot(user_id)
            if adaptation_records:
                context_data["adaptation_records"] = adaptation_records[:3]
            if preference_learnings:
                context_data["preference_learnings"] = preference_learnings[:3]
            if evolution_highlights:
                context_data["evolution_highlights"] = evolution_highlights[:3]
            if progress_snapshot:
                context_data["progress_snapshot"] = progress_snapshot
        except Exception as e:
            logger.warning(f"Failed to hydrate evolution context: {e}")
