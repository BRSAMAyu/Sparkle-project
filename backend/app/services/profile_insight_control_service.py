from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.memory import MemoryCorrection
from app.services.personalization.inferred_meta import INFERRED_META
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _coerce_preference_value(pref_key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (int, float)):
        return {"value": value}
    if isinstance(value, str):
        stripped = value.strip()
        if pref_key == "study_time_preference" and stripped.isdigit():
            return {"minutes": int(stripped)}
        if stripped.replace(".", "", 1).isdigit():
            return {"value": float(stripped)} if "." in stripped else {"value": int(stripped)}
        return {"value": stripped}
    return {"value": value}


def _merge_preferences(explicit: dict[str, Any], inferred: dict[str, Any]) -> dict[str, Any]:
    merged = dict(inferred or {})
    merged.update(explicit or {})
    return merged


def _merge_scope_overrides(merged_preferences: dict[str, Any], target_id: str, scope: str | None) -> dict[str, Any]:
    overrides = dict(merged_preferences.get("insight_scope_overrides") or {})
    if scope is None:
        overrides.pop(target_id, None)
    else:
        overrides[target_id] = {"scope": scope}
    return overrides


@dataclass
class ProfileInsightControlResult:
    status: str
    target_id: str
    action: str
    preference_version: int


class ProfileInsightControlService:
    """Shared Stage 9 user-correction lane for profile insight controls."""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis or cache_service.redis
        self.profile_write_service = ProfileWriteService(db, self.redis)
        self.pref_service = PreferenceService(db, self.redis)

    async def apply_control(
        self,
        *,
        user_id: UUID,
        target_id: str,
        action: str,
        value: Any | None = None,
        reason: str | None = None,
        source: str = "insight_control",
    ) -> ProfileInsightControlResult:
        normalized_target_id = _strip(target_id)
        normalized_action = _strip(action).lower()
        if not normalized_target_id:
            raise ValueError("target_id required")
        if normalized_action not in {"wrong", "used_to_be_true", "exam_mode_only", "reset_override"}:
            raise ValueError("unsupported action")

        prefs = await self.pref_service.get_preferences(user_id)
        merged_preferences = _merge_preferences(prefs.explicit or {}, prefs.inferred or {})
        meta = INFERRED_META.get(normalized_target_id)

        preference_version = prefs.version or 0
        if normalized_action == "reset_override":
            if meta is None:
                raise LookupError("unknown inferred key")
            result = await self.profile_write_service.reset_override_preference(
                user_id=user_id,
                pref_key=normalized_target_id,
            )
            scope_updates = _merge_scope_overrides(merged_preferences, normalized_target_id, None)
            scope_result = await self.profile_write_service.set_explicit_preference(
                user_id=user_id,
                pref_key="insight_scope_overrides",
                pref_value=scope_updates,
                evidence_refs=[{"type": "user_state", "id": source, "schema_version": "insight_control.v1"}],
                source_type="user_state",
                source=source,
            )
            preference_version = max(result.preference_version, scope_result.preference_version)
        elif meta is not None:
            if normalized_action == "wrong":
                if meta.adjustable and value is not None:
                    value_payload = _coerce_preference_value(normalized_target_id, value)
                    result = await self.profile_write_service.override_inferred_preference(
                        user_id=user_id,
                        pref_key=normalized_target_id,
                        pref_value=value_payload,
                        evidence_refs=[{"type": "user_state", "id": source, "schema_version": "insight_control.v1"}],
                        source=source,
                    )
                    preference_version = result.preference_version
                else:
                    result = await self.profile_write_service.remove_inferred_preference(
                        user_id=user_id,
                        pref_key=normalized_target_id,
                    )
                    preference_version = result.preference_version
                scope_updates = _merge_scope_overrides(merged_preferences, normalized_target_id, None)
                await self.profile_write_service.set_explicit_preference(
                    user_id=user_id,
                    pref_key="insight_scope_overrides",
                    pref_value=scope_updates,
                    evidence_refs=[{"type": "user_state", "id": source, "schema_version": "insight_control.v1"}],
                    source_type="user_state",
                    source=source,
                )
            elif normalized_action == "used_to_be_true":
                result = await self.profile_write_service.remove_inferred_preference(
                    user_id=user_id,
                    pref_key=normalized_target_id,
                )
                preference_version = result.preference_version
                scope_updates = _merge_scope_overrides(merged_preferences, normalized_target_id, None)
                await self.profile_write_service.set_explicit_preference(
                    user_id=user_id,
                    pref_key="insight_scope_overrides",
                    pref_value=scope_updates,
                    evidence_refs=[{"type": "user_state", "id": source, "schema_version": "insight_control.v1"}],
                    source_type="user_state",
                    source=source,
                )
            elif normalized_action == "exam_mode_only":
                scope_updates = _merge_scope_overrides(merged_preferences, normalized_target_id, "exam_mode_only")
                result = await self.profile_write_service.set_explicit_preference(
                    user_id=user_id,
                    pref_key="insight_scope_overrides",
                    pref_value=scope_updates,
                    evidence_refs=[{"type": "user_state", "id": source, "schema_version": "insight_control.v1"}],
                    source_type="user_state",
                    source=source,
                )
                preference_version = result.preference_version

        correction = MemoryCorrection(
            user_id=user_id,
            memory_type="insight_signal",
            memory_id=user_id,
            action=normalized_action,
            reason=json.dumps(
                {
                    "target_id": normalized_target_id,
                    "field_name": normalized_target_id,
                    "suggested_value": value,
                    "reason": reason,
                    "source": source,
                },
                ensure_ascii=True,
            ),
        )
        self.db.add(correction)
        await self.db.commit()
        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="insight_control_applied",
                category="cognitive",
                title="画像理解已根据你的反馈调整",
                description="Sparkle 会在后续判断中考虑这条修正",
                priority="medium",
                metadata={"target_id": normalized_target_id, "action": normalized_action},
            ),
        )
        return ProfileInsightControlResult(
            status="ok",
            target_id=normalized_target_id,
            action=normalized_action,
            preference_version=preference_version,
        )
