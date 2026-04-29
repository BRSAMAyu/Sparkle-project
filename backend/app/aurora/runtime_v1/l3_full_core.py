"""
Core: execution
Phase: clarify→adapt
Stage: T3.1.4 L3 Full Aurora Core — interactive modeling sessions.

L3 is the "cognitive calibration event" — high-cost, limited-quota,
interactive modeling where Aurora explains hypotheses, shows evidence,
asks key questions, receives corrections, and outputs new strategy.

Not normal chat. User experience is a structured calibration event.

Lifecycle: active → paused → completed → reflected
Entry: 8 wake conditions (model conflict, user rejection, strategy failure, etc.)
Exit: SessionClosure with state_patches, policy_changes, directives_to_regenerate
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.signals.aurora_core_session import (
    AuroraCoreSessionService,
    PredictedReplyOption,
    SessionClosure,
    StatePatch,
    PolicyChange,
)
from app.signals.types import _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── Session lifecycle ──────────────────────────────────────────────

SESSION_LIFECYCLE: dict[str, set[str]] = {
    "active":    {"paused", "completed"},
    "paused":    {"active", "completed", "abandoned"},
    "completed": {"reflected"},
    "reflected": set(),
    "abandoned": set(),
}

IDLE_TIMEOUT_SEC = 600        # 10 min idle → auto-pause
MAX_AGENDA_TURNS = 12         # max replies before forced close
SESSION_MAX_AGE_SEC = 86400   # 24h max session age


# ── Wake condition definitions ─────────────────────────────────────

_WAKE_CONDITIONS: list[dict[str, Any]] = [
    {
        "key": "deadline_high_risk",
        "session_type": "exam_emergency",
        "duration_sec": 300,
        "description": "deadline 高风险，紧急校准",
    },
    {
        "key": "model_conflict",
        "session_type": "conflict_resolution",
        "duration_sec": 180,
        "description": "系统发现关键模型冲突",
    },
    {
        "key": "consecutive_user_rejections",
        "session_type": "belief_revision",
        "duration_sec": 240,
        "description": "用户连续否定系统判断",
    },
    {
        "key": "consecutive_strategy_failures",
        "session_type": "strategy_recalibration",
        "duration_sec": 240,
        "description": "策略连续失效",
    },
    {
        "key": "goal_changed",
        "session_type": "goal_realignment",
        "duration_sec": 300,
        "description": "目标发生变化",
    },
    {
        "key": "self_model_confidence_dropped",
        "session_type": "self_model_recalibration",
        "duration_sec": 240,
        "description": "SparkleSelfModel 置信度下降",
    },
    {
        "key": "user_explicit_wake",
        "session_type": "deep_review",
        "duration_sec": 300,
        "description": "用户主动唤醒",
    },
    {
        "key": "momentum_stalled",
        "session_type": "motivation_check",
        "duration_sec": 240,
        "description": "成就动量停滞",
    },
]


# ── L3FullCoreEngine ────────────────────────────────────────────────

class L3FullCoreEngine:
    """L3 Aurora Core — orchestrates interactive modeling sessions.

    Responsibilities:
    - Validate session entry conditions (8 wake triggers)
    - Execute agenda items in sequence with state machine
    - Handle user interruptions (answer_then_resume / defer)
    - Enforce session constraints (timeout, max turns)
    - Produce SessionClosure with state_patches + policy_changes
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.session_service = AuroraCoreSessionService(redis_client)

    # ── Entry validation ────────────────────────────────────────────

    def validate_entry(
        self,
        *,
        wake_reasons: list[str],
        can_wake: bool = True,
        quota_remaining: int = 0,
        cooldown_status: str = "available",
    ) -> dict[str, Any]:
        """Validate L3 session entry conditions.

        Returns dict with:
            allowed: bool
            session_type: str (matched type or empty)
            duration_sec: int
            reason: str (why allowed or denied)
            matched_condition: str | None
        """
        if not can_wake:
            return {
                "allowed": False,
                "session_type": "",
                "duration_sec": 0,
                "reason": "Aurora wake not allowed",
                "matched_condition": None,
            }

        if quota_remaining <= 0:
            return {
                "allowed": False,
                "session_type": "",
                "duration_sec": 0,
                "reason": "Daily quota exhausted",
                "matched_condition": None,
            }

        if cooldown_status in ("cooling", "cooling_down"):
            return {
                "allowed": False,
                "session_type": "",
                "duration_sec": 0,
                "reason": "Cooldown period active",
                "matched_condition": None,
            }

        if not wake_reasons:
            return {
                "allowed": False,
                "session_type": "",
                "duration_sec": 0,
                "reason": "No wake reasons provided",
                "matched_condition": None,
            }

        # Match first condition by priority
        for cond in _WAKE_CONDITIONS:
            if cond["key"] in wake_reasons:
                return {
                    "allowed": True,
                    "session_type": cond["session_type"],
                    "duration_sec": cond["duration_sec"],
                    "reason": cond["description"],
                    "matched_condition": cond["key"],
                }

        # Custom/unknown wake reason — allow with defaults
        return {
            "allowed": True,
            "session_type": "strategy_recalibration",
            "duration_sec": 240,
            "reason": wake_reasons[0],
            "matched_condition": wake_reasons[0],
        }

    # ── Agenda execution ────────────────────────────────────────────

    async def execute_agenda_step(
        self,
        session_id: str,
        item_index: int,
        reply: str,
    ) -> dict[str, Any] | None:
        """Execute a single agenda step: record reply, advance, return next item.

        Returns dict with:
            session: the updated session dict
            next_item_index: int | None
            next_item: dict | None
            reply_options: list[PredictedReplyOption]
            session_should_close: bool
        """
        try:
            session = await self.session_service.get_session(session_id)
        except Exception:
            logger.warning("execute_agenda_step: get_session failed", exc_info=True)
            return None
        if not session:
            return None

        # Validate session is active
        status = session.get("status", "active")
        if status not in ("active", "paused"):
            return None

        agenda_items = session.get("agenda", {}).get("agenda_items", [])
        if item_index >= len(agenda_items):
            return None

        # Record reply
        try:
            updated = await self.session_service.record_reply(session_id, item_index, reply)
        except Exception:
            logger.warning("execute_agenda_step: record_reply failed", exc_info=True)
            return None
        if not updated:
            return None

        # Check if session should close (last item done or max turns)
        reply_count = sum(
            1 for item in updated.get("agenda", {}).get("agenda_items", [])
            if item.get("status") == "done"
        )

        next_index = item_index + 1
        items = updated.get("agenda", {}).get("agenda_items", [])

        # Check max turns
        if reply_count >= MAX_AGENDA_TURNS:
            return {
                "session": updated,
                "next_item_index": None,
                "next_item": None,
                "reply_options": [],
                "session_should_close": True,
                "close_reason": "max_turns_reached",
            }

        # Check if all items are done
        if next_index >= len(items):
            return {
                "session": updated,
                "next_item_index": None,
                "next_item": None,
                "reply_options": [],
                "session_should_close": True,
                "close_reason": "agenda_complete",
            }

        next_item = items[next_index]

        # Build reply options for next item
        options = self._build_reply_options_for_item(next_item)

        return {
            "session": updated,
            "next_item_index": next_index,
            "next_item": next_item,
            "reply_options": [o.to_dict() for o in options],
            "session_should_close": False,
            "close_reason": None,
        }

    # ── Session health checks ───────────────────────────────────────

    async def check_session_health(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Check session health: idle timeout, max turns, max age.

        Returns:
            healthy: bool
            action: "none" | "pause" | "force_close" | "abandon"
            reason: str
        """
        try:
            session = await self.session_service.get_session(session_id)
        except Exception:
            return {"healthy": False, "action": "none", "reason": "session_not_found"}
        if not session:
            return {"healthy": False, "action": "none", "reason": "session_not_found"}

        status = session.get("status", "active")
        if status in ("completed", "reflected", "abandoned"):
            return {"healthy": True, "action": "none", "reason": "session_terminated"}

        # Check max age
        created_at_str = session.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
            if (_utcnow() - created_at).total_seconds() > SESSION_MAX_AGE_SEC:
                return {
                    "healthy": False,
                    "action": "abandon",
                    "reason": "session_exceeded_max_age",
                }
        except (ValueError, TypeError):
            pass

        # Check max turns
        reply_count = sum(
            1 for item in session.get("agenda", {}).get("agenda_items", [])
            if item.get("status") == "done"
        )
        if reply_count >= MAX_AGENDA_TURNS:
            return {
                "healthy": False,
                "action": "force_close",
                "reason": "max_turns_reached",
            }

        # Check idle timeout (for active sessions only)
        if status == "active":
            last_activity = self._get_last_activity(session)
            if last_activity and (_utcnow() - last_activity).total_seconds() > IDLE_TIMEOUT_SEC:
                return {
                    "healthy": False,
                    "action": "pause",
                    "reason": "idle_timeout",
                }

        return {"healthy": True, "action": "none", "reason": "ok"}

    # ── Closure production ──────────────────────────────────────────

    def produce_closure(
        self,
        session: dict[str, Any],
        *,
        user_summary: str = "",
        additional_state_patches: list[StatePatch] | None = None,
    ) -> SessionClosure:
        """Produce a SessionClosure from a completed or force-closed session.

        Maps user replies from agenda items into state patches and policy changes.
        """
        patches: list[StatePatch] = list(additional_state_patches or [])
        policy_changes: list[PolicyChange] = []
        directives_to_regenerate: list[str] = ["ExecutionDirective", "ResponseDirective"]

        agenda_items = session.get("agenda", {}).get("agenda_items", [])

        for item in agenda_items:
            item_type = item.get("item_type", "")
            reply = item.get("payload", {}).get("user_reply", "")

            if not reply:
                continue

            # Map specific agenda item types to state patches
            if item_type == "confirm_available_time":
                patches.append(StatePatch(
                    state_key="task_granularity_fit",
                    old_value="too_large",
                    new_value=self._infer_granularity(reply),
                    reason=f"L3校准: 用户确认可用时间 → {reply}",
                    confidence=0.85,
                ))
            elif item_type == "confirm_hypothesis":
                # User confirmed or corrected a hypothesis
                patches.append(StatePatch(
                    state_key="knowledge_bottleneck",
                    old_value="assumed",
                    new_value=self._infer_knowledge_state(reply),
                    reason=f"L3校准: 假设确认 → {reply}",
                    confidence=0.80,
                ))
            elif item_type == "update_strategy":
                directives_to_regenerate.append("PlanDirective")
                policy_changes.append(PolicyChange(
                    signal_state_key="execution_consistency",
                    old_strategy="current",
                    new_strategy=self._infer_strategy(reply),
                    reason=f"L3校准: 策略更新 → {reply}",
                ))

        # Auto-generate summary if not provided
        if not user_summary:
            user_summary = self._build_auto_summary(patches, policy_changes)

        return SessionClosure(
            session_id=session.get("session_id", ""),
            state_patches=patches,
            policy_changes=policy_changes,
            directives_to_regenerate=list(set(directives_to_regenerate)),
            user_visible_summary=user_summary,
        )

    # ── Private helpers ─────────────────────────────────────────────

    def _build_reply_options_for_item(
        self,
        item: dict[str, Any],
    ) -> list[PredictedReplyOption]:
        """Build predicted reply options for an agenda item."""
        existing_options = item.get("payload", {}).get("options", [])
        if existing_options:
            return [
                PredictedReplyOption(
                    option_id=o.get("option_id", _uid("opt")),
                    label=o.get("label", ""),
                    expected_effect=o.get("expected_effect", ""),
                    is_free_text=o.get("is_free_text", False),
                )
                for o in existing_options
            ]

        # Default options: agree / partial / free text
        return [
            PredictedReplyOption(_uid("opt"), "是，确认", "confirmed"),
            PredictedReplyOption(_uid("opt"), "不完全对", "partial_correction"),
            PredictedReplyOption(_uid("opt"), "都不对，我解释一下", "free_input", is_free_text=True),
        ]

    def _get_last_activity(self, session: dict[str, Any]) -> datetime | None:
        """Extract last activity timestamp from session."""
        # Check agenda items for latest done item
        items = session.get("agenda", {}).get("agenda_items", [])
        latest: datetime | None = None

        try:
            created = datetime.fromisoformat(
                session.get("created_at", "").replace("Z", "+00:00")
            ).replace(tzinfo=None)
            latest = created
        except (ValueError, TypeError):
            pass

        return latest

    def _infer_granularity(self, reply: str) -> str:
        """Infer task granularity from user reply about available time."""
        reply_lower = reply.lower()
        if any(w in reply_lower for w in ("30", "半小时", "30分钟")):
            return "small_chunks"
        if any(w in reply_lower for w in ("45", "45分钟")):
            return "moderate"
        if any(w in reply_lower for w in ("60", "1小时")):
            return "standard"
        return "adjusted_by_user"

    def _infer_knowledge_state(self, reply: str) -> str:
        """Infer knowledge state from user's hypothesis confirmation reply."""
        reply_lower = reply.lower()
        if any(w in reply_lower for w in ("不会", "不理解", "没学过", "不懂")):
            return "knowledge_gap_confirmed"
        if any(w in reply_lower for w in ("会", "理解", "学过")):
            return "knowledge_confirmed"
        return "user_corrected"

    def _infer_strategy(self, reply: str) -> str:
        """Infer strategy change from user reply."""
        reply_lower = reply.lower()
        if any(w in reply_lower for w in ("例题", "worked example", "示范")):
            return "worked_example_first"
        if any(w in reply_lower for w in ("刷题", "练习", "做题")):
            return "retrieval_practice"
        if any(w in reply_lower for w in ("简单", "小任务", "easy")):
            return "small_wins"
        return "adaptive_replan"

    def _build_auto_summary(
        self,
        patches: list[StatePatch],
        changes: list[PolicyChange],
    ) -> str:
        """Build an auto-generated user-visible summary of what changed."""
        parts = ["这次校准完成。"]
        if patches:
            parts.append(f"更新了 {len(patches)} 个判断。")
        if changes:
            parts.append(f"调整了 {len(changes)} 个策略。")
        parts.append("Aurora 先退回后台。")
        return "".join(parts)
