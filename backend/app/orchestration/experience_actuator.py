from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from loguru import logger

from app.services.capability_knob_governor import CapabilityKnobGovernor
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.intervention_feedback_binding_service import InterventionFeedbackBindingService
from app.services.user_strategy_state_service import UserStrategyStateService
from app.tools.material_retrieval_tools import _resolve_scoped_files


AUTO_STRATEGY_CONFIDENCE_MIN = 0.65
AUTO_GROUNDING_LIMIT = 3
AUTO_GROUNDING_THRESHOLD = 0.35

_HELPED_PHRASES = (
    "这有帮助",
    "这个有帮助",
    "这有用",
    "这个有用",
    "这样可以",
    "这样就能开始",
    "这样我能开始",
    "这样轻一点我就能开始",
    "现在能开始了",
    "this helps",
    "that helped",
)
_ACCEPTED_PHRASES = (
    "我试试",
    "那我按这个来",
    "我按这个来",
    "我先这样做",
    "那就这样",
    "我先照这个",
    "i'll try that",
)
_NOT_HELPED_PHRASES = (
    "没帮助",
    "没帮到我",
    "没有帮助",
    "没有帮到我",
    "这没用",
    "这个没用",
    "还是不行",
    "还是开始不了",
    "还是启动不了",
    "还是卡住",
    "that did not help",
    "still stuck",
)
_DISMISSED_PHRASES = (
    "不要这个",
    "别这样",
    "不用这个",
    "不想这样",
    "这不适合我",
    "not this",
)
_SNOOZE_PHRASES = (
    "先不",
    "晚点再说",
    "之后再说",
    "回头再说",
    "明天再说",
    "later",
)
_MIXED_MARKERS = (
    "但是",
    "但",
    "不过",
    "只是",
    "still",
    "but",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _compact_text(value: Any, *, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        try:
            return round(float(left), 3) == round(float(right), 3)
        except (TypeError, ValueError):
            return False
    return left == right


def _contains_any(text: str, phrases: tuple[str, ...]) -> str | None:
    for phrase in phrases:
        if phrase in text:
            return phrase
    return None


def _serialize_adjustment_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "field": _strip(entry.get("field")),
        "layer": _strip(entry.get("layer")),
        "old_value": entry.get("old_value"),
        "new_value": entry.get("new_value"),
        "confidence": entry.get("confidence"),
        "timestamp": entry.get("timestamp"),
        "expires_at": entry.get("expires_at"),
    }


_FIELD_LABELS = {
    "difficulty_level": "难度先降了一档",
    "session_mode": "会话节奏改得更贴近你现在的状态",
    "explanation_style": "解释方式改成更慢一步",
    "retrieval_emphasis": "优先按你的资料来校准",
    "push_vs_support": "推进力度先放轻一点",
    "intervention_intensity": "干预强度先调低",
}


def _describe_adjustment_field(field: str, new_value: Any) -> str:
    label = _FIELD_LABELS.get(field)
    if label:
        return label
    normalized = field.replace("_", " ").strip()
    if not normalized:
        return "做了一个轻量调整"
    return f"{normalized} -> {new_value}"


def _build_opening_copy(*, experience_mode: str, what_matters_now: str, adjustment_bits: list[str]) -> str:
    first_adjustment = adjustment_bits[0] if adjustment_bits else ""
    if experience_mode == "stabilize":
        return (
            f"我先把这轮放轻一点，因为现在更重要的是先能开始。{first_adjustment}".strip()
            if first_adjustment
            else "我先把这轮放轻一点，因为现在更重要的是先能开始。"
        )
    if experience_mode == "mobilize":
        return (
            f"我先把它收成一个更容易落地的下一步，因为你已经接近能动起来了。{first_adjustment}".strip()
            if first_adjustment
            else "我先把它收成一个更容易落地的下一步，因为你已经接近能动起来了。"
        )
    if experience_mode == "explain":
        return (
            f"我先按你的材料把真正卡住的点校准清楚，因为现在最重要的是别让误解继续滚大。{first_adjustment}".strip()
            if first_adjustment
            else "我先按你的材料把真正卡住的点校准清楚，因为现在最重要的是别让误解继续滚大。"
        )
    if experience_mode == "decide":
        return (
            "我先帮你把判断标准摆清楚，再决定往哪边走，这样不容易被我替你做决定。"
        )
    if experience_mode == "reframe":
        return (
            "我会先用证据把这件事放稳一点，不急着给你施压。"
        )
    if what_matters_now:
        return f"我先顺着现在最重要的部分来帮你收紧：{what_matters_now}"
    return "我先按这轮真正重要的部分来帮你调整。"


def detect_intervention_feedback_signal(
    *,
    user_message: str,
    active_interventions: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if not active_interventions:
        return None

    message = _normalize_text(user_message)
    if not message:
        return None

    helped = _contains_any(message, _HELPED_PHRASES)
    negative = _contains_any(message, _NOT_HELPED_PHRASES)
    dismissed = _contains_any(message, _DISMISSED_PHRASES)
    snoozed = _contains_any(message, _SNOOZE_PHRASES)
    accepted = _contains_any(message, _ACCEPTED_PHRASES)
    mixed_marker = _contains_any(message, _MIXED_MARKERS)

    if helped and negative:
        return {"sentiment": "mixed", "confidence": 0.73, "trigger": mixed_marker or helped}
    if mixed_marker and (helped or negative):
        return {"sentiment": "mixed", "confidence": 0.72, "trigger": mixed_marker}
    if dismissed:
        return {"sentiment": "dismissed", "confidence": 0.84, "trigger": dismissed}
    if snoozed:
        return {"sentiment": "snoozed", "confidence": 0.8, "trigger": snoozed}
    if negative:
        return {"sentiment": "not_helped", "confidence": 0.87, "trigger": negative}
    if helped:
        return {"sentiment": "helped", "confidence": 0.88, "trigger": helped}
    if accepted:
        return {"sentiment": "accepted", "confidence": 0.8, "trigger": accepted}
    return None


class ExperienceActuator:
    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis

    async def apply(
        self,
        *,
        user_id: str,
        session_id: str | None,
        plan_id: UUID | None,
        request_id: str | None,
        user_message: str,
        file_ids: list[str] | None,
        user_context_payload: dict[str, Any] | None,
        use_document_context: bool | None = None,
        context_targets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        user_context = user_context_payload if isinstance(user_context_payload, dict) else None
        if user_context is None:
            return {}

        decision_context = user_context.get("residual_decision_context")
        if not isinstance(decision_context, dict):
            situation_brief = user_context.get("situation_brief")
            if isinstance(situation_brief, dict):
                decision_context = situation_brief.get("decision_context")
        if not isinstance(decision_context, dict):
            return {}

        targets = [user_context, *[item for item in (context_targets or []) if isinstance(item, dict)]]
        runtime_summary: dict[str, Any] = {
            "applied_at": _utcnow().isoformat(),
        }

        strategy_runtime = await self._apply_strategy_adjustments(
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
            decision_context=decision_context,
            user_context=user_context,
        )
        if strategy_runtime:
            runtime_summary["auto_strategy_adjustments"] = strategy_runtime
            self._write_targets(
                targets,
                {
                    "user_strategy_state": user_context.get("user_strategy_state"),
                    "user_strategy_history": user_context.get("user_strategy_history", []),
                },
            )
            decision_context["auto_applied_adjustments"] = strategy_runtime

        feedback_runtime = await self._bind_intervention_feedback(
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            user_message=user_message,
            user_context=user_context,
        )
        if feedback_runtime:
            runtime_summary["auto_feedback_binding"] = feedback_runtime
            self._write_targets(
                targets,
                {
                    "active_interventions": user_context.get("active_interventions", []),
                    "active_intervention_id": user_context.get("active_intervention_id"),
                    "last_feedback_binding": user_context.get("last_feedback_binding"),
                },
            )
            decision_context["auto_feedback_binding"] = feedback_runtime

        grounding_runtime = None
        if use_document_context is False:
            logger.info("Document grounding skipped: use_document_context=false session_id={}", session_id)
        else:
            grounding_runtime = await self._ground_with_user_materials(
                user_id=user_id,
                file_ids=file_ids,
                user_message=user_message,
                decision_context=decision_context,
                user_context=user_context,
            )
        if grounding_runtime:
            runtime_summary["user_material_grounding"] = grounding_runtime
            self._write_targets(targets, {"user_material_grounding": grounding_runtime})
            decision_context["grounding_runtime"] = {
                "status": grounding_runtime.get("status"),
                "query": grounding_runtime.get("query"),
                "result_count": len(_as_list(grounding_runtime.get("results"))),
            }

        visible_adaptation = self._build_visible_adaptation(
            decision_context=decision_context,
            runtime_summary=runtime_summary,
            user_context=user_context,
        )
        if visible_adaptation:
            runtime_summary["visible_adaptation"] = visible_adaptation
            self._write_targets(targets, {"visible_adaptation": visible_adaptation})
            decision_context["visible_adaptation"] = visible_adaptation

            if not _strip(user_context.get("proactive_opening_message")):
                self._write_targets(targets, {"proactive_opening_message": visible_adaptation.get("opening_message")})
            if not _strip(user_context.get("post_adaptation_question")):
                self._write_targets(targets, {"post_adaptation_question": visible_adaptation.get("follow_up_question")})

        if len(runtime_summary) == 1:
            return {}

        self._write_targets(
            targets,
            {
                "experience_phase_runtime": runtime_summary,
                "residual_decision_context": decision_context,
            },
        )
        self._sync_situation_brief(targets, decision_context)
        return runtime_summary

    async def _apply_strategy_adjustments(
        self,
        *,
        user_id: str,
        session_id: str | None,
        plan_id: UUID | None,
        decision_context: dict[str, Any],
        user_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        confidence = float(decision_context.get("confidence") or 0.0)
        if confidence < AUTO_STRATEGY_CONFIDENCE_MIN or not _strip(session_id):
            return []

        strategy_state = _as_dict(user_context.get("user_strategy_state"))
        direct_adjustments = [
            item
            for item in _as_list(decision_context.get("system_adjustments"))
            if isinstance(item, dict)
        ]
        capability_adjustments = [
            item
            for item in _as_list(decision_context.get("capability_bounded_adjustments"))
            if isinstance(item, dict)
        ]
        if not direct_adjustments and not capability_adjustments:
            return []

        governed = CapabilityKnobGovernor().evaluate(
            adjustments=[*direct_adjustments, *capability_adjustments],
            strategy_state=strategy_state,
        )
        adjustments = [
            item
            for item in _as_list(governed.get("allowed_adjustments"))
            if isinstance(item, dict)
            and _strip(item.get("target_layer")) == UserStrategyStateService.SESSION_LAYER
            and bool(item.get("reversible"))
        ]
        blocked_adjustments = [
            item for item in _as_list(governed.get("blocked_adjustments")) if isinstance(item, dict)
        ]
        if blocked_adjustments:
            decision_context["blocked_capability_adjustments"] = blocked_adjustments
        if not adjustments:
            return []

        changes: dict[str, Any] = {}
        pending: list[dict[str, Any]] = []
        for item in adjustments:
            field = _strip(item.get("field"))
            if not field:
                continue
            recommended_value = item.get("recommended_value")
            if _same_value(strategy_state.get(field), recommended_value):
                continue
            changes[field] = recommended_value
            pending.append(
                {
                    "field": field,
                    "old_value": strategy_state.get(field),
                    "new_value": recommended_value,
                    "reason": _strip(item.get("reason")),
                    "confidence_gate": item.get("confidence_gate"),
                    "source": _strip(item.get("source")),
                }
            )

        if not changes:
            return []

        service = UserStrategyStateService(self.db, self.redis)
        try:
            result = await service.apply_adjustment(
                UUID(str(user_id)),
                changes,
                layer=UserStrategyStateService.SESSION_LAYER,
                reason=(
                    f"phase4_auto:{_strip(decision_context.get('experience_mode')) or 'guided'}:"
                    f"{_strip(decision_context.get('intervention_family')) or 'general'}"
                ),
                evidence={
                    "source": "phase4_experience_actuator",
                    "primary_residual": _strip(decision_context.get("primary_residual")),
                    "loop_type": _strip(decision_context.get("loop_type")),
                    "what_matters_now": _compact_text(decision_context.get("what_matters_now"), limit=180),
                },
                confidence=confidence,
                session_id=session_id,
                plan_id=plan_id,
            )
            recent_changes = await service.get_recent_changes(
                UUID(str(user_id)),
                plan_id=plan_id,
                session_id=session_id,
                limit=6,
            )
        except Exception as exc:
            logger.warning(f"Phase 4 auto strategy adjustment failed: {exc}")
            return []

        user_context["user_strategy_state"] = result.get("effective_state") if isinstance(result, dict) else strategy_state
        if recent_changes:
            user_context["user_strategy_history"] = recent_changes

        applied = [
            _serialize_adjustment_summary(item)
            for item in _as_list((result or {}).get("applied"))
            if isinstance(item, dict)
        ]
        if applied:
            return applied
        return pending

    async def _bind_intervention_feedback(
        self,
        *,
        user_id: str,
        session_id: str | None,
        request_id: str | None,
        user_message: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        active_interventions = [
            item for item in _as_list(user_context.get("active_interventions")) if isinstance(item, dict)
        ]
        detected = detect_intervention_feedback_signal(
            user_message=user_message,
            active_interventions=active_interventions,
        )
        if detected is None:
            return None

        binding_service = InterventionFeedbackBindingService(self.db, self.redis)
        try:
            result = await binding_service.bind_feedback(
                user_id=UUID(str(user_id)),
                session_id=session_id,
                sentiment=_strip(detected.get("sentiment")),
                user_words=_compact_text(user_message, limit=600),
                confidence=float(detected.get("confidence") or 0.0),
                message_id=request_id,
                source="phase4_auto_feedback",
                runtime_active_interventions=active_interventions,
            )
        except Exception as exc:
            logger.warning(f"Phase 4 auto feedback binding failed: {exc}")
            return None

        active_after = result.get("active_interventions")
        if isinstance(active_after, list):
            user_context["active_interventions"] = active_after
            active_intervention_id = (
                _strip(active_after[0].get("intervention_id")) if active_after and isinstance(active_after[0], dict) else ""
            )
            if active_intervention_id:
                user_context["active_intervention_id"] = active_intervention_id
            elif "active_intervention_id" in user_context:
                user_context.pop("active_intervention_id", None)

        last_feedback_binding = result.get("last_feedback_binding")
        if isinstance(last_feedback_binding, dict):
            user_context["last_feedback_binding"] = last_feedback_binding
        else:
            user_context.pop("last_feedback_binding", None)

        return {
            "detected_sentiment": _strip(detected.get("sentiment")),
            "confidence": round(float(detected.get("confidence") or 0.0), 2),
            "trigger": _strip(detected.get("trigger")),
            "bound": bool(result.get("bound")),
            "duplicate_suppressed": bool(result.get("duplicate_suppressed")),
            "reason": _strip(result.get("reason")),
            "intervention_id": _strip(_as_dict(result.get("last_feedback_binding")).get("intervention_id")),
        }

    async def _ground_with_user_materials(
        self,
        *,
        user_id: str,
        file_ids: list[str] | None,
        user_message: str,
        decision_context: dict[str, Any],
        user_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        grounding_priority = [str(item).strip() for item in _as_list(decision_context.get("grounding_priority")) if str(item).strip()]
        strategy_state = _as_dict(user_context.get("user_strategy_state"))
        should_ground = (
            (grounding_priority and grounding_priority[0] == "user_materials")
            or _strip(strategy_state.get("retrieval_emphasis")) == "user_materials"
        )
        if not should_ground:
            return None

        query = self._build_grounding_query(
            user_message=user_message,
            user_context=user_context,
            decision_context=decision_context,
        )
        if not query:
            return None

        try:
            scoped_files = await _resolve_scoped_files(
                self.db,
                user_id=UUID(str(user_id)),
                requested_file_ids=file_ids,
            )
        except Exception as exc:
            logger.warning(f"Phase 4 user-material file resolution failed: {exc}")
            return {
                "status": "file_resolution_failed",
                "query": query,
                "results": [],
            }

        if not scoped_files:
            return {
                "status": "no_scoped_files",
                "query": query,
                "results": [],
                "scoped_file_count": 0,
            }

        try:
            retrieval = KnowledgeRetrievalService(self.db)
            results = await retrieval.document_vector_search(
                user_id=UUID(str(user_id)),
                query=query,
                file_ids=[file.id for file in scoped_files],
                vector_query=query,
                limit=AUTO_GROUNDING_LIMIT,
                threshold=AUTO_GROUNDING_THRESHOLD,
            )
        except Exception as exc:
            logger.warning(f"Phase 4 user-material grounding failed: {exc}")
            return {
                "status": "retrieval_failed",
                "query": query,
                "results": [],
                "scoped_file_count": len(scoped_files),
            }

        return {
            "status": "grounded" if results else "no_hits",
            "query": query,
            "scoped_file_count": len(scoped_files),
            "scoped_files": [
                {
                    "file_id": str(file.id),
                    "file_name": _strip(getattr(file, "file_name", "")),
                    "mime_type": _strip(getattr(file, "mime_type", "")),
                }
                for file in scoped_files[:10]
            ],
            "results": [
                {
                    "chunk_id": str(getattr(getattr(item, "chunk", None), "id", "") or ""),
                    "file_id": str(getattr(getattr(item, "chunk", None), "file_id", "") or ""),
                    "file_name": _strip(getattr(item, "file_name", "")),
                    "section_title": _strip(getattr(getattr(item, "chunk", None), "section_title", "")),
                    "page_numbers": list(getattr(getattr(item, "chunk", None), "page_numbers", []) or []),
                    "score": round(float(getattr(item, "score", 0.0) or 0.0), 4),
                    "snippet": _compact_text(getattr(getattr(item, "chunk", None), "content", ""), limit=320),
                }
                for item in results[:AUTO_GROUNDING_LIMIT]
            ],
        }

    @staticmethod
    def _build_grounding_query(
        *,
        user_message: str,
        user_context: dict[str, Any],
        decision_context: dict[str, Any],
    ) -> str:
        candidates: list[str] = []
        for raw in (
            user_context.get("current_query"),
            user_message,
            decision_context.get("what_matters_now"),
            _as_dict(user_context.get("primary_obstacle")).get("summary"),
        ):
            text = _compact_text(raw, limit=180)
            if not text or text in candidates:
                continue
            candidates.append(text)
        return _compact_text("；".join(candidates[:3]), limit=320)

    @staticmethod
    def _write_targets(targets: list[dict[str, Any]], values: dict[str, Any]) -> None:
        for target in targets:
            if not isinstance(target, dict):
                continue
            for key, value in values.items():
                if value is None:
                    continue
                target[key] = value

    @staticmethod
    def _sync_situation_brief(targets: list[dict[str, Any]], decision_context: dict[str, Any]) -> None:
        for target in targets:
            situation_brief = target.get("situation_brief")
            if isinstance(situation_brief, dict):
                situation_brief["decision_context"] = decision_context

    def _build_visible_adaptation(
        self,
        *,
        decision_context: dict[str, Any],
        runtime_summary: dict[str, Any],
        user_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        adjustments = [
            item
            for item in _as_list(runtime_summary.get("auto_strategy_adjustments"))
            if isinstance(item, dict) and _strip(item.get("field"))
        ]
        feedback_runtime = _as_dict(runtime_summary.get("auto_feedback_binding"))
        grounding_runtime = _as_dict(runtime_summary.get("user_material_grounding"))
        feedback_hook = _as_dict(decision_context.get("feedback_hook"))
        experience_mode = _strip(decision_context.get("experience_mode"))
        what_matters_now = _strip(decision_context.get("what_matters_now"))
        primary_residual = _strip(decision_context.get("primary_residual"))

        if not adjustments and not feedback_runtime and not grounding_runtime:
            return None

        adjustment_bits = [
            _describe_adjustment_field(_strip(item.get("field")), item.get("new_value"))
            for item in adjustments
            if _strip(item.get("field"))
        ]
        summary_bits: list[str] = []
        if what_matters_now:
            summary_bits.append(what_matters_now)
        if adjustment_bits:
            summary_bits.append("这轮我先做了更轻、更可逆的调整。")
        if feedback_runtime.get("bound"):
            summary_bits.append("我也记住了刚才那个调整对你是有帮助的。")
        if grounding_runtime.get("status") == "grounded":
            summary_bits.append("解释会优先按你的材料来，不先用泛化说法盖过去。")

        evidence_summary = ""
        if grounding_runtime.get("status") == "grounded":
            results = [
                item for item in _as_list(grounding_runtime.get("results")) if isinstance(item, dict)
            ]
            first = results[0] if results else {}
            file_name = _strip(first.get("file_name"))
            section_title = _strip(first.get("section_title"))
            if file_name or section_title:
                evidence_summary = f"这轮证据先来自你的资料：{file_name or '用户材料'} {section_title}".strip()
        elif feedback_runtime.get("bound"):
            evidence_summary = f"我根据你刚才的反馈做了保留：{_strip(feedback_runtime.get('trigger'))}"

        follow_up_question = _strip(feedback_hook.get("ask"))
        title = {
            "R_e": "我先把真正卡住的点校准清楚",
            "R_c": "我先把负荷调到更能动起来的水平",
            "R_n": "我先把判断标准摆出来",
            "R_i": "我先把这件事放回证据里",
        }.get(primary_residual, "我先做了一个更贴近你的调整")

        return {
            "title": title,
            "summary": " ".join(bit for bit in summary_bits if bit).strip(),
            "opening_message": _build_opening_copy(
                experience_mode=experience_mode,
                what_matters_now=what_matters_now,
                adjustment_bits=adjustment_bits,
            ),
            "what_changed": adjustment_bits[:4],
            "reversibility_note": "如果这次调整不合适，我们可以再改，不会把你锁死在这条路上。",
            "follow_up_question": follow_up_question,
            "evidence_summary": evidence_summary,
            "experience_mode": experience_mode,
            "intervention_family": _strip(decision_context.get("intervention_family")),
        }
