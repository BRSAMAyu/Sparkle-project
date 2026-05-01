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

import inspect
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

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

SessionStatus = Literal["active", "completed", "abandoned", "expired"]

SESSION_KEY_PREFIX = "aurora:core_session:"
SESSION_TTL_SECONDS = 30 * 60       # 30 min max lifetime
IDLE_TTL_SECONDS = 10 * 60         # 10 min idle kills session
MAX_USER_TURNS = 6
MAX_AURORA_MESSAGES = 12


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class AuroraCoreMessage:
    """A single message in the Aurora Core session."""
    role: Literal["aurora", "user"]
    content: str
    stage: SessionStage
    timestamp: str = field(default_factory=lambda: _utcnow().isoformat())
    option_id: str | None = None       # chip selected (if role=user)
    semantic_value: str | None = None  # semantic value of selection
    is_freeform: bool = False          # user typed free text

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
    scope_completed: str = ""
    strategy_changes: list[str] = field(default_factory=list)
    session_id: str = ""
    completed_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "updates_applied": self.updates_applied,
            "summary": self.summary,
            "scope_completed": self.scope_completed,
            "strategy_changes": self.strategy_changes,
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
    scope: str                     # declared calibration scope (1 sentence)
    session_type: str              # strategy_recalibration | quick_calibration | user_initiated
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
        messages = [
            AuroraCoreMessage(**m) for m in data.get("messages", [])
        ]
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
            messages=messages,
            calibration_result=result,
            user_turn_count=data.get("user_turn_count", 0),
            aurora_message_count=data.get("aurora_message_count", 0),
            pending_option_groups=data.get("pending_option_groups", []),
            created_at=data.get("created_at", _utcnow().isoformat()),
            last_activity_at=data.get("last_activity_at", _utcnow().isoformat()),
            expires_at=data.get("expires_at", (_utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()),
        )


class AuroraCoreSessionStore:
    """Redis-backed store for AuroraCoreSession objects."""

    def __init__(self, redis) -> None:
        self.redis = redis

    def _session_key(self, session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"

    def _user_active_key(self, user_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}active:{user_id}"

    async def save(self, session: AuroraCoreSession) -> None:
        if self.redis is None:
            return
        key = self._session_key(session.session_id)
        payload = json.dumps(session.to_dict(), ensure_ascii=False)
        await self._call("setex", key, SESSION_TTL_SECONDS, payload)
        if session.status == "active":
            await self._call("setex", self._user_active_key(session.user_id), SESSION_TTL_SECONDS, session.session_id)
        else:
            await self._call("delete", self._user_active_key(session.user_id))

    async def load(self, session_id: str) -> AuroraCoreSession | None:
        if self.redis is None:
            return None
        raw = await self._call("get", self._session_key(session_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return AuroraCoreSession.from_dict(json.loads(raw))
        except Exception:
            return None

    async def load_active(self, user_id: str) -> AuroraCoreSession | None:
        if self.redis is None:
            return None
        raw_id = await self._call("get", self._user_active_key(user_id))
        if not raw_id:
            return None
        if isinstance(raw_id, bytes):
            raw_id = raw_id.decode("utf-8")
        session = await self.load(raw_id.strip())
        if session is None or session.status != "active":
            return None
        if session.is_expired or session.is_idle_expired:
            session.status = "expired"
            await self.save(session)
            return None
        return session

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
        self.store = AuroraCoreSessionStore(redis)
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
    ) -> AuroraCoreSession:
        """Create a new L3 session and inject opening Aurora messages."""
        # Check for existing active session
        existing = await self.store.load_active(user_id)
        if existing is not None:
            return existing

        session_id = str(uuid.uuid4())
        resolved_scope = scope or self._infer_scope(band_status, wake_reasons or [])

        session = AuroraCoreSession(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            surface=surface,
            status="active",
            stage="declare",
            scope=resolved_scope,
            session_type=session_type,
        )

        # Inject opening message sequence
        self._inject_opening_sequence(session, wake_reasons=wake_reasons or [])
        await self.store.save(session)
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
        if session.status != "active":
            raise ValueError(f"Session is {session.status}, not active")
        if session.is_expired or session.is_idle_expired:
            session.status = "expired"
            await self.store.save(session)
            raise ValueError("Session has expired")

        # Record user turn
        session.add_user_message(
            content,
            option_id=option_id,
            semantic_value=semantic_value,
            is_freeform=is_freeform,
        )

        # Apply model write effect if present
        if model_write_effect:
            self._apply_write_effect(session, model_write_effect)

        # Advance session based on current stage and response
        self._advance_session(session, semantic_value=semantic_value, is_freeform=is_freeform)

        await self.store.save(session)
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

        self._finalize_session(session, abandoned=True)
        await self.store.save(session)
        return session

    async def get_active_session(self, user_id: str) -> AuroraCoreSession | None:
        return await self.store.load_active(user_id)

    async def get_session(self, session_id: str) -> AuroraCoreSession | None:
        return await self.store.load(session_id)

    # ── Session flow ───────────────────────────────────────────────

    def _inject_opening_sequence(
        self,
        session: AuroraCoreSession,
        *,
        wake_reasons: list[str],
    ) -> None:
        """Inject Aurora's ritualized opening messages."""
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
    ) -> None:
        """Decide next Aurora messages after a user response."""
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

        session.calibration_result = CalibrationResult(
            updates_applied=applied_effects,
            summary=self._build_result_summary(session, abandoned=abandoned),
            scope_completed=session.scope,
            strategy_changes=changes,
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
            return "好。还有一件事我想确认：这个情况是最近才开始的，还是已经持续一段时间了？", [
                self._duration_group()
            ]
        return None, []

    def _build_exit_message(self, session: AuroraCoreSession) -> str:
        changes = self._derive_strategy_changes(session)
        if not changes:
            return "这次校准完成。我更新了当前的判断，Aurora 先退回后台。"
        changes_text = "；".join(changes[:3])
        return f"这次校准完成。我更新了三件事：{changes_text}。\nAurora 先退回后台。"

    def _build_result_summary(self, session: AuroraCoreSession, *, abandoned: bool) -> str:
        if abandoned:
            return f"用户在 {session.user_turn_count} 轮后退出了校准。已记录到目前收集的信息。"
        return f"Aurora Core Session 完成，共 {session.user_turn_count} 轮，范围：{session.scope}"

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
        seen_semantics = {
            msg.semantic_value
            for msg in session.messages
            if msg.role == "user" and msg.semantic_value
        }
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
        return changes

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
