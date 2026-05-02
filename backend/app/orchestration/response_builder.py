"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import COLLABORATION_LATENCY
from app.core.metrics import (
    ACTIVE_SESSIONS,
    AI_RESPONSE_TOTAL_DURATION,
    REQUEST_LATENCY,
    RESPONSE_FALLBACK_GENERATED_TOTAL,
    SESSION_FEEDBACK_VISIBLE_HINT_TOTAL,
)
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
    def _memory_value(item: Any, *keys: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            for key in keys:
                value = item.get(key)
                if value not in (None, ""):
                    return value
            return default
        for key in keys:
            value = getattr(item, key, None)
            if value not in (None, ""):
                return value
        return default

    @staticmethod
    def _memory_reference_confidence(item: Any) -> float:
        for key in ("confidence", "reference_confidence", "evidence_score", "importance_score", "score"):
            value = ResponseBuilderMixin._memory_value(item, key)
            if value is None:
                continue
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                continue
            if parsed > 1.0:
                parsed = parsed / 100.0
            return max(0.0, min(1.0, parsed))
        return 0.5

    @staticmethod
    def _memory_reference_user_confirmed(item: Any) -> bool:
        explicit = ResponseBuilderMixin._memory_value(item, "user_confirmed", "confirmed", "explicitly_confirmed")
        if isinstance(explicit, bool):
            return explicit
        if isinstance(explicit, str):
            lowered = explicit.strip().lower()
            if lowered in {"true", "1", "yes", "confirmed", "user_confirmed"}:
                return True
            if lowered in {"false", "0", "no", "inferred", "system_inferred"}:
                return False
        source_lane = str(ResponseBuilderMixin._memory_value(item, "source_lane", default="") or "").strip()
        source_type = str(ResponseBuilderMixin._memory_value(item, "source_type", "source", default="") or "").strip()
        return source_lane != "inferred_extraction" and source_type not in {
            "ai_inferred",
            "analysis",
            "prediction",
            "system_inferred",
        }

    @staticmethod
    def _memory_reference_source_label(item: Any) -> str:
        source_lane = str(ResponseBuilderMixin._memory_value(item, "source_lane", default="") or "").strip().lower()
        source_type = (
            str(ResponseBuilderMixin._memory_value(item, "source_type", "source", default="") or "").strip().lower()
        )
        subject_type = str(ResponseBuilderMixin._memory_value(item, "subject_type", default="") or "").strip().lower()
        if source_lane == "inferred_extraction" or source_type in {"ai_inferred", "analysis", "system_inferred"}:
            return "从对话里推断的"
        if source_type in {"task", "practice_outcome"} or subject_type in {"task", "commitment"}:
            return "从任务完成情况推断的"
        if source_type in {"chat_turn", "user_state", "event", "manual", "direct_capture", "user_confirmed"}:
            return "你告诉我的"
        return "上下文里整理出的"

    @staticmethod
    def _parse_memory_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            raw = str(value or "").strip()
            if not raw:
                return None
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _memory_time_ago(value: Any) -> str:
        occurred_at = ResponseBuilderMixin._parse_memory_datetime(value)
        if occurred_at is None:
            return "时间未知"
        delta = datetime.now(UTC).replace(tzinfo=None) - occurred_at
        if delta.total_seconds() < 2 * 3600:
            return "刚才"
        if delta.days == 0:
            return "今天"
        if delta.days == 1:
            return "昨天"
        if delta.days <= 6:
            return f"{delta.days}天前"
        if delta.days <= 13:
            return "上周"
        return occurred_at.date().isoformat()

    @staticmethod
    def _memory_reference_tokens(text: str) -> set[str]:
        normalized = str(text or "").lower()
        tokens = set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", normalized))
        for segment in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
            if len(segment) <= 4:
                tokens.add(segment)
            for index in range(0, max(0, len(segment) - 1)):
                tokens.add(segment[index : index + 2])
        return {token for token in tokens if token.strip()}

    @staticmethod
    def _memory_was_naturally_referenced(summary: str, response_text: str) -> bool:
        normalized_summary = re.sub(r"\s+", "", str(summary or "")).lower()
        normalized_response = re.sub(r"\s+", "", str(response_text or "")).lower()
        if not normalized_summary or not normalized_response:
            return False
        if len(normalized_summary) >= 4 and normalized_summary in normalized_response:
            return True
        summary_tokens = ResponseBuilderMixin._memory_reference_tokens(summary)
        response_tokens = ResponseBuilderMixin._memory_reference_tokens(response_text)
        if not summary_tokens or not response_tokens:
            return False
        overlap = summary_tokens & response_tokens
        return any(len(token) >= 3 for token in overlap) or len(overlap) >= 2

    @staticmethod
    def _memory_candidate_relevance(entry: tuple[int, Any]) -> tuple[float, int]:
        index, item = entry
        for key in ("relevance_score", "rank_score", "score", "importance_score", "confidence", "evidence_score"):
            value = ResponseBuilderMixin._memory_value(item, key)
            if value is None:
                continue
            try:
                return (-float(value), index)
            except (TypeError, ValueError):
                continue
        return (0.0, index)

    @staticmethod
    def _collect_memory_reference_candidates(
        *,
        user_context_payload: dict[str, Any] | None,
        context_data: dict[str, Any],
    ) -> list[Any]:
        pools: list[Any] = []
        focused_memory = context_data.get("focused_memory")
        if isinstance(focused_memory, dict):
            pools.append(focused_memory.get("episodic_memories"))
        if isinstance(user_context_payload, dict):
            pools.extend(
                [
                    user_context_payload.get("episodic_memories"),
                    user_context_payload.get("past_session_memory"),
                ]
            )
        candidates: list[Any] = []
        seen: set[str] = set()
        for pool in pools:
            if not isinstance(pool, list):
                continue
            for item in pool:
                summary = str(
                    ResponseBuilderMixin._memory_value(item, "summary", "content", "text", "title", default="") or ""
                ).strip()
                if not summary:
                    continue
                key = str(ResponseBuilderMixin._memory_value(item, "id", default="") or summary)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(item)
        return [
            item
            for _, item in sorted(
                enumerate(candidates),
                key=ResponseBuilderMixin._memory_candidate_relevance,
            )[:5]
        ]

    @staticmethod
    def _build_memory_reference_receipt(
        *,
        full_response: str,
        user_context_payload: dict[str, Any] | None,
        context_data: dict[str, Any],
        response_id: str,
    ) -> dict[str, Any] | None:
        referenced: list[dict[str, Any]] = []
        for item in ResponseBuilderMixin._collect_memory_reference_candidates(
            user_context_payload=user_context_payload,
            context_data=context_data,
        ):
            summary = str(
                ResponseBuilderMixin._memory_value(item, "summary", "content", "text", "title", default="") or ""
            ).strip()
            if not ResponseBuilderMixin._memory_was_naturally_referenced(summary, full_response):
                continue
            referenced.append(
                {
                    "id": str(ResponseBuilderMixin._memory_value(item, "id", default="") or ""),
                    "type": "episodic",
                    "content": summary,
                    "time_ago": ResponseBuilderMixin._memory_time_ago(
                        ResponseBuilderMixin._memory_value(
                            item,
                            "occurred_at",
                            "last_seen_at",
                            "updated_at",
                            "created_at",
                        )
                    ),
                    "source": ResponseBuilderMixin._memory_reference_source_label(item),
                    "confidence": ResponseBuilderMixin._memory_reference_confidence(item),
                    "user_confirmed": ResponseBuilderMixin._memory_reference_user_confirmed(item),
                    "outcome": "pending",
                }
            )
            if len(referenced) >= 5:
                break

        if not referenced:
            return None
        return {
            "receipt_type": "memory_reference_receipt",
            "response_id": response_id,
            "used_count": len(referenced),
            "decision_reason": "Aurora 引用了和本轮有关的记忆，让回复能接上你的真实上下文。",
            "memory_reference_outcome": "pending",
            "supported_outcomes": ["accepted", "corrected", "ignored", "denied"],
            "referenced_memories": referenced,
        }

    @staticmethod
    def _decode_receipt_payload(raw: Any) -> Any:
        if raw is None:
            return None
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    @staticmethod
    def _receipt_summary(payload: dict[str, Any], *keys: str, default: str = "") -> str:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return default

    @staticmethod
    def _append_unified_receipt(receipts: list[dict[str, Any]], receipt: dict[str, Any] | None) -> None:
        if not receipt:
            return
        receipt_type = str(receipt.get("receipt_type") or "").strip()
        if not receipt_type:
            return
        summary = str(receipt.get("summary") or receipt.get("decision_reason") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or receipt.get("response_id") or "").strip()
        source_key = str(receipt.get("source_key") or "").strip()
        duplicate_key = (receipt_type, receipt_id, source_key, summary)
        for existing in receipts:
            existing_key = (
                str(existing.get("receipt_type") or "").strip(),
                str(existing.get("receipt_id") or existing.get("response_id") or "").strip(),
                str(existing.get("source_key") or "").strip(),
                str(existing.get("summary") or existing.get("decision_reason") or "").strip(),
            )
            if existing_key == duplicate_key:
                return
        receipts.append(receipt)

    @staticmethod
    def _normalize_source_context_receipt(
        payload: dict[str, Any],
        *,
        source_key: str,
        source_kind: str,
    ) -> dict[str, Any] | None:
        if not payload:
            return None
        raw_used_names = payload.get("used_names")
        raw_excluded_names = payload.get("excluded_names")
        raw_used_tools = payload.get("used_tools")
        used_names = [
            str(item).strip()
            for item in (raw_used_names if isinstance(raw_used_names, list) else [])
            if str(item).strip()
        ]
        excluded_names = [
            str(item).strip()
            for item in (raw_excluded_names if isinstance(raw_excluded_names, list) else [])
            if str(item).strip()
        ]
        used_tools = [
            item for item in (raw_used_tools if isinstance(raw_used_tools, list) else []) if isinstance(item, dict)
        ]
        used_count = int(payload.get("used_count") or 0) + int(payload.get("tool_count") or len(used_tools) or 0)
        reason = ResponseBuilderMixin._receipt_summary(
            payload,
            "summary",
            "decision_reason",
            default=(
                "参考了学习伙伴的动态" if source_kind == "social" else f"Aurora 参考了 {used_count} 个上下文来源。"
            ),
        )
        if used_count <= 0 and not reason:
            return None
        return {
            **payload,
            "receipt_type": "source_context_receipt",
            "source_key": source_key,
            "source_kind": source_kind,
            "summary": reason,
            "decision_reason": reason,
            "used_count": used_count,
            "used_names": used_names,
            "excluded_names": excluded_names,
            "used_tools": used_tools,
            "correction_actions": (
                [
                    {
                        "label": "不需要参考他的进度",
                        "prompt": "这次不要参考学习伙伴的进度或动态，请只基于我自己的状态来判断。",
                    }
                ]
                if source_kind == "social"
                else [
                    {
                        "label": "排除此资料",
                        "prompt": "请暂时排除刚才使用的资料，换一种解释。",
                    }
                ]
            ),
        }

    @staticmethod
    def _normalize_memory_reference_receipt(payload: dict[str, Any]) -> dict[str, Any] | None:
        memories = [item for item in payload.get("referenced_memories") or [] if isinstance(item, dict)]
        if not memories:
            return None
        used_count = int(payload.get("used_count") or len(memories))
        reason = ResponseBuilderMixin._receipt_summary(
            payload,
            "summary",
            "decision_reason",
            default=f"Aurora 引用了 {used_count} 条相关记忆。",
        )
        return {
            **payload,
            "receipt_type": "memory_reference_receipt",
            "summary": reason,
            "decision_reason": reason,
            "used_count": used_count,
            "referenced_memories": memories[:5],
            "correction_actions": [
                {
                    "label": "这个记忆引用不对",
                    "prompt": "这条记忆引用不对，请降低置信度，以后不要直接引用。",
                }
            ],
        }

    @staticmethod
    def _normalize_aurora_experience_receipt(
        payload: dict[str, Any],
        *,
        source_key: str,
    ) -> dict[str, Any] | None:
        if not payload:
            return None
        summary = ResponseBuilderMixin._receipt_summary(
            payload,
            "summary",
            "visible_hint",
            "message",
            "title",
        )
        what_changed = [str(item).strip() for item in payload.get("what_changed") or [] if str(item).strip()]
        if not summary and not what_changed:
            return None
        title = ResponseBuilderMixin._receipt_summary(payload, "title", default="Aurora 调整了体验")
        return {
            **payload,
            "receipt_type": "aurora_experience_receipt",
            "source_key": source_key,
            "summary": summary or title,
            "decision_reason": summary or title,
            "detail_title": title,
            "what_changed": what_changed,
            "correction_actions": [
                {
                    "label": "重新校准",
                    "prompt": "这个 Aurora 判断不太对，请基于我刚才的反馈重新校准。",
                }
            ],
        }

    @staticmethod
    def _aurora_everyday_presence_metadata(context_data: dict[str, Any]) -> dict[str, str]:
        presence = context_data.get("aurora_everyday_presence")
        if not isinstance(presence, dict):
            cognitive_context = context_data.get("cognitive_context")
            if isinstance(cognitive_context, dict):
                presence = cognitive_context.get("aurora_everyday_presence")
        if not isinstance(presence, dict) or not presence:
            return {}
        if presence.get("should_surface") is False:
            return {}

        chat_hint = str(presence.get("chat_hint") or presence.get("summary") or "").strip()
        if not chat_hint:
            return {}

        evidence_chain = [str(item).strip() for item in presence.get("evidence_chain") or [] if str(item).strip()]
        memory_references = [str(item).strip() for item in presence.get("memory_references") or [] if str(item).strip()]
        next_step = str(presence.get("next_step_suggestion") or "").strip()
        uncertainty = str(presence.get("uncertainty_level") or "medium").strip() or "medium"
        last_correction = presence.get("last_correction_effect")
        correction_visible = isinstance(last_correction, dict) and bool(last_correction.get("visible"))

        what_changed: list[str] = []
        if correction_visible:
            affected = [
                str(item).strip() for item in last_correction.get("affected_state_keys") or [] if str(item).strip()
            ]
            if affected:
                what_changed.append(f"已按纠正更新：{', '.join(affected[:3])}")
            else:
                what_changed.append("已把刚才的纠正作为本轮判断的约束。")
        if next_step:
            what_changed.append(f"下一步建议：{next_step}")

        payload = {
            "title": "Aurora 当前判断",
            "summary": chat_hint,
            "visible_hint": chat_hint,
            "what_changed": what_changed,
            "evidence_chain": evidence_chain,
            "memory_references": memory_references,
            "uncertainty_level": uncertainty,
            "overall_status": str(presence.get("overall_status") or "sensing"),
            "scene_alignment": str(presence.get("scene_alignment") or "matched"),
            "correction_actions": [
                {
                    "label": "这个判断不对",
                    "prompt": "这个 Aurora 判断不对，请先按我的纠正重新理解，再继续回答。",
                },
                {
                    "label": "只回答当前问题",
                    "prompt": "先不要引用旧状态，只回答我这次的问题。",
                },
            ],
        }
        return {"aurora_everyday_presence": json.dumps(payload, ensure_ascii=False)}

    @staticmethod
    def _normalize_next_action_receipt(payload: dict[str, Any]) -> dict[str, Any] | None:
        if not payload:
            return None
        summary = ResponseBuilderMixin._receipt_summary(
            payload,
            "summary",
            "message",
            "decision_reason",
            default="Aurora 调整了下一步行动。",
        )
        correction_options = [
            str(item).strip() for item in payload.get("correction_options") or [] if str(item).strip()
        ]
        return {
            **payload,
            "receipt_type": "next_action_changed_by_aurora",
            "source_key": "spine_receipt",
            "summary": summary,
            "decision_reason": summary,
            "correction_actions": [
                {
                    "label": option,
                    "prompt": f"{option}。请重新判断这次行动调整。",
                }
                for option in correction_options
            ],
        }

    @staticmethod
    def _build_unified_aurora_receipts(response_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        existing = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("aurora_receipts"))
        if isinstance(existing, list):
            for item in existing:
                if isinstance(item, dict):
                    ResponseBuilderMixin._append_unified_receipt(receipts, item)

        adaptation = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("adaptation_summary"))
        if isinstance(adaptation, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_aurora_experience_receipt(
                    adaptation,
                    source_key="adaptation_summary",
                ),
            )
        session_adaptation = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("session_adaptation"))
        if isinstance(session_adaptation, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_aurora_experience_receipt(
                    session_adaptation,
                    source_key="session_adaptation",
                ),
            )
        everyday_presence = ResponseBuilderMixin._decode_receipt_payload(
            response_metadata.get("aurora_everyday_presence")
        )
        if isinstance(everyday_presence, dict):
            normalized = ResponseBuilderMixin._normalize_aurora_experience_receipt(
                everyday_presence,
                source_key="aurora_everyday_presence",
            )
            if normalized is not None:
                normalized["evidence_chain"] = everyday_presence.get("evidence_chain") or []
                normalized["memory_references"] = everyday_presence.get("memory_references") or []
                normalized["uncertainty_level"] = everyday_presence.get("uncertainty_level") or "medium"
                if everyday_presence.get("correction_actions"):
                    normalized["correction_actions"] = everyday_presence["correction_actions"]
            ResponseBuilderMixin._append_unified_receipt(receipts, normalized)

        memory = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("memory_reference_receipt"))
        if isinstance(memory, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_memory_reference_receipt(memory),
            )

        source = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("context_receipt"))
        if isinstance(source, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_source_context_receipt(
                    source,
                    source_key="context_receipt",
                    source_kind="materials",
                ),
            )
        social = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("social_context_receipt"))
        if isinstance(social, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_source_context_receipt(
                    social,
                    source_key="social_context_receipt",
                    source_kind="social",
                ),
            )

        spine = ResponseBuilderMixin._decode_receipt_payload(response_metadata.get("spine_receipt"))
        if isinstance(spine, dict):
            ResponseBuilderMixin._append_unified_receipt(
                receipts,
                ResponseBuilderMixin._normalize_next_action_receipt(spine),
            )

        priority = {
            "aurora_experience_receipt": 0,
            "memory_reference_receipt": 1,
            "source_context_receipt": 2,
            "next_action_changed_by_aurora": 3,
        }
        receipts.sort(key=lambda item: priority.get(str(item.get("receipt_type") or ""), 99))
        return receipts

    @staticmethod
    def _inject_unified_aurora_receipts(response_metadata: dict[str, Any]) -> None:
        receipts = ResponseBuilderMixin._build_unified_aurora_receipts(response_metadata)
        if receipts:
            response_metadata["aurora_receipts"] = json.dumps(receipts, ensure_ascii=False)

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
            context_data.get("why_this_path") or capability_selection_report.get("why_this_path") or ""
        ).strip()
        if why_this_path:
            metadata["why_this_path"] = why_this_path
        return metadata

    @staticmethod
    def _dual_core_response_metadata(context_data: dict[str, Any]) -> dict[str, str]:
        dual_core_decision = context_data.get("dual_core_decision")
        if not isinstance(dual_core_decision, dict) or not dual_core_decision:
            return {}

        metadata = {
            "dual_core_decision": json.dumps(dual_core_decision, ensure_ascii=False),
        }
        structured = dual_core_decision.get("structured_adjustments") or []
        if structured:
            metadata["structured_cognitive_adjustments"] = json.dumps(
                structured,
                ensure_ascii=False,
            )
        return metadata

    @staticmethod
    def _task_stuck_intervention_metadata(context_data: dict[str, Any]) -> dict[str, str]:
        active = context_data.get("active_interventions")
        if not isinstance(active, list):
            return {}

        selected: dict[str, Any] | None = None
        diagnosis: dict[str, Any] = {}
        for item in active:
            if not isinstance(item, dict):
                continue
            candidate_diagnosis = item.get("diagnosis_payload")
            if not isinstance(candidate_diagnosis, dict):
                candidate_diagnosis = {}
            pattern_name = str(candidate_diagnosis.get("pattern_name") or "").strip().lower()
            trigger_type = str(item.get("trigger_type") or "").strip().upper()
            if pattern_name == "task stuck intervention" or (
                trigger_type == "STALL_PATTERN" and candidate_diagnosis.get("task_health")
            ):
                selected = item
                diagnosis = candidate_diagnosis
                break

        if not selected:
            return {}

        intervention_id = str(selected.get("intervention_id") or "").strip()
        description = str(diagnosis.get("description") or "几张任务连续出现了卡点").strip()
        task_titles = [str(item).strip() for item in list(diagnosis.get("task_titles") or [])[:3] if str(item).strip()]
        task_health = diagnosis.get("task_health") if isinstance(diagnosis.get("task_health"), dict) else {}
        micro_session = diagnosis.get("micro_session")
        if not isinstance(micro_session, dict):
            try:
                from app.services.task_stuck_signal_service import TaskStuckPatternAnalyzer

                micro_session = TaskStuckPatternAnalyzer.build_micro_session_payload(diagnosis)
            except Exception:
                micro_session = {}

        message_subject = description if description.startswith("最近") else f"最近{description}"
        payload = {
            "intervention_id": intervention_id,
            "message": f"我注意到{message_subject}。要不要聊一下？大概 2 分钟。",
            "observed_pattern": description,
            "task_titles": task_titles,
            "task_health": task_health,
            "micro_session": micro_session,
            "receipt": diagnosis.get("receipt") if isinstance(diagnosis.get("receipt"), dict) else {},
            "actions": [
                {"label": "聊聊", "feedback_action": "accepted", "role": "primary"},
                {"label": "稍后", "feedback_action": "snoozed", "snooze_hours": 24},
                {"label": "不需要", "feedback_action": "dismissed"},
            ],
        }
        return {"task_stuck_intervention": json.dumps(payload, ensure_ascii=False)}

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

    @staticmethod
    def _social_context_receipt_metadata(user_context_payload: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(user_context_payload, dict):
            return {}

        candidates = [
            user_context_payload.get("social_context_v1"),
            user_context_payload.get("social_signals_summary"),
        ]
        cognitive_context = user_context_payload.get("cognitive_context")
        if isinstance(cognitive_context, dict):
            candidates.extend(
                [
                    cognitive_context.get("social_context_v1"),
                    cognitive_context.get("social_signals_summary"),
                ]
            )

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            receipt = candidate.get("social_context_receipt")
            if isinstance(receipt, dict) and receipt:
                return {"social_context_receipt": json.dumps(receipt, ensure_ascii=False)}
        return {}

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
                agents_involved = [str(agent).strip() for agent in selected_experts_for_primary if str(agent).strip()]
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
        context_receipt: dict[str, Any] = {}
        if isinstance(doc_retrieval_meta, dict) and isinstance(doc_retrieval_meta.get("context_receipt"), dict):
            context_receipt.update(doc_retrieval_meta["context_receipt"])
        recent_tool_usage = (
            (user_context_payload or {}).get("recent_tool_usage") if isinstance(user_context_payload, dict) else None
        )
        if isinstance(recent_tool_usage, list) and recent_tool_usage:
            used_tools = [
                {
                    "name": str(item.get("label") or item.get("tool_name") or "").strip(),
                    "tool_name": str(item.get("tool_name") or "").strip(),
                    "summary": str(item.get("summary") or "").strip(),
                    "used_at": item.get("used_at"),
                    "privacy_note": str(item.get("privacy_note") or "").strip(),
                }
                for item in recent_tool_usage[:4]
                if isinstance(item, dict) and str(item.get("summary") or "").strip()
            ]
            if used_tools:
                context_receipt["used_tools"] = used_tools
                context_receipt["tool_names"] = [item["name"] for item in used_tools if item.get("name")]
                context_receipt["tool_count"] = len(used_tools)
                context_receipt.setdefault("decision_reason", "Aurora 已参考你刚刚的工具动作。")
        if context_receipt:
            response_metadata["context_receipt"] = json.dumps(context_receipt, ensure_ascii=False)
        response_metadata.update(self._social_context_receipt_metadata(user_context_payload))
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
        response_metadata.update(self._dual_core_response_metadata(final_state.context_data))
        response_metadata.update(self._task_stuck_intervention_metadata(final_state.context_data))
        response_metadata.update(self._aurora_everyday_presence_metadata(final_state.context_data))
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

        memory_reference_receipt = self._build_memory_reference_receipt(
            full_response=full_response,
            user_context_payload=user_context_payload,
            context_data=final_state.context_data,
            response_id=response_id,
        )
        if memory_reference_receipt:
            final_state.context_data["memory_reference_receipt"] = memory_reference_receipt
            response_metadata["memory_reference_receipt"] = json.dumps(memory_reference_receipt, ensure_ascii=False)

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
            cognitive_context=(
                (user_context_payload or {}).get("cognitive_context")
                if isinstance(user_context_payload, dict)
                else None
            ),
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
                    response_metadata["spine_receipt"] = json.dumps(
                        {
                            "receipt_id": _latest_receipt.receipt_id,
                            "trigger": _latest_receipt.receipt_type,
                            "summary": _latest_receipt.message,
                            "correctable": _correctable,
                            "correction_options": (
                                ["这个判断不准确", "我不同意这个调整", "继续，先看看效果"] if _correctable else []
                            ),
                        },
                        ensure_ascii=False,
                    )
                _community_hint = await _spine.get_latest_community_hint(user_id)
                if _community_hint:
                    response_metadata["spine_community_hint"] = json.dumps(_community_hint, ensure_ascii=False)
                _ux_warning = await _spine.get_ux_risk_warning(user_id)
                if _ux_warning:
                    response_metadata["spine_ux_warning"] = json.dumps(_ux_warning, ensure_ascii=False)
                _goal_arb = await _spine.get_goal_arbitration_summary(user_id)
                if _goal_arb:
                    response_metadata["spine_goal_arbitration"] = json.dumps(_goal_arb, ensure_ascii=False)
                # T3.3.1: Inject predicted reply options into response metadata
                try:
                    from app.aurora.runtime_v1.reply_option_injector import ReplyOptionInjector

                    _aurora_band = response_metadata.get("aurora_band_status", "sensing")
                    _aurora_energy = response_metadata.get("aurora_energy_level", "L1")
                    _injector = ReplyOptionInjector()
                    _reply_groups = _injector.generate(
                        band_status=_aurora_band,
                        energy_level=_aurora_energy,
                    )
                    _injector.inject_into_metadata(
                        response_metadata,
                        _reply_groups,
                        _aurora_band,
                    )
                except Exception:
                    pass
            except Exception:
                pass

        self._inject_unified_aurora_receipts(response_metadata)

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
                        utilization_metrics=(
                            context_data.get("utilization_metrics")
                            if isinstance(context_data.get("utilization_metrics"), dict)
                            else None
                        ),
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
