from __future__ import annotations

import inspect
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.orchestration.soul_compiler import DEFAULT_COMPANION_STATE
from app.services.constitutional_drift_firewall import ConstitutionalDriftFirewall
from app.services.five_layer_learning_contract import (
    DEFAULT_FIVE_LAYER_CONTRACT,
    build_temporal_metadata,
    classify_profile_claim_kind,
    count_distinct_sessions,
    learning_is_active,
)
from app.services.layer_conflict_resolver import LayerConflictResolver
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService
from app.services.relationship_profile_service import RelationshipProfileService
from app.services.self_revision_service import (
    COMPANION_GOVERNANCE_KEY,
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
COMPANION_CROSS_SESSION_LEDGER_KEY = "companion_cross_session_evidence"


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
        self.contract = DEFAULT_FIVE_LAYER_CONTRACT
        self.conflict_resolver = LayerConflictResolver(self.contract)
        self.drift_firewall = ConstitutionalDriftFirewall()

    async def get_effective_state(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        profile_governance = await self._get_profile_governance(user_id)
        episode_governance = await self._get_episode_governance(user_id, plan_id)
        profile_state = self._filter_governed_companion_state(
            await self._get_profile_companion_state(user_id),
            profile_governance,
        )
        episode_state = self._filter_governed_companion_state(
            await self._get_episode_companion_state(user_id, plan_id),
            episode_governance,
        )
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

    async def get_layer_alignment(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        profile_governance = await self._get_profile_governance(user_id)
        episode_governance = await self._get_episode_governance(user_id, plan_id)
        profile_state = self._filter_governed_companion_state(
            await self._get_profile_companion_state(user_id),
            profile_governance,
        )
        episode_state = self._filter_governed_companion_state(
            await self._get_episode_companion_state(user_id, plan_id),
            episode_governance,
        )
        session_state = self._normalize_companion_state(await self._get_session_companion_state(session_id))

        conflicts: list[dict[str, Any]] = []
        for field in _PROFILE_PROMOTABLE_FIELDS:
            values = []
            for layer_name, layer_state, governance in (
                ("profile", profile_state, profile_governance),
                ("episode", episode_state, episode_governance),
                ("session", session_state, {}),
            ):
                if field not in layer_state:
                    continue
                values.append(
                    {
                        "layer": layer_name,
                        "value": layer_state.get(field),
                        "confidence": _as_dict(governance.get(field)).get("confidence", 0.6),
                        "updated_at": _as_dict(governance.get(field)).get("promoted_at"),
                        "evidence_summary": _as_dict(governance.get(field)).get("evidence_summary") or f"{layer_name}:{field}",
                        "repeated_evidence": 2 if layer_name in {"profile", "episode"} else 1,
                    }
                )
            report = self.conflict_resolver.resolve_field_conflict(
                learning_key=field,
                layer_values=values,
                context_preferred_layer="episode" if "episode" in {item.get("layer") for item in values} else None,
            )
            if report is not None:
                conflicts.append(
                    {
                        "field": field,
                        "values": [{"layer": item["layer"], "value": item["value"]} for item in values],
                        "resolution_rule": report.explanation,
                        "conflict_report": report.to_dict(),
                    }
                )

        stale_items = [
            *self.conflict_resolver.stale_items_from_governance(profile_governance),
            *self.conflict_resolver.stale_items_from_governance(episode_governance),
        ]
        pending_reviews = [item for item in stale_items if item.get("status") == "review_due"]
        revisions = await self.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)
        pending_promotions = self._pending_promotions_from_revisions(revisions)

        return {
            "constitutional": {"status": "mostly_built", "writes_allowed": False},
            "session": {"status": "built_v1", "writes_allowed": True, "active_fields": sorted(session_state.keys())},
            "episode": {"status": "partially_built", "writes_allowed": "promotion_only", "active_fields": sorted(episode_state.keys())},
            "profile": {"status": "partially_built", "writes_allowed": "evidence_gated", "active_fields": sorted(profile_state.keys())},
            "conflicts": conflicts,
            "active_conflicts": [item.get("conflict_report") for item in conflicts if isinstance(item.get("conflict_report"), dict)],
            "stale_items": stale_items,
            "pending_promotions": pending_promotions,
            "required_reviews": pending_reviews,
            "contract_version": self.contract.version,
            "silent_drift_risk": "elevated" if conflicts else "bounded",
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
        evidence_payload["session_id"] = session_id
        if plan_id is not None:
            evidence_payload["plan_id"] = str(plan_id)
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
        if normalized_field in _PROFILE_PROMOTABLE_FIELDS or normalized_field == "relationship_note":
            await self._append_cross_session_revision(user_id, session_revision)

        plan_uuid = self._coerce_plan_uuid(plan_id)
        revisions = await self.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)
        matching_revision_count = self._count_matching_revisions(
            revisions,
            field=normalized_field,
            new_value=new_value,
        )
        cross_session_revisions = await self._get_cross_session_revisions(user_id)
        cross_session_matches = self._matching_cross_session_revisions(
            cross_session_revisions,
            field=normalized_field,
            new_value=new_value,
        )
        cross_session_match_count = len(cross_session_matches)
        distinct_session_count = count_distinct_sessions(cross_session_matches)

        promotions: list[dict[str, Any]] = []
        if plan_uuid is not None and self._should_promote_to_episode(
            field=normalized_field,
            evidence=evidence_payload,
            confidence=confidence_value,
            matching_revision_count=matching_revision_count,
        ):
            episode_firewall = None
            if normalized_field in {"self_description_note", "companion_growth_note"}:
                episode_firewall = self.drift_firewall.evaluate_change(
                    change_type=f"durable_self_description:{normalized_field}",
                    target_layer="episode",
                    proposed_value=new_value,
                    evidence=evidence_payload,
                ).to_dict()
            episode_state_before = await self._get_episode_companion_state(user_id, plan_uuid)
            if not episode_firewall or episode_firewall.get("allowed"):
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
                        governance_patch={
                            normalized_field: {
                                **build_temporal_metadata(
                                    contract=self.contract,
                                    target_layer="episode",
                                    source_layer="session",
                                    confidence=confidence_value,
                                    evidence=evidence_payload,
                                    promotion_reason="repeated_effective_evidence",
                                    state_kind="recent_state",
                                ),
                                "status": "active",
                            }
                        },
                    )
                )

        profile_state_before = (
            await self._get_profile_companion_state(user_id)
            if normalized_field in _PROFILE_PROMOTABLE_FIELDS
            else {}
        )
        profile_conflict = self._has_cross_session_conflict(
            existing_state=profile_state_before,
            field=normalized_field,
            new_value=new_value,
        )
        if normalized_field in _PROFILE_PROMOTABLE_FIELDS and self._should_promote_to_profile(
            field=normalized_field,
            evidence=evidence_payload,
            confidence=confidence_value,
            matching_revision_count=max(matching_revision_count, cross_session_match_count),
            distinct_session_count=distinct_session_count,
            has_conflict=profile_conflict,
        ):
            safety_report = self.drift_firewall.evaluate_change(
                change_type=f"profile_companion_learning:{normalized_field}",
                target_layer="profile",
                proposed_value=new_value,
                evidence=evidence_payload,
            ).to_dict()
            if not safety_report.get("allowed"):
                promotions.append(
                    {
                        "layer": "profile",
                        "field": normalized_field,
                        "decision": "constitutional_block",
                        "safety_report": safety_report,
                    }
                )
            elif safety_report.get("disposition") == "escalate_review":
                promotions.append(
                    {
                        "layer": "profile",
                        "field": normalized_field,
                        "decision": "review_required",
                        "safety_report": safety_report,
                    }
                )
            else:
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
                        governance_patch={
                            normalized_field: {
                                **build_temporal_metadata(
                                    contract=self.contract,
                                    target_layer="profile",
                                    source_layer="session",
                                    confidence=confidence_value,
                                    evidence=evidence_payload,
                                    promotion_reason="repeated_effective_evidence",
                                    state_kind=classify_profile_claim_kind(
                                        confidence=confidence_value,
                                        distinct_sessions=distinct_session_count,
                                        measurable_effect=bool(evidence_payload.get("measurable_effect")),
                                    ),
                                ),
                                "status": "active",
                                "firewall": safety_report,
                            }
                        },
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
            "layer_alignment": await self.get_layer_alignment(
                user_id,
                plan_id=plan_id,
                session_id=session_id,
            ),
            "promotions": promotions,
            "conflict_resolution": {
                "profile_conflict": profile_conflict,
                "rule": "Conflicting cross-session signals require stronger repeated evidence before profile overwrite.",
            },
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
        distinct_session_count = count_distinct_sessions(revisions)
        cross_session_revisions = await self._get_cross_session_revisions(user_id)
        cross_session_matches = self._matching_cross_session_revisions(
            cross_session_revisions,
            field="relationship_note",
            new_value=note,
        )
        matching_revision_count = max(matching_revision_count, len(cross_session_matches))
        distinct_session_count = count_distinct_sessions(cross_session_matches)
        safety_report = self.drift_firewall.evaluate_change(
            change_type="relationship_profile_promotion",
            target_layer="profile",
            proposed_value=note,
            evidence={**self._normalize_evidence(evidence), "note_kind": note_kind},
        ).to_dict()
        profile_promotion = None
        if safety_report.get("allowed") and safety_report.get("disposition") != "escalate_review":
            profile_promotion = await self.relationship_profile_service.maybe_promote_relationship_note(
                user_id=user_id,
                note=note,
                note_kind=note_kind,
                reason=reason,
                evidence={**self._normalize_evidence(evidence), "note_kind": note_kind, "session_id": session_id},
                confidence=_clamp_unit_interval(confidence, 0.7),
                matching_revision_count=matching_revision_count,
                distinct_session_count=distinct_session_count,
            )
        if profile_promotion:
            promotions = list(result.get("promotions") or [])
            promotions.append(profile_promotion)
            result["promotions"] = promotions
            result["relationship_profile"] = await self.get_relationship_profile(user_id)
        elif safety_report.get("disposition") in {"blocked", "escalate_review"}:
            promotions = list(result.get("promotions") or [])
            promotions.append(
                {
                    "layer": "profile",
                    "field": "relationship_note",
                    "decision": safety_report.get("disposition"),
                    "safety_report": safety_report,
                }
            )
            result["promotions"] = promotions
        return result

    async def _get_profile_companion_state(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        state = inferred.get("companion_state")
        return state if isinstance(state, dict) else {}

    async def _get_profile_governance(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        state = inferred.get(COMPANION_GOVERNANCE_KEY)
        return state if isinstance(state, dict) else {}

    async def _get_cross_session_revisions(self, user_id: UUID) -> list[dict[str, Any]]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        revisions = inferred.get(COMPANION_CROSS_SESSION_LEDGER_KEY)
        if not isinstance(revisions, list):
            return []
        return [dict(item) for item in revisions if isinstance(item, dict)][:20]

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

    async def _get_episode_governance(self, user_id: UUID, plan_id: UUID | str | None) -> dict[str, Any]:
        plan_uuid = self._coerce_plan_uuid(plan_id)
        if plan_uuid is None:
            return {}
        plan_state = await self.plan_state_service.get_plan_state(user_id, plan_uuid)
        if plan_state is None or not isinstance(plan_state.facts, dict):
            return {}
        state = plan_state.facts.get(COMPANION_GOVERNANCE_KEY)
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

    @classmethod
    def _filter_governed_companion_state(
        cls,
        raw: dict[str, Any] | None,
        governance: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized = cls._normalize_companion_state(raw)
        if not normalized:
            return {}
        governance = _as_dict(governance)
        filtered: dict[str, Any] = {}
        for field, value in normalized.items():
            if field not in governance or learning_is_active(_as_dict(governance.get(field))):
                filtered[field] = value
        return filtered

    async def _append_cross_session_revision(self, user_id: UUID, revision: dict[str, Any]) -> None:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = prefs.inferred if isinstance(prefs.inferred, dict) else {}
        ledger = [dict(item) for item in list(inferred.get(COMPANION_CROSS_SESSION_LEDGER_KEY) or []) if isinstance(item, dict)]
        ledger.insert(0, dict(revision))
        await self.preference_service.update_inferred(
            user_id,
            {COMPANION_CROSS_SESSION_LEDGER_KEY: ledger[:20]},
        )

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

    @classmethod
    def _matching_cross_session_revisions(
        cls,
        revisions: list[dict[str, Any]],
        *,
        field: str,
        new_value: Any,
    ) -> list[dict[str, Any]]:
        target = cls._normalize_revision_value(new_value)
        return [
            dict(item)
            for item in revisions
            if isinstance(item, dict)
            and item.get("field") == field
            and cls._normalize_revision_value(item.get("new_value")) == target
        ]

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
        threshold = DEFAULT_FIVE_LAYER_CONTRACT.promotion_threshold("episode", "companion_session_to_episode")
        return (
            field in COMPANION_SESSION_WRITE_FIELDS
            and field != "relationship_note"
            and (not threshold.requires_measurable_effect or bool(evidence.get("measurable_effect")))
            and confidence >= threshold.min_confidence
            and matching_revision_count >= threshold.min_matching_revisions
        )

    @staticmethod
    def _should_promote_to_profile(
        *,
        field: str,
        evidence: dict[str, Any],
        confidence: float,
        matching_revision_count: int,
        distinct_session_count: int = 0,
        has_conflict: bool = False,
    ) -> bool:
        threshold = (
            DEFAULT_FIVE_LAYER_CONTRACT.promotion_threshold("profile", "companion_conflict_overwrite")
            if has_conflict
            else DEFAULT_FIVE_LAYER_CONTRACT.promotion_threshold("profile", "companion_session_to_profile")
        )
        return (
            field in _PROFILE_PROMOTABLE_FIELDS
            and (not threshold.requires_measurable_effect or bool(evidence.get("measurable_effect")))
            and confidence >= threshold.min_confidence
            and matching_revision_count >= threshold.min_matching_revisions
            and distinct_session_count >= threshold.min_distinct_sessions
        )

    @classmethod
    def _has_cross_session_conflict(
        cls,
        *,
        existing_state: dict[str, Any] | None,
        field: str,
        new_value: Any,
    ) -> bool:
        if not isinstance(existing_state, dict) or field not in existing_state:
            return False
        current_value = existing_state.get(field)
        if current_value is None or str(current_value).strip() == "":
            return False
        return cls._normalize_revision_value(current_value) != cls._normalize_revision_value(new_value)

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

    def _pending_promotions_from_revisions(self, revisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for field in _PROFILE_PROMOTABLE_FIELDS:
            matches = [
                item for item in revisions
                if isinstance(item, dict) and item.get("field") == field and _as_dict(item.get("evidence")).get("measurable_effect")
            ]
            if not matches:
                continue
            distinct_sessions = count_distinct_sessions(matches)
            latest = matches[0]
            confidence = _clamp_unit_interval(latest.get("confidence"), 0.0)
            episode_threshold = self.contract.promotion_threshold("episode", "companion_session_to_episode")
            profile_threshold = self.contract.promotion_threshold("profile", "companion_session_to_profile")
            if len(matches) < profile_threshold.min_matching_revisions or distinct_sessions < profile_threshold.min_distinct_sessions:
                pending.append(
                    {
                        "field": field,
                        "next_target_layer": "profile",
                        "matching_revisions": len(matches),
                        "distinct_sessions": distinct_sessions,
                        "confidence": confidence,
                    }
                )
            elif len(matches) < episode_threshold.min_matching_revisions:
                pending.append(
                    {
                        "field": field,
                        "next_target_layer": "episode",
                        "matching_revisions": len(matches),
                        "distinct_sessions": distinct_sessions,
                        "confidence": confidence,
                    }
                )
        return pending[:10]


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
