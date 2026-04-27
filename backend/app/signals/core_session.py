"""
Core: execution
Phase: model→plan→execute→reflect
Stage: Signal-to-Action Spine P1-3 CoreSessionLifecycle

Core Session lifecycle — tracks a complete goal→plan→execute→reflect loop.
Sessions are short-lived control state, not long-term personality state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import _uid

_SESSION_KEY = "spine:session:{session_id}"
_ACTIVE_SESSION_KEY = "spine:session_active:{user_id}"
_SESSION_TTL_SECONDS = 7 * 24 * 3600
_VALID_PHASES = {"modeling", "planning", "executing", "reflecting", "completed"}


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class CoreSession:
    session_id: str
    user_id: str
    goal_id: str | None
    phase: str
    started_at: str
    updated_at: str
    pause_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0
    last_directive_id: str | None = None
    context_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "goal_id": self.goal_id,
            "phase": self.phase,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "pause_count": self.pause_count,
            "task_count": self.task_count,
            "completed_task_count": self.completed_task_count,
            "last_directive_id": self.last_directive_id,
            "context_snapshot": self.context_snapshot,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CoreSession:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CoreSessionManager:
    """Create and update short-lived core session state in Redis."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def create_session(self, user_id: str, goal_id: str | None = None) -> CoreSession:
        now = _utcnow()
        session = CoreSession(
            session_id=_uid("sess"),
            user_id=user_id,
            goal_id=goal_id,
            phase="modeling",
            started_at=now,
            updated_at=now,
        )
        await self._save_session(session, set_active=True)
        logger.info("CoreSession created: session={} user={}", session.session_id, user_id)
        return session

    async def get_session(self, session_id: str) -> CoreSession | None:
        raw = await self.redis.get(_SESSION_KEY.format(session_id=session_id))
        if not raw:
            return None
        return CoreSession.from_dict(json.loads(raw))

    async def get_active_session(self, user_id: str) -> CoreSession | None:
        session_id = await self.redis.get(_ACTIVE_SESSION_KEY.format(user_id=user_id))
        if not session_id:
            return None
        return await self.get_session(session_id)

    async def advance_phase(self, session_id: str, to_phase: str) -> CoreSession:
        if to_phase not in _VALID_PHASES:
            raise ValueError(f"invalid core session phase: {to_phase}")
        session = await self._require_session(session_id)
        session.phase = to_phase
        session.updated_at = _utcnow()
        if to_phase == "completed":
            await self._save_session(session, set_active=False)
            await self.redis.delete(_ACTIVE_SESSION_KEY.format(user_id=session.user_id))
            return session
        await self._save_session(session, set_active=True)
        return session

    async def pause_session(self, session_id: str) -> CoreSession:
        session = await self._require_session(session_id)
        session.pause_count += 1
        session.context_snapshot["paused"] = True
        session.updated_at = _utcnow()
        await self._save_session(session, set_active=True)
        return session

    async def resume_session(self, session_id: str) -> CoreSession:
        session = await self._require_session(session_id)
        session.context_snapshot["paused"] = False
        session.updated_at = _utcnow()
        await self._save_session(session, set_active=True)
        return session

    async def complete_session(self, session_id: str) -> CoreSession:
        return await self.advance_phase(session_id, "completed")

    async def record_task(self, session_id: str, completed: bool = False) -> CoreSession:
        session = await self._require_session(session_id)
        session.task_count += 1
        if completed:
            session.completed_task_count += 1
        session.updated_at = _utcnow()
        await self._save_session(session, set_active=session.phase != "completed")
        return session

    async def link_directive(self, session_id: str, directive_id: str) -> CoreSession:
        session = await self._require_session(session_id)
        session.last_directive_id = directive_id
        session.updated_at = _utcnow()
        await self._save_session(session, set_active=session.phase != "completed")
        return session

    async def _require_session(self, session_id: str) -> CoreSession:
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"core session not found: {session_id}")
        return session

    async def _save_session(self, session: CoreSession, *, set_active: bool) -> None:
        await self.redis.set(
            _SESSION_KEY.format(session_id=session.session_id),
            json.dumps(session.to_dict()),
            ex=_SESSION_TTL_SECONDS,
        )
        if set_active:
            await self.redis.set(
                _ACTIVE_SESSION_KEY.format(user_id=session.user_id),
                session.session_id,
                ex=_SESSION_TTL_SECONDS,
            )
