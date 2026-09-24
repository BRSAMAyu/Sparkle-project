"""Memory V3 unified mutation-effects pipeline (task M-07).

Single authority for the deterministic side effects of every destructive or
status-changing memory mutation (MEMORY_V3.md §6 "Correct / Delete"):

    correction (reject / no_longer_applicable)  ->  retraction
    revoke (user delete / kill switch)           ->  revocation
    supersede (preference version advance)       ->  supersession
    delete (memory panel retract of any kind)    ->  retraction/revocation

Every EFFECTIVE mutation (i.e. one that actually transitions a record out of
``active`` — idempotent repeats are no-ops) deterministically triggers, in ONE
database transaction together with the status change itself:

1. ``memory_epoch`` bump (atomic ``UPDATE ... RETURNING``, M-01 contract);
2. a ``memory.invalidated`` event in ``event_outbox`` (D-01 closed vocabulary,
   correlation carries ``memory_id``; payload is CONTENT-FREE by contract:
   ids / action / epoch only — SECURITY_PRIVACY audit-without-exposure);
3. derived-cache invalidation (Redis DEL of profile_context /
   inline_snapshot / prefs_center / aurora self-model) executed AFTER the
   caller's commit — ``apply_in_txn`` itself only computes the keys; each
   caller DELs via ``invalidate_derived_caches`` once its commit succeeded
   (``commit=True`` paths commit and DEL internally, in that order).

Why epoch+event live INSIDE the status-change transaction:
- no intermediate commit can break the caller's row locks (upsert_preference
  SELECT FOR UPDATE keeps its lock until the final commit);
- all-or-nothing: a status change can never exist without its epoch bump and
  invalidation event (the M-01 "best-effort" gap this card closes);
- crash between commit and the Redis DELs leaves only TTL-bounded staleness,
  and the consumer-side epoch gates (ProfileContextService) reject stale
  entries anyway — the DELs are acceleration, the gate is the guarantee.

Idempotency / concurrency contract (dual-device, retry, repeat):
- ALL FOUR memory-table entries (retract / revoke_episodic / correction-reject
  / bulk revoke_inferred) guard with SELECT ... FOR UPDATE + re-check of
  ``derive_status(record) != active`` so the SECOND caller (blocked on the
  row lock, or a plain retry) sees the terminal status and returns a no-op:
  exactly one epoch bump, one audit row, one event per effective mutation
  (M-07 R1-C2-2 brought the bulk entry under the same guard).

Working memory (session-scoped, Redis-resident) joins the same contract at the
API layer (``apply_working_memory_forget``): the Redis state is its own truth
(forget/reject mutate keys directly), so the pipeline adds epoch + event +
derived-cache invalidation around it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Iterable, cast
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_registry import EventSource, build_event_metadata
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_epistemic_contract import MEMORY_EPISTEMIC_CONTRACT_VERSION

MEMORY_INVALIDATION_PIPELINE_VERSION = "memory-v3.m07.v1"
MEMORY_INVALIDATION_EVENT = "memory.invalidated"
MEMORY_INVALIDATION_PAYLOAD_SCHEMA = "memory_invalidation.v1"

# Aggregate identity for the event domain: one user's memory namespace.
MEMORY_AGGREGATE_TYPE = "user_memory"


class MemoryMutationAction(StrEnum):
    """Unified action vocabulary of the four governance semantics."""

    CORRECTION = "correction"  # apply_correction(reject/no_longer_applicable)
    REVOKE = "revoke"  # revoke_episodic_memory (user "delete") / retract_memory
    SUPERSEDE = "supersede"  # preference version-chain advance
    BULK_REVOKE = "bulk_revoke"  # revoke_inferred_memories (per user)
    WORKING_MEMORY_FORGET = "working_memory_forget"  # session-scoped WM delete
    # M-04 (V3-FIX-10 F4): user arbitration of an unresolved conflict — the
    # 5th destructive entry of the epoch contract (sibling entry, same
    # pipeline; loser retraction/supersede is effective-destructive).
    USER_ARBITRATION = "user_arbitration"
    # M-08 (memory provenance/scope API): user-sovereignty IN-PLACE edit —
    # goal field updates and scope pause/resume (archived_at toggle). Sibling
    # entry, same pipeline: the record stays active (no version chain, unlike
    # SUPERSEDE; no rejection, unlike CORRECTION) but its content/recall
    # changes, so derived caches must drop. Event NAME stays memory.invalidated
    # (D-01 vocabulary untouched).
    USER_UPDATE = "user_update"


# Derived (compiled) cache keys invalidated on every effective mutation. These
# are the only cross-request derived artifacts that embed memory-derived
# content; the retrieval/context read paths re-query the source of truth.
PROFILE_CONTEXT_KEY_TEMPLATE = "user:profile_context:{user_id}"
INLINE_SNAPSHOT_KEY_TEMPLATE = "user:inline_snapshot:{user_id}"
PREFS_CENTER_KEY_TEMPLATE = "user:prefs:center:{user_id}"
# C-07：ContextOrchestrator 聚合快照（300s TTL，内嵌 profile_context 等
# 记忆派生文本）。读侧 epoch 门（context_manager 快照比对）是保证，此处
# DEL 是加速——与下方既有键同一双保险结构。
CONTEXT_SNAPSHOT_KEY_TEMPLATE = "user:context:snapshot:{user_id}"
# Aurora self-model: 90-day TTL Redis state hydrated from user context —
# without explicit DEL a deleted memory's assumptions survive for months.
AURORA_SELF_MODEL_KEY_TEMPLATE = "aurora:self_model:{user_id}"

# Cache keys cleared for every mutation kind vs preference-affecting only.
_ALWAYS_INVALIDATED_TEMPLATES = (
    PROFILE_CONTEXT_KEY_TEMPLATE,
    INLINE_SNAPSHOT_KEY_TEMPLATE,
    CONTEXT_SNAPSHOT_KEY_TEMPLATE,
    AURORA_SELF_MODEL_KEY_TEMPLATE,
)
_PREFERENCE_ONLY_TEMPLATES = (PREFS_CENTER_KEY_TEMPLATE,)


@dataclass(frozen=True)
class MemoryInvalidationResult:
    epoch: int
    # Keys the mutation must invalidate. With the default ``commit=False`` the
    # DEL has NOT run yet (the caller performs it post-commit via
    # ``invalidate_derived_caches``); with ``commit=True`` they were DELed.
    invalidated_cache_keys: tuple[str, ...]
    event_written: bool


def memory_epoch_version_string(epoch: int) -> str:
    """E-05-style version component for memory-derived cache keys.

    Consumers that cache memory-derived artifacts (M-03 retrieval prefilter,
    semantic-cache callers that become memory-sensitive) compose this into
    their cache key the same way ``knowledge_version`` is composed in
    ``SemanticCacheService._generate_cache_key`` — bumping the epoch then
    naturally orphans old entries instead of resurrecting them.
    """

    return f"mepoch:{int(epoch)}"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MemoryInvalidationPipeline:
    def __init__(self, db: AsyncSession, redis_client: Any | None = None):
        self.db = db
        self.redis = redis_client

    # ------------------------------------------------------------------
    # 1. In-transaction effects (call BEFORE the caller's commit)
    # ------------------------------------------------------------------

    async def apply_in_txn(
        self,
        *,
        user_id: UUID,
        action: MemoryMutationAction | str,
        kind: str,
        memory_ids: Iterable[UUID | str],
        reason_code: str | None = None,
        payload_extra: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> MemoryInvalidationResult:
        """Epoch bump + invalidation event, inside the caller's transaction.

        MUST be called after the status mutation is staged and BEFORE the
        caller commits, so status change, audit, epoch and event land
        atomically.

        Derived-cache DEL is NOT performed here (M-07 R1-C2-3): with the
        default ``commit=False`` the caller's transaction is still open, so a
        DEL now would fire before the commit it belongs to (harmless on
        rollback, but it widens the rebuild-vs-delete race window). The caller
        MUST instead call :meth:`invalidate_derived_caches` AFTER its own
        commit — the result's ``invalidated_cache_keys`` names exactly those
        keys. ``commit=True`` is a convenience for standalone use
        (working-memory path) where this method commits and then performs the
        DEL itself, in the correct order.
        """
        action_value = MemoryMutationAction(action).value
        normalized_ids = [str(UUID(str(mid))) for mid in memory_ids]

        epoch = await _bump_memory_epoch_in_txn(self.db, user_id, reason=f"{action_value}:{kind}")
        event_written = await self._write_invalidation_event_in_txn(
            user_id=user_id,
            action=action_value,
            kind=kind,
            memory_ids=normalized_ids,
            epoch=epoch,
            reason_code=reason_code or action_value,
            payload_extra=payload_extra,
        )
        keys = self.derived_cache_keys(user_id=user_id, kinds={kind})
        if commit:
            await self.db.commit()
            invalidated = await self.invalidate_derived_caches(user_id=user_id, kinds={kind})
            return MemoryInvalidationResult(
                epoch=epoch,
                invalidated_cache_keys=tuple(invalidated),
                event_written=event_written,
            )
        return MemoryInvalidationResult(
            epoch=epoch,
            invalidated_cache_keys=tuple(keys),
            event_written=event_written,
        )

    async def _write_invalidation_event_in_txn(
        self,
        *,
        user_id: UUID,
        action: str,
        kind: str,
        memory_ids: list[str],
        epoch: int,
        reason_code: str,
        payload_extra: dict[str, Any] | None = None,
    ) -> bool:
        """Write one content-free ``memory.invalidated`` row into event_outbox.

        Payload contract (frozen by test): ids / action / kind / epoch ONLY.
        No summary, no pref_value, no user-supplied reason text — the audit
        keeps the FACT of deletion without exposing deleted content
        (SECURITY_PRIVACY.md "logs redact" + task card acceptance 3).
        """
        if not await _outbox_tables_exist(self.db):
            logger.warning(
                "memory.invalidated skipped: event_outbox tables unavailable user_id={user_id}",
                user_id=user_id,
            )
            return False

        sequence_number = await _next_sequence(self.db, MEMORY_AGGREGATE_TYPE, user_id)
        payload: dict[str, Any] = {
            "schema_version": MEMORY_INVALIDATION_PAYLOAD_SCHEMA,
            "memory_type": kind,
            "action": action,
            "memory_ids": memory_ids,
            "memory_epoch": epoch,
            "reason_code": reason_code[:40],
        }
        if payload_extra:
            payload.update(payload_extra)
        metadata = build_event_metadata(
            user_id=user_id,
            source=EventSource.SERVER_SERVICE,
            service="memory_invalidation_pipeline",
            event_name=MEMORY_INVALIDATION_EVENT,
            aggregate_type=MEMORY_AGGREGATE_TYPE,
            aggregate_id=user_id,
            sequence_number=sequence_number,
            correlation=({"memory_id": memory_ids[0]} if len(memory_ids) == 1 else None),
            extra={
                "memory_epoch": epoch,
                "pipeline_version": MEMORY_INVALIDATION_PIPELINE_VERSION,
                "epistemic_contract_version": MEMORY_EPISTEMIC_CONTRACT_VERSION,
            },
        )
        await self.db.execute(
            text("""
                INSERT INTO event_outbox
                (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
                """),
            {
                "aggregate_type": MEMORY_AGGREGATE_TYPE,
                "aggregate_id": str(user_id),
                "event_type": MEMORY_INVALIDATION_EVENT,
                "sequence_number": sequence_number,
                "payload": json.dumps(payload, ensure_ascii=False),
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )
        return True

    # ------------------------------------------------------------------
    # 2. Post-commit derived-cache invalidation
    # ------------------------------------------------------------------

    @staticmethod
    def derived_cache_keys(*, user_id: UUID, kinds: set[str]) -> list[str]:
        """Keys a mutation of ``kinds`` must invalidate (pure computation)."""
        keys: list[str] = [template.format(user_id=user_id) for template in _ALWAYS_INVALIDATED_TEMPLATES]
        if "preference" in kinds:
            keys.extend(template.format(user_id=user_id) for template in _PREFERENCE_ONLY_TEMPLATES)
        return keys

    async def invalidate_derived_caches(self, *, user_id: UUID, kinds: set[str]) -> list[str]:
        """DEL the derived caches (async redis). Idempotent; failures are
        logged and left to the consumer-side epoch gates + TTLs (the DEL is
        acceleration, the gate is the guarantee).

        M-07 R1-C2-3: call AFTER the caller's commit — ``apply_in_txn`` no
        longer performs this DEL itself for ``commit=False`` paths."""
        keys = self.derived_cache_keys(user_id=user_id, kinds=kinds)

        redis = self._resolve_redis()
        if redis is None:
            return keys
        try:
            result = await redis.delete(*keys)
            logger.info(
                "memory invalidation cleared derived caches user_id={user_id} keys={keys} deleted={result}",
                user_id=user_id,
                keys=keys,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 — cache DEL must never break the mutation path
            logger.error(
                "memory invalidation cache DEL failed (epoch gates remain authoritative) "
                "user_id={user_id} keys={keys} error={exc}",
                user_id=user_id,
                keys=keys,
                exc=exc,
            )
        return keys

    def _resolve_redis(self):
        if self.redis is not None:
            return self.redis
        try:
            from app.core.cache import cache_service

            return cache_service.redis
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # 3. Working-memory forget (API layer path)
    # ------------------------------------------------------------------

    async def apply_working_memory_forget(
        self,
        *,
        user_id: UUID,
        session_id: str,
        entry_id: str,
    ) -> MemoryInvalidationResult:
        """WM forget/reject effects: the Redis entry deletion already happened
        at the caller (it IS the truth); this adds the epoch/event/cache-clear
        half of the unified contract. ``entry_id`` is not a UUID — it rides in
        the payload only, correlation stays UUID-clean."""
        return await self.apply_in_txn(
            user_id=user_id,
            action=MemoryMutationAction.WORKING_MEMORY_FORGET,
            kind="working_memory",
            memory_ids=(),
            reason_code="working_memory_forget",
            payload_extra={"working_memory_entry_id": str(entry_id)[:64], "session_id": str(session_id)[:64]},
            commit=True,
        )


# ---------------------------------------------------------------------------
# In-transaction epoch bump (the M-01 atomic increment without its own commit)
# ---------------------------------------------------------------------------


async def _bump_memory_epoch_in_txn(db: AsyncSession, user_id: UUID, *, reason: str | None) -> int:
    """Atomic epoch bump that joins the CALLER's transaction (no commit here).

    Mirrors ``MemoryService.bump_memory_epoch`` semantics (M-01 R2-F3: single
    UPDATE..RETURNING, lazy-create on missing row) but flushes instead of
    committing, so the bump is atomic with the status change it serves.
    Lazy-create IntegrityError (concurrent first-bump) propagates — the whole
    mutation aborts and the client retry converges through the idempotency
    guard.
    """
    from sqlalchemy import update

    from app.models.memory import MemoryCorrection

    now = _utcnow()
    trimmed_reason = (reason or "memory_epoch_bump")[:200]

    result = await db.execute(
        update(UserMemorySettings)
        .where(
            UserMemorySettings.user_id == user_id,
            UserMemorySettings.deleted_at.is_(None),
        )
        .values(
            memory_epoch=UserMemorySettings.memory_epoch + 1,
            memory_epoch_bumped_at=now,
            memory_epoch_reason=trimmed_reason,
            updated_at=now,
        )
        .returning(UserMemorySettings.id, UserMemorySettings.memory_epoch)
    )
    row = result.one_or_none()
    if row is not None:
        db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="memory_epoch",
                memory_id=row.id,
                action="epoch_bump",
                reason=trimmed_reason,
            )
        )
        await db.flush()
        return int(row.memory_epoch)

    # 懒建首行（首个 bump：1 -> 2），撞 unique(user_id) 时事务中止由上层重试收敛。
    settings_row = UserMemorySettings(
        user_id=user_id,
        memory_epoch=2,
        memory_epoch_bumped_at=now,
        memory_epoch_reason=trimmed_reason,
    )
    db.add(settings_row)
    await db.flush()
    db.add(
        MemoryCorrection(
            user_id=user_id,
            memory_type="memory_epoch",
            memory_id=settings_row.id,
            action="epoch_bump",
            reason=trimmed_reason,
        )
    )
    await db.flush()
    return int(settings_row.memory_epoch)


# ---------------------------------------------------------------------------
# Outbox helpers (galaxy_service writer pattern, standalone)
# ---------------------------------------------------------------------------


async def _outbox_tables_exist(db: AsyncSession) -> bool:
    # No cross-call caching: the answer is engine-bound and mutations are rare
    # user actions — a per-call inspector check (galaxy_service pattern) is
    # cheap and never lies across engines/tests.
    connection = await db.connection()
    return await connection.run_sync(lambda sync_conn: _has_table(sync_conn, "event_outbox"))


def _has_table(sync_conn, name: str) -> bool:
    from sqlalchemy import inspect

    try:
        return cast("bool", (inspect(sync_conn).has_table(name)))
    except Exception:  # noqa: BLE001
        return False


async def _next_sequence(db: AsyncSession, aggregate_type: str, aggregate_id: UUID) -> int:
    """Monotonic per-aggregate sequence (galaxy outbox pattern).

    Atomic on PostgreSQL (INSERT .. ON CONFLICT .. DO UPDATE .. RETURNING);
    falls back to read-modify-write on dialects without upsert-returning.
    """
    try:
        result = await db.execute(
            text("""
                INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                VALUES (:aggregate_type, :aggregate_id, 1)
                ON CONFLICT (aggregate_type, aggregate_id)
                DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                RETURNING next_sequence
                """),
            {"aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)},
        )
        return int(result.scalar_one())
    except Exception as exc:  # noqa: BLE001 — dialect without upsert/returning
        logger.debug("sequence upsert fallback ({})", exc)
        current_result = await db.execute(
            text(
                "SELECT next_sequence FROM event_sequence_counters " "WHERE aggregate_type = :t AND aggregate_id = :a"
            ),
            {"t": aggregate_type, "a": str(aggregate_id)},
        )
        current = current_result.scalar_one_or_none()
        if current is None:
            await db.execute(
                text(
                    "INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence) "
                    "VALUES (:t, :a, 1)"
                ),
                {"t": aggregate_type, "a": str(aggregate_id)},
            )
            return 1
        nxt = int(current) + 1
        await db.execute(
            text(
                "UPDATE event_sequence_counters SET next_sequence = :n "
                "WHERE aggregate_type = :t AND aggregate_id = :a"
            ),
            {"n": nxt, "t": aggregate_type, "a": str(aggregate_id)},
        )
        return nxt
