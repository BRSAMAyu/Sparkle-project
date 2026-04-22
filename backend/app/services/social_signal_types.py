from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SocialSignalsV1:
    mention_count: int = 0
    relationship_count: int = 0
    pending_commitments_count: int = 0
    community_engagement_level: str | None = None
    social_learning_preference: float | None = None
    content_contribution_rate: float | None = None
    summary_lines: tuple[str, ...] = field(default_factory=tuple)

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
        if (
            not summary_lines
            and mention_count <= 0
            and relationship_count <= 0
            and pending_commitments_count <= 0
            and community_engagement_level is None
            and social_learning_preference is None
            and content_contribution_rate is None
        ):
            return None
        return cls(
            mention_count=mention_count,
            relationship_count=relationship_count,
            pending_commitments_count=pending_commitments_count,
            community_engagement_level=community_engagement_level,
            social_learning_preference=social_learning_preference,
            content_contribution_rate=content_contribution_rate,
            summary_lines=tuple(summary_lines),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "mention_count": self.mention_count,
            "relationship_count": self.relationship_count,
            "pending_commitments_count": self.pending_commitments_count,
            "community_engagement_level": self.community_engagement_level,
            "social_learning_preference": self.social_learning_preference,
            "content_contribution_rate": self.content_contribution_rate,
            "summary_lines": list(self.summary_lines),
            "summary_text": self.to_summary_text(),
        }

    def to_summary_text(self, *, max_chars: int = 400) -> str:
        if not self.summary_lines:
            return ""
        summary = "；".join(item for item in self.summary_lines if item)
        return summary[:max_chars].strip()
