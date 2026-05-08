"""
Core: execution
Phase: clarify→adapt
Stage: P2-5 Full Aurora Core Session v1

L3 Aurora Core Session — high-cost, limited-quota, explicit calibration.

Lifecycle:
  AuroraWakeRequest → AuroraWakeEligibility → AuroraCaseFile → AuroraCoreSession
  → (multi-turn agenda) → SessionClosure → PolicyDecision / Directives

Per D6 ruling: backend maintains session state, frontend drives presentation.
L3 uses dedicated session prompt, not reusing normal chat prompt.
All writes go through Spine — Aurora Core never writes directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import AuroraAgenda, AuroraAgendaItem, _uid

# ── AuroraCoreSessionEntryReason ───────────────────────────────────

_TRIGGER_SOURCE_LABELS: dict[str, str] = {
    "status_bar": "状态带提示",
    "status_bar_correction_chip": "状态带纠错",
    "chat_correction_chip": "聊天里的纠错反馈",
    "checkpoint_card": "阶段检查提醒",
    "task_stuck_prompt": "任务卡点提示",
    "user_initiated": "你主动打开的校准入口",
}

_WAKE_REASON_LABELS: dict[str, str] = {
    "task_time_overrun": "最近的任务用时明显超过预估",
    "repeated_mistake_cluster": "同一类错误重复出现",
    "state_conflict": "你的实际推进和我之前的判断不一致",
    "self_model_confidence_drop": "我对当前判断的置信度下降",
    "plan_drift": "当前计划开始偏离原来的目标",
    "user_distress": "你最近的状态压力偏高",
    "standard_layer_uncertainty": "普通对话层不足以稳妥处理这个判断",
    "checkpoint_due": "现在到了适合复盘进度的检查点",
    "task_stuck": "当前任务出现了明确卡点",
}


@dataclass
class AuroraCoreSessionEntryReason:
    """Standardized entry protocol for any Aurora Core Session trigger."""

    trigger_source: str
    observed_signals: list[str] = field(default_factory=list)
    suggested_agenda_preview: list[str] = field(default_factory=list)
    why_now: str = ""
    estimated_minutes: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AuroraCoreSessionEntryReason | None:
        if not data:
            return None
        return cls(
            trigger_source=str(data.get("trigger_source") or "user_initiated"),
            observed_signals=[str(item).strip() for item in data.get("observed_signals", []) if str(item).strip()][:5],
            suggested_agenda_preview=[
                str(item).strip() for item in data.get("suggested_agenda_preview", []) if str(item).strip()
            ][:5],
            why_now=str(data.get("why_now") or "").strip(),
            estimated_minutes=max(1, min(10, int(data.get("estimated_minutes") or 3))),
        )

    @classmethod
    def from_context(
        cls,
        *,
        trigger_source: str,
        wake_reason: str = "",
        wake_reasons: list[str] | None = None,
        active_states: list[dict[str, Any]] | None = None,
        current_plan_summary: str = "",
    ) -> AuroraCoreSessionEntryReason:
        raw_reasons = [wake_reason, *(wake_reasons or [])]
        observed = [_WAKE_REASON_LABELS.get(reason, reason.replace("_", " ")) for reason in raw_reasons if reason]
        for state in active_states or []:
            key = str(state.get("state_key") or "").strip()
            value = str(state.get("value") or "").strip()
            if key and value:
                observed.append(f"{key} 现在显示为 {value}")
        if not observed and current_plan_summary:
            observed.append(current_plan_summary)
        why_now = _TRIGGER_SOURCE_LABELS.get(trigger_source, trigger_source.replace("_", " "))
        if observed:
            why_now = f"{why_now}里出现了需要当场校准的信号"
        return cls(
            trigger_source=trigger_source,
            observed_signals=observed[:5],
            suggested_agenda_preview=["先确认我看到的信号", "再校准接下来的策略"],
            why_now=why_now,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_source": self.trigger_source,
            "observed_signals": self.observed_signals,
            "suggested_agenda_preview": self.suggested_agenda_preview,
            "why_now": self.why_now,
            "estimated_minutes": self.estimated_minutes,
        }

    def opening_message(self) -> str:
        observed = "、".join(self.observed_signals[:3]) if self.observed_signals else "这里有一个判断需要重新确认"
        why_now = (self.why_now or "现在校准一下，后面的推进会更贴近你的真实情况").rstrip("。！？.!?")
        return (
            f"我注意到你最近{observed}。"
            f"现在聊这个是因为{why_now}。"
            f"这大概需要 {self.estimated_minutes} 分钟，你也可以随时暂停或跳过。"
        )


# ── AuroraCaseFile ──────────────────────────────────────────────────


@dataclass
class AuroraCaseFile:
    """Evidence package assembled before Aurora Core Session starts."""

    case_file_id: str
    user_id: str
    goal_summary: str
    current_plan_summary: str
    recent_task_events: list[dict[str, Any]] = field(default_factory=list)
    recent_failures: list[dict[str, Any]] = field(default_factory=list)
    recent_user_corrections: list[dict[str, Any]] = field(default_factory=list)
    active_hypotheses: list[str] = field(default_factory=list)
    conflicts_to_resolve: list[str] = field(default_factory=list)
    source_summary: list[dict[str, Any]] = field(default_factory=list)
    relationship_notes: list[str] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    wake_reason: str = ""
    entry_reason: AuroraCoreSessionEntryReason | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_file_id": self.case_file_id,
            "user_id": self.user_id,
            "goal_summary": self.goal_summary,
            "current_plan_summary": self.current_plan_summary,
            "recent_task_events": self.recent_task_events,
            "recent_failures": self.recent_failures,
            "recent_user_corrections": self.recent_user_corrections,
            "active_hypotheses": self.active_hypotheses,
            "conflicts_to_resolve": self.conflicts_to_resolve,
            "source_summary": self.source_summary,
            "relationship_notes": self.relationship_notes,
            "suggested_questions": self.suggested_questions,
            "wake_reason": self.wake_reason,
            "entry_reason": self.entry_reason.to_dict() if self.entry_reason else None,
            "created_at": self.created_at,
        }


# ── SessionClosure ──────────────────────────────────────────────────


@dataclass
class StatePatch:
    """A single state change from Aurora calibration."""

    state_key: str
    old_value: str
    new_value: str
    reason: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_key": self.state_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class PolicyChange:
    """A policy strategy change from Aurora calibration."""

    signal_state_key: str
    old_strategy: str
    new_strategy: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_state_key": self.signal_state_key,
            "old_strategy": self.old_strategy,
            "new_strategy": self.new_strategy,
            "reason": self.reason,
        }


@dataclass
class SessionClosure:
    """Output of a completed Aurora Core Session."""

    session_id: str
    state_patches: list[StatePatch] = field(default_factory=list)
    policy_changes: list[PolicyChange] = field(default_factory=list)
    directives_to_regenerate: list[str] = field(default_factory=list)
    next_changes: list[str] = field(default_factory=list)
    user_visible_summary: str = ""
    aurora_returns_to_background: bool = True
    model_write_candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state_patches": [p.to_dict() for p in self.state_patches],
            "policy_changes": [p.to_dict() for p in self.policy_changes],
            "directives_to_regenerate": self.directives_to_regenerate,
            "next_changes": self.next_changes,
            "user_visible_summary": self.user_visible_summary,
            "aurora_returns_to_background": self.aurora_returns_to_background,
            "model_write_candidates": self.model_write_candidates,
        }


# ── PredictedReplyOption ────────────────────────────────────────────


@dataclass
class PredictedReplyOption:
    """A predicted reply option for an agenda item. Always includes free-text."""

    option_id: str
    label: str
    expected_effect: str = ""  # what happens if user picks this
    is_free_text: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "expected_effect": self.expected_effect,
            "is_free_text": self.is_free_text,
        }


# ── AuroraCoreSession ───────────────────────────────────────────────

_SESSION_KEY = "spine:aurora_session:{session_id}"
_ACTIVE_SESSION_KEY = "spine:aurora_session_active:{user_id}"
_SESSION_TTL = 24 * 3600  # 24h

# Session lifecycle transitions — only these transitions are valid
_SESSION_TRANSITIONS: dict[str, set[str]] = {
    "active": {"paused", "completed"},
    "paused": {"active", "completed", "abandoned"},
    "completed": {"reflected"},
    "reflected": set(),
    "abandoned": set(),
}


class AuroraCoreSessionService:
    """Manage L3 Aurora Core Sessions.

    Per ruling: Aurora Core never writes directly. All state changes go
    through SessionClosure → SpineOrchestrator for proper audit.
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    def build_case_file(
        self,
        user_id: str,
        *,
        goal_summary: str,
        current_plan_summary: str,
        wake_reason: str,
        entry_reason: AuroraCoreSessionEntryReason | dict[str, Any] | None = None,
        trigger_source: str = "user_initiated",
        active_states: list[dict[str, Any]] | None = None,
        recent_outcomes: list[dict[str, Any]] | None = None,
        recent_corrections: list[dict[str, Any]] | None = None,
        wake_reasons: list[str] | None = None,
    ) -> AuroraCaseFile:
        """Build a case file from current context."""
        active_states = active_states or []
        recent_outcomes = recent_outcomes or []
        recent_corrections = recent_corrections or []
        if isinstance(entry_reason, AuroraCoreSessionEntryReason):
            normalized_entry_reason = entry_reason
        else:
            normalized_entry_reason = AuroraCoreSessionEntryReason.from_dict(entry_reason)
        if normalized_entry_reason is None:
            normalized_entry_reason = AuroraCoreSessionEntryReason.from_context(
                trigger_source=trigger_source,
                wake_reason=wake_reason,
                wake_reasons=wake_reasons,
                active_states=active_states,
                current_plan_summary=current_plan_summary,
            )

        hypotheses: list[str] = []
        conflicts: list[str] = []

        for state in active_states:
            key = state.get("state_key", "")
            value = state.get("value", "")
            if key == "task_granularity_fit":
                hypotheses.append(f"任务颗粒度判断为 {value}")
            elif key == "knowledge_bottleneck":
                hypotheses.append(f"知识瓶颈: {value}")
            elif key == "affective_pressure":
                hypotheses.append(f"压力水平: {value}")

        # Detect conflicts: opposing signals
        state_map = {s.get("state_key"): s.get("value") for s in active_states}
        if state_map.get("task_granularity_fit") == "too_large" and state_map.get("knowledge_bottleneck"):
            conflicts.append("任务可能不是太大，而是用户不会做")

        failures = [
            {"outcome": o.get("attribution", ""), "strategy": o.get("strategy", "")}
            for o in recent_outcomes
            if o.get("attribution") == "insufficient"
        ][-5:]

        return AuroraCaseFile(
            case_file_id=_uid("acf"),
            user_id=user_id,
            goal_summary=goal_summary,
            current_plan_summary=current_plan_summary,
            recent_failures=failures,
            recent_user_corrections=recent_corrections[-5:],
            active_hypotheses=hypotheses,
            conflicts_to_resolve=conflicts,
            wake_reason=wake_reason,
            entry_reason=normalized_entry_reason,
        )

    def build_agenda_from_case_file(
        self,
        case_file: AuroraCaseFile,
        session_type: str = "strategy_recalibration",
    ) -> AuroraAgenda:
        """Generate an AuroraAgenda from a case file."""
        items: list[AuroraAgendaItem] = []

        # Item 1: Enter session
        items.append(
            AuroraAgendaItem(
                item_id=_uid("ai"),
                item_type="enter_session",
                status="pending",
                payload={
                    "message": (
                        case_file.entry_reason.opening_message()
                        if case_file.entry_reason
                        else (
                            "我需要重新校准一个判断。"
                            if case_file.conflicts_to_resolve
                            else "我想跟你确认一下当前的方向。"
                        )
                    ),
                    "entry_reason": case_file.entry_reason.to_dict() if case_file.entry_reason else None,
                },
            )
        )

        # Item 2: Explain conflict
        if case_file.conflicts_to_resolve:
            conflict_text = case_file.conflicts_to_resolve[0]
            items.append(
                AuroraAgendaItem(
                    item_id=_uid("ai"),
                    item_type="explain_conflict",
                    status="pending",
                    payload={
                        "message": f"我之前{case_file.active_hypotheses[0] if case_file.active_hypotheses else '做了一个判断'}，但你的反馈说明可能是{conflict_text}。",
                    },
                )
            )

        # Item 3: Ask confirmation
        items.append(
            AuroraAgendaItem(
                item_id=_uid("ai"),
                item_type="ask_confirmation",
                status="pending",
                payload={
                    "question": "更接近哪一种？",
                    "options": [
                        PredictedReplyOption(_uid("opt"), "确实任务太大", "保持缩短任务策略").to_dict(),
                        PredictedReplyOption(
                            _uid("opt"), "不是任务大，是我不会", "切换到 worked_example 策略"
                        ).to_dict(),
                        PredictedReplyOption(_uid("opt"), "只是这几天忙", "临时调整，不改变长期策略").to_dict(),
                        PredictedReplyOption(
                            _uid("opt"), "都不对，我解释一下", "等待用户自由输入", is_free_text=True
                        ).to_dict(),
                    ],
                },
            )
        )

        # Item 4: Apply update
        items.append(
            AuroraAgendaItem(
                item_id=_uid("ai"),
                item_type="apply_update",
                status="pending",
                payload={"expected_state_patch": {}},
            )
        )

        # Item 5: Close session
        items.append(
            AuroraAgendaItem(
                item_id=_uid("ai"),
                item_type="close_session",
                status="pending",
                payload={
                    "message": "好的，我更新了判断。接下来的任务会按新的理解来安排。",
                },
            )
        )

        scope_desc = case_file.conflicts_to_resolve[0] if case_file.conflicts_to_resolve else case_file.wake_reason

        return AuroraAgenda(
            session_id=_uid("acs"),
            scope=scope_desc,
            agenda_items=items,
            interruption_policy="answer_then_resume",
            status="active",
        )

    def build_reply_options(self, context: str) -> list[PredictedReplyOption]:
        """Build predicted reply options for a given context. Always includes free-text."""
        options = [
            PredictedReplyOption(_uid("opt"), context, expected_effect="confirmed"),
            PredictedReplyOption(_uid("opt"), "不完全对", expected_effect="partial_correction"),
            PredictedReplyOption(_uid("opt"), "都不对，我解释一下", expected_effect="free_input", is_free_text=True),
        ]
        return options

    async def create_session(
        self,
        user_id: str,
        case_file: AuroraCaseFile,
        agenda: AuroraAgenda,
    ) -> dict[str, Any]:
        """Persist and activate an Aurora Core Session."""
        session_data = {
            "session_id": agenda.session_id,
            "user_id": user_id,
            "case_file": case_file.to_dict(),
            "agenda": agenda.to_dict(),
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
        }

        key = _SESSION_KEY.format(session_id=agenda.session_id)
        await self.redis.set(key, json.dumps(session_data), ex=_SESSION_TTL)

        active_key = _ACTIVE_SESSION_KEY.format(user_id=user_id)
        await self.redis.set(active_key, agenda.session_id, ex=_SESSION_TTL)

        try:
            from app.signals.agenda_queue import AgendaQueueService
            await AgendaQueueService(self.redis).save_agenda(user_id, agenda)
        except Exception:
            pass

        logger.info(
            "AuroraCoreSession: created session={} user={} type={}",
            agenda.session_id,
            user_id,
            case_file.wake_reason,
        )
        return session_data

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Load a session by ID."""
        try:
            raw = await self.redis.get(_SESSION_KEY.format(session_id=session_id))
        except Exception:
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def get_active_session(self, user_id: str) -> dict[str, Any] | None:
        """Get the active Aurora session for a user."""
        session_id = await self.redis.get(_ACTIVE_SESSION_KEY.format(user_id=user_id))
        if not session_id:
            return None
        return await self.get_session(session_id)

    async def record_reply(
        self,
        session_id: str,
        item_index: int,
        reply: str,
    ) -> dict[str, Any] | None:
        """Record a user reply to an agenda item."""
        session = await self.get_session(session_id)
        if not session:
            return None

        agenda_data = session["agenda"]
        items = agenda_data["agenda_items"]
        if item_index >= len(items):
            return None

        items[item_index]["status"] = "done"
        items[item_index]["payload"]["user_reply"] = reply

        # Advance next item to pending if exists
        if item_index + 1 < len(items) and items[item_index + 1]["status"] == "pending":
            items[item_index + 1]["status"] = "waiting_user"

        await self.redis.set(
            _SESSION_KEY.format(session_id=session_id),
            json.dumps(session),
            ex=_SESSION_TTL,
        )
        return session

    async def close_session(
        self,
        session_id: str,
        closure: SessionClosure,
    ) -> dict[str, Any]:
        """Close a session and store its closure output."""
        session = await self.get_session(session_id)
        if not session:
            return {"error": "session_not_found"}

        session["status"] = "completed"
        session["closure"] = closure.to_dict()
        session["completed_at"] = datetime.now(UTC).isoformat()

        # Update agenda status
        for item in session["agenda"]["agenda_items"]:
            if item["status"] in ("pending", "waiting_user"):
                item["status"] = "done"

        await self.redis.set(
            _SESSION_KEY.format(session_id=session_id),
            json.dumps(session),
            ex=_SESSION_TTL,
        )

        # Clear active session pointer
        user_id = session.get("user_id", "")
        if user_id:
            await self.redis.delete(_ACTIVE_SESSION_KEY.format(user_id=user_id))

        logger.info(
            "AuroraCoreSession: closed session={} patches={} policy_changes={}",
            session_id,
            len(closure.state_patches),
            len(closure.policy_changes),
        )
        return session

    async def transition_session(
        self,
        session_id: str,
        new_status: str,
    ) -> dict[str, Any] | None:
        """Transition session to a new status, validating the transition."""
        try:
            session = await self.get_session(session_id)
        except Exception:
            return None
        if not session:
            return None

        current = session.get("status", "active")
        valid_next = _SESSION_TRANSITIONS.get(current, set())
        if new_status not in valid_next:
            logger.warning(
                "AuroraCoreSession: invalid transition {} → {} for session={}",
                current,
                new_status,
                session_id,
            )
            return None

        session["status"] = new_status
        session["updated_at"] = datetime.now(UTC).isoformat()

        if new_status in ("completed", "abandoned"):
            session[new_status + "_at"] = datetime.now(UTC).isoformat()

        try:
            await self.redis.set(
                _SESSION_KEY.format(session_id=session_id),
                json.dumps(session),
                ex=_SESSION_TTL,
            )
        except Exception:
            logger.warning("AuroraCoreSession: transition persist failed", exc_info=True)
            return None

        # Clear active pointer for terminal states
        if new_status in ("completed", "abandoned"):
            user_id = session.get("user_id", "")
            if user_id:
                try:
                    await self.redis.delete(_ACTIVE_SESSION_KEY.format(user_id=user_id))
                except Exception:
                    logger.debug("AuroraCoreSession: failed to clear active session key for user={}", user_id)

        logger.info(
            "AuroraCoreSession: transitioned session={} {} → {}",
            session_id,
            current,
            new_status,
        )
        return session

    async def pause_session(
        self,
        session_id: str,
        reason: str = "user_request",
    ) -> dict[str, Any] | None:
        """Pause an active session."""
        session = await self.transition_session(session_id, "paused")
        if session:
            session["pause_reason"] = reason
            session["paused_at"] = datetime.now(UTC).isoformat()
            await self.redis.set(
                _SESSION_KEY.format(session_id=session_id),
                json.dumps(session),
                ex=_SESSION_TTL,
            )
        return session

    async def resume_session(self, session_id: str) -> dict[str, Any] | None:
        """Resume a paused session."""
        session = await self.transition_session(session_id, "active")
        if session:
            session.pop("pause_reason", None)
            session.pop("paused_at", None)
            await self.redis.set(
                _SESSION_KEY.format(session_id=session_id),
                json.dumps(session),
                ex=_SESSION_TTL,
            )
        return session

    def get_reply_count(self, session: dict[str, Any]) -> int:
        """Count how many agenda items have been completed."""
        return sum(1 for item in session.get("agenda", {}).get("agenda_items", []) if item.get("status") == "done")
