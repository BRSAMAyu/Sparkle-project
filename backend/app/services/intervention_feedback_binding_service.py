from __future__ import annotations

import hashlib
import json
from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.models.card_protocol import (
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.intervention_strategy_learner import InterventionStrategyLearner


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compact_text(value: Any, *, limit: int = 600) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _coerce_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _coerce_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


class InterventionFeedbackBindingService:
    ACTIVE_INTERVENTIONS_KEY_PREFIX = "session:active_interventions:"
    LAST_FEEDBACK_BINDING_KEY_PREFIX = "session:last_feedback_binding:"
    DEDUPE_KEY_PREFIX = "session:feedback_binding_dedupe:"

    ACTIVE_INTERVENTIONS_TTL_SECONDS = 7 * 24 * 60 * 60
    LAST_FEEDBACK_BINDING_TTL_SECONDS = 7 * 24 * 60 * 60
    DEDUPE_TTL_SECONDS = 12 * 60 * 60
    RECENT_PLAUSIBLE_DAYS = 7

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.record_service = InterventionRecordService(db)
        self.strategy_learner = InterventionStrategyLearner(db)

    @staticmethod
    def extract_active_interventions_from_updates(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for update in updates:
            if not isinstance(update, dict):
                continue
            metadata = update.get("metadata") if isinstance(update.get("metadata"), dict) else {}
            raw_intervention_id = metadata.get("intervention_id")
            if not raw_intervention_id:
                continue
            try:
                intervention_id = str(UUID(str(raw_intervention_id)))
            except (TypeError, ValueError):
                continue
            if intervention_id in seen:
                continue
            seen.add(intervention_id)
            candidates.append(
                {
                    "intervention_id": intervention_id,
                    "source": "system_update",
                    "update_type": str(update.get("type") or "").strip(),
                    "evolution_kind": str(metadata.get("evolution_kind") or "").strip(),
                    "description": _compact_text(update.get("description"), limit=220),
                }
            )
        return candidates

    async def remember_active_interventions(
        self,
        session_id: str | None,
        active_interventions: list[dict[str, Any]] | None,
    ) -> None:
        if not self.redis or not str(session_id or "").strip():
            return
        payload = active_interventions if isinstance(active_interventions, list) else []
        try:
            await self.redis.setex(
                f"{self.ACTIVE_INTERVENTIONS_KEY_PREFIX}{session_id}",
                self.ACTIVE_INTERVENTIONS_TTL_SECONDS,
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            logger.warning(f"Failed to persist active interventions for session {session_id}: {exc}")

    async def get_remembered_active_interventions(self, session_id: str | None) -> list[dict[str, Any]]:
        if not self.redis or not str(session_id or "").strip():
            return []
        try:
            raw = await self.redis.get(f"{self.ACTIVE_INTERVENTIONS_KEY_PREFIX}{session_id}")
            decoded = json.loads(raw) if raw else []
        except Exception as exc:
            logger.warning(f"Failed to read active interventions for session {session_id}: {exc}")
            return []
        return _coerce_list_of_dicts(decoded)

    async def get_last_feedback_binding(self, session_id: str | None) -> dict[str, Any] | None:
        if not self.redis or not str(session_id or "").strip():
            return None
        try:
            raw = await self.redis.get(f"{self.LAST_FEEDBACK_BINDING_KEY_PREFIX}{session_id}")
            decoded = json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning(f"Failed to read last feedback binding for session {session_id}: {exc}")
            return None
        return decoded if isinstance(decoded, dict) else None

    async def resolve_active_interventions(
        self,
        *,
        user_id: UUID,
        session_id: str | None = None,
        explicit_intervention_id: str | None = None,
        runtime_active_interventions: list[dict[str, Any]] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        seen: set[str] = set()

        async def _append_record(record_id: str, source: str, metadata: dict[str, Any] | None = None) -> None:
            try:
                record_uuid = UUID(str(record_id))
            except (TypeError, ValueError):
                return
            if str(record_uuid) in seen:
                return
            stmt = select(InterventionRecord).where(
                InterventionRecord.id == record_uuid,
                InterventionRecord.user_id == user_id,
                InterventionRecord.not_deleted_filter(),
            )
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()
            if record is None:
                return
            seen.add(str(record.id))
            resolved.append(self._serialize_record(record, source=source, metadata=metadata))

        if explicit_intervention_id:
            await _append_record(explicit_intervention_id, "explicit_context")

        for candidate in runtime_active_interventions or []:
            if len(resolved) >= limit:
                break
            await _append_record(
                str(candidate.get("intervention_id") or ""),
                str(candidate.get("source") or "runtime_context"),
                metadata=candidate,
            )

        if len(resolved) < limit:
            for candidate in await self.get_remembered_active_interventions(session_id):
                if len(resolved) >= limit:
                    break
                await _append_record(
                    str(candidate.get("intervention_id") or ""),
                    str(candidate.get("source") or "session_memory"),
                    metadata=candidate,
                )

        if len(resolved) < limit:
            pending_records = await self.record_service.get_pending_for_user(user_id, limit=limit)
            for record in pending_records:
                if len(resolved) >= limit:
                    break
                if str(record.id) in seen:
                    continue
                seen.add(str(record.id))
                resolved.append(self._serialize_record(record, source="pending_record"))

        if len(resolved) < limit:
            recent_records = await self.record_service.get_recent_for_user(
                user_id,
                days=self.RECENT_PLAUSIBLE_DAYS,
                limit=limit,
            )
            for record in recent_records:
                if len(resolved) >= limit:
                    break
                if str(record.id) in seen:
                    continue
                seen.add(str(record.id))
                resolved.append(self._serialize_record(record, source="recent_record"))

        if session_id and resolved:
            await self.remember_active_interventions(session_id, resolved)
        return resolved[:limit]

    async def bind_feedback(
        self,
        *,
        user_id: UUID,
        session_id: str | None,
        sentiment: str,
        user_words: str,
        confidence: float,
        intervention_id: str | None = None,
        message_id: str | None = None,
        source: str = "conversation",
        runtime_active_interventions: list[dict[str, Any]] | None = None,
        snooze_hours: int = 24,
    ) -> dict[str, Any]:
        normalized_sentiment = str(sentiment or "").strip().lower()
        normalized_words = _compact_text(user_words, limit=600)
        bounded_confidence = round(max(0.0, min(1.0, float(confidence))), 2)

        candidates = await self.resolve_active_interventions(
            user_id=user_id,
            session_id=session_id,
            explicit_intervention_id=intervention_id,
            runtime_active_interventions=runtime_active_interventions,
            limit=3,
        )
        if not candidates:
            return {
                "bound": False,
                "duplicate_suppressed": False,
                "reason": "no_active_intervention",
                "active_interventions": [],
            }

        target_id = str(candidates[0].get("intervention_id") or "").strip()
        target_record = await self._load_record(user_id=user_id, intervention_id=target_id)
        if target_record is None:
            return {
                "bound": False,
                "duplicate_suppressed": False,
                "reason": "intervention_not_found",
                "active_interventions": candidates,
            }

        fingerprint = self._feedback_fingerprint(
            sentiment=normalized_sentiment,
            user_words=normalized_words,
            message_id=message_id,
        )
        prior_binding = await self.get_last_feedback_binding(session_id)
        if isinstance(prior_binding, dict) and prior_binding.get("fingerprint") == fingerprint:
            return {
                "bound": False,
                "duplicate_suppressed": True,
                "reason": "duplicate_feedback",
                "active_interventions": candidates,
                "last_feedback_binding": prior_binding,
                "intervention_record": self._serialize_record(target_record, source="duplicate_hit"),
            }

        transition_warning: str | None = None
        try:
            target_record = await self._apply_feedback_transition(
                target_record=target_record,
                sentiment=normalized_sentiment,
                user_words=normalized_words,
                snooze_hours=snooze_hours,
            )
        except ValueError as exc:
            transition_warning = str(exc)

        self._append_feedback_evidence(
            target_record=target_record,
            sentiment=normalized_sentiment,
            user_words=normalized_words,
            confidence=bounded_confidence,
            source=source,
            message_id=message_id,
            fingerprint=fingerprint,
        )
        await self.db.flush()

        learner_recorded = await self._record_strategy_learning(
            user_id=user_id,
            record=target_record,
            sentiment=normalized_sentiment,
            confidence=bounded_confidence,
            message_id=message_id,
            user_words=normalized_words,
        )

        last_feedback_binding = {
            "timestamp": _utcnow().isoformat(),
            "intervention_id": str(target_record.id),
            "sentiment": normalized_sentiment,
            "confidence": bounded_confidence,
            "message_id": message_id,
            "fingerprint": fingerprint,
            "duplicate_suppressed": False,
            "resolved_via": str(candidates[0].get("source") or "unknown"),
        }
        await self._persist_last_feedback_binding(session_id, last_feedback_binding)

        payload = {
            "bound": True,
            "duplicate_suppressed": False,
            "active_interventions": candidates,
            "last_feedback_binding": last_feedback_binding,
            "intervention_record": self._serialize_record(
                target_record,
                source=str(candidates[0].get("source") or "bound_feedback"),
            ),
            "learner_recorded": learner_recorded,
        }
        if transition_warning:
            payload["transition_warning"] = transition_warning
        return payload

    async def _apply_feedback_transition(
        self,
        *,
        target_record: InterventionRecord,
        sentiment: str,
        user_words: str,
        snooze_hours: int,
    ) -> InterventionRecord:
        del user_words
        current = target_record.acceptance_status
        if sentiment in {"helped", "accepted", "dismissed", "not_helped"}:
            if current == InterventionAcceptanceStatus.CREATED:
                target_record = await self.record_service.mark_delivered(target_record.id) or target_record
                current = target_record.acceptance_status
            if current == InterventionAcceptanceStatus.DELIVERED:
                target_record = await self.record_service.mark_seen(target_record.id) or target_record
                current = target_record.acceptance_status

        if sentiment == "helped":
            if current in {
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                target_record = await self.record_service.mark_accepted(target_record.id) or target_record
                current = target_record.acceptance_status
            if current == InterventionAcceptanceStatus.ACCEPTED:
                target_record = await self.record_service.mark_acted(
                    target_record.id,
                    action_payload={"feedback_summary": "helped"},
                ) or target_record
            return target_record

        if sentiment == "accepted":
            if current in {
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                target_record = await self.record_service.mark_accepted(target_record.id) or target_record
            return target_record

        if sentiment in {"dismissed", "not_helped"}:
            if current in {
                InterventionAcceptanceStatus.SEEN,
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SNOOZED,
            }:
                target_record = await self.record_service.mark_dismissed(target_record.id) or target_record
            return target_record

        if sentiment == "snoozed":
            if current == InterventionAcceptanceStatus.CREATED:
                target_record = await self.record_service.mark_delivered(target_record.id) or target_record
                current = target_record.acceptance_status
            if current in {
                InterventionAcceptanceStatus.DELIVERED,
                InterventionAcceptanceStatus.SEEN,
            }:
                target_record = await self.record_service.mark_snoozed(
                    target_record.id,
                    snooze_hours=snooze_hours,
                ) or target_record
            return target_record

        if sentiment == "mixed":
            return target_record

        raise ValueError(f"Unsupported sentiment: {sentiment}")

    def _append_feedback_evidence(
        self,
        *,
        target_record: InterventionRecord,
        sentiment: str,
        user_words: str,
        confidence: float,
        source: str,
        message_id: str | None,
        fingerprint: str,
    ) -> None:
        action_payload = _coerce_dict(target_record.action_payload)
        log_entries = [
            item
            for item in (action_payload.get("conversation_feedback_log") or [])
            if isinstance(item, dict)
        ]
        entry = {
            "timestamp": _utcnow().isoformat(),
            "sentiment": sentiment,
            "user_words": user_words,
            "confidence": confidence,
            "source": source,
            "message_id": message_id,
            "fingerprint": fingerprint,
        }
        log_entries.insert(0, entry)
        action_payload["conversation_feedback_log"] = log_entries[:20]
        action_payload["latest_feedback"] = entry
        target_record.action_payload = action_payload

    async def _record_strategy_learning(
        self,
        *,
        user_id: UUID,
        record: InterventionRecord,
        sentiment: str,
        confidence: float,
        message_id: str | None,
        user_words: str,
    ) -> bool:
        if sentiment == "mixed":
            return False
        outcome = (
            record.outcome_status
            if record.outcome_status != InterventionOutcomeStatus.PENDING
            else InterventionOutcomeStatus.UNKNOWN
        )
        try:
            saved = await self.strategy_learner.record_outcome(
                user_id=user_id,
                intervention_id=record.id,
                outcome_status=outcome,
                context_snapshot={
                    "source": "conversation_feedback_binding",
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "message_id": message_id,
                    "user_words": _compact_text(user_words, limit=240),
                },
            )
            return saved is not None
        except Exception as exc:
            logger.warning(f"Failed to record intervention strategy outcome for {record.id}: {exc}")
            return False

    async def _load_record(
        self,
        *,
        user_id: UUID,
        intervention_id: str,
    ) -> InterventionRecord | None:
        try:
            intervention_uuid = UUID(str(intervention_id))
        except (TypeError, ValueError):
            return None
        stmt = select(InterventionRecord).where(
            InterventionRecord.id == intervention_uuid,
            InterventionRecord.user_id == user_id,
            InterventionRecord.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _persist_last_feedback_binding(
        self,
        session_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        if not self.redis or not str(session_id or "").strip():
            return
        try:
            await self.redis.setex(
                f"{self.LAST_FEEDBACK_BINDING_KEY_PREFIX}{session_id}",
                self.LAST_FEEDBACK_BINDING_TTL_SECONDS,
                json.dumps(payload, ensure_ascii=False),
            )
            await self.redis.setex(
                f"{self.DEDUPE_KEY_PREFIX}{session_id}",
                self.DEDUPE_TTL_SECONDS,
                json.dumps({"fingerprint": payload.get("fingerprint")}, ensure_ascii=False),
            )
        except Exception as exc:
            logger.warning(f"Failed to persist feedback binding for session {session_id}: {exc}")

    @staticmethod
    def _feedback_fingerprint(
        *,
        sentiment: str,
        user_words: str,
        message_id: str | None,
    ) -> str:
        base = str(message_id or "").strip()
        if not base:
            base = f"{sentiment}:{' '.join(str(user_words or '').split()).lower()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_record(
        record: InterventionRecord,
        *,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "intervention_id": str(record.id),
            "source": source,
            "trigger_type": record.trigger_type.value if record.trigger_type else None,
            "delivery_strategy": record.delivery_strategy.value if record.delivery_strategy else None,
            "delivery_channel": record.delivery_channel.value if record.delivery_channel else None,
            "acceptance_status": record.acceptance_status.value if record.acceptance_status else None,
            "outcome_status": record.outcome_status.value if record.outcome_status else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "metadata": metadata or {},
        }
