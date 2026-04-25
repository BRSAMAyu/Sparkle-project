from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.memory import MemoryCorrection
from app.services.personalization.preference_service import PreferenceService
from app.services.system_update_service import SystemUpdateService, build_system_update

SELF_MODEL_KEY = "self_model"
KNOWN_ASSUMPTIONS_KEY = "known_assumptions"
MAX_VISIBLE_CARDS = 3
VISIBLE_CONFIDENCE_THRESHOLD = 0.7


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = _strip(value).lower()
    return text in {"true", "1", "yes", "y"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence(value: Any) -> float:
    return round(max(0.0, min(1.0, _as_float(value, 0.0))), 3)


def _confidence_label(value: Any) -> str:
    return f"{int(round(_confidence(value) * 100))}%"


def _parse_iso(value: Any) -> datetime:
    text = _strip(value)
    if not text:
        return datetime.min
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.min


def _recency_sort_value(value: Any) -> float:
    parsed = _parse_iso(value)
    if parsed == datetime.min:
        return 0.0
    try:
        return -parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


class AuroraCalibrationCardService:
    """Read/write lane for Aurora calibration cards backed by self_model."""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis or cache_service.redis
        self.pref_service = PreferenceService(db, self.redis)

    async def list_cards(
        self,
        *,
        user_id: UUID,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        prefs = await self.pref_service.get_preferences(user_id)
        self_model = self._get_self_model(prefs.inferred or {})
        assumptions = _as_list(self_model.get(KNOWN_ASSUMPTIONS_KEY))

        visible = [item for item in assumptions if self._is_visible_assumption(item, plan_id=plan_id)]
        visible.sort(key=self._sort_key)
        cards = [self._serialize_card(item) for item in visible[:MAX_VISIBLE_CARDS]]

        needs_confirmation = any(_as_bool(item.get("needs_confirmation")) for item in cards)
        return {
            "items": cards,
            "surface": {
                "state": "needs_confirmation" if needs_confirmation else "observing",
                "label": "Aurora · 需要确认" if needs_confirmation else "Aurora · 观察中",
            },
        }

    async def respond(
        self,
        *,
        user_id: UUID,
        card_id: str,
        response: str,
        reason: str | None = None,
        corrected_assumption: str | None = None,
    ) -> dict[str, Any]:
        normalized_card_id = _strip(card_id)
        normalized_response = _strip(response).lower()
        if not normalized_card_id:
            raise ValueError("card_id required")
        if normalized_response not in {"confirm", "incorrect", "mute"}:
            raise ValueError("unsupported response")

        prefs = await self.pref_service.get_preferences(user_id)
        inferred = dict(prefs.inferred or {})
        self_model = self._get_self_model(inferred)
        assumptions = _as_list(self_model.get(KNOWN_ASSUMPTIONS_KEY))
        now_iso = _utcnow_iso()

        updated_assumption: dict[str, Any] | None = None
        updated_items: list[dict[str, Any]] = []
        for raw_item in assumptions:
            item = _as_dict(raw_item)
            if _strip(item.get("id")) != normalized_card_id:
                updated_items.append(item)
                continue
            updated_assumption = self._apply_response(
                item=item,
                response=normalized_response,
                reason=reason,
                corrected_assumption=corrected_assumption,
                responded_at=now_iso,
            )
            updated_items.append(updated_assumption)

        if updated_assumption is None:
            raise LookupError("calibration card not found")

        self_model[KNOWN_ASSUMPTIONS_KEY] = updated_items
        self_model["updated_at"] = now_iso
        inferred[SELF_MODEL_KEY] = self_model

        updated_prefs = await self.pref_service.update_inferred_raw(user_id, inferred)

        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="aurora_calibration_card",
                memory_id=user_id,
                action=normalized_response,
                reason=json.dumps(
                    {
                        "card_id": normalized_card_id,
                        "reason": reason,
                        "corrected_assumption": corrected_assumption,
                    },
                    ensure_ascii=True,
                ),
            )
        )
        await self.db.commit()

        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="aurora_calibration_card_responded",
                category="cognitive",
                title="Aurora 已记录你的校准反馈",
                description="后续判断会参考这次确认与修正。",
                priority="low",
                metadata={
                    "card_id": normalized_card_id,
                    "response": normalized_response,
                },
            ),
        )

        return {
            "status": "ok",
            "card": self._serialize_card(updated_assumption),
            "preference_version": updated_prefs.version or 0,
        }

    @staticmethod
    def _get_self_model(inferred: dict[str, Any]) -> dict[str, Any]:
        value = inferred.get(SELF_MODEL_KEY)
        model = _as_dict(value)
        assumptions = _as_list(model.get(KNOWN_ASSUMPTIONS_KEY))
        model[KNOWN_ASSUMPTIONS_KEY] = [
            _as_dict(item) for item in assumptions if isinstance(item, dict) and _strip(item.get("id"))
        ]
        return model

    @staticmethod
    def _is_visible_assumption(item: Any, *, plan_id: str | None = None) -> bool:
        assumption = _as_dict(item)
        if not assumption:
            return False

        status = _strip(assumption.get("status") or "pending").lower()
        if status in {"confirmed", "rejected", "suppressed", "dismissed", "archived"}:
            return False
        if _as_bool(assumption.get("suppressed_by_user")):
            return False

        if plan_id:
            assumption_plan_id = _strip(assumption.get("plan_id"))
            if assumption_plan_id and assumption_plan_id != _strip(plan_id):
                return False

        return _as_bool(assumption.get("needs_confirmation")) or (
            _confidence(assumption.get("confidence")) < VISIBLE_CONFIDENCE_THRESHOLD
        )

    @staticmethod
    def _sort_key(item: Any) -> tuple[int, float, float]:
        assumption = _as_dict(item)
        updated_at = assumption.get("updated_at") or assumption.get("last_observed_at")
        return (
            0 if _as_bool(assumption.get("needs_confirmation")) else 1,
            _confidence(assumption.get("confidence")),
            _recency_sort_value(updated_at),
        )

    @staticmethod
    def _serialize_card(item: dict[str, Any]) -> dict[str, Any]:
        evidence = [_strip(entry) for entry in _as_list(item.get("evidence")) if _strip(entry)][:3]
        statement = _strip(item.get("statement") or item.get("title"))
        evidence_summary = _strip(item.get("evidence_summary"))
        if not evidence_summary and evidence:
            evidence_summary = "证据：" + "；".join(evidence[:2])

        return {
            "id": _strip(item.get("id")),
            "title": _strip(item.get("title") or statement or "我有一个判断需要你确认"),
            "statement": statement or "我有一个判断需要你确认。",
            "confidence": _confidence(item.get("confidence")),
            "confidence_label": _confidence_label(item.get("confidence")),
            "needs_confirmation": _as_bool(item.get("needs_confirmation")),
            "evidence_summary": evidence_summary,
            "evidence": evidence,
            "plan_id": _strip(item.get("plan_id")) or None,
            "source": _strip(item.get("source")) or None,
            "last_observed_at": _strip(item.get("last_observed_at")) or None,
        }

    @staticmethod
    def _apply_response(
        *,
        item: dict[str, Any],
        response: str,
        reason: str | None,
        corrected_assumption: str | None,
        responded_at: str,
    ) -> dict[str, Any]:
        updated = dict(item)
        history = _as_list(updated.get("response_history"))
        history.append(
            {
                "response": response,
                "reason": _strip(reason) or None,
                "corrected_assumption": _strip(corrected_assumption) or None,
                "responded_at": responded_at,
            }
        )
        updated["response_history"] = history[-10:]
        updated["last_user_response"] = response
        updated["last_responded_at"] = responded_at
        updated["updated_at"] = responded_at
        updated["needs_confirmation"] = False

        if response == "confirm":
            updated["status"] = "confirmed"
            updated["confirmed_at"] = responded_at
            updated["confidence"] = max(_confidence(updated.get("confidence")), 0.85)
        elif response == "incorrect":
            updated["status"] = "rejected"
            updated["rejected_at"] = responded_at
            updated["confidence"] = min(_confidence(updated.get("confidence")), 0.25)
            if _strip(corrected_assumption):
                updated["user_correction"] = _strip(corrected_assumption)
        else:
            updated["status"] = "suppressed"
            updated["suppressed_by_user"] = True
            updated["suppressed_at"] = responded_at

        return updated
