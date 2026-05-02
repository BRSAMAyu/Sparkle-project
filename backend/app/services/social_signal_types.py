from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SocialSignalsV1:
    mention_count: int = 0
    relationship_count: int = 0
    pending_commitments_count: int = 0
    active_accountability_contract_count: int = 0
    community_engagement_level: str | None = None
    social_learning_preference: float | None = None
    content_contribution_rate: float | None = None
    summary_lines: tuple[str, ...] = field(default_factory=tuple)
    high_relevance_events: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    tone_guidance: tuple[str, ...] = field(default_factory=tuple)
    social_context_receipt: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> SocialSignalsV1 | None:
        if not isinstance(payload, dict):
            return None
        nested_value = payload.get("value")
        if isinstance(nested_value, dict):
            payload = nested_value
        summary_lines = [
            str(item).strip()
            for item in (payload.get("summary_lines") or [])
            if str(item).strip()
        ]
        if not summary_lines and str(payload.get("summary_text") or "").strip():
            summary_lines = [
                part.strip()
                for part in str(payload.get("summary_text") or "").split("；")
                if part.strip()
            ]
        mention_count = int(payload.get("mention_count") or 0)
        relationship_count = int(payload.get("relationship_count") or 0)
        pending_commitments_count = int(payload.get("pending_commitments_count") or 0)
        active_accountability_contract_count = int(payload.get("active_accountability_contract_count") or 0)
        community_engagement_level = (
            str(payload.get("community_engagement_level")).strip()
            if payload.get("community_engagement_level") is not None
            else None
        )
        social_learning_preference = (
            float(payload["social_learning_preference"])
            if payload.get("social_learning_preference") is not None
            else None
        )
        content_contribution_rate = (
            float(payload["content_contribution_rate"])
            if payload.get("content_contribution_rate") is not None
            else None
        )
        high_relevance_events = tuple(
            item
            for item in (payload.get("high_relevance_events") or [])
            if isinstance(item, dict) and item
        )
        tone_guidance = tuple(
            str(item).strip()
            for item in (payload.get("tone_guidance") or [])
            if str(item).strip()
        )
        social_context_receipt = payload.get("social_context_receipt")
        social_context_receipt = social_context_receipt if isinstance(social_context_receipt, dict) else None
        if (
            not summary_lines
            and mention_count <= 0
            and relationship_count <= 0
            and pending_commitments_count <= 0
            and active_accountability_contract_count <= 0
            and community_engagement_level is None
            and social_learning_preference is None
            and content_contribution_rate is None
            and not high_relevance_events
            and not tone_guidance
        ):
            return None
        return cls(
            mention_count=mention_count,
            relationship_count=relationship_count,
            pending_commitments_count=pending_commitments_count,
            active_accountability_contract_count=active_accountability_contract_count,
            community_engagement_level=community_engagement_level,
            social_learning_preference=social_learning_preference,
            content_contribution_rate=content_contribution_rate,
            summary_lines=tuple(summary_lines),
            high_relevance_events=high_relevance_events,
            tone_guidance=tone_guidance,
            social_context_receipt=social_context_receipt,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "mention_count": self.mention_count,
            "relationship_count": self.relationship_count,
            "pending_commitments_count": self.pending_commitments_count,
            "active_accountability_contract_count": self.active_accountability_contract_count,
            "community_engagement_level": self.community_engagement_level,
            "social_learning_preference": self.social_learning_preference,
            "content_contribution_rate": self.content_contribution_rate,
            "summary_lines": list(self.summary_lines),
            "summary_text": self.to_summary_text(),
            "high_relevance_events": [dict(item) for item in self.high_relevance_events],
            "tone_guidance": list(self.tone_guidance),
            "social_context_receipt": dict(self.social_context_receipt or {}),
        }

    def to_summary_text(self, *, max_chars: int = 400) -> str:
        if not self.summary_lines:
            return ""
        summary = "；".join(item for item in self.summary_lines if item)
        return summary[:max_chars].strip()
