from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class EvidenceSourceType(StrEnum):
    CONVERSATIONAL_IMPLICIT = "conversational_implicit"
    CONVERSATIONAL_EXPLICIT = "conversational_explicit"
    PROBE_EXPLICIT = "probe_explicit"
    BEHAVIORAL_IMPLICIT = "behavioral_implicit"
    OUTCOME = "outcome"
    HEURISTIC_FALLBACK = "heuristic_fallback"


class EvidenceDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    OBSERVE = "observe"


class EvidenceTarget(StrEnum):
    COGNITIVE_LOAD = "cognitive_load"
    EMOTIONAL_BLOCK = "emotional_block"
    TASK_AVERSION = "task_aversion"
    EXECUTION_CAPACITY = "execution_capacity"
    GOAL_CLARITY = "goal_clarity"
    METACOGNITION_ACCURACY = "metacognition_accuracy"
    AI_VERBOSITY_PREFERENCE = "ai_verbosity_preference"
    DIRECTNESS_PREFERENCE = "directness_preference"
    SYSTEM_DISSATISFACTION = "system_dissatisfaction"
    TASK_COMPLETION_STATE = "task_completion_state"
    CONVERSATION_RHYTHM = "conversation_rhythm"


class UnifiedEvidence(BaseModel):
    """A normalized, shadow-safe observation for Aurora state sensing."""

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: EvidenceSourceType
    target_latent_variable: EvidenceTarget
    direction: EvidenceDirection
    strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str = Field(default="", max_length=500)
    timestamp: datetime = Field(default_factory=_utcnow)
    ttl_seconds: int = Field(default=4 * 3600, ge=60, le=30 * 24 * 3600)
    scope: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    extractor_version: str = "conversational_evidence.v1"

    @field_validator("evidence_text", mode="before")
    @classmethod
    def _trim_text(cls, value: Any) -> str:
        return str(value or "").strip()[:500]

    @field_validator("scope", "metadata", mode="before")
    @classmethod
    def _dict_or_empty(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        *,
        source_type: EvidenceSourceType,
        fallback_text: str,
        timestamp: datetime | None = None,
        scope: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UnifiedEvidence | None:
        """Build evidence from untrusted extractor output."""
        try:
            target = EvidenceTarget(str(raw.get("target_latent_variable") or raw.get("target") or "").strip())
            direction = EvidenceDirection(str(raw.get("direction") or "").strip())
            strength = cls._clamp(raw.get("strength"), default=0.0)
            confidence = cls._clamp(raw.get("confidence"), default=0.0)
            evidence_text = str(raw.get("evidence_text") or raw.get("text") or fallback_text or "").strip()
            if strength <= 0.0 or confidence <= 0.0 or not evidence_text:
                return None
            raw_ttl = raw.get("ttl_seconds") or raw.get("ttl")
            ttl_seconds = cls._coerce_ttl_seconds(raw_ttl)
            merged_scope = dict(scope or {})
            if isinstance(raw.get("scope"), dict):
                merged_scope.update(raw["scope"])
            merged_metadata = dict(metadata or {})
            if isinstance(raw.get("metadata"), dict):
                merged_metadata.update(raw["metadata"])
            return cls(
                source_type=source_type,
                target_latent_variable=target,
                direction=direction,
                strength=strength,
                confidence=confidence,
                evidence_text=evidence_text,
                timestamp=timestamp or _utcnow(),
                ttl_seconds=ttl_seconds,
                scope=merged_scope,
                metadata=merged_metadata,
            )
        except (TypeError, ValueError):
            return None

    def to_cognitive_context(self) -> dict[str, Any]:
        return {
            "schema_version": "unified_evidence.v1",
            "evidence_id": self.evidence_id,
            "source_type": self.source_type.value,
            "target_latent_variable": self.target_latent_variable.value,
            "direction": self.direction.value,
            "strength": round(float(self.strength), 4),
            "confidence": round(float(self.confidence), 4),
            "ttl_seconds": int(self.ttl_seconds),
            "scope": dict(self.scope),
            "metadata": dict(self.metadata),
            "extractor_version": self.extractor_version,
        }

    @staticmethod
    def _clamp(value: Any, *, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        return max(0.0, min(1.0, parsed))

    @staticmethod
    def _coerce_ttl_seconds(value: Any) -> int:
        if isinstance(value, str):
            raw = value.strip().lower()
            try:
                if raw.endswith("h"):
                    return max(60, min(30 * 24 * 3600, int(float(raw[:-1]) * 3600)))
                if raw.endswith("d"):
                    return max(60, min(30 * 24 * 3600, int(float(raw[:-1]) * 24 * 3600)))
                if raw.endswith("m"):
                    return max(60, min(30 * 24 * 3600, int(float(raw[:-1]) * 60)))
            except ValueError:
                return 4 * 3600
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 4 * 3600
        return max(60, min(30 * 24 * 3600, parsed))
