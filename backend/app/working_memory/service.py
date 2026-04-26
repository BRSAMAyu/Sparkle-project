from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.i18n import I18n
from app.working_memory.schema import WorkingMemoryEntry, WorkingMemorySnapshotItem


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WorkingMemoryService:
    ENTRY_PREFIX = "working_memory"
    SESSION_META_PREFIX = "working_memory:meta"
    MAX_ENTRIES_PER_SESSION = 40
    IDLE_EXPIRY_SECONDS = 60 * 60 * 4
    SESSION_END_GRACE_SECONDS = 60 * 10
    _local_store: dict[str, tuple[str, datetime | None]] = {}

    def __init__(self, redis_client=None, *, now_fn=_utcnow):
        self.redis = redis_client
        self._now_fn = now_fn

    async def upsert_entry(
        self,
        *,
        user_id: str,
        session_id: str,
        text: str,
        semantic_key: str,
        salience_score: float,
        subject_type: str,
        confidence: float,
        evidence_token: str,
        occurred_at: datetime,
        source_turn_id: str,
        due_at: datetime | None = None,
        source_lane: str = "working_memory",
    ) -> WorkingMemoryEntry:
        now = self._now_fn()
        await self._touch_session(user_id=user_id, session_id=session_id, now=now)
        entries = await self.list_entries(user_id=user_id, session_id=session_id, limit=None)
        matched = next((entry for entry in entries if entry.semantic_key == semantic_key), None)

        if matched is None:
            entry = WorkingMemoryEntry(
                entry_id=str(uuid4()),
                user_id=user_id,
                session_id=session_id,
                text=text,
                semantic_key=semantic_key,
                salience_score=round(max(min(salience_score, 1.0), 0.0), 3),
                mention_count=1,
                first_seen_at=now,
                last_seen_at=now,
                source_turn_ids=(source_turn_id,),
                subject_type=subject_type,
                confidence=confidence,
                evidence_token=evidence_token,
                occurred_at=occurred_at,
                due_at=due_at,
                source_lane=source_lane,
            )
        else:
            source_turn_ids = matched.source_turn_ids
            if source_turn_id not in source_turn_ids:
                source_turn_ids = (*source_turn_ids, source_turn_id)
            entry = replace(
                matched,
                text=text or matched.text,
                salience_score=round(min(1.0, max(matched.salience_score, salience_score) + 0.08), 3),
                mention_count=matched.mention_count + 1,
                last_seen_at=now,
                source_turn_ids=source_turn_ids,
                confidence=max(matched.confidence, confidence),
                occurred_at=occurred_at,
                due_at=due_at or matched.due_at,
                rejected=False,
            )

        await self._save_entry(entry, ttl_seconds=self.IDLE_EXPIRY_SECONDS)
        await self._evict_if_needed(user_id=user_id, session_id=session_id)
        return entry

    async def list_entries(
        self,
        *,
        user_id: str,
        session_id: str,
        limit: int | None = 10,
        include_rejected: bool = False,
    ) -> list[WorkingMemoryEntry]:
        entries = []
        pattern = self._entry_pattern(user_id=user_id, session_id=session_id)
        if self.redis is not None:
            async for key in self.redis.scan_iter(pattern):
                payload = await self.redis.get(key)
                if payload:
                    entry = self._deserialize_entry(payload)
                    if include_rejected or not entry.rejected:
                        entries.append(entry)
        else:
            now = self._now_fn()
            for key, (payload, expires_at) in list(self._local_store.items()):
                if not self._matches_pattern(key, pattern):
                    continue
                if expires_at is not None and expires_at <= now:
                    self._local_store.pop(key, None)
                    continue
                entry = self._deserialize_entry(payload)
                if include_rejected or not entry.rejected:
                    entries.append(entry)
        entries.sort(key=lambda item: (item.salience_score, item.last_seen_at), reverse=True)
        if limit is None:
            return entries
        return entries[:limit]

    async def get_entry(
        self,
        *,
        user_id: str,
        session_id: str,
        entry_id: str,
    ) -> WorkingMemoryEntry | None:
        payload = await self._get_raw(self._entry_key(user_id=user_id, session_id=session_id, entry_id=entry_id))
        if payload is None:
            return None
        return self._deserialize_entry(payload)

    async def forget_entry(self, *, user_id: str, session_id: str, entry_id: str) -> bool:
        key = self._entry_key(user_id=user_id, session_id=session_id, entry_id=entry_id)
        if self.redis is not None:
            return bool(await self.redis.delete(key))
        return self._local_store.pop(key, None) is not None

    async def mark_correct(
        self,
        *,
        user_id: str,
        session_id: str,
        entry_id: str,
    ) -> WorkingMemoryEntry | None:
        entry = await self.get_entry(user_id=user_id, session_id=session_id, entry_id=entry_id)
        if entry is None:
            return None
        updated = replace(entry, confirmation_status="confirmed")
        await self._save_entry(updated, ttl_seconds=self.IDLE_EXPIRY_SECONDS)
        return updated

    async def mark_rejected(
        self,
        *,
        user_id: str,
        session_id: str,
        entry_id: str,
    ) -> WorkingMemoryEntry | None:
        entry = await self.get_entry(user_id=user_id, session_id=session_id, entry_id=entry_id)
        if entry is None:
            return None
        updated = replace(entry, rejected=True, confirmation_status="rejected")
        await self._save_entry(updated, ttl_seconds=self.IDLE_EXPIRY_SECONDS)
        return updated

    async def mark_consolidated(
        self,
        *,
        user_id: str,
        session_id: str,
        entry_id: str,
        l1_memory_id: str,
    ) -> WorkingMemoryEntry | None:
        entry = await self.get_entry(user_id=user_id, session_id=session_id, entry_id=entry_id)
        if entry is None:
            return None
        updated = replace(entry, consolidated_to_l1_id=l1_memory_id)
        await self._save_entry(updated, ttl_seconds=self.IDLE_EXPIRY_SECONDS)
        return updated

    async def build_snapshot(
        self,
        *,
        user_id: str,
        session_id: str,
        limit: int = 5,
    ) -> tuple[WorkingMemorySnapshotItem, ...]:
        entries = await self.list_entries(user_id=user_id, session_id=session_id, limit=limit)
        return tuple(
            WorkingMemorySnapshotItem(
                summary=self._snapshot_summary(entry),
                subject_type=entry.subject_type,
                salience_score=entry.salience_score,
                mention_count=entry.mention_count,
                last_seen_at=entry.last_seen_at,
                consolidated=entry.consolidated_to_l1_id is not None,
            )
            for entry in entries
        )

    async def close_session(self, *, user_id: str, session_id: str) -> None:
        entries = await self.list_entries(user_id=user_id, session_id=session_id, limit=None, include_rejected=True)
        for entry in entries:
            await self._save_entry(entry, ttl_seconds=self.SESSION_END_GRACE_SECONDS)
        now = self._now_fn()
        meta_key = self._session_meta_key(user_id=user_id, session_id=session_id)
        payload = json.dumps(
            {
                "user_id": user_id,
                "session_id": session_id,
                "last_active_at": now.isoformat(),
                "session_ended_at": now.isoformat(),
            },
            ensure_ascii=True,
        )
        await self._set_raw(meta_key, payload, ttl_seconds=self.SESSION_END_GRACE_SECONDS)

    async def cleanup_orphaned_namespaces(self, *, active_session_ids: set[str]) -> int:
        deleted = 0
        meta_pattern = f"{self.SESSION_META_PREFIX}:*"
        if self.redis is not None:
            async for key in self.redis.scan_iter(meta_pattern):
                raw = await self.redis.get(key)
                if not raw:
                    continue
                payload = json.loads(raw)
                session_id = str(payload.get("session_id") or "")
                if session_id and session_id not in active_session_ids:
                    user_id = str(payload.get("user_id") or "")
                    deleted += await self._delete_session(user_id=user_id, session_id=session_id)
        else:
            for key, (raw, expires_at) in list(self._local_store.items()):
                if not self._matches_pattern(key, meta_pattern):
                    continue
                if expires_at is not None and expires_at <= self._now_fn():
                    self._local_store.pop(key, None)
                    continue
                payload = json.loads(raw)
                session_id = str(payload.get("session_id") or "")
                if session_id and session_id not in active_session_ids:
                    user_id = str(payload.get("user_id") or "")
                    deleted += await self._delete_session(user_id=user_id, session_id=session_id)
        return deleted

    async def _delete_session(self, *, user_id: str, session_id: str) -> int:
        deleted = 0
        pattern = self._entry_pattern(user_id=user_id, session_id=session_id)
        if self.redis is not None:
            async for key in self.redis.scan_iter(pattern):
                deleted += int(await self.redis.delete(key))
            deleted += int(await self.redis.delete(self._session_meta_key(user_id=user_id, session_id=session_id)))
            return deleted
        for key in list(self._local_store.keys()):
            if self._matches_pattern(key, pattern) or key == self._session_meta_key(user_id=user_id, session_id=session_id):
                self._local_store.pop(key, None)
                deleted += 1
        return deleted

    async def _evict_if_needed(self, *, user_id: str, session_id: str) -> None:
        entries = await self.list_entries(user_id=user_id, session_id=session_id, limit=None, include_rejected=True)
        if len(entries) <= self.MAX_ENTRIES_PER_SESSION:
            return
        doomed = sorted(entries, key=lambda item: (item.salience_score, item.last_seen_at))[
            : len(entries) - self.MAX_ENTRIES_PER_SESSION
        ]
        for entry in doomed:
            await self.forget_entry(user_id=user_id, session_id=session_id, entry_id=entry.entry_id)

    async def _touch_session(self, *, user_id: str, session_id: str, now: datetime) -> None:
        payload = json.dumps(
            {
                "user_id": user_id,
                "session_id": session_id,
                "last_active_at": now.isoformat(),
                "session_ended_at": None,
            },
            ensure_ascii=True,
        )
        await self._set_raw(self._session_meta_key(user_id=user_id, session_id=session_id), payload, ttl_seconds=self.IDLE_EXPIRY_SECONDS)

    async def _save_entry(self, entry: WorkingMemoryEntry, *, ttl_seconds: int) -> None:
        await self._set_raw(self._entry_key(user_id=entry.user_id, session_id=entry.session_id, entry_id=entry.entry_id), self._serialize_entry(entry), ttl_seconds=ttl_seconds)

    async def _set_raw(self, key: str, payload: str, *, ttl_seconds: int) -> None:
        if self.redis is not None:
            await self.redis.set(key, payload, ex=ttl_seconds)
            return
        self._local_store[key] = (payload, self._now_fn() + timedelta(seconds=ttl_seconds))

    async def _get_raw(self, key: str) -> str | None:
        if self.redis is not None:
            return await self.redis.get(key)
        cached = self._local_store.get(key)
        if cached is None:
            return None
        payload, expires_at = cached
        if expires_at is not None and expires_at <= self._now_fn():
            self._local_store.pop(key, None)
            return None
        return payload

    @classmethod
    def _entry_key(cls, *, user_id: str, session_id: str, entry_id: str) -> str:
        return f"{cls.ENTRY_PREFIX}:{user_id}:{session_id}:{entry_id}"

    @classmethod
    def _entry_pattern(cls, *, user_id: str, session_id: str) -> str:
        return f"{cls.ENTRY_PREFIX}:{user_id}:{session_id}:*"

    @classmethod
    def _session_meta_key(cls, *, user_id: str, session_id: str) -> str:
        return f"{cls.SESSION_META_PREFIX}:{user_id}:{session_id}"

    @staticmethod
    def _matches_pattern(key: str, pattern: str) -> bool:
        if not pattern.endswith("*"):
            return key == pattern
        return key.startswith(pattern[:-1])

    @staticmethod
    def _snapshot_summary(entry: WorkingMemoryEntry) -> str:
        if entry.subject_type == "commitment":
            return I18n.t("working_memory.commitment_summary", locale="zh")
        if entry.subject_type in {"person_mention", "relationship"}:
            return I18n.t("working_memory.relationship_summary", locale="zh")
        return entry.text[:48]

    @staticmethod
    def _serialize_entry(entry: WorkingMemoryEntry) -> str:
        payload: dict[str, Any] = {
            "entry_id": entry.entry_id,
            "user_id": entry.user_id,
            "session_id": entry.session_id,
            "text": entry.text,
            "semantic_key": entry.semantic_key,
            "salience_score": entry.salience_score,
            "mention_count": entry.mention_count,
            "first_seen_at": entry.first_seen_at.isoformat(),
            "last_seen_at": entry.last_seen_at.isoformat(),
            "source_turn_ids": list(entry.source_turn_ids),
            "subject_type": entry.subject_type,
            "confidence": entry.confidence,
            "evidence_token": entry.evidence_token,
            "occurred_at": entry.occurred_at.isoformat(),
            "due_at": entry.due_at.isoformat() if entry.due_at else None,
            "source_lane": entry.source_lane,
            "confirmation_status": entry.confirmation_status,
            "consolidated_to_l1_id": entry.consolidated_to_l1_id,
            "rejected": entry.rejected,
        }
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _deserialize_entry(payload: str) -> WorkingMemoryEntry:
        raw = json.loads(payload)
        return WorkingMemoryEntry(
            entry_id=str(raw["entry_id"]),
            user_id=str(raw["user_id"]),
            session_id=str(raw["session_id"]),
            text=str(raw["text"]),
            semantic_key=str(raw["semantic_key"]),
            salience_score=float(raw["salience_score"]),
            mention_count=int(raw["mention_count"]),
            first_seen_at=datetime.fromisoformat(raw["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(raw["last_seen_at"]),
            source_turn_ids=tuple(raw.get("source_turn_ids") or ()),
            subject_type=str(raw["subject_type"]),
            confidence=float(raw["confidence"]),
            evidence_token=str(raw["evidence_token"]),
            occurred_at=datetime.fromisoformat(raw["occurred_at"]),
            due_at=datetime.fromisoformat(raw["due_at"]) if raw.get("due_at") else None,
            source_lane=str(raw.get("source_lane") or "working_memory"),
            confirmation_status=str(raw.get("confirmation_status") or "none"),
            consolidated_to_l1_id=raw.get("consolidated_to_l1_id"),
            rejected=bool(raw.get("rejected", False)),
        )
