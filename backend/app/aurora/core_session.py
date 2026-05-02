"""AuroraCoreSession — multi-message interactive modeling session (L3).

This is the "complete-state Aurora" — high-cost, time-limited, used for
explicit user modeling. It is NOT a continuous chat mode.

Session lifecycle:
    declare → observe → judge → ask → process_response → update → exit

Rules:
- Session is limited to 6 user turns and 12 Aurora messages.
- Session must produce a calibration_result before closing.
- Sessions expire after IDLE_TTL_SECONDS without activity.
- L3 energy state is updated on session start and close.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from loguru import logger
from sqlalchemy import select

from app.core.event_bus import event_bus
from app.core.metrics import AURORA_CORE_SESSION_EVENT_TOTAL
from app.signals.aurora_core_session import AuroraCoreSessionEntryReason

SessionStage = Literal[
    "declare",
    "observe",
    "judge",
    "ask",
    "await_user",
    "process_response",
    "update",
    "exit",
]

SessionStatus = Literal["active", "paused", "completed", "abandoned", "expired"]

SESSION_KEY_PREFIX = "aurora:core_session:"
RESUME_TOKEN_KEY_PREFIX = f"{SESSION_KEY_PREFIX}resume:"
SESSION_TTL_SECONDS = 30 * 60  # 30 min max lifetime
IDLE_TTL_SECONDS = 10 * 60  # 10 min idle kills session
IDLE_PAUSE_SECONDS = 10 * 60
MAX_USER_TURNS = 6
MAX_AURORA_MESSAGES = 12


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _new_resume_token() -> str:
    return f"acs_{uuid.uuid4().hex}"


def _hash_resume_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


@dataclass
class AuroraCoreMessage:
    """A single message in the Aurora Core session."""

    role: Literal["aurora", "user"]
    content: str
    stage: SessionStage
    timestamp: str = field(default_factory=lambda: _utcnow().isoformat())
    option_id: str | None = None  # chip selected (if role=user)
    semantic_value: str | None = None  # semantic value of selection
    is_freeform: bool = False  # user typed free text

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "stage": self.stage,
            "timestamp": self.timestamp,
            "option_id": self.option_id,
            "semantic_value": self.semantic_value,
            "is_freeform": self.is_freeform,
        }


@dataclass
class CalibrationResult:
    """Outcomes of an Aurora Core session — written back to user model."""

    updates_applied: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    user_visible_summary: str = ""
    scope_completed: str = ""
    strategy_changes: list[str] = field(default_factory=list)
    state_patches: list[dict[str, Any]] = field(default_factory=list)
    next_changes: list[str] = field(default_factory=list)
    session_id: str = ""
    completed_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "updates_applied": self.updates_applied,
            "summary": self.summary,
            "user_visible_summary": self.user_visible_summary,
            "scope_completed": self.scope_completed,
            "strategy_changes": self.strategy_changes,
            "state_patches": self.state_patches,
            "next_changes": self.next_changes,
            "session_id": self.session_id,
            "completed_at": self.completed_at,
        }


@dataclass
class AuroraCoreSession:
    """State of one L3 interactive modeling session."""

    session_id: str
    user_id: str
    conversation_id: str | None
    surface: str
    status: SessionStatus
    stage: SessionStage
    scope: str  # declared calibration scope (1 sentence)
    session_type: str  # strategy_recalibration | quick_calibration | user_initiated
    entry_reason: dict[str, Any] = field(default_factory=dict)
    case_file: dict[str, Any] = field(default_factory=dict)
    resume_token: str = ""
    messages: list[AuroraCoreMessage] = field(default_factory=list)
    calibration_result: CalibrationResult | None = None
    user_turn_count: int = 0
    aurora_message_count: int = 0
    pending_option_groups: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    last_activity_at: str = field(default_factory=lambda: _utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: (_utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat())

    @property
    def is_expired(self) -> bool:
        try:
            expires = datetime.fromisoformat(self.expires_at)
        except ValueError:
            return True
        return _utcnow() > expires

    @property
    def is_idle_expired(self) -> bool:
        try:
            last = datetime.fromisoformat(self.last_activity_at)
        except ValueError:
            return True
        return _utcnow() > last + timedelta(seconds=IDLE_TTL_SECONDS)

    @property
    def at_turn_limit(self) -> bool:
        return self.user_turn_count >= MAX_USER_TURNS

    @property
    def at_message_limit(self) -> bool:
        return self.aurora_message_count >= MAX_AURORA_MESSAGES

    def add_aurora_message(self, content: str, stage: SessionStage) -> AuroraCoreMessage:
        msg = AuroraCoreMessage(role="aurora", content=content, stage=stage)
        self.messages.append(msg)
        self.aurora_message_count += 1
        self.last_activity_at = _utcnow().isoformat()
        return msg

    def add_user_message(
        self,
        content: str,
        *,
        option_id: str | None = None,
        semantic_value: str | None = None,
        is_freeform: bool = False,
    ) -> AuroraCoreMessage:
        msg = AuroraCoreMessage(
            role="user",
            content=content,
            stage=self.stage,
            option_id=option_id,
            semantic_value=semantic_value,
            is_freeform=is_freeform,
        )
        self.messages.append(msg)
        self.user_turn_count += 1
        self.last_activity_at = _utcnow().isoformat()
        return msg

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "surface": self.surface,
            "status": self.status,
            "stage": self.stage,
            "scope": self.scope,
            "session_type": self.session_type,
            "entry_reason": self.entry_reason,
            "case_file": self.case_file,
            "agenda": self.agenda_snapshot(),
            "resume_token": self.resume_token,
            "messages": [m.to_dict() for m in self.messages],
            "calibration_result": self.calibration_result.to_dict() if self.calibration_result else None,
            "user_turn_count": self.user_turn_count,
            "aurora_message_count": self.aurora_message_count,
            "pending_option_groups": self.pending_option_groups,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuroraCoreSession:
        messages = [AuroraCoreMessage(**m) for m in data.get("messages", [])]
        raw_result = data.get("calibration_result")
        result = CalibrationResult(**raw_result) if isinstance(raw_result, dict) else None
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            conversation_id=data.get("conversation_id"),
            surface=data.get("surface", "aurora_modeling"),
            status=data.get("status", "active"),
            stage=data.get("stage", "declare"),
            scope=data.get("scope", ""),
            session_type=data.get("session_type", "user_initiated"),
            entry_reason=data.get("entry_reason") if isinstance(data.get("entry_reason"), dict) else {},
            case_file=data.get("case_file") if isinstance(data.get("case_file"), dict) else {},
            resume_token=data.get("resume_token") or "",
            messages=messages,
            calibration_result=result,
            user_turn_count=data.get("user_turn_count", 0),
            aurora_message_count=data.get("aurora_message_count", 0),
            pending_option_groups=data.get("pending_option_groups", []),
            created_at=data.get("created_at", _utcnow().isoformat()),
            last_activity_at=data.get("last_activity_at", _utcnow().isoformat()),
            expires_at=data.get("expires_at", (_utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()),
        )

    def agenda_snapshot(self) -> dict[str, Any]:
        """Return the backend-authoritative agenda projection for the UI."""
        entry_reason = self.entry_reason if isinstance(self.entry_reason, dict) else {}
        estimated_minutes = entry_reason.get("estimated_minutes") or 4
        agenda_preview = entry_reason.get("suggested_agenda_preview") or []
        items = [
            {
                "id": "enter_session",
                "label": "进入 Aurora 校准",
                "status": "done",
                "message_stage": "declare",
            },
            {
                "id": "explain_conflict",
                "label": "说明我看见的冲突",
                "status": "done" if self.aurora_message_count >= 2 else "in_progress",
                "message_stage": "observe",
            },
            {
                "id": "ask_confirmation",
                "label": "向你确认关键判断",
                "status": "in_progress" if self.status in ("active", "paused") else "done",
                "message_stage": "ask",
            },
            {
                "id": "apply_update",
                "label": "应用校准结果",
                "status": "done" if self.calibration_result is not None else "pending",
                "message_stage": "update",
            },
            {
                "id": "close_session",
                "label": "Aurora 回到后台",
                "status": "done" if self.stage == "exit" else "pending",
                "message_stage": "exit",
            },
        ]
        return {
            "session_id": self.session_id,
            "scope": self.scope,
            "status": self.status,
            "current_stage": self.stage,
            "interruption_policy": "answer_then_resume",
            "interruption_policy_label": "可以随时暂停；回来后从当前问题继续",
            "resume_hint": "暂停后 Aurora 会保留阶段、消息和待确认问题，不需要你重讲。",
            "estimated_minutes": int(estimated_minutes) if isinstance(estimated_minutes, (int, float)) else 4,
            "preview": [str(item) for item in agenda_preview[:4]],
            "items": items,
        }


class AuroraCoreSessionStore:
    """Redis-backed store for AuroraCoreSession objects."""

    def __init__(self, redis, db=None) -> None:
        self.redis = redis
        self.db = db

    def _session_key(self, session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"

    def _user_active_key(self, user_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}active:{user_id}"

    def _user_current_key(self, user_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}current:{user_id}"

    def _user_last_key(self, user_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}last:{user_id}"

    def _resume_key(self, resume_token: str) -> str:
        return f"{RESUME_TOKEN_KEY_PREFIX}{resume_token}"

    async def save(
        self,
        session: AuroraCoreSession,
        *,
        previous_resume_token: str | None = None,
    ) -> None:
        await self._save_durable(session)
        if self.redis is None:
            return
        key = self._session_key(session.session_id)
        payload = json.dumps(session.to_dict(), ensure_ascii=False)
        await self._call("setex", key, SESSION_TTL_SECONDS, payload)
        await self._call(
            "setex",
            self._user_last_key(session.user_id),
            SESSION_TTL_SECONDS,
            session.session_id,
        )

        if session.status == "active":
            await self._call(
                "setex",
                self._user_active_key(session.user_id),
                SESSION_TTL_SECONDS,
                session.session_id,
            )
        else:
            await self._call("delete", self._user_active_key(session.user_id))

        if session.status in ("active", "paused"):
            await self._call(
                "setex",
                self._user_current_key(session.user_id),
                SESSION_TTL_SECONDS,
                session.session_id,
            )
            if session.resume_token:
                await self._call(
                    "setex",
                    self._resume_key(session.resume_token),
                    SESSION_TTL_SECONDS,
                    session.session_id,
                )
        else:
            await self._call("delete", self._user_active_key(session.user_id))
            await self._call("delete", self._user_current_key(session.user_id))
            if session.resume_token:
                await self._call("delete", self._resume_key(session.resume_token))
        if previous_resume_token and previous_resume_token != session.resume_token:
            await self._call("delete", self._resume_key(previous_resume_token))

    async def load(self, session_id: str) -> AuroraCoreSession | None:
        raw = await self._call("get", self._session_key(session_id)) if self.redis is not None else None
        if not raw:
            session = await self._load_durable_by_session_id(session_id)
            if session is not None:
                await self.save(session)
            return session
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return AuroraCoreSession.from_dict(json.loads(raw))
        except Exception:
            return None

    async def load_active(self, user_id: str) -> AuroraCoreSession | None:
        raw_id = await self._call("get", self._user_active_key(user_id)) if self.redis is not None else None
        if not raw_id:
            return await self._load_durable_latest(user_id=user_id, statuses=("active",))
        if isinstance(raw_id, bytes):
            raw_id = raw_id.decode("utf-8")
        session = await self.load(raw_id.strip())
        if session is None or session.status != "active":
            return None
        return session

    async def load_current(self, user_id: str) -> AuroraCoreSession | None:
        raw_id = await self._call("get", self._user_current_key(user_id)) if self.redis is not None else None
        if not raw_id:
            return await self._load_durable_latest(user_id=user_id, statuses=("active", "paused", "expired"))
        if isinstance(raw_id, bytes):
            raw_id = raw_id.decode("utf-8")
        return await self.load(raw_id.strip())

    async def load_last(self, user_id: str) -> AuroraCoreSession | None:
        raw_id = await self._call("get", self._user_last_key(user_id)) if self.redis is not None else None
        if not raw_id:
            return await self._load_durable_latest(user_id=user_id, statuses=None)
        if isinstance(raw_id, bytes):
            raw_id = raw_id.decode("utf-8")
        return await self.load(raw_id.strip())

    async def load_by_resume_token(self, resume_token: str) -> AuroraCoreSession | None:
        raw_id = await self._call("get", self._resume_key(resume_token)) if self.redis is not None else None
        if raw_id:
            if isinstance(raw_id, bytes):
                raw_id = raw_id.decode("utf-8")
            return await self.load(raw_id.strip())
        durable = await self._load_durable_by_resume_token(resume_token)
        if durable is not None:
            await self.save(durable)
            return durable
        # Migration fallback for sessions created before opaque resume tokens.
        return await self.load(resume_token)

    async def _save_durable(self, session: AuroraCoreSession) -> None:
        if self.db is None:
            return
        try:
            from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot

            result = await self.db.execute(
                select(AuroraCoreSessionSnapshot).where(AuroraCoreSessionSnapshot.session_id == session.session_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = AuroraCoreSessionSnapshot(session_id=session.session_id)
                self.db.add(record)
            record.user_id = session.user_id
            record.conversation_id = session.conversation_id
            record.surface = session.surface
            record.status = session.status
            record.stage = session.stage
            record.resume_token_hash = _hash_resume_token(session.resume_token) if session.resume_token else None
            record.last_activity_at = _parse_dt(session.last_activity_at) or _utcnow()
            record.expires_at = _parse_dt(session.expires_at) or (_utcnow() + timedelta(days=3))
            record.payload = session.to_dict()
            record.runtime_metadata = {"source": "AuroraCoreSessionStore.save"}
            await self.db.flush()
        except Exception as exc:
            logger.debug(f"Failed to persist Aurora core session {session.session_id}: {exc}")

    async def _load_durable_by_session_id(self, session_id: str) -> AuroraCoreSession | None:
        if self.db is None:
            return None
        try:
            from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot

            result = await self.db.execute(
                select(AuroraCoreSessionSnapshot).where(AuroraCoreSessionSnapshot.session_id == session_id).limit(1)
            )
            record = result.scalar_one_or_none()
            return self._session_from_record(record)
        except Exception as exc:
            logger.debug(f"Failed to load durable Aurora core session {session_id}: {exc}")
            return None

    async def _load_durable_by_resume_token(self, resume_token: str) -> AuroraCoreSession | None:
        if self.db is None or not resume_token:
            return None
        try:
            from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot

            result = await self.db.execute(
                select(AuroraCoreSessionSnapshot)
                .where(AuroraCoreSessionSnapshot.resume_token_hash == _hash_resume_token(resume_token))
                .limit(1)
            )
            record = result.scalar_one_or_none()
            return self._session_from_record(record)
        except Exception as exc:
            logger.debug(f"Failed to load durable Aurora core session by resume token: {exc}")
            return None

    async def _load_durable_latest(
        self,
        *,
        user_id: str,
        statuses: tuple[str, ...] | None,
    ) -> AuroraCoreSession | None:
        if self.db is None:
            return None
        try:
            from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot

            query = select(AuroraCoreSessionSnapshot).where(AuroraCoreSessionSnapshot.user_id == user_id)
            if statuses:
                query = query.where(AuroraCoreSessionSnapshot.status.in_(statuses))
            result = await self.db.execute(query.order_by(AuroraCoreSessionSnapshot.last_activity_at.desc()).limit(1))
            record = result.scalar_one_or_none()
            session = self._session_from_record(record)
            if session is not None:
                await self.save(session)
            return session
        except Exception as exc:
            logger.debug(f"Failed to load latest durable Aurora core session for {user_id}: {exc}")
            return None

    @staticmethod
    def _session_from_record(record: Any) -> AuroraCoreSession | None:
        if record is None:
            return None
        payload = getattr(record, "payload", None)
        if not isinstance(payload, dict):
            return None
        try:
            return AuroraCoreSession.from_dict(payload)
        except Exception:
            return None

    async def _call(self, method: str, *args, **kwargs):
        fn = getattr(self.redis, method, None)
        if fn is None:
            return None
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


class AuroraCoreSessionService:
    """Manages AuroraCoreSession lifecycle and message processing.

    This service orchestrates:
    - session creation (start)
    - injecting Aurora's opening sequence
    - processing user responses (respond)
    - applying model_write_effects
    - closing and producing CalibrationResult
    """

    def __init__(self, redis, db=None) -> None:
        self.store = AuroraCoreSessionStore(redis, db=db)
        self.db = db

    async def start_session(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        surface: str = "aurora_modeling",
        session_type: str = "user_initiated",
        scope: str | None = None,
        wake_reasons: list[str] | None = None,
        band_status: str = "calibration_available",
        entry_reason: dict[str, Any] | AuroraCoreSessionEntryReason | None = None,
        case_file: dict[str, Any] | None = None,
        resume_token: str | None = None,
    ) -> AuroraCoreSession:
        """Create a new L3 session and inject opening Aurora messages."""
        if resume_token:
            return await self.resume_session(user_id=user_id, resume_token=resume_token)

        # Check for existing active session
        existing = await self.store.load_active(user_id)
        if existing is not None:
            if await self._expire_if_needed(existing):
                return await self.start_session(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    surface=surface,
                    session_type=session_type,
                    scope=scope,
                    wake_reasons=wake_reasons,
                    band_status=band_status,
                    entry_reason=entry_reason,
                    case_file=case_file,
                )
            return existing

        session_id = str(uuid.uuid4())
        resolved_scope = scope or self._infer_scope(band_status, wake_reasons or [])
        normalized_entry_reason = self._normalize_entry_reason(
            entry_reason=entry_reason,
            surface=surface,
            band_status=band_status,
            wake_reasons=wake_reasons or [],
            scope=resolved_scope,
        )

        session = AuroraCoreSession(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            surface=surface,
            status="active",
            stage="declare",
            scope=resolved_scope,
            session_type=session_type,
            entry_reason=normalized_entry_reason.to_dict(),
            case_file=self._build_case_file(
                user_id=user_id,
                scope=resolved_scope,
                wake_reasons=wake_reasons or [],
                entry_reason=normalized_entry_reason,
                supplied=case_file,
            ),
            resume_token=_new_resume_token(),
        )

        # Inject opening message sequence
        self._inject_opening_sequence(session, wake_reasons=wake_reasons or [])
        await self.store.save(session)
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="started", status=session.status).inc()
        return session

    async def respond(
        self,
        *,
        user_id: str,
        session_id: str,
        content: str,
        option_id: str | None = None,
        semantic_value: str | None = None,
        model_write_effect: dict[str, Any] | None = None,
        is_freeform: bool = False,
    ) -> AuroraCoreSession:
        """Process a user response in an active session."""
        session = await self.store.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        if session.user_id != user_id:
            raise PermissionError("Session does not belong to this user")
        previous_resume_token: str | None = None
        if session.status == "paused":
            previous_resume_token = self._refresh_resume_token(session)
            session.status = "active"
            session.last_activity_at = _utcnow().isoformat()
            if not session.at_message_limit:
                session.add_aurora_message(
                    "我们从暂停的地方继续。你刚才这句我会接在前面的校准里处理。",
                    "process_response",
                )
        elif session.status != "active":
            raise ValueError(f"Session is {session.status}, not active")
        if await self._expire_if_needed(session):
            raise ValueError("Session has expired")

        # Record user turn
        session.add_user_message(
            content,
            option_id=option_id,
            semantic_value=semantic_value,
            is_freeform=is_freeform,
        )
        previous_resume_token = previous_resume_token or self._refresh_resume_token(session)

        # Apply model write effect if present
        if model_write_effect:
            self._apply_write_effect(session, model_write_effect)

        # Advance session based on current stage and response
        self._advance_session(
            session,
            semantic_value=semantic_value,
            is_freeform=is_freeform,
            content=content,
        )

        await self.store.save(session, previous_resume_token=previous_resume_token)
        if session.status == "completed":
            AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="completed", status=session.status).inc()
            try:
                await event_bus.publish(
                    "aurora.calibration.completed",
                    {
                        "event_type": "aurora.calibration.completed",
                        "user_id": str(user_id),
                        "session_id": session.id,
                        "surface": session.scope,
                        "entry_reason": session.entry_reason,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            except Exception as exc:
                logger.warning("Failed to publish Aurora calibration achievement event: {}", exc)
        return session

    async def close_session(self, *, user_id: str, session_id: str) -> AuroraCoreSession:
        """Force-close a session (user-initiated exit)."""
        session = await self.store.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        if session.user_id != user_id:
            raise PermissionError("Session does not belong to this user")
        if session.status == "completed":
            return session

        previous_resume_token = session.resume_token
        self._finalize_session(session, abandoned=True)
        await self.store.save(session, previous_resume_token=previous_resume_token)
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="closed", status=session.status).inc()
        return session

    async def pause_session(
        self,
        *,
        user_id: str,
        session_id: str,
        reason: str = "user_request",
    ) -> AuroraCoreSession:
        """Pause a session and return a resume token."""
        del reason
        session = await self.store.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        if session.user_id != user_id:
            raise PermissionError("Session does not belong to this user")
        if session.status != "active":
            raise ValueError(f"Session is {session.status}, not active")
        if await self._expire_if_needed(session):
            return session

        previous_resume_token = self._refresh_resume_token(session)
        session.status = "paused"
        session.last_activity_at = _utcnow().isoformat()
        if not session.at_message_limit:
            session.add_aurora_message(
                "好，我们先暂停在这里。回来时我会从这次校准继续，不会让你重讲一遍。",
                "process_response",
            )
        await self.store.save(session, previous_resume_token=previous_resume_token)
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="paused", status=session.status).inc()
        return session

    async def get_active_session(self, user_id: str) -> AuroraCoreSession | None:
        session = await self.store.load_active(user_id)
        if session is None:
            return None
        if await self._expire_if_needed(session):
            return None
        if session.status != "active":
            return None
        return session

    async def get_current_session(self, user_id: str) -> AuroraCoreSession | None:
        session = await self.store.load_current(user_id)
        if session is None:
            last_session = await self.store.load_last(user_id)
            if last_session and last_session.status == "expired":
                return last_session
            return None
        await self._expire_if_needed(session)
        return session

    async def get_session(self, session_id: str) -> AuroraCoreSession | None:
        return await self.store.load(session_id)

    async def resume_session(
        self,
        *,
        user_id: str,
        resume_token: str,
    ) -> AuroraCoreSession:
        session = await self._resume_session_from_token(
            user_id=user_id,
            resume_token=resume_token,
        )
        if session is None:
            last_session = await self.store.load_last(user_id)
            if last_session and last_session.status == "expired":
                return last_session
            raise LookupError("Session resume token is no longer valid")
        return session

    async def _resume_session_from_token(
        self,
        *,
        user_id: str,
        resume_token: str,
    ) -> AuroraCoreSession | None:
        session = await self.store.load_by_resume_token(resume_token)
        if session is None:
            return None
        if session.user_id != user_id:
            raise PermissionError("Session does not belong to this user")
        if session.status not in ("paused", "active"):
            if session.status == "expired":
                return session
            raise ValueError(f"Session is {session.status}, not resumable")
        if await self._expire_if_needed(session):
            return session
        was_paused = session.status == "paused"
        previous_resume_token = self._refresh_resume_token(session)
        session.status = "active"
        session.last_activity_at = _utcnow().isoformat()
        if was_paused and not session.at_message_limit:
            session.add_aurora_message(
                "我们从刚才暂停的地方继续。你不用重讲，我还保留着前面的判断。",
                "process_response",
            )
        await self.store.save(session, previous_resume_token=previous_resume_token)
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="resumed", status=session.status).inc()
        return session

    def _refresh_resume_token(self, session: AuroraCoreSession) -> str | None:
        previous = session.resume_token
        session.resume_token = _new_resume_token()
        return previous or None

    async def _expire_if_needed(self, session: AuroraCoreSession) -> bool:
        if session.status not in ("active", "paused"):
            return session.status == "expired"
        if session.status == "active" and session.is_idle_expired and not session.is_expired:
            previous_resume_token = self._refresh_resume_token(session)
            self._pause_for_idle(session)
            await self.store.save(session, previous_resume_token=previous_resume_token)
            return False
        if not session.is_expired:
            return False
        previous_resume_token = session.resume_token
        self._mark_session_expired(session)
        await self.store.save(session, previous_resume_token=previous_resume_token)
        return True

    def _pause_for_idle(self, session: AuroraCoreSession) -> None:
        session.status = "paused"
        session.last_activity_at = _utcnow().isoformat()
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="idle_paused", status=session.status).inc()
        if not session.messages or "暂停在这里" not in session.messages[-1].content:
            session.add_aurora_message(
                "我先把这次深度校准暂停在这里。回来时我们可以从这个问题继续，不用你重新解释前面的内容。",
                "process_response",
            )

    def _mark_session_expired(self, session: AuroraCoreSession) -> None:
        if session.calibration_result is None:
            user_visible_summary = self._build_expired_summary(session)
            session.calibration_result = CalibrationResult(
                updates_applied=[],
                summary=user_visible_summary,
                user_visible_summary=user_visible_summary,
                scope_completed=session.scope,
                strategy_changes=[],
                state_patches=[],
                next_changes=[],
                session_id=session.session_id,
            )
        if not session.messages or "上次的深度对话已结束" not in session.messages[-1].content:
            session.add_aurora_message(
                "上次的深度对话已结束。你可以看看我们停在了哪里，也可以重新开始一次短校准。",
                "exit",
            )
        session.status = "expired"
        session.stage = "exit"
        session.pending_option_groups = []
        session.resume_token = ""
        AURORA_CORE_SESSION_EVENT_TOTAL.labels(event="expired", status=session.status).inc()

    def _build_expired_summary(self, session: AuroraCoreSession) -> str:
        if session.user_turn_count:
            return (
                f"上次我们围绕「{session.scope}」聊了 {session.user_turn_count} 轮，"
                "但会话已经超过可恢复时间。我保留这段摘要供你回看，不会把未确认内容直接写入长期判断。"
            )
        return f"上次深度对话停在「{session.scope}」，还没进入正式校准，已经自动结束。"

    # ── Session flow ───────────────────────────────────────────────

    def _build_case_file(
        self,
        *,
        user_id: str,
        scope: str,
        wake_reasons: list[str],
        entry_reason: AuroraCoreSessionEntryReason,
        supplied: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the evidence package the UI and closure can audit."""
        source_summary = []
        for signal in entry_reason.observed_signals:
            source_summary.append(
                {
                    "source": "entry_reason",
                    "summary": signal,
                    "confidence": 0.72,
                }
            )
        for reason in wake_reasons:
            source_summary.append(
                {
                    "source": "wake_reason",
                    "summary": reason,
                    "confidence": 0.68,
                }
            )

        base = {
            "case_file_id": f"acf_{uuid.uuid4().hex}",
            "user_id": user_id,
            "goal_summary": str((supplied or {}).get("goal_summary") or scope),
            "current_plan_summary": str((supplied or {}).get("current_plan_summary") or scope),
            "recent_task_events": list((supplied or {}).get("recent_task_events") or [])[:8],
            "recent_failures": list((supplied or {}).get("recent_failures") or [])[:8],
            "recent_user_corrections": list((supplied or {}).get("recent_user_corrections") or [])[:8],
            "active_hypotheses": list((supplied or {}).get("active_hypotheses") or [])[:6],
            "conflicts_to_resolve": list((supplied or {}).get("conflicts_to_resolve") or [])[:6],
            "source_summary": list((supplied or {}).get("source_summary") or source_summary)[:10],
            "relationship_notes": list((supplied or {}).get("relationship_notes") or [])[:5],
            "suggested_questions": list(
                (supplied or {}).get("suggested_questions")
                or entry_reason.suggested_agenda_preview
                or ["我这次哪里理解错了？", "接下来需要先改哪个动作？"]
            )[:5],
            "wake_reason": wake_reasons[0] if wake_reasons else "",
            "entry_reason": entry_reason.to_dict(),
            "created_at": _utcnow().isoformat(),
        }
        if supplied:
            for key in ("source_receipt", "recent_outcomes", "active_state_packet"):
                value = supplied.get(key)
                if value:
                    base[key] = value
        return base

    def _normalize_entry_reason(
        self,
        *,
        entry_reason: dict[str, Any] | AuroraCoreSessionEntryReason | None,
        surface: str,
        band_status: str,
        wake_reasons: list[str],
        scope: str,
    ) -> AuroraCoreSessionEntryReason:
        if isinstance(entry_reason, AuroraCoreSessionEntryReason):
            return entry_reason
        parsed = AuroraCoreSessionEntryReason.from_dict(entry_reason)
        if parsed is not None:
            return parsed
        trigger_source = surface if surface != "aurora_modeling" else "user_initiated"
        why_now = "当前状态提示这个判断值得现在校准"
        if band_status == "risk_found":
            why_now = "已经出现可能影响接下来行动的风险信号"
        elif band_status == "needs_confirm":
            why_now = "有几个判断还没有被你确认，继续推进前最好先对齐"
        elif band_status == "calibration_available":
            why_now = "现在有足够信号做一次短校准"
        base_reason = AuroraCoreSessionEntryReason.from_context(
            trigger_source=trigger_source,
            wake_reason=wake_reasons[0] if wake_reasons else "",
            wake_reasons=wake_reasons[1:],
            current_plan_summary=scope,
        )
        return AuroraCoreSessionEntryReason(
            trigger_source=trigger_source,
            observed_signals=base_reason.observed_signals,
            suggested_agenda_preview=["确认我观察到的信号", "校准接下来的策略", "生成可执行的调整结果"],
            why_now=why_now,
            estimated_minutes=4,
        )

    def _inject_opening_sequence(
        self,
        session: AuroraCoreSession,
        *,
        wake_reasons: list[str],
    ) -> None:
        """Inject Aurora's ritualized opening messages."""
        entry_reason = AuroraCoreSessionEntryReason.from_dict(session.entry_reason)
        if entry_reason is not None:
            session.add_aurora_message(entry_reason.opening_message(), "declare")
            if entry_reason.suggested_agenda_preview:
                preview = "；".join(entry_reason.suggested_agenda_preview[:3])
                session.add_aurora_message(f"这次我会先{preview}。", "observe")
        else:
            session.add_aurora_message("等一下，我需要重新校准一下。", "declare")

            observation = self._build_observation(wake_reasons)
            if observation:
                session.add_aurora_message(observation, "observe")

            judgment = self._build_judgment(session.scope)
            session.add_aurora_message(judgment, "judge")

        question, options = self._build_first_question(session)
        session.add_aurora_message(question, "ask")
        session.pending_option_groups = options
        session.stage = "await_user"

    def _advance_session(
        self,
        session: AuroraCoreSession,
        *,
        semantic_value: str | None,
        is_freeform: bool,
        content: str = "",
    ) -> None:
        """Decide next Aurora messages after a user response."""
        if semantic_value == "topic_switch":
            session.scope = content.strip()[:80] or session.scope
            session.add_aurora_message(
                "可以，我们先把话题切到你刚才说的这个点。我会按新的重点继续问，不强行拉回原来的 agenda。",
                "process_response",
            )
            session.pending_option_groups = [self._simple_confirm_group()]
            session.stage = "await_user"
            return

        # Handle freeform correction — ask clarifying follow-up
        if is_freeform:
            session.add_aurora_message(
                "好，我记下来了。帮我确认一下：你说的意思是这件事的情况和我之前理解的不一样？",
                "process_response",
            )
            session.pending_option_groups = [self._simple_confirm_group()]
            session.stage = "await_user"
            return

        # Turn limit reached — finalize
        if session.at_turn_limit or session.at_message_limit:
            self._finalize_session(session, abandoned=False)
            return

        # Progress through stages
        if session.stage in ("await_user", "process_response"):
            next_question, options = self._build_follow_up(session, semantic_value)
            if next_question:
                session.add_aurora_message(next_question, "ask")
                session.pending_option_groups = options
                session.stage = "await_user"
            else:
                self._finalize_session(session, abandoned=False)

    def _finalize_session(self, session: AuroraCoreSession, *, abandoned: bool) -> None:
        """Write CalibrationResult and close session."""
        applied_effects = [
            msg_meta
            for msg in session.messages
            if msg.role == "user" and msg.semantic_value
            for msg_meta in [{"semantic_value": msg.semantic_value, "option_id": msg.option_id}]
        ]
        changes = self._derive_strategy_changes(session)
        state_patches = self._derive_state_patches(session)
        next_changes = self._derive_next_changes(session, changes=changes, state_patches=state_patches)
        user_visible_summary = self._build_result_summary(session, abandoned=abandoned)

        session.calibration_result = CalibrationResult(
            updates_applied=applied_effects,
            summary=user_visible_summary,
            user_visible_summary=user_visible_summary,
            scope_completed=session.scope,
            strategy_changes=changes,
            state_patches=state_patches,
            next_changes=next_changes,
            session_id=session.session_id,
        )
        if not abandoned:
            session.add_aurora_message(
                self._build_exit_message(session),
                "exit",
            )
        session.status = "completed" if not abandoned else "abandoned"
        session.stage = "exit"
        session.pending_option_groups = []

    # ── Message builders ───────────────────────────────────────────

    def _build_observation(self, wake_reasons: list[str]) -> str:
        reason_map = {
            "task_time_overrun": "最近两张任务卡都明显超时",
            "repeated_mistake_cluster": "我发现同一类错误重复出现了三次",
            "state_conflict": "你的行为和你之前说的目标之间出现了不一致",
            "self_model_confidence_drop": "我对自己的一些判断置信度下降了",
            "plan_drift": "当前计划似乎在逐渐偏离原来的目标方向",
            "user_distress": "我感觉到你最近的状态可能有些压力",
            "standard_layer_uncertainty": "标准层在这里不确定该怎么处理",
        }
        observations = [reason_map[r] for r in wake_reasons if r in reason_map]
        if not observations:
            return ""
        if len(observations) == 1:
            return f"我注意到：{observations[0]}。"
        listed = "；".join(observations[:3])
        return f"我注意到几件事：{listed}。"

    def _build_judgment(self, scope: str) -> str:
        if scope:
            return f"所以我怀疑这里需要重新看一下：{scope}。"
        return "我觉得有一个地方可能需要重新校准一下，让我们一起确认。"

    def _build_first_question(
        self,
        session: AuroraCoreSession,
    ) -> tuple[str, list[dict[str, Any]]]:
        from app.aurora.predicted_reply_engine import PredictedReplyOptionEngine

        scope = session.scope.lower()
        if "时间" in scope or "available" in scope:
            question = "先确认一个关键点：今晚你真实可用时间更接近哪个？"
            options = PredictedReplyOptionEngine().generate(
                band_status="needs_confirm",
                facets=[],
                user_model_meta={"available_time_confirmed": False},
            )
        elif "目标" in scope or "goal" in scope:
            question = "你的目标现在还是先过线，还是已经变成冲高分了？"
            options = PredictedReplyOptionEngine().generate(
                band_status="needs_confirm",
                facets=[],
                user_model_meta={"goal_type_confirmed": False, "available_time_confirmed": True},
            )
        else:
            question = "我先问你一个关键问题：这件事最近发生了变化吗？"
            options = [self._simple_confirm_group()]
        return question, options

    def _build_follow_up(
        self,
        session: AuroraCoreSession,
        semantic_value: str | None,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        user_turn = session.user_turn_count
        if user_turn >= 3:
            return None, []
        if semantic_value == "freeform_correction":
            return "我理解了。还有什么我应该知道的吗？", [self._simple_confirm_group()]
        if user_turn == 1:
            return "好。还有一件事我想确认：这个情况是最近才开始的，还是已经持续一段时间了？", [self._duration_group()]
        return None, []

    def _build_exit_message(self, session: AuroraCoreSession) -> str:
        changes = self._derive_strategy_changes(session)
        if not changes:
            return "这次校准完成。我更新了当前的判断，Aurora 先退回后台。"
        changes_text = "；".join(changes[:3])
        return f"这次校准完成。我更新了三件事：{changes_text}。\nAurora 先退回后台。"

    def _build_result_summary(self, session: AuroraCoreSession, *, abandoned: bool) -> str:
        if abandoned:
            return f"这次我们先聊到这里。我已经保留了前 {session.user_turn_count} 轮里的校准信息，之后会少用刚才被你修正过的判断。"
        changes = self._derive_strategy_changes(session)
        if changes:
            return f"这次我们确认了「{session.scope}」，并把接下来的处理方式调整为：{'；'.join(changes[:3])}。"
        return f"这次我们确认了「{session.scope}」。我会把它作为接下来判断你的状态和计划时的参考。"

    # ── Helper groups ──────────────────────────────────────────────

    def _simple_confirm_group(self) -> dict[str, Any]:
        return {
            "group_id": "simple_confirm",
            "question": "",
            "question_type": "assumption_check",
            "context_note": "",
            "options": [
                {
                    "id": "yes_correct",
                    "label": "是的",
                    "semantic_value": "confirmed",
                    "reply_type": "assumption_check",
                    "confidence": 0.6,
                    "model_write_effect": None,
                    "is_disconfirming": False,
                    "is_freeform": False,
                    "context_source": "simple_confirm",
                    "telemetry_id": "simple_yes",
                },
                {
                    "id": "no_incorrect",
                    "label": "不对",
                    "semantic_value": "denied",
                    "reply_type": "assumption_check",
                    "confidence": 0.3,
                    "model_write_effect": None,
                    "is_disconfirming": True,
                    "is_freeform": False,
                    "context_source": "simple_confirm",
                    "telemetry_id": "simple_no",
                },
                {
                    "id": "freeform_correction",
                    "label": "都不对，我解释一下",
                    "semantic_value": "freeform_correction",
                    "reply_type": "freeform",
                    "confidence": 0.0,
                    "model_write_effect": None,
                    "is_disconfirming": True,
                    "is_freeform": True,
                    "context_source": "simple_confirm",
                    "telemetry_id": "simple_freeform",
                },
            ],
        }

    def _duration_group(self) -> dict[str, Any]:
        return {
            "group_id": "duration_check",
            "question": "这种情况持续多久了？",
            "question_type": "fact_confirm",
            "context_note": "",
            "options": [
                {
                    "id": "duration_today",
                    "label": "就今天",
                    "semantic_value": "duration_exceptional",
                    "reply_type": "fact_confirm",
                    "confidence": 0.35,
                    "model_write_effect": None,
                    "is_disconfirming": False,
                    "is_freeform": False,
                    "context_source": "duration_check",
                    "telemetry_id": "dur_today",
                },
                {
                    "id": "duration_few_days",
                    "label": "几天了",
                    "semantic_value": "duration_recurring",
                    "reply_type": "fact_confirm",
                    "confidence": 0.45,
                    "model_write_effect": None,
                    "is_disconfirming": False,
                    "is_freeform": False,
                    "context_source": "duration_check",
                    "telemetry_id": "dur_days",
                },
                {
                    "id": "duration_week_plus",
                    "label": "一周以上了",
                    "semantic_value": "duration_chronic",
                    "reply_type": "fact_confirm",
                    "confidence": 0.2,
                    "model_write_effect": None,
                    "is_disconfirming": False,
                    "is_freeform": False,
                    "context_source": "duration_check",
                    "telemetry_id": "dur_week",
                },
                {
                    "id": "freeform_correction",
                    "label": "都不对，我解释一下",
                    "semantic_value": "freeform_correction",
                    "reply_type": "freeform",
                    "confidence": 0.0,
                    "model_write_effect": None,
                    "is_disconfirming": True,
                    "is_freeform": True,
                    "context_source": "duration_check",
                    "telemetry_id": "dur_freeform",
                },
            ],
        }

    # ── Write effect application ───────────────────────────────────

    def _apply_write_effect(self, session: AuroraCoreSession, effect: dict[str, Any]) -> None:
        """Record model write effect as pending calibration update."""
        if not effect or not effect.get("field_key"):
            return
        if not hasattr(session, "_pending_effects"):
            object.__setattr__(session, "_pending_effects", [])
        session._pending_effects = getattr(session, "_pending_effects", []) + [effect]

    # ── Strategy change derivation ─────────────────────────────────

    def _derive_strategy_changes(self, session: AuroraCoreSession) -> list[str]:
        changes: list[str] = []
        seen_semantics = {msg.semantic_value for msg in session.messages if msg.role == "user" and msg.semantic_value}
        correction_profile = self._interpret_freeform_corrections(session)
        if "available_time_30" in seen_semantics:
            changes.append("今晚按 30 分钟处理任务")
        elif "available_time_45" in seen_semantics:
            changes.append("今晚按 45 分钟处理任务")
        elif "available_time_60" in seen_semantics:
            changes.append("今晚按 60 分钟处理任务")
        if "goal_pass_threshold" in seen_semantics:
            changes.append("目标确认为先过线")
        elif "goal_maximize_score" in seen_semantics:
            changes.append("目标更新为冲高分")
        if "reduce_scope" in seen_semantics or "task_scope_too_large" in seen_semantics:
            changes.append("后续任务颗粒度调小")
        if "duration_chronic" in seen_semantics:
            changes.append("该问题已持续一周以上，调整为长期策略")
        if correction_profile.get("blocker_type") == "skill_gap":
            changes.append("先按能力缺口处理，不再把它当作时间不够")
        return changes

    def _derive_state_patches(self, session: AuroraCoreSession) -> list[dict[str, Any]]:
        patches: list[dict[str, Any]] = []
        seen_semantics = [msg.semantic_value for msg in session.messages if msg.role == "user" and msg.semantic_value]
        correction_profile = self._interpret_freeform_corrections(session)
        semantic_map = {
            "available_time_30": ("available_time_today", "unknown", "30_minutes", "用户确认今晚可用时间约 30 分钟"),
            "available_time_45": ("available_time_today", "unknown", "45_minutes", "用户确认今晚可用时间约 45 分钟"),
            "available_time_60": ("available_time_today", "unknown", "60_minutes", "用户确认今晚可用时间约 60 分钟"),
            "goal_pass_threshold": ("goal_strategy", "unclear", "pass_threshold", "用户确认目标是先过线"),
            "goal_maximize_score": ("goal_strategy", "unclear", "maximize_score", "用户确认目标是冲高分"),
            "denied": ("aurora_assumption", "accepted", "needs_revision", "用户否认了 Aurora 的当前判断"),
            "freeform_correction": ("aurora_assumption", "inferred", "user_corrected", "用户用自由文本修正了判断"),
            "duration_chronic": ("issue_duration", "unknown", "week_plus", "用户确认问题已持续一周以上"),
        }
        for semantic in seen_semantics:
            mapped = semantic_map.get(semantic or "")
            if not mapped:
                continue
            state_key, old_value, new_value, reason = mapped
            if any(p["state_key"] == state_key and p["new_value"] == new_value for p in patches):
                continue
            patches.append(
                {
                    "state_key": state_key,
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": reason,
                    "confidence": 0.72,
                }
            )
        if correction_profile.get("blocker_type") == "skill_gap":
            skill_reason = correction_profile.get("reason") or "用户明确说明卡住原因是不会做，而不是时间不足"
            blocker_patches = [
                {
                    "state_key": "current_blocker",
                    "old_value": "time_or_effort_unclear",
                    "new_value": "skill_gap",
                    "reason": skill_reason,
                    "confidence": 0.82,
                },
                {
                    "state_key": "policy_directive",
                    "old_value": "push_current_task",
                    "new_value": "diagnose_prerequisite_first",
                    "reason": "自由校正要求 Aurora 先定位前置能力缺口，再继续建议",
                    "confidence": 0.78,
                },
                {
                    "state_key": "task_adjustment",
                    "old_value": "continue_original_card",
                    "new_value": "create_prerequisite_micro_task",
                    "reason": "当前任务需要降级成可开始的前置练习卡",
                    "confidence": 0.76,
                },
            ]
            for patch in blocker_patches:
                if any(p["state_key"] == patch["state_key"] and p["new_value"] == patch["new_value"] for p in patches):
                    continue
                patches.append(patch)
        if not patches:
            patches.append(
                {
                    "state_key": "core_session_scope",
                    "old_value": "unconfirmed",
                    "new_value": session.scope,
                    "reason": "Aurora Core Session 完成了显式校准",
                    "confidence": 0.6,
                }
            )
        return patches

    def _derive_next_changes(
        self,
        session: AuroraCoreSession,
        *,
        changes: list[str],
        state_patches: list[dict[str, Any]],
    ) -> list[str]:
        if changes:
            next_steps = [f"接下来的计划会{change}" for change in changes[:3]]
        else:
            next_steps = []
        if any(p.get("new_value") == "skill_gap" for p in state_patches):
            next_steps.extend(
                [
                    "下一张任务卡会先定位不会做的前置点，而不是催你挤时间",
                    "Aurora 以后遇到相似卡顿会先问能力缺口，再判断时间安排",
                ]
            )
        if next_steps:
            deduped: list[str] = []
            for step in next_steps:
                if step not in deduped:
                    deduped.append(step)
            return deduped[:4]
        if any(p.get("state_key") == "aurora_assumption" for p in state_patches):
            return ["后续回复会降低刚才那类推断的权重", "需要确认时会优先问你，而不是直接下判断"]
        return [f"后续会按「{session.scope}」重新判断任务节奏", "状态带会继续观察这个校准是否有效"]

    def _interpret_freeform_corrections(self, session: AuroraCoreSession) -> dict[str, Any]:
        """Extract durable intent from short freeform corrections without requiring an LLM."""
        freeform_texts = [
            msg.content.strip()
            for msg in session.messages
            if msg.role == "user" and (msg.is_freeform or msg.semantic_value == "freeform_correction")
        ]
        if not freeform_texts:
            return {}
        joined = "。".join(freeform_texts)
        skill_gap_markers = (
            "不会",
            "不懂",
            "没学会",
            "看不懂",
            "完全不会做",
            "不知道怎么",
            "基础不行",
            "前置",
            "知识点",
        )
        not_time_markers = ("不是没时间", "不是时间", "不是太忙", "不是拖延", "不是懒")
        has_skill_gap = any(marker in joined for marker in skill_gap_markers)
        contrasts_time = any(marker in joined for marker in not_time_markers)
        if has_skill_gap:
            return {
                "blocker_type": "skill_gap",
                "reason": ("用户自由校正说问题是不会做" + ("，并明确排除了时间不足" if contrasts_time else "")),
                "raw_text": joined[:240],
            }
        return {"raw_text": joined[:240]}

    # ── Scope inference ────────────────────────────────────────────

    def _infer_scope(self, band_status: str, wake_reasons: list[str]) -> str:
        if "task_time_overrun" in wake_reasons:
            return "今晚任务颗粒度与后续两天策略"
        if "repeated_mistake_cluster" in wake_reasons:
            return "当前错题集中的题型与讲法策略"
        if "plan_drift" in wake_reasons:
            return "当前计划与目标之间的对齐程度"
        if "user_distress" in wake_reasons:
            return "当前状态与接下来最应该做的事"
        if band_status == "needs_confirm":
            return "Aurora 当前几个待确认的判断"
        return "当前策略与你的实际情况"
