from __future__ import annotations

import inspect
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.orchestration.soul_compiler import DEFAULT_COMPANION_STATE
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService
from app.services.relationship_profile_service import RelationshipProfileService
from app.services.self_revision_service import (
    SESSION_COMPANION_KEY_PREFIX,
    SESSION_COMPANION_REVISIONS_KEY_PREFIX,
    SelfRevisionService,
)

COMPANION_STATE_ALLOWED_FIELDS = (
    "warmth_calibration",
    "candor_calibration",
    "challenge_style",
    "emotional_explicitness",
    "relationship_stage",
    "self_description_note",
    "companion_growth_note",
    "relationship_note",
    "preferred_truth_style",
    "growth_confidence",
)
COMPANION_SESSION_WRITE_FIELDS = (
    "warmth_calibration",
    "candor_calibration",
    "challenge_style",
    "emotional_explicitness",
    "self_description_note",
    "companion_growth_note",
    "relationship_note",
)
_PROFILE_PROMOTABLE_FIELDS = {
    "warmth_calibration",
    "candor_calibration",
    "challenge_style",
    "emotional_explicitness",
    "self_description_note",
    "companion_growth_note",
}
_FLOAT_FIELDS = {
    "warmth_calibration",
    "candor_calibration",
    "emotional_explicitness",
    "growth_confidence",
}
_ENUM_FIELDS = {
    "challenge_style": {"gentle", "balanced", "firm"},
    "relationship_stage": {"early", "building", "trusted", "deepening"},
    "preferred_truth_style": {"honest_warm", "direct_structured", "gentle_reflective"},
}


