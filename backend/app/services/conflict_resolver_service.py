from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aurora_stage20 import ConflictResolutionRecord, UnresolvedConflict
from app.models.memory import EpisodicMemory
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


ResolutionAction = Literal["accept", "reject", "surface_to_user"]
UserSelection = Literal["left", "right", "none"]


@dataclass(frozen=True)
class ConflictCandidate:
    user_id: UUID
    summary: str
    source_lane: str
    confidence: float
    occurred_at: datetime
    evidence_token: str
    semantic_key: str
    subject_type: str = "self"
    due_at: datetime | None = None
    evidence_refs: tuple[dict[str, Any], ...] = ()
    mentioned_entity_hash: str | None = None
    mentioned_entity_owner_user_id: UUID | None = None
    source_type: str = "chat"
    source_id: str | None = None


@dataclass(frozen=True)
class ResolutionDecision:
    action: ResolutionAction
    reason: str
    winner_record_id: UUID | None = None
    winner_lane: str | None = None
    loser_record_ids: tuple[UUID, ...] = ()
    loser_lanes: tuple[str, ...] = ()
    evidence_tokens: tuple[str, ...] = ()
    conflict_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ConflictResolverService:
    """Deterministic Stage 20 conflict arbitration with explicit audit records."""

    PRIORITY_BY_TIER = {
        "working_memory": 1,
        "llm": 2,
        "rule": 3,
        "explicit": 4,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def load_conflicting_records(
        self,
        *,
        user_id: UUID,
        semantic_key: str,
    ) -> list[EpisodicMemory]:
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.semantic_key == semantic_key,
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def resolve(
        self,
        *,
        candidate: ConflictCandidate,
        existing_records: list[EpisodicMemory],
    ) -> ResolutionDecision:
        if not candidate.evidence_token:
            raise ValueError("ConflictResolver requires a non-empty evidence_token")

        if not existing_records:
            return ResolutionDecision(
                action="accept",
                reason="no_conflict",
                evidence_tokens=(candidate.evidence_token,),
                conflict_key=candidate.semantic_key,
            )

        for record in existing_records:
            if record.user_id != candidate.user_id:
                raise ValueError("ConflictResolver may not arbitrate across users")

        stronger_existing: EpisodicMemory | None = None
        tie_record: EpisodicMemory | None = None
        loser_records: list[EpisodicMemory] = []

        for record in existing_records:
            comparison = self._compare_candidate_to_record(candidate, record)
            if comparison == "candidate_loses":
                stronger_existing = self._pick_stronger_record(stronger_existing, record)
            elif comparison == "tie":
                tie_record = self._pick_stronger_record(tie_record, record)
            else:
                loser_records.append(record)

        if stronger_existing is not None:
            return ResolutionDecision(
                action="reject",
                reason="higher_priority_existing",
                winner_record_id=stronger_existing.id,
                winner_lane=stronger_existing.source_lane,
                evidence_tokens=self._collect_tokens(candidate, stronger_existing),
                conflict_key=candidate.semantic_key,
                metadata={
                    "candidate_lane": candidate.source_lane,
                    "candidate_summary": candidate.summary,
                },
            )

        if tie_record is not None:
            return ResolutionDecision(
                action="surface_to_user",
                reason="unresolved_conflict",
                winner_lane=tie_record.source_lane,
                evidence_tokens=self._collect_tokens(candidate, tie_record),
                conflict_key=candidate.semantic_key,
                metadata={
                    "candidate_summary": candidate.summary,
                    "existing_summary": tie_record.summary,
                    "existing_record_id": str(tie_record.id),
                },
            )

        return ResolutionDecision(
            action="accept",
            reason="candidate_overrides_lower_priority",
            winner_lane=candidate.source_lane,
            loser_record_ids=tuple(record.id for record in loser_records),
            loser_lanes=tuple(record.source_lane for record in loser_records),
            evidence_tokens=tuple(dict.fromkeys(self._collect_tokens(candidate, *loser_records))),
            conflict_key=candidate.semantic_key,
        )

    async def record_resolution(
        self,
        *,
        user_id: UUID,
        decision: ResolutionDecision,
        winner_record_id: UUID | None = None,
    ) -> ConflictResolutionRecord:
        record = ConflictResolutionRecord(
            user_id=user_id,
            loser_record_id=decision.loser_record_ids[0] if decision.loser_record_ids else None,
            winner_record_id=winner_record_id or decision.winner_record_id,
            loser_lane=decision.loser_lanes[0] if decision.loser_lanes else None,
            winner_lane=decision.winner_lane,
            resolution_action=decision.action,
            resolution_reason=decision.reason,
            resolved_at=_utcnow(),
            conflict_key=decision.conflict_key,
            evidence_tokens=list(decision.evidence_tokens),
            metadata_payload=decision.metadata,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def apply_live_decision(
        self,
        *,
        candidate: ConflictCandidate,
        decision: ResolutionDecision,
        new_record: EpisodicMemory | None = None,
    ) -> ResolutionDecision:
        if decision.action == "accept":
            if new_record is None or not decision.loser_record_ids:
                return decision
            records = await self._load_records(decision.loser_record_ids)
            for record in records:
                record.retracted_at = _utcnow()
                record.updated_at = _utcnow()
            await self.record_resolution(
                user_id=candidate.user_id,
                decision=decision,
                winner_record_id=new_record.id,
            )
            await self.db.commit()
            return decision

        if decision.action == "reject":
            await self.record_resolution(user_id=candidate.user_id, decision=decision)
            await self.db.commit()
            return decision

        unresolved = await self.create_unresolved_conflict(candidate=candidate, decision=decision)
        await self.record_resolution(
            user_id=candidate.user_id,
            decision=ResolutionDecision(
                action=decision.action,
                reason=decision.reason,
                winner_lane=decision.winner_lane,
                evidence_tokens=decision.evidence_tokens,
                conflict_key=decision.conflict_key,
                metadata={**decision.metadata, "unresolved_conflict_id": str(unresolved.id)},
            ),
        )
        await self.db.commit()
        return decision

    async def record_shadow_comparison(
        self,
        *,
        user_id: UUID,
        legacy_blocked: bool,
        decision: ResolutionDecision,
    ) -> ConflictResolutionRecord:
        metadata = {
            **decision.metadata,
            "shadow_mode": True,
            "legacy_blocked": legacy_blocked,
            "resolver_action": decision.action,
        }
        shadow_decision = ResolutionDecision(
            action=decision.action,
            reason=f"shadow_compare:{decision.reason}",
            winner_record_id=decision.winner_record_id,
            winner_lane=decision.winner_lane,
            loser_record_ids=decision.loser_record_ids,
            loser_lanes=decision.loser_lanes,
            evidence_tokens=decision.evidence_tokens,
            conflict_key=decision.conflict_key,
            metadata=metadata,
        )
        record = await self.record_resolution(user_id=user_id, decision=shadow_decision)
        await self.db.commit()
        return record

    async def create_unresolved_conflict(
        self,
        *,
        candidate: ConflictCandidate,
        decision: ResolutionDecision,
    ) -> UnresolvedConflict:
        existing_record = None
        existing_id = decision.metadata.get("existing_record_id")
        if existing_id:
            existing_record = await EpisodicMemory.get_by_id(self.db, UUID(str(existing_id)), include_deleted=True)

        unresolved = UnresolvedConflict(
            user_id=candidate.user_id,
            conflict_key=decision.conflict_key or candidate.semantic_key,
            left_record_id=None,
            right_record_id=existing_record.id if existing_record is not None else None,
            left_summary=candidate.summary,
            right_summary=existing_record.summary if existing_record is not None else str(decision.metadata.get("existing_summary") or ""),
            left_lane=candidate.source_lane,
            right_lane=existing_record.source_lane if existing_record is not None else str(decision.winner_lane or ""),
            left_evidence_token=candidate.evidence_token,
            right_evidence_token=existing_record.evidence_token if existing_record is not None else None,
            left_payload=self._candidate_payload(candidate),
            right_payload=self._record_payload(existing_record) if existing_record is not None else {},
            surfaced_at=_utcnow(),
        )
        self.db.add(unresolved)
        await self.db.flush()
        return unresolved

    async def list_unresolved_conflicts(
        self,
        *,
        user_id: UUID,
    ) -> list[UnresolvedConflict]:
        result = await self.db.execute(
            select(UnresolvedConflict).where(
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.status == "pending_user",
                UnresolvedConflict.deleted_at.is_(None),
            )
            .order_by(UnresolvedConflict.surfaced_at.desc())
        )
        return list(result.scalars().all())

    async def arbitrate_unresolved_conflict(
        self,
        *,
        user_id: UUID,
        conflict_id: UUID,
        selection: UserSelection,
    ) -> UnresolvedConflict | None:
        result = await self.db.execute(
            select(UnresolvedConflict).where(
                UnresolvedConflict.id == conflict_id,
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.deleted_at.is_(None),
            )
        )
        conflict = result.scalar_one_or_none()
        if conflict is None:
            return None

        winner_record_id: UUID | None = None
        if selection == "left":
            winner_record_id = await self._materialize_side(conflict.left_payload, user_id=user_id)
            await self._retract_if_present(conflict.right_record_id, user_id=user_id)
        elif selection == "right":
            winner_record_id = await self._materialize_side(conflict.right_payload, user_id=user_id)
            await self._retract_if_present(conflict.left_record_id, user_id=user_id)
        else:
            await self._retract_if_present(conflict.left_record_id, user_id=user_id)
            await self._retract_if_present(conflict.right_record_id, user_id=user_id)

        conflict.status = "resolved"
        conflict.selected_side = selection
        conflict.resolved_at = _utcnow()
        conflict.resolution_reason = "user_arbitrated"
        conflict.updated_at = _utcnow()

        decision = ResolutionDecision(
            action="accept" if selection in {"left", "right"} else "reject",
            reason="user_arbitrated",
            winner_record_id=winner_record_id,
            winner_lane=conflict.left_lane if selection == "left" else conflict.right_lane if selection == "right" else None,
            conflict_key=conflict.conflict_key,
            evidence_tokens=tuple(
                token
                for token in (conflict.left_evidence_token, conflict.right_evidence_token)
                if token
            ),
            metadata={
                "unresolved_conflict_id": str(conflict.id),
                "selected_side": selection,
            },
        )
        await self.record_resolution(user_id=user_id, decision=decision, winner_record_id=winner_record_id)
        await self.db.commit()
        await self.db.refresh(conflict)
        return conflict

    def _compare_candidate_to_record(
        self,
        candidate: ConflictCandidate,
        record: EpisodicMemory,
    ) -> Literal["candidate_wins", "candidate_loses", "tie"]:
        candidate_rank = self._priority(candidate.source_lane)
        record_rank = self._priority(record.source_lane)
        if candidate_rank != record_rank:
            return "candidate_wins" if candidate_rank > record_rank else "candidate_loses"

        candidate_conf = float(candidate.confidence or 0.0)
        record_conf = float(record.confidence or 0.0)
        if candidate_conf != record_conf:
            return "candidate_wins" if candidate_conf > record_conf else "candidate_loses"

        candidate_time = candidate.occurred_at
        record_time = record.occurred_at or record.updated_at
        if candidate_time != record_time:
            return "candidate_wins" if candidate_time > record_time else "candidate_loses"
        return "tie"

    def _priority(self, source_lane: str) -> int:
        lane = (source_lane or "").strip().lower()
        if lane == "working_memory":
            return self.PRIORITY_BY_TIER["working_memory"]
        if lane in {"llm_extractor", "llm_extraction"}:
            return self.PRIORITY_BY_TIER["llm"]
        if lane == "inferred_extraction":
            return self.PRIORITY_BY_TIER["rule"]
        return self.PRIORITY_BY_TIER["explicit"]

    def _pick_stronger_record(
        self,
        current: EpisodicMemory | None,
        candidate: EpisodicMemory,
    ) -> EpisodicMemory:
        if current is None:
            return candidate
        if self._priority(candidate.source_lane) > self._priority(current.source_lane):
            return candidate
        if float(candidate.confidence or 0.0) > float(current.confidence or 0.0):
            return candidate
        current_time = current.occurred_at or current.updated_at
        candidate_time = candidate.occurred_at or candidate.updated_at
        if candidate_time > current_time:
            return candidate
        return current

    def _collect_tokens(self, candidate: ConflictCandidate, *records: EpisodicMemory) -> tuple[str, ...]:
        tokens = [candidate.evidence_token]
        tokens.extend(record.evidence_token for record in records if record.evidence_token)
        return tuple(dict.fromkeys(token for token in tokens if token))

    async def _load_records(self, record_ids: tuple[UUID, ...]) -> list[EpisodicMemory]:
        if not record_ids:
            return []
        result = await self.db.execute(
            select(EpisodicMemory).where(EpisodicMemory.id.in_(record_ids))
        )
        return list(result.scalars().all())

    async def _retract_if_present(self, record_id: UUID | None, *, user_id: UUID) -> None:
        if record_id is None:
            return
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.id == record_id,
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return
        record.retracted_at = _utcnow()
        record.updated_at = _utcnow()

    async def _materialize_side(self, payload: dict[str, Any], *, user_id: UUID) -> UUID | None:
        record_id = payload.get("record_id")
        if record_id:
            return UUID(str(record_id))
        if not payload:
            return None
        memory_service = MemoryService(self.db)
        record = await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=str(payload.get("summary") or ""),
            source_type=str(payload.get("source_type") or "chat"),
            source_id=payload.get("source_id"),
            source_lane=str(payload.get("source_lane") or "inferred_extraction"),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            importance_score=float(payload.get("confidence") or 0.0),
            confidence=float(payload.get("confidence") or 0.0),
            tags=["stage20:user_arbitrated_conflict"],
            evidence_refs=list(payload.get("evidence_refs") or []),
            evidence_token=payload.get("evidence_token"),
            decay_policy=payload.get("decay_policy"),
            semantic_key=payload.get("semantic_key"),
            subject_type=str(payload.get("subject_type") or "self"),
            due_at=datetime.fromisoformat(str(payload["due_at"])) if payload.get("due_at") else None,
            mentioned_entity_hash=payload.get("mentioned_entity_hash"),
            mentioned_entity_owner_user_id=UUID(str(payload["mentioned_entity_owner_user_id"]))
            if payload.get("mentioned_entity_owner_user_id")
            else None,
            emit_system_update=False,
        )
        return record.id if record is not None else None

    def _candidate_payload(self, candidate: ConflictCandidate) -> dict[str, Any]:
        return {
            "summary": candidate.summary,
            "source_type": candidate.source_type,
            "source_id": candidate.source_id,
            "source_lane": candidate.source_lane,
            "occurred_at": candidate.occurred_at.isoformat(),
            "due_at": candidate.due_at.isoformat() if candidate.due_at else None,
            "confidence": candidate.confidence,
            "evidence_refs": list(candidate.evidence_refs),
            "evidence_token": candidate.evidence_token,
            "semantic_key": candidate.semantic_key,
            "subject_type": candidate.subject_type,
            "mentioned_entity_hash": candidate.mentioned_entity_hash,
            "mentioned_entity_owner_user_id": (
                str(candidate.mentioned_entity_owner_user_id) if candidate.mentioned_entity_owner_user_id else None
            ),
        }

    def _record_payload(self, record: EpisodicMemory) -> dict[str, Any]:
        return {
            "record_id": str(record.id),
            "summary": record.summary,
            "source_type": record.source_type,
            "source_id": record.source_id,
            "source_lane": record.source_lane,
            "occurred_at": record.occurred_at.isoformat(),
            "due_at": record.due_at.isoformat() if record.due_at else None,
            "confidence": record.confidence,
            "evidence_refs": list(record.evidence_refs or []),
            "evidence_token": record.evidence_token,
            "semantic_key": record.semantic_key,
            "subject_type": record.subject_type,
            "mentioned_entity_hash": record.mentioned_entity_hash,
            "mentioned_entity_owner_user_id": (
                str(record.mentioned_entity_owner_user_id) if record.mentioned_entity_owner_user_id else None
            ),
        }
