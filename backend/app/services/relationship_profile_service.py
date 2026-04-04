from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.self_revision_service import SelfRevisionService

_PROMOTABLE_RELATIONSHIP_KINDS = {"milestone", "boundary", "trust", "repair", "growth"}


class RelationshipProfileService:
    """Promote durable relationship signals into the profile layer."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.self_revision_service = SelfRevisionService(db, redis)

    async def maybe_promote_relationship_note(
        self,
        *,
        user_id: UUID,
        note: str,
        note_kind: str,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        matching_revision_count: int,
    ) -> dict[str, Any] | None:
        normalized_kind = str(note_kind or "general").strip().lower()
        normalized_note = self._normalize_note(note)
        if normalized_kind not in _PROMOTABLE_RELATIONSHIP_KINDS:
            return None
        if matching_revision_count < 2:
            return None
        if not evidence.get("measurable_effect"):
            return None
        if confidence < 0.7:
            return None
        if len(normalized_note) < 12:
            return None

        profile_patch = self._build_profile_patch(
            note=note,
            note_kind=normalized_kind,
            evidence=evidence,
            confidence=confidence,
        )
        revision = self.self_revision_service.build_revision(
            field="relationship_note",
            layer="profile",
            old_value=None,
            new_value=note,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            promotion_source_layer="session",
        )
        result = await self.self_revision_service.append_profile_revision(
            user_id=user_id,
            revision=revision,
            relationship_profile_patch=profile_patch,
        )
        result["promoted_relationship_kind"] = normalized_kind
        return result

    @staticmethod
    def _build_profile_patch(
        *,
        note: str,
        note_kind: str,
        evidence: dict[str, Any],
        confidence: float,
    ) -> dict[str, Any]:
        trimmed_note = str(note).strip()
        entry = {
            "kind": note_kind,
            "summary": trimmed_note[:320],
            "confidence": float(confidence),
            "evidence_refs": [dict(evidence)],
        }
        if note_kind in {"boundary", "trust"}:
            return {"boundary_notes": [entry]}
        return {"shared_milestones": [entry]}

    @staticmethod
    def _normalize_note(note: str) -> str:
        return " ".join(str(note or "").strip().lower().split())
