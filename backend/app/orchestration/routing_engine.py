from __future__ import annotations

import contextlib
import json
import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL, ROUTING_SUMMARY_CONTEXT_TOTAL
from app.core.unified_intent_router import UnifiedIntentType
from app.orchestration.chat_modes import CHAT_MODE_STANDARD
from app.orchestration.context_focus import infer_route_intent_from_chat_mode
from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRoutingInput
from app.orchestration.mode_workflow_config import get_mode_strategy, get_workflow_config
from app.orchestration.route_adapter import to_route_decision
from app.orchestration.schemas import RouteDecision
from app.gen.agent.v1 import agent_service_pb2
from app.services.plan_progress_service import PlanProgressService


class RoutingEngineMixin:
    """Mixin that groups all routing / classification helpers for the Orchestrator."""

    # ------------------------------------------------------------------
    # Preference extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_primary_challenge_area(
        plan_context: dict[str, Any] | None,
    ) -> str | None:
        if not isinstance(plan_context, dict):
            return None
        user_profile = plan_context.get("user_profile")
        if not isinstance(user_profile, dict):
            return None
        derived = user_profile.get("derived_insights")
        if not isinstance(derived, dict):
            return None
        value = derived.get("primary_challenge_area")
        return str(value).strip() if value else None

    @staticmethod
    def _extract_session_length_preference(
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
    ) -> int | None:
        facts = (plan_context or {}).get("facts") if isinstance(plan_context, dict) else None
        if isinstance(facts, dict):
            raw = facts.get("session_length_preference")
            if isinstance(raw, (int, float)):
                return int(raw)
        preferences = (user_context_payload or {}).get("preferences") if isinstance(user_context_payload, dict) else None
        if isinstance(preferences, dict):
            raw = preferences.get("focus_duration_preference") or preferences.get("session_length_preference")
            if isinstance(raw, (int, float)):
                return int(raw)
        profile = ((plan_context or {}).get("user_profile") or {}).get("preferences_snapshot") if isinstance(plan_context, dict) else None
        if isinstance(profile, dict):
            raw = profile.get("focus_duration_preference") or profile.get("inferred_session_length")
            if isinstance(raw, (int, float)):
                return int(raw)
        return None

    @staticmethod
    def _extract_difficulty_preference(
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
    ) -> float | None:
        facts = (plan_context or {}).get("facts") if isinstance(plan_context, dict) else None
        if isinstance(facts, dict):
            raw = facts.get("difficulty_preference")
            if isinstance(raw, (int, float)):
                return float(raw)
        profile = ((plan_context or {}).get("user_profile") or {}).get("preferences_snapshot") if isinstance(plan_context, dict) else None
        if isinstance(profile, dict):
            raw = profile.get("inferred_difficulty")
            if isinstance(raw, (int, float)):
                return float(raw)
        preferences = (user_context_payload or {}).get("preferences") if isinstance(user_context_payload, dict) else None
        if isinstance(preferences, dict):
            raw = preferences.get("difficulty_preference")
            if isinstance(raw, (int, float)):
                return float(raw)
        return None

    @staticmethod
    def _extract_behavior_pattern_names(
        plan_context: dict[str, Any] | None,
    ) -> list[str]:
        user_profile = (plan_context or {}).get("user_profile") if isinstance(plan_context, dict) else None
        patterns = user_profile.get("behavior_patterns") if isinstance(user_profile, dict) else None
        if not isinstance(patterns, list):
            return []
        names: list[str] = []
        for item in patterns:
            if not isinstance(item, dict):
                continue
            raw = item.get("pattern_name")
            if raw:
                names.append(str(raw).strip())
        return names

    @staticmethod
    def _extract_behavior_pattern_types(
        plan_context: dict[str, Any] | None,
    ) -> dict[str, int]:
        user_profile = (plan_context or {}).get("user_profile") if isinstance(plan_context, dict) else None
        patterns = user_profile.get("behavior_patterns") if isinstance(user_profile, dict) else None
        if not isinstance(patterns, list):
            return {}
        counts: dict[str, int] = {}
        for item in patterns:
            if not isinstance(item, dict):
                continue
            raw = str(item.get("pattern_type") or "").strip().lower()
            if not raw:
                continue
            counts[raw] = counts.get(raw, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Dual-core routing
    # ------------------------------------------------------------------

    async def _build_dual_core_input(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        unified_routing_result: Any | None,
        information_sufficient: bool,
    ) -> DualCoreRoutingInput:
        active_plan_id = plan_id
        if active_plan_id is None:
            active_plans = (user_context_payload or {}).get("active_plans")
            if isinstance(active_plans, list) and active_plans:
                raw_plan_id = active_plans[0].get("id") if isinstance(active_plans[0], dict) else None
                with contextlib.suppress(ValueError, TypeError, AttributeError):
                    active_plan_id = uuid.UUID(str(raw_plan_id))

        plan_health_status: str | None = None
        if active_db and active_plan_id:
            try:
                report = await PlanProgressService(active_db, self.redis).evaluate_progress(
                    uuid.UUID(user_id),
                    active_plan_id,
                )
                plan_health_status = report.severity
            except Exception as e:
                logger.warning(f"Failed to evaluate plan health for dual core routing: {e}")

        return DualCoreRoutingInput(
            intent=(
                unified_routing_result.primary_intent.value
                if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                else "chat"
            ),
            intent_confidence=float(getattr(unified_routing_result, "confidence", 0.5) or 0.5),
            information_sufficient=information_sufficient,
            primary_challenge_area=self._extract_primary_challenge_area(plan_context),
            recent_sentiment_distribution=await self._get_recent_sentiment_distribution(user_id, active_db),
            has_active_plan=bool(active_plan_id),
            plan_health_status=plan_health_status,
            recent_task_feedback_distribution=await self._get_recent_task_feedback_distribution(user_id, active_db),
            behavior_pattern_names=self._extract_behavior_pattern_names(plan_context),
            behavior_pattern_types=self._extract_behavior_pattern_types(plan_context),
            session_length_preference=self._extract_session_length_preference(user_context_payload, plan_context),
            difficulty_preference=self._extract_difficulty_preference(user_context_payload, plan_context),
        )

    async def _emit_dual_core_status(self, decision, stream_callback) -> None:
        stage = "planning"
        headline = "我会直接把目标收敛成可执行方案。"
        detail = decision.reason

        if decision.mode == "cognitive_first":
            stage = "understanding"
            headline = "我先处理你当前的阻力，再一起收紧计划。"
        elif decision.mode == "balanced":
            stage = "reviewing"
            headline = "我会一边推进方案，一边兼顾你当前的状态。"

        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=headline,
                    current_agent_name="Sparkle AI",
                ),
                metadata={
                    "ux_progress": json.dumps(
                        {
                            "stage": stage,
                            "headline": headline,
                            "detail": detail,
                            "is_blocked": False,
                        },
                        ensure_ascii=False,
                    )
                },
            )
        )

    async def _apply_dual_core_routing(
        self,
        *,
        route_decision: RouteDecision,
        state,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        unified_routing_result: Any | None,
        information_sufficient: bool,
        stream_callback,
    ) -> RouteDecision:
        routing_input = await self._build_dual_core_input(
            active_db=active_db,
            user_id=user_id,
            plan_id=plan_id,
            user_context_payload=user_context_payload,
            plan_context=plan_context,
            unified_routing_result=unified_routing_result,
            information_sufficient=information_sufficient,
        )
        if routing_input.intent == "chat" and route_decision.execution_mode == "direct":
            decision = DualCoreDecision(
                mode="execution_first",
                reason="通用知识问答优先直接回答，避免把认知调制或任务背景混入基础解释。",
                cognitive_adjustments=[],
                execution_constraints=[],
            )
        else:
            decision = self.dual_core_router.route(routing_input)
        state.context_data["dual_core_decision"] = decision.to_dict()
        state.context_data["dual_core_prompt_instruction"] = decision.prompt_instruction
        state.context_data["dual_core_signal_snapshot"] = {
            "intent": routing_input.intent,
            "intent_confidence": routing_input.intent_confidence,
            "primary_challenge_area": routing_input.primary_challenge_area,
            "recent_sentiment_distribution": routing_input.recent_sentiment_distribution,
            "recent_task_feedback_distribution": routing_input.recent_task_feedback_distribution,
            "behavior_pattern_names": routing_input.behavior_pattern_names[:5],
            "behavior_pattern_types": routing_input.behavior_pattern_types,
            "plan_health_status": routing_input.plan_health_status,
        }

        await self._emit_dual_core_status(decision, stream_callback)

        if decision.mode == "cognitive_first" and route_decision.execution_mode in ["langgraph", "hybrid"]:
            route_decision.execution_mode = "direct"
            route_decision.reason = (
                f"{route_decision.reason} | dual_core:cognitive_first"
                if route_decision.reason
                else "dual_core:cognitive_first"
            )
        elif decision.mode == "execution_first" and route_decision.reason:
            route_decision.reason = f"{route_decision.reason} | dual_core:execution_first"
        elif decision.mode == "balanced" and route_decision.reason:
            route_decision.reason = f"{route_decision.reason} | dual_core:balanced"

        plan_meta = state.context_data.get("plan_metadata", {})
        if isinstance(plan_meta, dict):
            plan_meta["dual_core_mode"] = decision.mode
            plan_meta["dual_core_reason"] = decision.reason
            state.context_data["plan_metadata"] = plan_meta

        return route_decision

    # ------------------------------------------------------------------
    # Unified routing & classification
    # ------------------------------------------------------------------

    async def _route_and_classify(
        self,
        *,
        user_message: str,
        user_id: str,
        session_id: str,
        grpc_context: dict[str, Any],
        conversation_context: dict[str, Any] | None,
        state,
    ) -> tuple[RouteDecision, Any | None]:
        unified_routing_result = None
        has_summary = self._has_conversation_summary(conversation_context)
        if has_summary:
            ROUTING_SUMMARY_CONTEXT_TOTAL.labels(phase="router_input").inc()
        routing_history = self._build_routing_history(conversation_context)
        try:
            unified_routing_result = await self.unified_router.route(
                message=user_message,
                user_id=user_id,
                session_id=session_id,
                payload=grpc_context,
                conversation_history=routing_history,
            )
            logger.info(
                f"Unified routing: {unified_routing_result.primary_intent.value} "
                f"(confidence={unified_routing_result.confidence:.2f}, "
                f"layer={unified_routing_result.routing_layer})"
            )
        except Exception as e:
            logger.warning(f"Unified routing failed: {e}")

        if unified_routing_result:
            state.context_data["unified_intent"] = {
                "primary_intent": unified_routing_result.primary_intent.value,
                "confidence": unified_routing_result.confidence,
                "routing_layer": unified_routing_result.routing_layer,
                "execution_mode": unified_routing_result.execution_mode,
                "risk_level": unified_routing_result.risk_level,
                "context_signals": unified_routing_result.context_signals,
            }
            if unified_routing_result.primary_intent == UnifiedIntentType.COGNITIVE_PRISM:
                state.context_data["special_intent"] = "cognitive_prism"
            elif unified_routing_result.primary_intent == UnifiedIntentType.TRANSLATION:
                state.context_data["special_intent"] = "translation"
            elif unified_routing_result.primary_intent == UnifiedIntentType.SPRINT_PLAN:
                state.context_data["special_intent"] = "sprint_plan"
            route_decision = to_route_decision(unified_routing_result)
        else:
            route_decision = RouteDecision(
                execution_mode="direct",
                reason="unified:fallback",
                risk_level="low",
                confidence=0.5,
                context_version=None,
            )

        route_decision, adaptive_notes = self._apply_adaptive_routing_policy(
            route_decision=route_decision,
            unified_routing_result=unified_routing_result,
            user_message=user_message,
            conversation_context=conversation_context,
        )
        if adaptive_notes:
            state.context_data["adaptive_routing"] = {
                "notes": adaptive_notes,
                "execution_mode": route_decision.execution_mode,
                "risk_level": route_decision.risk_level,
                "reason": route_decision.reason,
            }
        if unified_routing_result and "unified_intent" in state.context_data:
            state.context_data["unified_intent"]["execution_mode"] = route_decision.execution_mode
            state.context_data["unified_intent"]["risk_level"] = route_decision.risk_level

        state.context_data["plan_metadata"] = {
            "context_version": route_decision.context_version,
            "execution_mode": route_decision.execution_mode,
            "risk_level": route_decision.risk_level,
            "confidence": route_decision.confidence,
            "route_reason": route_decision.reason,
            "routing_layer": unified_routing_result.routing_layer if unified_routing_result else "fallback",
            "adaptive_notes": ",".join(adaptive_notes) if adaptive_notes else "",
            "summary_used_for_routing": "true" if has_summary else "false",
        }
        state.context_data["grounding_validator"] = self.grounding_validator
        return route_decision, unified_routing_result

    # ------------------------------------------------------------------
    # History building & normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _build_routing_history(conversation_context: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(conversation_context, dict):
            return []
        messages = conversation_context.get("messages")
        history: list[dict[str, Any]] = [m for m in messages if isinstance(m, dict)] if isinstance(messages, list) else []
        summary = conversation_context.get("summary")
        if isinstance(summary, str) and summary.strip():
            summary_content = summary.strip()
            if len(summary_content) > 600:
                summary_content = summary_content[:600] + "..."
            history = [{"role": "system", "content": f"Summary of prior conversation: {summary_content}"}] + history
        return history

    @staticmethod
    def _normalize_proto_history(history_messages: list[Any]) -> list[dict[str, Any]]:
        normalized_history: list[dict[str, Any]] = []
        for msg in history_messages or []:
            role = str(getattr(msg, "role", "") or "").strip().lower()
            if not role:
                continue

            history_item: dict[str, Any] = {
                "role": role,
                "content": str(getattr(msg, "content", "") or ""),
            }

            name = str(getattr(msg, "name", "") or "").strip()
            if name:
                history_item["name"] = name

            tool_call_id = str(getattr(msg, "tool_call_id", "") or "").strip()
            if tool_call_id:
                history_item["tool_call_id"] = tool_call_id

            metadata = {
                str(k): str(v)
                for k, v in dict(getattr(msg, "metadata", {}) or {}).items()
            }
            if metadata:
                history_item["metadata"] = metadata
                raw_tool_calls = metadata.get("tool_calls")
                if raw_tool_calls:
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        parsed_tool_calls = json.loads(raw_tool_calls)
                        if isinstance(parsed_tool_calls, list):
                            history_item["tool_calls"] = parsed_tool_calls

            normalized_history.append(history_item)

        return normalized_history

    def _merge_request_history_into_conversation_context(
        self,
        conversation_context: dict[str, Any] | None,
        request_history: list[Any],
    ) -> dict[str, Any]:
        proto_history = self._normalize_proto_history(request_history)
        if not proto_history:
            return conversation_context or {"messages": [], "summary": None}

        merged_context = dict(conversation_context or {"messages": [], "summary": None})
        existing_messages = merged_context.get("messages")
        existing_history = [m for m in existing_messages if isinstance(m, dict)] if isinstance(existing_messages, list) else []

        overlap = 0
        max_overlap = min(len(existing_history), len(proto_history))
        for size in range(max_overlap, 0, -1):
            if existing_history[-size:] == proto_history[:size]:
                overlap = size
                break

        merged_context["messages"] = existing_history + proto_history[overlap:]
        return merged_context

    # ------------------------------------------------------------------
    # Query analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_conversation_summary(conversation_context: dict[str, Any] | None) -> bool:
        if not isinstance(conversation_context, dict):
            return False
        summary = conversation_context.get("summary")
        return isinstance(summary, str) and bool(summary.strip())

    @staticmethod
    def _is_complex_user_query(message: str) -> bool:
        if not message:
            return False
        msg_lower = message.lower()
        complex_keywords = {
            "方案", "策略", "权衡", "分阶段", "multi-step", "tradeoff", "design", "architecture",
            "学习计划", "复习计划", "错误诊断", "knowledge graph", "then", "after that", "首先", "然后", "接着",
        }
        if any(keyword in msg_lower for keyword in complex_keywords):
            return True
        sentence_count = (
            message.count("。")
            + message.count(".")
            + message.count("!")
            + message.count("?")
            + message.count("！")
            + message.count("？")
        )
        return len(message) > 90 and sentence_count >= 2

    @staticmethod
    def _is_context_dependent_query(message: str) -> bool:
        if not message:
            return False
        msg_lower = message.lower()
        context_markers = {
            "继续", "接着", "刚才", "上面", "这个", "那个", "如前所述", "继续上次",
            "continue", "as above", "that one", "the previous", "what we discussed",
        }
        return any(marker in msg_lower for marker in context_markers)

    @staticmethod
    def _extract_route_intent(reason: str) -> str:
        if not reason:
            return "unknown"
        reason_lc = str(reason).lower()
        if reason_lc.startswith("unified:"):
            return reason_lc.split(":", 1)[1] or "unknown"
        if reason_lc.startswith("adaptive:"):
            parts = reason_lc.split(":")
            if len(parts) >= 3:
                return parts[-1] or "unknown"
        if ":" in reason_lc:
            return reason_lc.split(":", 1)[0]
        return reason_lc

    # ------------------------------------------------------------------
    # Adaptive routing policy
    # ------------------------------------------------------------------

    def _apply_adaptive_routing_policy(
        self,
        *,
        route_decision: RouteDecision,
        unified_routing_result: Any | None,
        user_message: str,
        conversation_context: dict[str, Any] | None,
    ) -> tuple[RouteDecision, list[str]]:
        notes: list[str] = []
        if not route_decision:
            return route_decision, notes

        confidence = route_decision.confidence if route_decision.confidence is not None else 0.5
        is_complex = self._is_complex_user_query(user_message)
        is_context_dependent = self._is_context_dependent_query(user_message)
        has_summary = bool(isinstance(conversation_context, dict) and str(conversation_context.get("summary") or "").strip())

        inferred_intent = (
            unified_routing_result.primary_intent.value
            if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
            else self._extract_route_intent(route_decision.reason)
        )

        if route_decision.risk_level != "high" and route_decision.execution_mode == "direct":
            if confidence < 0.6 and is_complex:
                from_mode = route_decision.execution_mode
                route_decision.execution_mode = "hybrid"
                if route_decision.risk_level == "low":
                    route_decision.risk_level = "medium"
                route_decision.reason = f"adaptive:low_confidence_complex:{inferred_intent}"
                notes.append("upgraded_to_hybrid_low_confidence_complex")
                ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                    action="upgrade",
                    trigger="low_confidence_complex",
                    from_mode=from_mode,
                    to_mode=route_decision.execution_mode,
                ).inc()
            elif confidence < 0.7 and is_context_dependent and has_summary:
                from_mode = route_decision.execution_mode
                route_decision.execution_mode = "hybrid"
                route_decision.reason = f"adaptive:context_continuity:{inferred_intent}"
                notes.append("upgraded_to_hybrid_context_continuity")
                ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                    action="upgrade",
                    trigger="context_continuity",
                    from_mode=from_mode,
                    to_mode=route_decision.execution_mode,
                ).inc()

        if route_decision.execution_mode == "hybrid" and confidence >= 0.92 and not is_complex and not is_context_dependent:
            from_mode = route_decision.execution_mode
            route_decision.execution_mode = "direct"
            route_decision.reason = f"adaptive:high_confidence_simple:{inferred_intent}"
            notes.append("downgraded_to_direct_high_confidence_simple")
            ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                action="downgrade",
                trigger="high_confidence_simple",
                from_mode=from_mode,
                to_mode=route_decision.execution_mode,
            ).inc()

        return route_decision, notes

    # ------------------------------------------------------------------
    # Mode strategy & suggestions
    # ------------------------------------------------------------------

    def _apply_mode_strategy_override(
        self,
        *,
        chat_mode: str,
        route_decision: RouteDecision,
        user_message: str,
    ) -> tuple[RouteDecision, dict[str, Any] | None]:
        strategy = get_mode_strategy(chat_mode)
        if not strategy:
            return route_decision, None

        metadata: dict[str, Any] = {
            "chat_mode": strategy.chat_mode,
            "required_agents": list(strategy.required_agents),
            "preferred_agents": list(strategy.preferred_agents),
            "collaboration_mode": strategy.collaboration_mode,
            "review_strictness": strategy.review_strictness,
            "require_alignment_check": strategy.require_alignment_check,
            "output_structure": list(strategy.output_structure),
            "synthesis_instruction": str(strategy.synthesis_instruction or "").strip(),
        }

        if strategy.force_execution_mode:
            route_decision.execution_mode = strategy.force_execution_mode
            route_decision.reason = f"mode_strategy:forced:{strategy.chat_mode}"

        threshold = strategy.min_confidence_for_direct
        if (
            threshold is not None
            and route_decision.execution_mode == "hybrid"
            and route_decision.confidence >= threshold
            and not self._is_complex_user_query(user_message)
            and not self._is_context_dependent_query(user_message)
        ):
            route_decision.execution_mode = "direct"
            route_decision.reason = f"mode_strategy:direct_threshold:{strategy.chat_mode}"
            metadata["direct_threshold_applied"] = threshold

        return route_decision, metadata

    def _suggest_mode_switch(
        self,
        *,
        intent: Any,
        confidence: float,
        context_signals: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        intent_value = intent.value if hasattr(intent, "value") else str(intent or "")
        intent_value = intent_value.strip().lower()
        if confidence < 0.75:
            return None
        intent_mode_map = {
            "plan": ("study_plan", "检测到你在制定学习计划，切换到「学习规划」模式可以调用多专家协作。"),
            "sprint_plan": ("study_plan", "检测到你在做冲刺安排，切换到「学习规划」模式更适合拆解节奏。"),
            "error_diagnosis": ("error_diagnosis", "检测到你在分析错误原因，切换到「错因诊断」模式会更深入。"),
            "knowledge": ("deep_analysis", "这个问题偏复杂，切换到「深度分析」模式可以更系统地拆解。"),
            "learn": ("deep_analysis", "检测到你需要深入理解，切换到「深度分析」模式可以给出完整证据链。"),
            "review": ("deep_analysis", "检测到你需要复盘总结，切换到「深度分析」模式可以做更完整的结构化整理。"),
        }
        if intent_value not in intent_mode_map:
            return None
        suggested_mode, reason = intent_mode_map[intent_value]
        return {
            "suggested_mode": suggested_mode,
            "reason": reason,
            "intent": intent_value,
            "confidence": round(float(confidence), 4),
            "context_signals": context_signals or {},
        }

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _execution_mode_label(execution_mode: str) -> str:
        if execution_mode == "langgraph":
            return "系统编排"
        if execution_mode == "hybrid":
            return "混合执行"
        return "直接回答"

    @staticmethod
    def _dual_core_mode_label(mode: str) -> str:
        if mode == "cognitive_first":
            return "认知优先"
        if mode == "execution_first":
            return "执行优先"
        return "双核平衡"
