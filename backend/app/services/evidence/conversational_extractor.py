from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.config import settings
from app.core.llm_secure_io import sanitize_text_for_llm
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)
from app.services.llm_fallback_utils import safe_llm_json_call


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


COGNITIVE_LOAD_TYPES = {"intrinsic", "extraneous", "germane", "unknown"}
STAGES_OF_CHANGE = {
    "precontemplation",
    "contemplation",
    "preparation",
    "action",
    "maintenance",
    "unknown",
}


class ConversationalEvidenceExtractor:
    """Extract shadow-safe Aurora evidence from a single dialogue turn."""

    def __init__(
        self,
        *,
        llm_enabled: bool | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
    ) -> None:
        self.llm_enabled = (
            bool(settings.SPARKLE_LLM_EXTRACTOR_ENABLED) and not bool(settings.SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED)
            if llm_enabled is None
            else bool(llm_enabled)
        )
        self.model = model or settings.SPARKLE_LLM_EXTRACTOR_MODEL
        self.timeout_seconds = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(getattr(settings, "SPARKLE_LLM_EXTRACTOR_TIMEOUT_SECONDS", 12.0))
        )
        self.retry_count = (
            max(0, int(retry_count))
            if retry_count is not None
            else max(0, int(getattr(settings, "SPARKLE_LLM_EXTRACTOR_RETRY_COUNT", 1)))
        )

    async def extract(
        self,
        *,
        user_id: UUID,
        user_message: str,
        ai_response: str = "",
        conversation_id: str,
        turn_index: int,
        current_state: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> list[UnifiedEvidence]:
        scope = {
            "user_id": str(user_id),
            "conversation_id": conversation_id,
            "turn_index": int(turn_index),
        }
        metadata = {
            "shadow_only": True,
            "ai_response_excerpt": self._compact(ai_response, 220),
        }
        fallback = self.extract_rule_based(
            user_message=user_message,
            timestamp=timestamp,
            scope=scope,
            metadata={**metadata, "extractor": "rule_fallback"},
        )
        if not self.llm_enabled or not user_message.strip():
            return fallback

        payload = await safe_llm_json_call(
            self._build_messages(
                user_message=user_message,
                ai_response=ai_response,
                current_state=current_state or {},
            ),
            fallback=[],
            timeout=self.timeout_seconds,
            retry_count=self.retry_count,
            model=self.model,
            temperature=0.0,
        )
        llm_items = self._coerce_items(payload)
        evidence: list[UnifiedEvidence] = []
        for item in llm_items[:5]:
            parsed = UnifiedEvidence.from_raw(
                item,
                source_type=self._source_type_for_item(item),
                fallback_text=user_message,
                timestamp=timestamp,
                scope=scope,
                metadata={**metadata, "extractor": "llm"},
            )
            if parsed is not None:
                self._normalize_metadata(parsed)
                evidence.append(parsed)

        if evidence:
            return self._dedupe(evidence)
        return fallback

    def extract_rule_based(
        self,
        *,
        user_message: str,
        timestamp: datetime | None = None,
        scope: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[UnifiedEvidence]:
        text = user_message.strip()
        if not text:
            return []
        lowered = text.lower()
        cognitive_load_type = self._classify_cognitive_load_type(lowered)
        stage_of_change = self._classify_stage_of_change(lowered)
        base_metadata = {**dict(metadata or {}), "stage_of_change": stage_of_change}
        specs: list[tuple[EvidenceTarget, EvidenceDirection, float, float, int, str, dict[str, Any]]] = []

        if self._contains(lowered, ("头晕", "脑子乱", "太多了", "overwhelmed", "too much", "confused")):
            specs.append(
                (
                    EvidenceTarget.COGNITIVE_LOAD,
                    EvidenceDirection.INCREASE,
                    0.72,
                    0.68,
                    4 * 3600,
                    "overload_marker",
                    self._cognitive_load_metadata(cognitive_load_type),
                )
            )
        if cognitive_load_type != "unknown" and not any(spec[0] == EvidenceTarget.COGNITIVE_LOAD for spec in specs):
            specs.append(
                (
                    EvidenceTarget.COGNITIVE_LOAD,
                    EvidenceDirection.INCREASE,
                    0.66 if cognitive_load_type == "germane" else 0.72,
                    0.66,
                    4 * 3600,
                    f"{cognitive_load_type}_load_marker",
                    self._cognitive_load_metadata(cognitive_load_type),
                )
            )
        if self._contains(lowered, ("烦", "不想开始", "下不了手", "拖", "不想做", "avoid", "procrastinat")):
            specs.append(
                (EvidenceTarget.TASK_AVERSION, EvidenceDirection.INCREASE, 0.70, 0.64, 24 * 3600, "aversion_marker", {})
            )
        if self._contains(lowered, ("累", "崩", "焦虑", "难受", "burnout", "exhausted", "anxious")):
            specs.append(
                (
                    EvidenceTarget.EMOTIONAL_BLOCK,
                    EvidenceDirection.INCREASE,
                    0.68,
                    0.62,
                    12 * 3600,
                    "emotion_marker",
                    {},
                )
            )
        if self._contains(lowered, ("做完了", "已经完成", "刚做完", "finished", "done")):
            specs.append(
                (
                    EvidenceTarget.TASK_COMPLETION_STATE,
                    EvidenceDirection.OBSERVE,
                    0.82,
                    0.72,
                    24 * 3600,
                    "completion_marker",
                    {},
                )
            )
        if self._contains(lowered, ("太啰嗦", "太长", "少说", "短一点", "too long", "verbose")):
            specs.append(
                (
                    EvidenceTarget.AI_VERBOSITY_PREFERENCE,
                    EvidenceDirection.DECREASE,
                    0.78,
                    0.74,
                    30 * 24 * 3600,
                    "verbosity_marker",
                    {},
                )
            )
            specs.append(
                (
                    EvidenceTarget.SYSTEM_DISSATISFACTION,
                    EvidenceDirection.INCREASE,
                    0.58,
                    0.62,
                    24 * 3600,
                    "verbosity_friction",
                    {},
                )
            )
        if self._contains(lowered, ("直接告诉我", "别安慰", "少废话", "directly", "just tell me")):
            specs.append(
                (
                    EvidenceTarget.DIRECTNESS_PREFERENCE,
                    EvidenceDirection.INCREASE,
                    0.75,
                    0.72,
                    30 * 24 * 3600,
                    "directness_marker",
                    {},
                )
            )
        if self._contains(lowered, ("不对", "不太对", "没懂", "不明白", "wrong", "not helpful", "still confused")):
            specs.append(
                (
                    EvidenceTarget.SYSTEM_DISSATISFACTION,
                    EvidenceDirection.INCREASE,
                    0.74,
                    0.72,
                    24 * 3600,
                    "dissatisfaction_marker",
                    {},
                )
            )

        return [
            UnifiedEvidence(
                source_type=EvidenceSourceType.HEURISTIC_FALLBACK,
                target_latent_variable=target,
                direction=direction,
                strength=strength,
                confidence=confidence,
                evidence_text=text,
                timestamp=timestamp or _utcnow(),
                ttl_seconds=ttl,
                scope=dict(scope or {}),
                metadata={**base_metadata, **extra_metadata, "extractor": "rule_fallback", "rule": rule},
            )
            for target, direction, strength, confidence, ttl, rule, extra_metadata in specs[:5]
        ]

    def _build_messages(
        self,
        *,
        user_message: str,
        ai_response: str,
        current_state: dict[str, Any],
    ) -> list[dict[str, str]]:
        targets = [item.value for item in EvidenceTarget]
        system = (
            "You extract Aurora state-sensing evidence from one dialogue turn. "
            "Return JSON only: a list of evidence objects. Return [] if the user did not clearly express a state, "
            "preference, friction, completion, correction, aversion, fatigue, or smooth execution. "
            "Do not infer from stereotypes or generic common sense. Each item must include "
            "target_latent_variable, direction, strength, confidence, evidence_text, ttl_seconds. "
            f"Allowed target_latent_variable values: {targets}. "
            "Allowed direction values: increase, decrease, observe. "
            "Use strength/confidence in [0,1]. Keep evidence_text as the exact short user phrase. "
            "When target_latent_variable is cognitive_load, include metadata.cognitive_load_type as one of "
            "intrinsic, extraneous, germane, unknown and metadata.academic_prior='cognitive_load_theory.v1'. "
            "Classify intrinsic load when the task/concept itself is hard, extraneous load when the system "
            "explanation/UI/material organization is causing friction, and germane load when the user is productively "
            "processing difficult material. Include metadata.stage_of_change as one of precontemplation, "
            "contemplation, preparation, action, maintenance, unknown when the utterance gives a clear readiness stage."
        )
        compact_payload = {
            "user_message": sanitize_text_for_llm(self._compact(user_message, 900)),
            "ai_response_excerpt": sanitize_text_for_llm(self._compact(ai_response, 500)),
            "current_state": self._safe_state(current_state),
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(compact_payload, ensure_ascii=False, default=str)},
        ]

    @staticmethod
    def _coerce_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            raw = payload.get("evidence") or payload.get("items") or payload.get("evidence_objects")
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
        return []

    @staticmethod
    def _source_type_for_item(item: dict[str, Any]) -> EvidenceSourceType:
        raw = str(item.get("source_type") or "").strip()
        if raw:
            try:
                return EvidenceSourceType(raw)
            except ValueError:
                pass
        explicit_markers = ("我希望", "以后", "请", "prefer", "i want", "please")
        text = str(item.get("evidence_text") or "")
        if any(marker in text.lower() for marker in explicit_markers):
            return EvidenceSourceType.CONVERSATIONAL_EXPLICIT
        return EvidenceSourceType.CONVERSATIONAL_IMPLICIT

    @classmethod
    def _normalize_metadata(cls, evidence: UnifiedEvidence) -> None:
        stage = str(evidence.metadata.get("stage_of_change") or "").strip()
        if stage not in STAGES_OF_CHANGE:
            evidence.metadata["stage_of_change"] = "unknown"
        if evidence.target_latent_variable == EvidenceTarget.COGNITIVE_LOAD:
            load_type = str(evidence.metadata.get("cognitive_load_type") or "").strip()
            if load_type not in COGNITIVE_LOAD_TYPES:
                load_type = cls._classify_cognitive_load_type(evidence.evidence_text.lower())
            evidence.metadata.update(cls._cognitive_load_metadata(load_type))

    @classmethod
    def _cognitive_load_metadata(cls, cognitive_load_type: str) -> dict[str, str]:
        normalized = cognitive_load_type if cognitive_load_type in COGNITIVE_LOAD_TYPES else "unknown"
        return {
            "cognitive_load_type": normalized,
            "academic_prior": "cognitive_load_theory.v1",
        }

    @classmethod
    def _classify_cognitive_load_type(cls, text: str) -> str:
        if cls._contains(
            text,
            (
                "题太难",
                "太难",
                "概念不会",
                "知识点",
                "看不懂题",
                "看不懂知识",
                "不会做",
                "不理解概念",
                "concept",
                "too hard",
            ),
        ):
            return "intrinsic"
        if cls._contains(
            text,
            (
                "解释太乱",
                "讲得太乱",
                "步骤太多",
                "信息太多",
                "界面混乱",
                "卡片太多",
                "材料太乱",
                "too many steps",
                "confusing explanation",
                "too much information",
            ),
        ):
            return "extraneous"
        if cls._contains(
            text,
            (
                "我在理解",
                "正在理解",
                "需要消化",
                "正在消化",
                "有点吃力但",
                "能学",
                "可以学",
                "challenging but",
                "need to digest",
            ),
        ):
            return "germane"
        return "unknown"

    @classmethod
    def _classify_stage_of_change(cls, text: str) -> str:
        if cls._contains(text, ("不想改", "没必要", "无所谓", "算了", "don't care", "no need")):
            return "precontemplation"
        if cls._contains(text, ("也许", "可能要", "我在想", "要不要", "maybe", "thinking about")):
            return "contemplation"
        if cls._contains(text, ("准备", "先试试", "从哪里开始", "怎么开始", "ready to try", "start with")):
            return "preparation"
        if cls._contains(text, ("正在做", "我现在做", "开始做", "继续做", "doing it", "working on")):
            return "action"
        if cls._contains(text, ("坚持", "保持", "已经连续", "复盘", "maintain", "keep going")):
            return "maintenance"
        return "unknown"

    @staticmethod
    def _safe_state(state: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "routing_mode",
            "signal_scores",
            "recent_corrections",
            "recent_route_outcomes",
            "aurora_preferences",
            "cognitive_context",
        }
        return {key: state.get(key) for key in allowed if key in state}

    @staticmethod
    def _dedupe(items: list[UnifiedEvidence]) -> list[UnifiedEvidence]:
        seen: set[tuple[str, str, str]] = set()
        result: list[UnifiedEvidence] = []
        for item in sorted(items, key=lambda ev: ev.confidence, reverse=True):
            key = (
                item.target_latent_variable.value,
                item.direction.value,
                item.evidence_text[:80],
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result[:5]

    @staticmethod
    def _compact(value: str, limit: int) -> str:
        text = str(value or "").strip()
        return text if len(text) <= limit else text[: limit - 1] + "…"

    @staticmethod
    def _contains(text: str, markers: tuple[str, ...]) -> bool:
        return any(marker in text for marker in markers)
