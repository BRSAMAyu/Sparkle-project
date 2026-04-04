from __future__ import annotations

import copy
import inspect
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService

SESSION_COMPANION_KEY_PREFIX = "session:companion:"
SESSION_COMPANION_REVISIONS_KEY_PREFIX = "session:companion:revisions:"
SESSION_COMPANION_TTL_SECONDS = 14 * 24 * 3600
MAX_COMPANION_REVISIONS = 20
MAX_RELATIONSHIP_PROFILE_ITEMS = 8
MAX_RELATIONSHIP_EVIDENCE_REFS = 4


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfRevisionService:
    """Persist companion-level revisions across session, episode, and profile layers."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)
        self.plan_state_service = PlanStateService(db, redis)

    @staticmethod
    def build_revision(
        *,
        field: str,
        layer: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        promotion_source_layer: str | None = None,
    ) -> dict[str, Any]:
        revision = {
            "field": field,
            "layer": layer,
            "old_value": old_value,
            "new_value": new_value,
            "reason": str(reason or "").strip(),
            "evidence": dict(evidence or {}),
            "confidence": float(confidence),
            "timestamp": utcnow_iso(),
        }
        if promotion_source_layer:
            revision["promotion_source_layer"] = promotion_source_layer
        return revision

    async def append_session_revision(
        self,
        *,
        session_id: str,
        revision: dict[str, Any],
        state_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = await self._read_json_key(f"{SESSION_COMPANION_KEY_PREFIX}{session_id}")
        payload = copy.deepcopy(payload) if isinstance(payload, dict) else {}

        companion_state = payload.get("companion_state")
        companion_state = dict(companion_state) if isinstance(companion_state, dict) else {}
        if state_patch:
            companion_state.update(dict(state_patch))

        revisions = await self._session_revisions(session_id, payload=payload)
        revisions.insert(0, dict(revision))
        revisions = revisions[:MAX_COMPANION_REVISIONS]

        payload["companion_state"] = companion_state
        payload["companion_revision_history"] = revisions
        payload["updated_at"] = utcnow_iso()

        await self._write_json_key(
            f"{SESSION_COMPANION_KEY_PREFIX}{session_id}",
            payload,
            ttl_seconds=SESSION_COMPANION_TTL_SECONDS,
        )
        await self._write_json_key(
            f"{SESSION_COMPANION_REVISIONS_KEY_PREFIX}{session_id}",
            revisions,
            ttl_seconds=SESSION_COMPANION_TTL_SECONDS,
        )
        return {
            "layer": "session",
            "revision": dict(revision),
            "companion_state": companion_state,
            "revision_count": len(revisions),
        }

    async def append_episode_revision(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        revision: dict[str, Any],
        state_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan_state = await self.plan_state_service.get_or_create_plan_state(user_id, plan_id)
        facts = copy.deepcopy(plan_state.facts or {})

        companion_state = facts.get("companion_state")
        companion_state = dict(companion_state) if isinstance(companion_state, dict) else {}
        if state_patch:
            companion_state.update(dict(state_patch))

        revisions = [
            dict(item) for item in list(facts.get("companion_revision_history") or []) if isinstance(item, dict)
        ]
        revisions.insert(0, dict(revision))
        revisions = revisions[:MAX_COMPANION_REVISIONS]

        facts["companion_state"] = companion_state
        facts["companion_revision_history"] = revisions

        await self.plan_state_service.upsert_plan_state(
            user_id,
            plan_id,
            {"facts": facts},
        )
        return {
            "layer": "episode",
            "revision": dict(revision),
            "companion_state": companion_state,
            "revision_count": len(revisions),
        }

    async def append_profile_revision(
        self,
        *,
        user_id: UUID,
        revision: dict[str, Any],
        state_patch: dict[str, Any] | None = None,
        relationship_profile_patch: dict[str, Any] | None = None,
        identity_adjustment_candidate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = copy.deepcopy(prefs.inferred or {})
        inferred_updates: dict[str, Any] = {}

        companion_state = inferred.get("companion_state")
        companion_state = dict(companion_state) if isinstance(companion_state, dict) else {}
        if state_patch:
            companion_state.update(dict(state_patch))
            inferred_updates["companion_state"] = companion_state

        revisions = [
            dict(item) for item in list(inferred.get("companion_revision_history") or []) if isinstance(item, dict)
        ]
        revisions.insert(0, dict(revision))
        inferred_updates["companion_revision_history"] = revisions[:MAX_COMPANION_REVISIONS]

        if relationship_profile_patch:
            inferred_updates["relationship_profile"] = self._merge_dict(
                inferred.get("relationship_profile"),
                relationship_profile_patch,
            )

        if identity_adjustment_candidate:
            candidates = [
                dict(item)
                for item in list(inferred.get("identity_adjustment_candidates") or [])
                if isinstance(item, dict)
            ]
            candidates.insert(0, dict(identity_adjustment_candidate))
            inferred_updates["identity_adjustment_candidates"] = candidates[:10]

        updated = await self.preference_service.update_inferred(user_id, inferred_updates)
        return {
            "layer": "profile",
            "revision": dict(revision),
            "companion_state": dict((updated.inferred or {}).get("companion_state") or {}),
            "relationship_profile": dict((updated.inferred or {}).get("relationship_profile") or {}),
            "revision_count": len(list((updated.inferred or {}).get("companion_revision_history") or [])),
        }

    async def _session_revisions(
        self,
        session_id: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        revisions = await self._read_json_key(f"{SESSION_COMPANION_REVISIONS_KEY_PREFIX}{session_id}")
        if isinstance(revisions, list):
            return [dict(item) for item in revisions if isinstance(item, dict)]
        source = (
            payload
            if isinstance(payload, dict)
            else await self._read_json_key(f"{SESSION_COMPANION_KEY_PREFIX}{session_id}")
        )
        if isinstance(source, dict) and isinstance(source.get("companion_revision_history"), list):
            return [dict(item) for item in source["companion_revision_history"] if isinstance(item, dict)]
        return []

    async def _read_json_key(self, key: str) -> dict[str, Any] | list[Any] | None:
        if not self.redis:
            return None
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

    async def _write_json_key(self, key: str, payload: dict[str, Any] | list[Any], *, ttl_seconds: int) -> None:
        if not self.redis:
            return
        dumped = json.dumps(payload, ensure_ascii=False)
        if hasattr(self.redis, "setex"):
            result = self.redis.setex(key, ttl_seconds, dumped)
            if inspect.isawaitable(result):
                await result
            return
        result = self.redis.set(key, dumped)
        if inspect.isawaitable(result):
            await result
        if hasattr(self.redis, "expire"):
            expire_result = self.redis.expire(key, ttl_seconds)
            if inspect.isawaitable(expire_result):
                await expire_result

    @staticmethod
    def _merge_dict(base: Any, patch: dict[str, Any]) -> dict[str, Any]:
        merged = copy.deepcopy(base) if isinstance(base, dict) else {}
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = SelfRevisionService._merge_dict(merged[key], value)
            elif isinstance(value, list) and isinstance(merged.get(key), list):
                if key in {"shared_milestones", "boundary_notes"}:
                    merged[key] = SelfRevisionService._merge_relationship_entries(merged[key], value)
                else:
                    merged[key] = copy.deepcopy(value) + [
                        copy.deepcopy(item) for item in merged[key] if item not in value
                    ]
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    @staticmethod
    def _merge_relationship_entries(base: list[Any], patch: list[Any]) -> list[dict[str, Any]]:
        by_identity: dict[tuple[str, str], dict[str, Any]] = {}
        ordered_identities: list[tuple[str, str]] = []

        def _remember(item: Any, *, prefer_new: bool) -> None:
            if not isinstance(item, dict):
                return
            identity = SelfRevisionService._relationship_entry_identity(item)
            if identity not in ordered_identities:
                ordered_identities.append(identity)
            existing = by_identity.get(identity)
            if existing is None:
                by_identity[identity] = copy.deepcopy(item)
                return

            merged = copy.deepcopy(existing if prefer_new else item)
            merged.update(copy.deepcopy(item if prefer_new else existing))
            merged["evidence_refs"] = SelfRevisionService._merge_evidence_refs(
                existing.get("evidence_refs"),
                item.get("evidence_refs"),
            )
            try:
                merged["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(item.get("confidence") or 0.0),
                )
            except (TypeError, ValueError):
                pass
            by_identity[identity] = merged

        for item in patch:
            _remember(item, prefer_new=True)
        for item in base:
            _remember(item, prefer_new=False)

        return [
            by_identity[identity]
            for identity in ordered_identities[:MAX_RELATIONSHIP_PROFILE_ITEMS]
            if identity in by_identity
        ]

    @staticmethod
    def _merge_evidence_refs(existing: Any, new_refs: Any) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for collection in (new_refs, existing):
            for item in collection or []:
                if not isinstance(item, dict):
                    continue
                identity = (
                    str(item.get("source") or "").strip(),
                    str(item.get("message_id") or "").strip(),
                    str(item.get("snippet") or "").strip(),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                merged.append(copy.deepcopy(item))
                if len(merged) >= MAX_RELATIONSHIP_EVIDENCE_REFS:
                    return merged
        return merged

    @staticmethod
    def _relationship_entry_identity(item: dict[str, Any]) -> tuple[str, str]:
        return (
            str(item.get("kind") or "").strip().lower(),
            " ".join(str(item.get("summary") or "").strip().lower().split()),
        )