def _clamp_unit_interval(value: Any, fallback: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


class CompanionStateService:
    """Runtime access plus guarded write/promotion logic for companion state."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)
        self.plan_state_service = PlanStateService(db, redis)
        self.self_revision_service = SelfRevisionService(db, redis)
        self.relationship_profile_service = RelationshipProfileService(db, redis)

    async def get_effective_state(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        profile_state = await self._get_profile_companion_state(user_id)
        episode_state = await self._get_episode_companion_state(user_id, plan_id)
        session_state = await self._get_session_companion_state(session_id)

        merged = dict(DEFAULT_COMPANION_STATE.to_dict())
        for layer in (profile_state, episode_state, session_state):
            merged.update(self._normalize_companion_state(layer))
        return merged

    async def get_recent_revisions(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        profile_revisions = await self._get_profile_revisions(user_id)
        episode_revisions = await self._get_episode_revisions(user_id, plan_id)
        session_revisions = await self._get_session_revisions(session_id)

        merged = [
            dict(item)
            for item in [*session_revisions, *episode_revisions, *profile_revisions]
            if isinstance(item, dict)
        ]
        merged.sort(key=self._revision_sort_key, reverse=True)
        return merged[:10]

    async def get_self_revision_history(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        history = await self.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)
        return history[: max(1, min(limit, 20))]

    async def get_relationship_profile(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        relationship_profile = inferred.get("relationship_profile")
        if not isinstance(relationship_profile, dict):
            return {}
        return {
            "trust_level": _clamp_unit_interval(relationship_profile.get("trust_level"), 0.0),
            "repair_history_score": _clamp_unit_interval(relationship_profile.get("repair_history_score"), 0.0),
            "candor_tolerance": _clamp_unit_interval(relationship_profile.get("candor_tolerance"), 0.5),
            "warmth_preference": _clamp_unit_interval(relationship_profile.get("warmth_preference"), 0.5),
            "shared_milestones": [
                dict(item) for item in (relationship_profile.get("shared_milestones") or []) if isinstance(item, dict)
            ][:3],
            "boundary_notes": [
                dict(item) for item in (relationship_profile.get("boundary_notes") or []) if isinstance(item, dict)
            ][:3],
        }

    async def write_session_state(
        self,
        *,
        user_id: UUID,
        session_id: str,
        field: str,
        value: Any,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        plan_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        normalized_field = str(field or "").strip()
        if normalized_field not in COMPANION_SESSION_WRITE_FIELDS:
            raise ValueError(f"Unsupported companion field for session write: {normalized_field}")
        if not session_id:
            raise ValueError("session_id is required for companion session writes")

        session_state_before = await self._get_session_companion_state(session_id)
        old_value = session_state_before.get(normalized_field)
        normalized_patch = self._normalize_companion_state({normalized_field: value})
        if normalized_field not in normalized_patch:
            raise ValueError(f"Invalid companion value for field: {normalized_field}")
        new_value = normalized_patch[normalized_field]
        evidence_payload = self._normalize_evidence(evidence)
        confidence_value = _clamp_unit_interval(confidence, 0.7)

        session_revision = self.self_revision_service.build_revision(
            field=normalized_field,
            layer="session",
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            evidence=evidence_payload,
            confidence=confidence_value,
        )
        session_result = await self.self_revision_service.append_session_revision(
            session_id=session_id,
            revision=session_revision,
            state_patch={normalized_field: new_value},
        )

        plan_uuid = self._coerce_plan_uuid(plan_id)
        revisions = await self.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)
        matching_revision_count = self._count_matching_revisions(
            revisions,
            field=normalized_field,
            new_value=new_value,
        )

        promotions: list[dict[str, Any]] = []
        if plan_uuid is not None and self._should_promote_to_episode(
            field=normalized_field,
            evidence=evidence_payload,
            confidence=confidence_value,
            matching_revision_count=matching_revision_count,
        ):
            episode_state_before = await self._get_episode_companion_state(user_id, plan_uuid)
            episode_revision = self.self_revision_service.build_revision(
                field=normalized_field,
                layer="episode",
                old_value=episode_state_before.get(normalized_field),
                new_value=new_value,
                reason=reason,
                evidence=evidence_payload,
                confidence=confidence_value,
                promotion_source_layer="session",
            )
            promotions.append(
                await self.self_revision_service.append_episode_revision(
                    user_id=user_id,
                    plan_id=plan_uuid,
                    revision=episode_revision,
                    state_patch={normalized_field: new_value},
                )
            )

        if normalized_field in _PROFILE_PROMOTABLE_FIELDS and self._should_promote_to_profile(
            field=normalized_field,
            evidence=evidence_payload,
            confidence=confidence_value,
            matching_revision_count=matching_revision_count,
        ):
            profile_state_before = await self._get_profile_companion_state(user_id)
            profile_revision = self.self_revision_service.build_revision(
                field=normalized_field,
                layer="profile",
                old_value=profile_state_before.get(normalized_field),
                new_value=new_value,
                reason=reason,
                evidence=evidence_payload,
                confidence=confidence_value,
                promotion_source_layer="session",
            )
            promotions.append(
                await self.self_revision_service.append_profile_revision(
                    user_id=user_id,
                    revision=profile_revision,
                    state_patch={normalized_field: new_value},
                )
            )

        return {
            "updated": True,
            "field": normalized_field,
            "session_write": session_result,
            "effective_companion_state": await self.get_effective_state(
                user_id, plan_id=plan_id, session_id=session_id
            ),
            "recent_revisions": await self.get_self_revision_history(
                user_id,
                plan_id=plan_id,
                session_id=session_id,
            ),
            "promotions": promotions,
        }

    async def write_companion_growth_note(
        self,
        *,
        user_id: UUID,
        session_id: str,
        note: str,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        plan_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        return await self.write_session_state(
            user_id=user_id,
            session_id=session_id,
            field="companion_growth_note",
            value=note,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            plan_id=plan_id,
        )

    async def write_relationship_note(
        self,
        *,
        user_id: UUID,
        session_id: str,
        note: str,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        note_kind: str = "milestone",
        plan_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        result = await self.write_session_state(
            user_id=user_id,
            session_id=session_id,
            field="relationship_note",
            value=note,
            reason=reason,
            evidence={**dict(evidence or {}), "note_kind": note_kind},
            confidence=confidence,
            plan_id=plan_id,
        )

        revisions = result.get("recent_revisions") or []
        matching_revision_count = self._count_matching_revisions(
            revisions,
            field="relationship_note",
            new_value=note,
        )
        profile_promotion = await self.relationship_profile_service.maybe_promote_relationship_note(
            user_id=user_id,
            note=note,
            note_kind=note_kind,
            reason=reason,
            evidence={**self._normalize_evidence(evidence), "note_kind": note_kind},
            confidence=_clamp_unit_interval(confidence, 0.7),
            matching_revision_count=matching_revision_count,
        )
        if profile_promotion:
            promotions = list(result.get("promotions") or [])
            promotions.append(profile_promotion)
            result["promotions"] = promotions
            result["relationship_profile"] = await self.get_relationship_profile(user_id)
        return result

    async def _get_profile_companion_state(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        state = inferred.get("companion_state")
        return state if isinstance(state, dict) else {}

    async def _get_profile_revisions(self, user_id: UUID) -> list[dict[str, Any]]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        revisions = inferred.get("companion_revision_history")
        if not isinstance(revisions, list):
            return []
        return [dict(item) for item in revisions if isinstance(item, dict)][:5]

    async def _get_episode_companion_state(self, user_id: UUID, plan_id: UUID | str | None) -> dict[str, Any]:
        plan_uuid = self._coerce_plan_uuid(plan_id)
        if plan_uuid is None:
            return {}
        plan_state = await self.plan_state_service.get_plan_state(user_id, plan_uuid)
        if plan_state is None or not isinstance(plan_state.facts, dict):
            return {}
        state = plan_state.facts.get("companion_state")
        return state if isinstance(state, dict) else {}

    async def _get_episode_revisions(self, user_id: UUID, plan_id: UUID | str | None) -> list[dict[str, Any]]:
        plan_uuid = self._coerce_plan_uuid(plan_id)
        if plan_uuid is None:
            return []
        plan_state = await self.plan_state_service.get_plan_state(user_id, plan_uuid)
        if plan_state is None or not isinstance(plan_state.facts, dict):
            return []
        revisions = plan_state.facts.get("companion_revision_history")
        if not isinstance(revisions, list):
            return []
        return [dict(item) for item in revisions if isinstance(item, dict)][:5]

    async def _get_session_companion_state(self, session_id: str | None) -> dict[str, Any]:
        if not self.redis or not session_id:
            return {}
        payload = await self._read_json_key(f"{SESSION_COMPANION_KEY_PREFIX}{session_id}")
        if not isinstance(payload, dict):
            return {}
        if isinstance(payload.get("companion_state"), dict):
            return dict(payload["companion_state"])
        return dict(payload)

    async def _get_session_revisions(self, session_id: str | None) -> list[dict[str, Any]]:
        if not self.redis or not session_id:
            return []
        revisions = await self._read_json_key(f"{SESSION_COMPANION_REVISIONS_KEY_PREFIX}{session_id}")
        if isinstance(revisions, list):
            return [dict(item) for item in revisions if isinstance(item, dict)][:5]
        payload = await self._read_json_key(f"{SESSION_COMPANION_KEY_PREFIX}{session_id}")
        if isinstance(payload, dict) and isinstance(payload.get("companion_revision_history"), list):
            return [dict(item) for item in payload["companion_revision_history"] if isinstance(item, dict)][:5]
        return []

    async def _read_json_key(self, key: str) -> dict[str, Any] | list[Any] | None:
        try:
            raw = self.redis.get(key)
            if inspect.isawaitable(raw):
                raw = await raw
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if isinstance(raw, (dict, list)):
                return raw
            if isinstance(raw, str):
                parsed = json.loads(raw)
                if isinstance(parsed, (dict, list)):
                    return parsed
        except Exception:
            return None
        return None

    @staticmethod
    def _normalize_companion_state(raw: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {}

        defaults = DEFAULT_COMPANION_STATE.to_dict()
        normalized: dict[str, Any] = {}
        for key in COMPANION_STATE_ALLOWED_FIELDS:
            if key not in raw:
                continue
            value = raw.get(key)
            if key in _FLOAT_FIELDS:
                normalized[key] = _clamp_unit_interval(value, float(defaults[key]))
                continue
            if key in _ENUM_FIELDS:
                candidate = str(value or "").strip().lower()
                normalized[key] = candidate if candidate in _ENUM_FIELDS[key] else defaults[key]
                continue
            normalized[key] = str(value or "").strip()[:320]
        return normalized

    @staticmethod
    def _normalize_evidence(evidence: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(evidence or {})
        normalized = {
            "source": str(payload.get("source") or "conversation").strip(),
            "message_id": str(payload.get("message_id") or "").strip(),
            "snippet": str(payload.get("snippet") or "").strip()[:280],
            "measurable_effect": bool(payload.get("measurable_effect")),
        }
        if payload.get("note_kind"):
            normalized["note_kind"] = str(payload.get("note_kind")).strip().lower()
        return normalized

    @staticmethod
    def _count_matching_revisions(
        revisions: list[dict[str, Any]],
        *,
        field: str,
        new_value: Any,
    ) -> int:
        target = CompanionStateService._normalize_revision_value(new_value)
        return sum(
            1
            for item in revisions
            if isinstance(item, dict)
            and item.get("field") == field
            and CompanionStateService._normalize_revision_value(item.get("new_value")) == target
        )

    @staticmethod
    def _normalize_revision_value(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _should_promote_to_episode(
        *,
        field: str,
        evidence: dict[str, Any],
        confidence: float,
        matching_revision_count: int,
    ) -> bool:
        return (
            field in COMPANION_SESSION_WRITE_FIELDS
            and field != "relationship_note"
            and bool(evidence.get("measurable_effect"))
            and confidence >= 0.7
            and matching_revision_count >= 2
        )

    @staticmethod
    def _should_promote_to_profile(
        *,
        field: str,
        evidence: dict[str, Any],
        confidence: float,
        matching_revision_count: int,
    ) -> bool:
        return (
            field in _PROFILE_PROMOTABLE_FIELDS
            and bool(evidence.get("measurable_effect"))
            and confidence >= 0.8
            and matching_revision_count >= 3
        )

    @staticmethod
    def _coerce_plan_uuid(plan_id: UUID | str | None) -> UUID | None:
        if isinstance(plan_id, UUID):
            return plan_id
        raw = str(plan_id or "").strip()
        if not raw:
            return None
        try:
            return UUID(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _revision_sort_key(item: dict[str, Any]) -> tuple[int, str]:
        raw = str(item.get("timestamp") or "").strip()
        if not raw:
            return (0, "")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return (1, parsed.isoformat())
        except ValueError:
            return (0, raw)
