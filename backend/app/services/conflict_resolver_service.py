"""Memory V3 conflict arbitration (Stage 20 prototype, extended by task M-04).

Deterministic arbitration of same-``semantic_key`` episodic claims across
lanes, time and scope. This module EXTENDS the merged prototype — the lane
registry (``KNOWN_SOURCE_LANES`` / ``PRIORITY_BY_TIER``) remains the single
source of truth for lane tiers (the M-01 epistemic contract delegates to it),
and the ``ConflictResolutionRecord`` / ``UnresolvedConflict`` audit tables
remain the resolution-record authority.

M-04 additions (CONFLICT_RESOLVER.md §2-§5):

1. **Priority tuple** — pairwise comparison over
   ``(validity, epistemic class, explicitness(lane tier), user-correction,
   recency, evidence strength)``. Element order follows §3's default priority
   (user statement/correction first, class before recency, recency before
   evidence strength — the §2 tuple lists dimensions, §3 fixes their order).
2. **Conflict categories** — every contested pair is classified
   deterministically into SCOPE_DIFFERENCE / INFERENCE_CONTRADICTION /
   SOURCE_DISAGREEMENT / TEMPORAL_CHANGE / UNSAFE_AMBIGUITY and the category
   rides the resolution record (debug/eval provenance).
3. **Behaviors** (§5): auto-resolve (accept/reject with supersede chain),
   preserve-both (scope difference), revoke-inference (explicit fact
   supersedes an inference-class loser), ask-once (tie → ``surface_to_user``
   with a structured ``clarification`` payload — never a silent pick),
   abstain (both sides unregistered lanes → no write, no question, audited).
4. **M-07-isomorphic side effects (V3-FIX-10 F2/F4)** — every EFFECTIVE
   destructive arbitration effect (loser active→superseded, user-arbitration
   retraction) lands with epoch bump + ``memory.invalidated`` event
   (content-free payload) + derived-cache invalidation, exactly once;
   replays and terminal-state losers are no-ops. User arbitration is the
   5th destructive entry of the epoch contract, registered as
   ``MemoryMutationAction.USER_ARBITRATION`` (sibling entry, same pipeline).

Machine vs human boundary (V3-FIX-10 F6, explicit declaration): "explicit"
means USER-STATED provenance — ``user_confirmed`` lane, or ``direct_capture``
with ``source_type`` in ``USER_STATEMENT_SOURCE_TYPES`` (→ FACT). Machine
writes riding an explicit lane (chat_turn/analysis/…) classify as
OBSERVATION, not FACT (M-01 F1). The arbitration guard blocks inference-TIER
winners over explicit-TIER losers; it does not block all automated writes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import (
    MEMORY_CONFLICT_RESOLUTIONS_TOTAL,
    MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL,
)
from app.core.time_utils import ensure_naive_utc
from app.models.aurora_stage20 import ConflictResolutionRecord, UnresolvedConflict
from app.models.memory import EpisodicMemory
from app.services.memory_epistemic_contract import (
    MEMORY_EPISTEMIC_CONTRACT_VERSION,
    EpistemicClass,
    MemoryRecordStatus,
    classify_episodic_class,
    derive_status,
    lane_priority,
)
from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline, MemoryMutationAction
from app.services.memory_retrieval_prefilter import (
    EPISODIC_HARD_TTL_BY_DECAY_POLICY,
    TODAY_ONLY_DECAY_POLICIES,
)
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

CONFLICT_RESOLVER_VERSION = "memory-v3.m04.v1"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


ResolutionAction = Literal["accept", "reject", "surface_to_user"]
UserSelection = Literal["left", "right", "none"]


class ConflictCategory(StrEnum):
    """Conflict categories (CONFLICT_RESOLVER.md §4)."""

    NONE = "NONE"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    SCOPE_DIFFERENCE = "SCOPE_DIFFERENCE"
    SOURCE_DISAGREEMENT = "SOURCE_DISAGREEMENT"
    INFERENCE_CONTRADICTION = "INFERENCE_CONTRADICTION"
    UNSAFE_AMBIGUITY = "UNSAFE_AMBIGUITY"


# Epistemic-class rank inside the priority tuple (§3 default priority):
# user-stated fact > lived experience outcome > system observation >
# inference/hypothesis.
EPISTEMIC_CLASS_RANK: dict[str, int] = {
    EpistemicClass.FACT.value: 4,
    EpistemicClass.EXPERIENCE.value: 3,
    EpistemicClass.OBSERVATION.value: 2,
    EpistemicClass.HYPOTHESIS.value: 1,
}

# Lanes whose writes ARE user correction/confirmation actions (the
# "user correction" element of the resolution tuple).
USER_CORRECTION_LANES: frozenset[str] = frozenset({"user_confirmed"})

CLARIFICATION_QUESTION = "两条记忆对同一件事的说法不一致，需要你确认保留哪一条"


def _metric_inc(counter: Any, **labels: str) -> None:
    """Metrics must never break arbitration (M-03 convention)."""
    try:
        counter.labels(**labels).inc()
    except Exception:  # noqa: BLE001
        pass


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
    # M-04: decay policy rides the candidate so time-scope arbitration sees
    # the same signals as the stored record side (today-only vs standing).
    decay_policy: str | None = None
    # M-04: writers that already know their epistemic class (e.g. M-06
    # EXPERIENCE lane records) carry it explicitly — same explicit-outranks-
    # derived semantics as the record side's epistemic_class column.
    epistemic_class: str | None = None


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


@dataclass(frozen=True)
class _SideView:
    """Flat comparable projection of one side of a conflict pair."""

    lane: str
    source_type: str
    epistemic_class: str
    lane_tier: int
    is_user_correction: bool
    occurred_at: datetime
    confidence: float
    decay_policy: str | None
    due_at: datetime | None
    entity_hash: str | None

    @property
    def time_scope(self) -> str:
        return _time_scope_of(self.decay_policy, self.due_at)

    def priority_tuple(self) -> tuple:
        return (
            1,  # validity: candidates are new; records are pre-filtered active
            EPISTEMIC_CLASS_RANK.get(self.epistemic_class, 1),
            self.lane_tier,
            1 if self.is_user_correction else 0,
            ensure_naive_utc(self.occurred_at) or datetime.min,
            float(self.confidence or 0.0),
        )

    def provenance(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "epistemic_class": self.epistemic_class,
            "lane_tier": self.lane_tier,
            "user_correction": self.is_user_correction,
            "time_scope": self.time_scope,
        }


def _time_scope_of(decay_policy: str | None, due_at: datetime | None) -> str:
    """Time scope of a claim: ``today`` / ``bounded`` / ``global``.

    Reuses the M-03 TTL vocabularies as the single source of truth: today-only
    decay policies are day-scoped; hard-TTL/due_at-anchored claims are
    event-bounded; soft half-life decay (7d/30d/…) is a RETENTION policy, not
    a claim horizon — such records describe standing (global) claims.
    """
    decay = str(decay_policy or "").strip().lower()
    if decay in TODAY_ONLY_DECAY_POLICIES:
        return "today"
    if due_at is not None or decay in EPISODIC_HARD_TTL_BY_DECAY_POLICY:
        return "bounded"
    return "global"


class ConflictResolverService:
    """Deterministic Stage 20 conflict arbitration with explicit audit records."""

    PRIORITY_BY_TIER = {
        # D2（审计 round2）：未登记 lane 的保守兜底档位——低于一切已知 lane，
        # 防止未来新 lane（如 aurora_calibration_receipt）静默压过 direct_capture。
        "unknown": 0,
        "working_memory": 1,
        "llm": 2,
        "rule": 3,
        "explicit": 4,
    }

    # 显式登记的已知 source_lane（新增 lane 必须登记，否则按 unknown 最低档裁决）
    KNOWN_SOURCE_LANES: dict[str, str] = {
        "direct_capture": "explicit",
        "user_confirmed": "explicit",
        "llm_extractor": "llm",
        "llm_extraction": "llm",
        "inferred_extraction": "rule",
        "working_memory": "working_memory",
    }

    _warned_unknown_lanes: set[str] = set()

    def __init__(self, db: AsyncSession, redis_client: Any | None = None) -> None:
        self.db = db
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------

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

    async def has_unresolved_conflict(
        self,
        *,
        user_id: UUID,
        topic_keys: tuple[str, ...],
        semantic_keys: tuple[str, ...] = (),
    ) -> bool:
        """检测用户是否存在 pending_user 的未决冲突。

        D1（审计 round2）修复：conflict_key 是 semantic_key（sha1 十六进制），
        原实现拿人类可读 topic 与其做子串匹配，数学上永不命中（死门）。
        现按两类语义对齐：
        - ``semantic_keys``：与 conflict_key / payload 内 semantic_key 精确比对；
        - ``topic_keys``：与行内可读范围（left/right_summary 及 payload semantic_key）
          做归一化双向包含比对。
        """
        normalized_topics = tuple(key.strip().lower() for key in topic_keys if key and key.strip())
        normalized_semantic = tuple(key.strip().lower() for key in semantic_keys if key and key.strip())
        if not normalized_topics and not normalized_semantic:
            return False
        result = await self.db.execute(
            select(UnresolvedConflict).where(
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.deleted_at.is_(None),
                UnresolvedConflict.status == "pending_user",
            )
        )
        conflicts = result.scalars().all()
        for conflict in conflicts:
            left_payload = conflict.left_payload if isinstance(conflict.left_payload, dict) else {}
            right_payload = conflict.right_payload if isinstance(conflict.right_payload, dict) else {}
            readable_fields = [
                str(field or "").strip().lower()
                for field in (
                    conflict.conflict_key,
                    conflict.left_summary,
                    conflict.right_summary,
                    left_payload.get("semantic_key"),
                    right_payload.get("semantic_key"),
                )
            ]
            if any(field and field in normalized_semantic for field in readable_fields):
                return True
            if any(
                topic and field and (topic in field or field in topic)
                for field in readable_fields
                for topic in normalized_topics
            ):
                return True
        return False

    # ------------------------------------------------------------------
    # Arbitration core (pure)
    # ------------------------------------------------------------------

    def resolve(
        self,
        *,
        candidate: ConflictCandidate,
        existing_records: list[EpisodicMemory],
    ) -> ResolutionDecision:
        if not candidate.evidence_token:
            raise ValueError("ConflictResolver requires a non-empty evidence_token")

        candidate_side = self._candidate_side(candidate)

        if not existing_records:
            return ResolutionDecision(
                action="accept",
                reason="no_conflict",
                evidence_tokens=(candidate.evidence_token,),
                conflict_key=candidate.semantic_key,
                metadata={
                    "conflict_category": ConflictCategory.NONE.value,
                    "provenance": self._provenance(candidate_side),
                },
            )

        for record in existing_records:
            if record.user_id != candidate.user_id:
                raise ValueError("ConflictResolver may not arbitrate across users")

        # M-04: non-active records (revoked/superseded/retracted/archived/…,
        # per the M-01 status machine) are not contenders — the write path
        # pre-filters them, but resolve() is a public entrypoint (F2 defense).
        contenders: list[tuple[EpisodicMemory, _SideView]] = []
        coexisting: list[EpisodicMemory] = []
        inactive_ignored: list[str] = []
        for record in existing_records:
            if derive_status(record) != MemoryRecordStatus.ACTIVE.value:
                inactive_ignored.append(str(record.id))
                continue
            side = self._record_side(record)
            if self._scopes_disjoint(candidate_side, side):
                coexisting.append(record)
            else:
                contenders.append((record, side))

        base_metadata: dict[str, Any] = {"provenance": self._provenance(candidate_side)}
        if inactive_ignored:
            base_metadata["inactive_ignored_ids"] = inactive_ignored

        # 全部既有记录均非 active（撤销/已取代/过档）→ 等同无冲突。
        # （与上面 existing_records 为空的分支同型，但保留 inactive_ignored 审计。）
        if not contenders and not coexisting:
            return ResolutionDecision(
                action="accept",
                reason="no_conflict",
                evidence_tokens=(candidate.evidence_token,),
                conflict_key=candidate.semantic_key,
                metadata={
                    **base_metadata,
                    "conflict_category": ConflictCategory.NONE.value,
                },
            )

        # SCOPE_DIFFERENCE：范围不同，两者都真 → preserve both（§5）。
        if not contenders:
            return ResolutionDecision(
                action="accept",
                reason="scope_difference_preserve_both",
                winner_lane=candidate.source_lane,
                evidence_tokens=(
                    candidate.evidence_token,
                    *(record.evidence_token for record in coexisting if record.evidence_token),
                ),
                conflict_key=candidate.semantic_key,
                metadata={
                    **base_metadata,
                    "conflict_category": ConflictCategory.SCOPE_DIFFERENCE.value,
                    "coexisting_record_ids": [str(record.id) for record in coexisting],
                },
            )

        candidate_tuple = candidate_side.priority_tuple()
        candidate_registered = candidate_side.lane_tier > 0

        stronger_existing: EpisodicMemory | None = None
        stronger_side: _SideView | None = None
        tie_record: EpisodicMemory | None = None
        tie_side: _SideView | None = None
        loser_records: list[EpisodicMemory] = []
        per_record_categories: dict[str, str] = {}

        for record, side in contenders:
            record_tuple = side.priority_tuple()
            category = self._classify_pair(candidate_side, side, candidate_tuple, record_tuple)
            per_record_categories[str(record.id)] = category
            if record_tuple > candidate_tuple:
                if stronger_side is None or record_tuple > stronger_side.priority_tuple():
                    stronger_existing, stronger_side = record, side
            elif record_tuple == candidate_tuple:
                if tie_side is None or record_tuple > tie_side.priority_tuple():
                    tie_record, tie_side = record, side
            else:
                loser_records.append(record)

        abstain = (
            tie_record is not None
            and stronger_existing is None
            and not candidate_registered
            and tie_side is not None
            and tie_side.lane_tier == 0
            and not loser_records
        )

        if abstain:
            # UNSAFE_AMBIGUITY（双方均未登记 lane）：无法排名两种来源 →
            # abstain：不写、不问、留审计（§5）。
            return ResolutionDecision(
                action="reject",
                reason="abstain_unsafe_ambiguity",
                winner_lane=tie_side.lane if tie_side else None,
                evidence_tokens=(
                    self._collect_tokens(candidate, tie_record) if tie_record else (candidate.evidence_token,)
                ),
                conflict_key=candidate.semantic_key,
                metadata={
                    **base_metadata,
                    "conflict_category": ConflictCategory.UNSAFE_AMBIGUITY.value,
                    "candidate_registered": False,
                    "per_record_categories": per_record_categories,
                },
            )

        if stronger_existing is not None:
            return ResolutionDecision(
                action="reject",
                reason="higher_priority_existing",
                winner_record_id=stronger_existing.id,
                winner_lane=stronger_existing.source_lane,
                evidence_tokens=self._collect_tokens(candidate, stronger_existing),
                conflict_key=candidate.semantic_key,
                metadata={
                    **base_metadata,
                    "conflict_category": per_record_categories.get(
                        str(stronger_existing.id), ConflictCategory.NONE.value
                    ),
                    "candidate_lane": candidate.source_lane,
                    "candidate_summary": candidate.summary,
                    "per_record_categories": per_record_categories,
                    "provenance": self._provenance(candidate_side, deciding=stronger_side),
                },
            )

        if tie_record is not None:
            # 平级不确定 + 两条说法都活着 → 高信息增益：ask once（不静默选）。
            category = per_record_categories.get(str(tie_record.id), ConflictCategory.UNSAFE_AMBIGUITY.value)
            return ResolutionDecision(
                action="surface_to_user",
                reason="unresolved_conflict",
                winner_lane=tie_record.source_lane,
                evidence_tokens=self._collect_tokens(candidate, tie_record),
                conflict_key=candidate.semantic_key,
                metadata={
                    **base_metadata,
                    "conflict_category": category,
                    "candidate_summary": candidate.summary,
                    "existing_summary": tie_record.summary,
                    "existing_record_id": str(tie_record.id),
                    "per_record_categories": per_record_categories,
                    "coexisting_record_ids": [str(record.id) for record in coexisting],
                    "clarification": self._clarification_payload(candidate, tie_record, category),
                    "provenance": self._provenance(candidate_side, deciding=tie_side),
                },
            )

        primary_loser = loser_records[0] if loser_records else None
        category = (
            per_record_categories.get(str(primary_loser.id), ConflictCategory.NONE.value)
            if primary_loser is not None
            else ConflictCategory.NONE.value
        )
        return ResolutionDecision(
            action="accept",
            reason="candidate_overrides_lower_priority",
            winner_lane=candidate.source_lane,
            loser_record_ids=tuple(record.id for record in loser_records),
            loser_lanes=tuple(record.source_lane for record in loser_records),
            evidence_tokens=tuple(dict.fromkeys(self._collect_tokens(candidate, *loser_records))),
            conflict_key=candidate.semantic_key,
            metadata={
                **base_metadata,
                "conflict_category": category,
                "per_record_categories": per_record_categories,
                "coexisting_record_ids": [str(record.id) for record in coexisting],
                "provenance": self._provenance(
                    candidate_side,
                    deciding=self._record_side(primary_loser) if primary_loser is not None else None,
                ),
            },
        )

    # ------------------------------------------------------------------
    # Audit + application
    # ------------------------------------------------------------------

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
            if new_record is None:
                return decision
            records = await self._load_records(decision.loser_record_ids, user_id=candidate.user_id)

            # Memory V3 (M-01) 写守卫（变更点防御）：自动冲突裁决不得让
            # 推断 lane 的 winner retract/supersede 显式 lane 的记录。
            # resolve() 的 lane 算术不会产出这种决策；本守卫面向的是
            # apply_live_decision 的其他调用方（M-04 接线后更多）。
            # 用户仲裁（arbitrate_unresolved_conflict）是显式人类动作，
            # 不经过此处，保持最高权限。
            winner_rank = lane_priority(candidate.source_lane)
            now = _utcnow()
            effective_records: list[EpisodicMemory] = []
            skipped_loser_ids: list[str] = []
            guarded_loser_ids: list[str] = []
            for record in records:
                status = derive_status(record)
                if status != MemoryRecordStatus.ACTIVE.value:
                    # F2：生命周期过滤——已撤销/已被取代/已过档的行不再改写。
                    # 已 superseded 的行保留首链指针，不指向新 winner。
                    skipped_loser_ids.append(str(record.id))
                    continue
                if winner_rank < lane_priority(record.source_lane):
                    guarded_loser_ids.append(str(record.id))
                    continue
                record.retracted_at = now
                # Memory V3 (M-01)：败者指向胜者，构成与
                # memory_preferences.replaced_by_id 对称的 supersede 链。
                record.superseded_by_id = new_record.id
                record.updated_at = now
                effective_records.append(record)

            if guarded_loser_ids:
                logger.warning(
                    "Epistemic guard: inferred-tier winner %s may not supersede explicit-tier records %s",
                    candidate.source_lane,
                    guarded_loser_ids,
                )
                # F7：守卫跳过必须有计数指标（不再只有日志）。
                for loser_lane in dict.fromkeys(
                    record.source_lane for record in records if str(record.id) in set(guarded_loser_ids)
                ):
                    _metric_inc(
                        MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL,
                        winner_lane=candidate.source_lane,
                        loser_lane=loser_lane,
                    )

            decision = replace(
                decision,
                metadata={
                    **decision.metadata,
                    "skipped_loser_ids": skipped_loser_ids,
                    "epistemic_guard_skipped_loser_ids": guarded_loser_ids,
                },
            )

            # F2 幂等：同一决策重放（全部败者已由本 winner 取代）→ no-op，
            # 不重复审计/epoch/事件（M-07 同构：第二调用者见终态即返回）。
            already_applied = any(record.superseded_by_id == new_record.id for record in records)
            if already_applied and not effective_records:
                return decision

            # R2 F-4：结局指标在幂等早退之后计数——重放对指标也必须是 no-op
            # （"counted at application time"，仅有效应用计一次）。
            _metric_inc(
                MEMORY_CONFLICT_RESOLUTIONS_TOTAL,
                action="accept",
                category=str(decision.metadata.get("conflict_category") or "NONE"),
            )

            pipeline = MemoryInvalidationPipeline(self.db, self._redis)
            if effective_records:
                # F2/M-07 同构：有效 supersede 与 epoch bump + memory.invalidated
                # 同事务原子生效（payload content-free：ids/action/category）。
                await pipeline.apply_in_txn(
                    user_id=candidate.user_id,
                    action=MemoryMutationAction.SUPERSEDE,
                    kind="episodic",
                    memory_ids=[record.id for record in effective_records],
                    reason_code="conflict_auto_resolution",
                    payload_extra={
                        "conflict_category": str(decision.metadata.get("conflict_category") or "NONE"),
                        "winner_record_id": str(new_record.id),
                        "resolver_version": CONFLICT_RESOLVER_VERSION,
                    },
                )
            await self.record_resolution(
                user_id=candidate.user_id,
                decision=decision,
                winner_record_id=new_record.id,
            )
            await self.db.commit()
            if effective_records:
                await pipeline.invalidate_derived_caches(user_id=candidate.user_id, kinds={"episodic"})
            return decision

        if decision.action == "reject":
            _metric_inc(
                MEMORY_CONFLICT_RESOLUTIONS_TOTAL,
                action="reject",
                category=str(decision.metadata.get("conflict_category") or "NONE"),
            )
            await self.record_resolution(user_id=candidate.user_id, decision=decision)
            await self.db.commit()
            return decision

        _metric_inc(
            MEMORY_CONFLICT_RESOLUTIONS_TOTAL,
            action="surface_to_user",
            category=str(decision.metadata.get("conflict_category") or ConflictCategory.UNSAFE_AMBIGUITY.value),
        )
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

        left_payload = self._candidate_payload(candidate)
        clarification = decision.metadata.get("clarification")
        if clarification:
            # clarification 随 payload 落库：ask-once 消费方（未决冲突 API）
            # 可直接取结构化澄清问题，不依赖决策对象存活。
            left_payload["clarification"] = clarification

        unresolved = UnresolvedConflict(
            user_id=candidate.user_id,
            conflict_key=decision.conflict_key or candidate.semantic_key,
            left_record_id=None,
            right_record_id=existing_record.id if existing_record is not None else None,
            left_summary=candidate.summary,
            right_summary=(
                existing_record.summary
                if existing_record is not None
                else str(decision.metadata.get("existing_summary") or "")
            ),
            left_lane=candidate.source_lane,
            right_lane=existing_record.source_lane if existing_record is not None else str(decision.winner_lane or ""),
            left_evidence_token=candidate.evidence_token,
            right_evidence_token=existing_record.evidence_token if existing_record is not None else None,
            left_payload=left_payload,
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
            select(UnresolvedConflict)
            .where(
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
        """User arbitration (ask-once answer). Explicit human action — highest
        authority, not subject to the automated epistemic guard.

        M-04 (V3-FIX-10 F4): this is the 5th destructive entry of the memory
        epoch contract. An effective arbitration (≥1 loser active→superseded/
        retracted) bumps ``memory_epoch`` and writes ``memory.invalidated``
        (action ``user_arbitration``) in the same transaction; the loser gets
        ``superseded_by_id`` = winner (SUPERSEDED semantics, symmetric with
        the automated path — no longer a bare RETRACTED). Replays (conflict
        already resolved) are no-ops.

        R2 返修：
        - F-1 物化直达存储层（绕开 lane 机器写守卫）；**先物化后毁败者**；
          物化失败 → 冲突保持 pending_user 并响亮失败，绝不静默 resolved。
        - F-2 物化/stash 的内部提交会释放入口行锁——破坏性阶段前重取
          conflict 行 FOR UPDATE 并复查 status=="pending_user"，并发对手
          已处理 → 按已处理收敛（不双 bump/不双事件/不分叉审计）。
        - F-5 中断尝试物化并暂存的残留（materialized_record_id）由对侧
          选择/none 选择按败者清算，不再无人认领地双活。
        """
        result = await self.db.execute(
            select(UnresolvedConflict)
            .where(
                UnresolvedConflict.id == conflict_id,
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.deleted_at.is_(None),
            )
            .with_for_update()
        )
        conflict = result.scalar_one_or_none()
        if conflict is None:
            return None
        if conflict.status != "pending_user":
            # F4 幂等：重放已终态的仲裁 → no-op（不重复 epoch/事件/审计）。
            return conflict

        left_payload = conflict.left_payload if isinstance(conflict.left_payload, dict) else {}
        right_payload = conflict.right_payload if isinstance(conflict.right_payload, dict) else {}

        winner_record_id: UUID | None = None
        intended_loser_ids: list[UUID | None] = []

        # --- 物化阶段（可含内部提交；仅加性效果：新记录 + stash 锚点，零破坏） ---
        if selection == "left":
            # 败者优先取 right 行；行已不在（删）则取中断 right 尝试的暂存残留（F-5 对称）。
            intended_loser_ids = [conflict.right_record_id or self._stashed_materialized_id(right_payload)]
            winner_record_id = self._stashed_materialized_id(left_payload)
            if winner_record_id is None:
                winner_record_id = await self._materialize_side(left_payload, user_id=user_id)
                if winner_record_id is not None:
                    # 物化幂等锚点先行落库（缩小 crash 重复物化窗口）。
                    await self._stash_materialized_id(conflict, "left_payload", winner_record_id)
        elif selection == "right":
            winner_record_id = conflict.right_record_id or self._stashed_materialized_id(right_payload)
            if winner_record_id is None:
                winner_record_id = await self._materialize_side(right_payload, user_id=user_id)
                if winner_record_id is not None:
                    await self._stash_materialized_id(conflict, "right_payload", winner_record_id)
            # F-5：中断的 left 尝试可能已物化并暂存（冲突仍 pending）——按败者清算。
            intended_loser_ids = [conflict.left_record_id, self._stashed_materialized_id(left_payload)]
        else:  # "none"：两边都否 → 双侧撤下，无 supersede 指针；暂存残留一并清算。
            intended_loser_ids = [
                conflict.left_record_id,
                conflict.right_record_id,
                self._stashed_materialized_id(left_payload),
                self._stashed_materialized_id(right_payload),
            ]

        # --- F-2：终态（破坏性）阶段前重取锁复查 ---
        # 物化（create_episodic_memory 内部 commit）与 stash 的提交已把入口
        # FOR UPDATE 释放；并发重复仲裁在此之后即可见。重取行锁并复查
        # status——已非 pending_user 说明并发对手已完成，按已处理收敛。
        result = await self.db.execute(
            select(UnresolvedConflict)
            .where(
                UnresolvedConflict.id == conflict_id,
                UnresolvedConflict.user_id == user_id,
                UnresolvedConflict.deleted_at.is_(None),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        conflict = result.scalar_one_or_none()
        if conflict is None:
            return None
        if conflict.status != "pending_user":
            return conflict
        left_payload = conflict.left_payload if isinstance(conflict.left_payload, dict) else {}
        right_payload = conflict.right_payload if isinstance(conflict.right_payload, dict) else {}

        if selection in {"left", "right"} and winner_record_id is None:
            # F-1：物化失败 → 不 resolved、不毁败者、响亮失败（保持 pending_user 可重试）。
            raise ValueError(
                f"conflict arbitration materialization failed (selection={selection}); " "conflict remains pending_user"
            )

        # --- 破坏性阶段（本调用单事务收口：supersede + epoch + 事件 + 审计 + 终态） ---
        transitioned: list[EpisodicMemory] = []
        for loser_id in intended_loser_ids:
            if loser_id is None:
                continue
            transitioned.extend(await self._supersede_record_to(loser_id, winner_id=winner_record_id, user_id=user_id))

        effective_loser_ids = [record.id for record in transitioned]
        if not effective_loser_ids:
            # crash 恢复面：败者已被上一次中断的仲裁撤下（transition 已生效、
            # epoch/事件未落地）→ 本次重放补 bump。多余的一次 bump 只会
            # 保守地多失效一轮缓存，不会漏（F4 的"不漏"优先于"不多"）。
            effective_loser_ids = await self._half_done_loser_ids(intended_loser_ids, user_id=user_id)

        pipeline = MemoryInvalidationPipeline(self.db, self._redis)
        if effective_loser_ids:
            # F4：仲裁的破坏性效果与 epoch bump + memory.invalidated 同事务。
            await pipeline.apply_in_txn(
                user_id=user_id,
                action=MemoryMutationAction.USER_ARBITRATION,
                kind="episodic",
                memory_ids=effective_loser_ids,
                reason_code="user_arbitrated",
                payload_extra={
                    "selected_side": str(selection),
                    "unresolved_conflict_id": str(conflict.id),
                    "winner_record_id": str(winner_record_id) if winner_record_id else None,
                },
            )

        conflict.status = "resolved"
        conflict.selected_side = selection
        conflict.resolved_at = _utcnow()
        conflict.resolution_reason = "user_arbitrated"
        conflict.updated_at = _utcnow()

        decision = ResolutionDecision(
            action="accept" if selection in {"left", "right"} else "reject",
            reason="user_arbitrated",
            winner_record_id=winner_record_id,
            winner_lane=(
                conflict.left_lane if selection == "left" else conflict.right_lane if selection == "right" else None
            ),
            conflict_key=conflict.conflict_key,
            evidence_tokens=tuple(
                token for token in (conflict.left_evidence_token, conflict.right_evidence_token) if token
            ),
            metadata={
                "unresolved_conflict_id": str(conflict.id),
                "selected_side": selection,
                "conflict_category": str(
                    (left_payload.get("clarification") or {}).get("conflict_category")
                    or ConflictCategory.UNSAFE_AMBIGUITY.value
                ),
                "provenance": {
                    "resolver_version": CONFLICT_RESOLVER_VERSION,
                    "epistemic_contract_version": MEMORY_EPISTEMIC_CONTRACT_VERSION,
                    "arbitration": "user",
                },
            },
        )
        _metric_inc(
            MEMORY_CONFLICT_RESOLUTIONS_TOTAL,
            action=str(decision.action),
            category=str(decision.metadata["conflict_category"]),
        )
        await self.record_resolution(user_id=user_id, decision=decision, winner_record_id=winner_record_id)
        await self.db.commit()
        if effective_loser_ids:
            await pipeline.invalidate_derived_caches(user_id=user_id, kinds={"episodic"})
        await self.db.refresh(conflict)
        return conflict

    # ------------------------------------------------------------------
    # Pairwise classification helpers (M-04 core)
    # ------------------------------------------------------------------

    def _candidate_side(self, candidate: ConflictCandidate) -> _SideView:
        lane = str(candidate.source_lane or "").strip().lower()
        return _SideView(
            lane=lane,
            source_type=str(candidate.source_type or ""),
            epistemic_class=classify_episodic_class(
                lane,
                explicit_class=candidate.epistemic_class,
                source_type=candidate.source_type,
            ),
            lane_tier=lane_priority(lane),
            is_user_correction=lane in USER_CORRECTION_LANES,
            occurred_at=candidate.occurred_at,
            confidence=float(candidate.confidence or 0.0),
            decay_policy=candidate.decay_policy,
            due_at=candidate.due_at,
            entity_hash=candidate.mentioned_entity_hash,
        )

    def _record_side(self, record: EpisodicMemory) -> _SideView:
        lane = str(record.source_lane or "").strip().lower()
        return _SideView(
            lane=lane,
            source_type=str(record.source_type or ""),
            epistemic_class=classify_episodic_class(
                lane,
                explicit_class=getattr(record, "epistemic_class", None),
                source_type=record.source_type,
            ),
            lane_tier=lane_priority(lane),
            is_user_correction=lane in USER_CORRECTION_LANES,
            occurred_at=record.occurred_at or record.updated_at or datetime.min,
            confidence=float(record.confidence or 0.0),
            decay_policy=record.decay_policy,
            due_at=record.due_at,
            entity_hash=record.mentioned_entity_hash,
        )

    @staticmethod
    def _scopes_disjoint(candidate: _SideView, record: _SideView) -> bool:
        """Two claims about the same semantic key that live in DIFFERENT
        scopes are both true in their own windows (§3: today-only 约束不覆盖
        永久偏好). Deterministic signals only: time scope (M-03 vocabularies)
        and explicit entity anchors. Deliberately narrow — soft-decay standing
        claims are ``global`` and DO arbitrate."""
        if candidate.time_scope != record.time_scope:
            return True
        if (
            candidate.entity_hash is not None
            and record.entity_hash is not None
            and candidate.entity_hash != record.entity_hash
        ):
            return True
        return False

    def _classify_pair(
        self,
        candidate: _SideView,
        record: _SideView,
        candidate_tuple: tuple,
        record_tuple: tuple,
    ) -> str:
        if self._scopes_disjoint(candidate, record):  # pragma: no cover — resolve() pre-splits
            return ConflictCategory.SCOPE_DIFFERENCE.value
        cand_class = candidate.epistemic_class
        rec_class = record.epistemic_class
        if cand_class != rec_class:
            if cand_class == EpistemicClass.HYPOTHESIS.value or rec_class == EpistemicClass.HYPOTHESIS.value:
                return ConflictCategory.INFERENCE_CONTRADICTION.value
            # FACT(user) vs OBSERVATION/EXPERIENCE(system) —— 来源冲突。
            return ConflictCategory.SOURCE_DISAGREEMENT.value
        if candidate_tuple == record_tuple:
            return ConflictCategory.UNSAFE_AMBIGUITY.value
        return ConflictCategory.TEMPORAL_CHANGE.value

    def _clarification_payload(
        self,
        candidate: ConflictCandidate,
        record: EpisodicMemory,
        category: str,
    ) -> dict[str, Any]:
        return {
            "policy": "ask_once",
            "question": CLARIFICATION_QUESTION,
            "conflict_category": category,
            "options": [
                {
                    "side": "left",
                    "summary": candidate.summary,
                    "lane": candidate.source_lane,
                    "evidence_token": candidate.evidence_token,
                },
                {
                    "side": "right",
                    "summary": record.summary,
                    "lane": record.source_lane,
                    "evidence_token": record.evidence_token,
                },
            ],
        }

    def _provenance(self, candidate: _SideView, deciding: _SideView | None = None) -> dict[str, Any]:
        provenance: dict[str, Any] = {
            "resolver_version": CONFLICT_RESOLVER_VERSION,
            "epistemic_contract_version": MEMORY_EPISTEMIC_CONTRACT_VERSION,
            "candidate": candidate.provenance(),
        }
        if deciding is not None:
            provenance["deciding"] = deciding.provenance()
        return provenance

    # ------------------------------------------------------------------
    # Legacy comparison surface (kept for direct callers/tests)
    # ------------------------------------------------------------------

    def _compare_candidate_to_record(
        self,
        candidate: ConflictCandidate,
        record: EpisodicMemory,
    ) -> Literal["candidate_wins", "candidate_loses", "tie"]:
        candidate_tuple = self._candidate_side(candidate).priority_tuple()
        record_tuple = self._record_side(record).priority_tuple()
        if candidate_tuple != record_tuple:
            return "candidate_wins" if candidate_tuple > record_tuple else "candidate_loses"
        return "tie"

    def _priority(self, source_lane: str) -> int:
        lane = (source_lane or "").strip().lower()
        tier = self.KNOWN_SOURCE_LANES.get(lane)
        if tier is not None:
            return self.PRIORITY_BY_TIER[tier]
        if lane and lane not in self._warned_unknown_lanes:
            self._warned_unknown_lanes.add(lane)
            logger.warning(
                "ConflictResolver: unregistered source_lane '%s' falls to lowest priority tier; "
                "register it in KNOWN_SOURCE_LANES if it should arbitrate higher",
                lane,
            )
        return self.PRIORITY_BY_TIER["unknown"]

    def _pick_stronger_record(
        self,
        current: EpisodicMemory | None,
        candidate: EpisodicMemory,
    ) -> EpisodicMemory:
        if current is None:
            return candidate
        if self._record_side(candidate).priority_tuple() > self._record_side(current).priority_tuple():
            return candidate
        return current

    def _collect_tokens(self, candidate: ConflictCandidate, *records: EpisodicMemory) -> tuple[str, ...]:
        tokens = [candidate.evidence_token]
        tokens.extend(record.evidence_token for record in records if record.evidence_token)
        return tuple(dict.fromkeys(token for token in tokens if token))

    async def _load_records(self, record_ids: tuple[UUID, ...], *, user_id: UUID) -> list[EpisodicMemory]:
        """F2：写路径装载带行锁（PG FOR UPDATE；sqlite 静默忽略），生命周期
        过滤在调用方按 derive_status 逐行复核（锁内复查，关 TOCTOU 窗口）。"""
        if not record_ids:
            return []
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.id.in_(record_ids),
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return list(result.scalars().all())

    async def _supersede_record_to(
        self,
        record_id: UUID | None,
        *,
        winner_id: UUID | None,
        user_id: UUID,
    ) -> list[EpisodicMemory]:
        """Transition one arbitration loser active → superseded/retracted.

        Returns the transitioned ORM objects (empty = no-op: missing row,
        wrong user, or already terminal — the F2 idempotency guard). Only
        ACTIVE rows move; revoked/superseded/retracted rows keep their first
        chain pointer untouched.
        """
        if record_id is None:
            return []
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.id == record_id,
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return []
        if derive_status(record) != MemoryRecordStatus.ACTIVE.value:
            return []
        now = _utcnow()
        record.retracted_at = now
        if winner_id is not None:
            record.superseded_by_id = winner_id
        record.updated_at = now
        await self.db.flush()
        return [record]

    async def _half_done_loser_ids(
        self,
        record_ids: list[UUID | None],
        *,
        user_id: UUID,
    ) -> list[UUID]:
        """Crash-recovery companion of the epoch contract (F4): arbitration
        losers that are ALREADY terminal (superseded/retracted by an earlier
        interrupted attempt whose epoch bump never landed) while the conflict
        is still pending. Revoked rows are excluded — user hard-delete is not
        an arbitration effect."""
        half_done: list[UUID] = []
        for record_id in record_ids:
            if record_id is None:
                continue
            result = await self.db.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.id == record_id,
                    EpisodicMemory.user_id == user_id,
                    EpisodicMemory.deleted_at.is_(None),
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                continue
            status = derive_status(record)
            if status in {
                MemoryRecordStatus.SUPERSEDED.value,
                MemoryRecordStatus.RETRACTED.value,
            }:
                half_done.append(record.id)
        return half_done

    @staticmethod
    def _stashed_materialized_id(payload: dict[str, Any]) -> UUID | None:
        stashed = payload.get("materialized_record_id")
        if not stashed:
            return None
        try:
            return UUID(str(stashed))
        except (TypeError, ValueError):
            return None

    async def _stash_materialized_id(
        self,
        conflict: UnresolvedConflict,
        payload_key: str,
        record_id: UUID,
    ) -> None:
        payload = getattr(conflict, payload_key)
        payload = dict(payload) if isinstance(payload, dict) else {}
        payload["materialized_record_id"] = str(record_id)
        setattr(conflict, payload_key, payload)
        conflict.updated_at = _utcnow()
        await self.db.commit()  # 物化幂等锚点先行落库（缩小 crash 重复窗口）

    async def _materialize_side(self, payload: dict[str, Any], *, user_id: UUID) -> UUID | None:
        """Materialize one side of an arbitrated conflict as a stored record.

        R2 F-1：仲裁物化是用户显式动作的兑现，**直达存储层**（MemoryService）
        ——刻意绕开 inferred lane 的机器写守卫（_is_duplicate / 限流 / 用户禁用）
        与 lane 内的再仲裁：同 key 第三条 active 推断行（preserve-both 共存的
        常态产物）不得吞掉用户答案，机器守卫也不得重新裁决用户刚刚给出的
        显式选择（CONFLICT_RESOLVER.md §3「当前明确用户陈述/纠正」首位）。
        物化后的记录与任何记录一样参与后续常规仲裁。
        """
        record_id = payload.get("record_id")
        if record_id:
            return UUID(str(record_id))
        if not payload:
            return None
        source_lane = str(payload.get("source_lane") or "inferred_extraction")
        source_type = str(payload.get("source_type") or "chat")
        source_id = payload.get("source_id")
        occurred_at = datetime.fromisoformat(str(payload["occurred_at"]))
        confidence = float(payload.get("confidence") or 0.0)
        evidence_refs = list(payload.get("evidence_refs") or [])
        evidence_token = payload.get("evidence_token")
        semantic_key = payload.get("semantic_key")
        due_at = datetime.fromisoformat(str(payload["due_at"])) if payload.get("due_at") else None
        mentioned_entity_owner_user_id = (
            UUID(str(payload["mentioned_entity_owner_user_id"]))
            if payload.get("mentioned_entity_owner_user_id")
            else None
        )

        memory_service = MemoryService(self.db)
        record = await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=str(payload.get("summary") or ""),
            source_type=source_type,
            source_id=source_id,
            source_lane=source_lane,
            occurred_at=occurred_at,
            importance_score=confidence,
            confidence=confidence,
            tags=["stage20:user_arbitrated_conflict"],
            evidence_refs=evidence_refs,
            evidence_token=evidence_token,
            decay_policy=payload.get("decay_policy"),
            semantic_key=semantic_key,
            subject_type=str(payload.get("subject_type") or "self"),
            due_at=due_at,
            mentioned_entity_hash=payload.get("mentioned_entity_hash"),
            mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
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
            "decay_policy": candidate.decay_policy,
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
            "decay_policy": record.decay_policy,
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
