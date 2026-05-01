from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout
from app.aurora.runtime_v1.decision_loop import AuroraDecisionLoop
from app.aurora.runtime_v1.models import AuroraScheduledWake, AuroraStateSnapshot
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.aurora.runtime_v1.state import merge_expression_settings
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter

AURORA_CHECKPOINT_SURFACE = "aurora_checkpoint"
RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60
FOLLOW_UP_DISABLED_ACTION = "proactive_follow_up"
NEGATIVE_MARKERS = (
    "落后",
    "没完成",
    "没做完",
    "跑偏",
    "没时间",
    "来不及",
    "没跟上",
    "没有完成",
    "卡住",
)
UNDERSTANDING_MARKERS = (
    "不懂",
    "没搞懂",
    "没搞定",
    "看不懂",
    "不会",
    "理解",
    "概念",
    "传输层",
    "公式",
    "题型",
)
TIME_PRESSURE_MARKERS = (
    "没时间",
    "来不及",
    "时间不够",
    "排不过来",
    "事情多",
    "太忙",
    "时间问题",
)
RESOLUTION_MARKERS = (
    "补上",
    "补完",
    "搞定",
    "解决",
    "完成",
    "弄完",
    "会了",
    "明白了",
    "搞明白",
    "顺了",
)
WORKING_MARKERS = (
    "在补",
    "补着",
    "正在补",
    "在看",
    "正在看",
    "在学",
    "正在学",
    "先补",
    "回去补",
    "继续补",
    "继续看",
    "刚开始",
    "刚在",
)
GENERIC_SEGMENTS = {
    "主要是",
    "就是",
    "然后",
    "现在",
    "感觉",
    "还是",
    "其实",
    "问题是",
}
LOW_URGENCY_FOLLOW_UP_THRESHOLD = 0.58
HIGH_URGENCY_FOLLOW_UP_THRESHOLD = 0.78


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _naive_utc(value).isoformat()


def _coerce_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return _naive_utc(value)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    return _naive_utc(parsed)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _redis_setex(redis: Any, key: str, ttl: int, value: Any) -> None:
    if redis is None:
        return
    if hasattr(redis, "setex"):
        await _maybe_await(redis.setex(key, ttl, value))
        return
    if hasattr(redis, "set"):
        try:
            await _maybe_await(redis.set(key, value, ex=ttl))
        except TypeError:
            await _maybe_await(redis.set(key, value, ttl=ttl))


@dataclass(slots=True)
class FollowUpTimingDecision:
    action: str
    reason: str
    next_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "next_at": _isoformat(self.next_at),
            "metadata": dict(self.metadata or {}),
        }


def build_aurora_surface_metadata(
    *,
    surface: str,
    surface_complete: bool,
    modeling_complete: bool = False,
) -> dict[str, Any]:
    return {
        "aurora_surface": surface,
        "aurora_runtime_enabled": True,
        "surface_complete": bool(surface_complete),
        "modeling_complete": bool(modeling_complete),
    }


class AuroraCheckpointRuntimeService:
    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        *,
        decision_loop: AuroraDecisionLoop | None = None,
        chat_adapter: ChatLayerAdapter | None = None,
        skill_registry: AuroraSkillRegistry | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.decision_loop = decision_loop or AuroraDecisionLoop()
        self.chat_adapter = chat_adapter or ChatLayerAdapter()
        self.skill_registry = skill_registry or AuroraSkillRegistry()

    async def finalize_checkpoint_debrief(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        conversation_id: str,
        plan_id: UUID | None,
        checkpoint_day: int,
        checkpoint_description: str,
        first_answer: str,
        second_answer: str,
        goal_met: bool,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current_time = _naive_utc(now) or _utcnow()
        plan = await self.db.get(Plan, plan_id) if plan_id else None
        next_task = await self._load_next_pending_task(user_id=user_id, plan_id=plan_id)
        aurora_prefs, timezone_name = await self._load_aurora_preferences(user_id)
        blocker = self._summarize_blocker(
            checkpoint_description=checkpoint_description,
            first_answer=first_answer,
            second_answer=second_answer,
            goal_met=goal_met,
            next_task_title=getattr(next_task, "title", None),
        )
        activity_profile = self._build_activity_profile(
            blocker=blocker,
            checkpoint_day=checkpoint_day,
            plan=plan,
            next_task=next_task,
            now=current_time,
        )
        metadata = build_aurora_surface_metadata(
            surface=AURORA_CHECKPOINT_SURFACE,
            surface_complete=True,
            modeling_complete=False,
        )
        metadata.update(
            {
                "conversation_id": conversation_id,
                "checkpoint_day": checkpoint_day,
                "goal_met": goal_met,
            }
        )

        snapshot = AuroraStateSnapshot(
            user_id=user_id,
            surface=AURORA_CHECKPOINT_SURFACE,
            conversation_id=conversation_id,
            snapshot_at=current_time,
            user_model_snapshot={
                "plan_name": plan.name if plan else None,
                "checkpoint_description": checkpoint_description,
                "first_answer": first_answer,
                "second_answer": second_answer,
                "blocker_summary": blocker["summary"],
                "next_task_title": getattr(next_task, "title", None),
            },
            informational_tensions=[
                {
                    "tension_id": f"{conversation_id}:checkpoint-gap",
                    "domain": activity_profile["agenda_priority"] or "checkpoint_gap",
                    "description": blocker["summary"],
                    "priority": blocker["urgency_score"],
                    "status": "resolved" if goal_met else "open",
                    "evidence": [first_answer, second_answer],
                    "created_at": current_time.isoformat(),
                    "last_attempted_at": current_time.isoformat(),
                }
            ],
            latent_threads=(
                []
                if goal_met
                else [
                    {
                        "thread_id": f"{conversation_id}:follow-up",
                        "source_intent": {
                            "intent_type": "schedule_follow_up",
                            "target_tension_id": f"{conversation_id}:checkpoint-gap",
                            "payload": {"summary": blocker["summary"]},
                        },
                        "tension_links": [f"{conversation_id}:checkpoint-gap"],
                        "salience": blocker["urgency_score"],
                        "context_snapshot": blocker["summary"],
                        "created_at": current_time.isoformat(),
                    }
                ]
            ),
            activity_profile=activity_profile,
            runtime_metadata=metadata,
        )
        self.db.add(snapshot)

        wake_result = await self._maybe_schedule_wake(
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
            blocker=blocker,
            activity_profile=activity_profile,
            metadata=metadata,
            aurora_prefs=aurora_prefs,
            timezone_name=timezone_name,
            next_task=next_task,
            now=current_time,
        )

        await self.db.flush()
        await self.db.commit()
        await self._write_runtime_state(
            user_id=user_id,
            conversation_id=conversation_id,
            session_id=session_id,
            checkpoint_description=checkpoint_description,
            blocker=blocker,
            activity_profile=activity_profile,
            wake_result=wake_result,
            metadata=metadata,
            now=current_time,
        )
        return {
            "snapshot_id": str(snapshot.id),
            "wake": wake_result,
            "activity_profile": activity_profile,
            "metadata": metadata,
        }

    async def process_due_wakes(self, *, now: datetime | None = None) -> dict[str, int]:
        current_time = _naive_utc(now) or _utcnow()
        result = await self.db.execute(
            select(AuroraScheduledWake)
            .where(
                AuroraScheduledWake.surface == AURORA_CHECKPOINT_SURFACE,
                AuroraScheduledWake.status == "pending",
                AuroraScheduledWake.scheduled_at <= current_time,
            )
            .order_by(
                AuroraScheduledWake.scheduled_at.asc(),
                AuroraScheduledWake.created_at.asc(),
            )
        )
        wakes = list(result.scalars().all())
        summary = {
            "due": len(wakes),
            "executed": 0,
            "suppressed": 0,
            "deferred": 0,
            "cancelled": 0,
            "errors": 0,
        }
        for wake in wakes:
            try:
                outcome = await self._process_single_wake(wake=wake, now=current_time)
                if outcome in summary:
                    summary[outcome] += 1
            except Exception as exc:
                summary["errors"] += 1
                logger.warning(f"Aurora checkpoint wake failed wake={wake.id}: {exc}")
        await self.db.commit()
        return summary

    async def _process_single_wake(self, *, wake: AuroraScheduledWake, now: datetime) -> str:
        aurora_prefs, timezone_name = await self._load_aurora_preferences(wake.user_id)
        payload = dict(wake.payload or {})
        hard_bounds = self._hard_bounds_from_preferences(aurora_prefs, timezone_name)
        follow_up_timing, recent_signals, follow_up_policy = await self._evaluate_due_follow_up_timing(
            wake=wake,
            now=now,
            hard_bounds=hard_bounds,
            timezone_name=timezone_name,
        )
        payload["recent_user_activity"] = recent_signals
        payload["follow_up_policy"] = follow_up_policy
        self._record_follow_up_timing(payload=payload, decision=follow_up_timing, now=now)
        if follow_up_timing.action == "suppress":
            wake.status = "suppressed"
            wake.suppression_reason = follow_up_timing.reason
            wake.payload = payload
            return "suppressed"
        if follow_up_timing.action == "cancel":
            wake.status = "cancelled"
            wake.suppression_reason = follow_up_timing.reason
            wake.payload = payload
            return "cancelled"
        if follow_up_timing.action == "defer":
            wake.scheduled_at = follow_up_timing.next_at or now + timedelta(
                minutes=int(follow_up_policy.get("recent_activity_defer_minutes") or 60)
            )
            wake.suppression_reason = follow_up_timing.reason
            wake.payload = payload
            return "deferred"

        readout = self._build_due_wake_readout(
            wake=wake,
            hard_bounds=hard_bounds,
            payload=payload,
            recent_signals=recent_signals,
            follow_up_policy=follow_up_policy,
            now=now,
        )
        decision = await self.decision_loop.decide(readout)
        if decision.action == "wait":
            wake.status = "suppressed"
            wake.suppression_reason = "decision_wait"
            payload["aurora_decision"] = decision.to_payload()
            self._record_follow_up_timing(
                payload=payload,
                decision=FollowUpTimingDecision(
                    action="suppress",
                    reason="decision_wait",
                    metadata={"decision_action": decision.action},
                ),
                now=now,
            )
            wake.payload = payload
            return "suppressed"
        if decision.action == "drop_thread":
            wake.status = "cancelled"
            wake.suppression_reason = "decision_drop_thread"
            payload["aurora_decision"] = decision.to_payload()
            self._record_follow_up_timing(
                payload=payload,
                decision=FollowUpTimingDecision(
                    action="cancel",
                    reason="decision_drop_thread",
                    metadata={"decision_action": decision.action},
                ),
                now=now,
            )
            wake.payload = payload
            return "cancelled"
        if decision.action == "schedule_wake":
            next_at = self._coerce_decision_wake_time(
                wake_schedule=decision.wake_schedule,
                fallback_at=now + timedelta(minutes=int(follow_up_policy.get("recent_activity_defer_minutes") or 60)),
            )
            wake.scheduled_at = next_at
            wake.suppression_reason = "decision_deferred"
            payload["aurora_decision"] = decision.to_payload()
            self._record_follow_up_timing(
                payload=payload,
                decision=FollowUpTimingDecision(
                    action="defer",
                    reason="decision_deferred",
                    next_at=next_at,
                    metadata={"decision_action": decision.action},
                ),
                now=now,
            )
            wake.payload = payload
            return "deferred"

        if decision.metadata.get("fallback_reason"):
            messages = self._build_follow_up_messages(payload)
        else:
            messages = await self.chat_adapter.render(decision, readout)
        if not messages:
            messages = self._build_follow_up_messages(payload)
        for index, text in enumerate(messages):
            self.db.add(
                ChatMessage(
                    user_id=wake.user_id,
                    session_id=wake.session_id,
                    role=MessageRole.ASSISTANT,
                    content=text,
                    actions=[
                        {
                            "type": "aurora_runtime_follow_up",
                            "data": {
                                **build_aurora_surface_metadata(
                                    surface=AURORA_CHECKPOINT_SURFACE,
                                    surface_complete=index == len(messages) - 1,
                                    modeling_complete=False,
                                ),
                                "wake_id": str(wake.id),
                                "conversation_id": wake.conversation_id,
                            },
                        }
                    ],
                )
            )
        wake.status = "executed"
        wake.executed_at = now
        wake.suppression_reason = None
        payload["emitted_messages"] = messages
        payload["executed_at"] = now.isoformat()
        payload["aurora_decision"] = decision.to_payload()
        wake.payload = payload
        await self._write_runtime_state(
            user_id=wake.user_id,
            conversation_id=wake.conversation_id,
            session_id=wake.session_id,
            checkpoint_description=str(payload.get("checkpoint_description") or ""),
            blocker={
                "summary": str(payload.get("blocker_summary") or ""),
                "urgency_score": float(wake.urgency_score or 0.0),
                "agenda_priority": payload.get("agenda_priority"),
                "time_pressure": payload.get("time_pressure"),
                "understanding_gap": payload.get("understanding_gap"),
            },
            activity_profile=dict(payload.get("activity_profile") or {}),
            wake_result={
                "wake_id": str(wake.id),
                "status": "executed",
                "scheduled_at": _isoformat(wake.scheduled_at),
                "executed_at": _isoformat(now),
            },
            metadata=dict(wake.runtime_metadata or {}),
            now=now,
        )
        return "executed"

    def _hard_bounds_from_preferences(self, aurora_prefs: dict[str, Any], timezone_name: str) -> AuroraHardBounds:
        return AuroraHardBounds.model_validate(
            {
                "dnd_windows": aurora_prefs.get("dnd_windows") or [],
                "privacy_boundaries": aurora_prefs.get("privacy_boundaries") or [],
                "disabled_actions": aurora_prefs.get("disabled_actions") or [],
                "timezone_name": timezone_name,
            }
        )

    async def _maybe_schedule_wake(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        conversation_id: str,
        checkpoint_day: int,
        checkpoint_description: str,
        blocker: dict[str, Any],
        activity_profile: dict[str, Any],
        metadata: dict[str, Any],
        aurora_prefs: dict[str, Any],
        timezone_name: str,
        next_task: Task | None,
        now: datetime,
    ) -> dict[str, Any]:
        hard_bounds = self._hard_bounds_from_preferences(aurora_prefs, timezone_name)
        if FOLLOW_UP_DISABLED_ACTION in set(aurora_prefs.get("disabled_actions") or []):
            activity_profile["next_wake_at"] = None
            return {
                "status": "suppressed",
                "reason": "disabled_action",
                "scheduled_at": None,
            }
        if hard_bounds.is_privacy_blocked(blocker.get("agenda_priority")):
            activity_profile["next_wake_at"] = None
            return {
                "status": "suppressed",
                "reason": "privacy_boundary",
                "scheduled_at": None,
            }

        next_wake_at = activity_profile.get("next_wake_at")
        if not next_wake_at:
            return {
                "status": "not_scheduled",
                "reason": "goal_met",
                "scheduled_at": None,
            }

        follow_up_policy = self._build_follow_up_policy(blocker=blocker)
        if follow_up_policy["quiet_by_default"]:
            activity_profile["next_wake_at"] = None
            return {
                "status": "not_scheduled",
                "reason": "low_urgency_quiet",
                "scheduled_at": None,
            }

        scheduled_at = datetime.fromisoformat(str(next_wake_at))
        dnd_decision = self._evaluate_dnd(
            when=scheduled_at,
            timezone_name=timezone_name,
            dnd_windows=aurora_prefs.get("dnd_windows") or [],
            urgency_score=float(blocker["urgency_score"]),
        )
        if dnd_decision["decision"] == "suppress":
            activity_profile["next_wake_at"] = None
            return {
                "status": "suppressed",
                "reason": "dnd_window",
                "scheduled_at": _isoformat(scheduled_at),
            }
        if dnd_decision["decision"] == "defer":
            scheduled_at = dnd_decision["next_at"]
            activity_profile["next_wake_at"] = scheduled_at.isoformat()

        wake = AuroraScheduledWake(
            user_id=user_id,
            surface=AURORA_CHECKPOINT_SURFACE,
            conversation_id=conversation_id,
            session_id=session_id,
            scheduled_at=scheduled_at,
            status="pending",
            reason=str(blocker["summary"]),
            planned_action="checkpoint_follow_up",
            urgency_score=float(blocker["urgency_score"]),
            payload={
                "checkpoint_day": checkpoint_day,
                "checkpoint_description": checkpoint_description,
                "blocker_summary": blocker["summary"],
                "blocker_keywords": blocker["keywords"],
                "agenda_priority": blocker["agenda_priority"],
                "time_pressure": blocker["time_pressure"],
                "understanding_gap": blocker["understanding_gap"],
                "next_task_title": getattr(next_task, "title", None),
                "activity_profile": activity_profile,
                "follow_up_policy": follow_up_policy,
                "follow_up_state": {
                    "defer_count": 0,
                    "timing_history": [],
                    "scheduled_from_checkpoint": now.isoformat(),
                },
            },
            runtime_metadata=metadata,
            suppression_reason=None,
        )
        self.db.add(wake)
        await self.db.flush()
        return {
            "status": "scheduled",
            "wake_id": str(wake.id),
            "reason": str(blocker["summary"]),
            "scheduled_at": _isoformat(scheduled_at),
        }

    def _build_due_wake_readout(
        self,
        *,
        wake: AuroraScheduledWake,
        hard_bounds: AuroraHardBounds,
        payload: dict[str, Any],
        recent_signals: dict[str, Any],
        follow_up_policy: dict[str, Any],
        now: datetime,
    ) -> DashboardReadout:
        activity_profile = dict(payload.get("activity_profile") or {})
        activity_profile.setdefault("conversation_style", "warm")
        activity_profile.setdefault("task_density_hint", 0.45)
        activity_profile.setdefault("agenda_priority", payload.get("agenda_priority"))
        activity_profile["expression"] = merge_expression_settings(activity_profile.get("expression"))
        informational_tensions = []
        blocker_summary = str(payload.get("blocker_summary") or "").strip()
        if blocker_summary:
            informational_tensions.append(
                {
                    "tension_id": f"{wake.conversation_id}:checkpoint-gap",
                    "domain": payload.get("agenda_priority") or "checkpoint_gap",
                    "description": blocker_summary,
                    "priority": float(wake.urgency_score or 0.0),
                    "status": "open",
                    "last_observed_at": recent_signals.get("last_blocker_signal_at"),
                }
            )
        latent_threads = []
        if blocker_summary:
            latent_threads.append(
                {
                    "thread_id": f"{wake.conversation_id}:follow-up",
                    "salience": float(wake.urgency_score or 0.0),
                    "context_snapshot": blocker_summary,
                    "status_hint": recent_signals.get("status_hint") or "pending_follow_up",
                }
            )
        minutes_overdue = max(
            0.0,
            round((now - _naive_utc(wake.scheduled_at)).total_seconds() / 60.0, 1),
        )
        return DashboardReadout(
            surface=AURORA_CHECKPOINT_SURFACE,
            user_id=str(wake.user_id),
            conversation_id=str(wake.conversation_id),
            request_id=f"wake:{wake.id}",
            user_message="",
            activity_profile=activity_profile,
            hard_bounds=hard_bounds,
            candidate_affordances=self.skill_registry.load_candidate_affordances(AURORA_CHECKPOINT_SURFACE),
            informational_tensions=informational_tensions,
            latent_threads=latent_threads,
            checkpoint_state={
                "checkpoint_day": payload.get("checkpoint_day"),
                "checkpoint_description": payload.get("checkpoint_description"),
                "blocker_summary": payload.get("blocker_summary"),
                "urgency_score": float(wake.urgency_score or 0.0),
                "planned_action": wake.planned_action,
                "recent_user_activity": recent_signals,
                "follow_up_policy": follow_up_policy,
                "due_context": {
                    "scheduled_at": _isoformat(wake.scheduled_at),
                    "minutes_overdue": minutes_overdue,
                },
            },
            request_extra_context={
                "surface_complete": True,
                "follow_up_policy": follow_up_policy,
                "recent_user_activity": recent_signals,
                "decision_loop_required": True,
            },
        )

    async def _evaluate_due_follow_up_timing(
        self,
        *,
        wake: AuroraScheduledWake,
        now: datetime,
        hard_bounds: AuroraHardBounds,
        timezone_name: str,
    ) -> tuple[FollowUpTimingDecision, dict[str, Any], dict[str, Any]]:
        payload = dict(wake.payload or {})
        blocker = {
            "summary": str(payload.get("blocker_summary") or ""),
            "urgency_score": float(wake.urgency_score or 0.0),
            "agenda_priority": payload.get("agenda_priority"),
            "time_pressure": bool(payload.get("time_pressure")),
            "understanding_gap": bool(payload.get("understanding_gap")),
        }
        follow_up_policy = {
            **self._build_follow_up_policy(blocker=blocker),
            **dict(payload.get("follow_up_policy") or {}),
        }
        recent_signals = await self._collect_recent_user_signals(wake=wake, now=now)
        recent_signals["status_hint"] = self._derive_recent_status_hint(recent_signals)

        if FOLLOW_UP_DISABLED_ACTION in set(hard_bounds.disabled_actions or []):
            return (
                FollowUpTimingDecision(
                    action="suppress",
                    reason="disabled_action",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        if hard_bounds.is_privacy_blocked(blocker.get("agenda_priority")):
            return (
                FollowUpTimingDecision(
                    action="suppress",
                    reason="privacy_boundary",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        if recent_signals["gap_closed"]:
            return (
                FollowUpTimingDecision(
                    action="cancel",
                    reason="gap_already_closed",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        dnd_decision = self._evaluate_dnd(
            when=now,
            timezone_name=timezone_name,
            dnd_windows=hard_bounds.model_dump(mode="python").get("dnd_windows") or [],
            urgency_score=float(wake.urgency_score or 0.0),
        )
        if dnd_decision["decision"] == "suppress":
            return (
                FollowUpTimingDecision(
                    action="suppress",
                    reason="dnd_window",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )
        if dnd_decision["decision"] == "defer":
            return (
                FollowUpTimingDecision(
                    action="defer",
                    reason="dnd_deferred",
                    next_at=dnd_decision["next_at"],
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        defer_count = int((payload.get("follow_up_state") or {}).get("defer_count") or 0)
        recent_activity_grace = int(follow_up_policy.get("recent_activity_grace_minutes") or 0)
        in_progress_grace = int(follow_up_policy.get("in_progress_grace_minutes") or 0)
        recent_minutes = recent_signals["minutes_since_last_user_message"]
        urgency_score = float(wake.urgency_score or 0.0)
        can_defer = defer_count < int(follow_up_policy.get("max_deferrals") or 0)

        if (
            recent_signals["working_on_gap"]
            and recent_minutes is not None
            and recent_minutes <= in_progress_grace
        ):
            if can_defer:
                return (
                    FollowUpTimingDecision(
                        action="defer",
                        reason="working_gap_in_progress",
                        next_at=now
                        + timedelta(
                            minutes=max(
                                int(follow_up_policy.get("recent_activity_defer_minutes") or 60),
                                90,
                            )
                        ),
                        metadata={"recent_user_activity": recent_signals},
                    ),
                    recent_signals,
                    follow_up_policy,
                )
            return (
                FollowUpTimingDecision(
                    action="suppress",
                    reason="working_gap_in_progress",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        if recent_minutes is not None and recent_minutes <= recent_activity_grace:
            if urgency_score < LOW_URGENCY_FOLLOW_UP_THRESHOLD and not recent_signals["fresh_blocker_signal"]:
                return (
                    FollowUpTimingDecision(
                        action="suppress",
                        reason="low_urgency_recent_activity",
                        metadata={"recent_user_activity": recent_signals},
                    ),
                    recent_signals,
                    follow_up_policy,
                )
            if can_defer:
                return (
                    FollowUpTimingDecision(
                        action="defer",
                        reason="recent_user_activity",
                        next_at=now
                        + timedelta(minutes=int(follow_up_policy.get("recent_activity_defer_minutes") or 60)),
                        metadata={"recent_user_activity": recent_signals},
                    ),
                    recent_signals,
                    follow_up_policy,
                )

        if urgency_score < LOW_URGENCY_FOLLOW_UP_THRESHOLD and not recent_signals["fresh_blocker_signal"]:
            return (
                FollowUpTimingDecision(
                    action="suppress",
                    reason="low_urgency",
                    metadata={"recent_user_activity": recent_signals},
                ),
                recent_signals,
                follow_up_policy,
            )

        return (
            FollowUpTimingDecision(
                action="execute",
                reason="execute",
                metadata={"recent_user_activity": recent_signals},
            ),
            recent_signals,
            follow_up_policy,
        )

    def _build_follow_up_policy(self, *, blocker: dict[str, Any]) -> dict[str, Any]:
        urgency_score = float(blocker.get("urgency_score") or 0.0)
        if (
            urgency_score >= HIGH_URGENCY_FOLLOW_UP_THRESHOLD
            or bool(blocker.get("time_pressure"))
            or bool(blocker.get("understanding_gap"))
        ):
            urgency_band = "high"
            recent_activity_grace_minutes = 30
            recent_activity_defer_minutes = 35
            in_progress_grace_minutes = 120
            max_deferrals = 3
        elif urgency_score >= LOW_URGENCY_FOLLOW_UP_THRESHOLD:
            urgency_band = "medium"
            recent_activity_grace_minutes = 75
            recent_activity_defer_minutes = 60
            in_progress_grace_minutes = 180
            max_deferrals = 2
        else:
            urgency_band = "low"
            recent_activity_grace_minutes = 120
            recent_activity_defer_minutes = 120
            in_progress_grace_minutes = 240
            max_deferrals = 1
        quiet_by_default = (
            urgency_score < LOW_URGENCY_FOLLOW_UP_THRESHOLD
            and not bool(blocker.get("time_pressure"))
            and not bool(blocker.get("understanding_gap"))
        )
        return {
            "urgency_band": urgency_band,
            "quiet_by_default": quiet_by_default,
            "decision_loop_required": True,
            "recent_activity_grace_minutes": recent_activity_grace_minutes,
            "recent_activity_defer_minutes": recent_activity_defer_minutes,
            "in_progress_grace_minutes": in_progress_grace_minutes,
            "max_deferrals": max_deferrals,
        }

    async def _collect_recent_user_signals(
        self,
        *,
        wake: AuroraScheduledWake,
        now: datetime,
    ) -> dict[str, Any]:
        payload = dict(wake.payload or {})
        keywords = [str(item) for item in payload.get("blocker_keywords") or [] if str(item).strip()]
        since = max(_naive_utc(wake.created_at), now - timedelta(days=3))
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == wake.user_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= since,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        messages = list(result.scalars().all())
        last_message_at = messages[-1].created_at if messages else None
        last_blocker_signal_at: datetime | None = None
        gap_closed = False
        working_on_gap = False
        fresh_blocker_signal = False
        for message in messages:
            text = str(message.content or "")
            matches_keyword = not keywords or any(keyword in text for keyword in keywords)
            if not matches_keyword:
                continue
            if any(marker in text for marker in RESOLUTION_MARKERS):
                gap_closed = True
            if any(marker in text for marker in WORKING_MARKERS):
                working_on_gap = True
                last_blocker_signal_at = message.created_at
            if (
                any(marker in text for marker in NEGATIVE_MARKERS)
                or any(marker in text for marker in UNDERSTANDING_MARKERS)
                or any(marker in text for marker in TIME_PRESSURE_MARKERS)
            ):
                fresh_blocker_signal = True
                last_blocker_signal_at = message.created_at
        if not fresh_blocker_signal and last_blocker_signal_at is not None:
            fresh_blocker_signal = (now - last_blocker_signal_at) <= timedelta(hours=24)
        minutes_since_last = None
        if last_message_at is not None:
            minutes_since_last = round(
                max(0.0, (now - _naive_utc(last_message_at)).total_seconds() / 60.0),
                1,
            )
        return {
            "message_count_since_wake": len(messages),
            "last_user_message_at": _isoformat(last_message_at),
            "minutes_since_last_user_message": minutes_since_last,
            "last_blocker_signal_at": _isoformat(last_blocker_signal_at),
            "gap_closed": gap_closed,
            "working_on_gap": working_on_gap,
            "fresh_blocker_signal": fresh_blocker_signal,
        }

    def _derive_recent_status_hint(self, recent_signals: dict[str, Any]) -> str:
        if recent_signals.get("gap_closed"):
            return "gap_closed"
        if recent_signals.get("working_on_gap"):
            return "in_progress"
        if recent_signals.get("fresh_blocker_signal"):
            return "still_blocked"
        if recent_signals.get("last_user_message_at"):
            return "recent_user_activity"
        return "quiet"

    def _coerce_decision_wake_time(
        self,
        *,
        wake_schedule: dict[str, Any] | None,
        fallback_at: datetime,
    ) -> datetime:
        raw = {}
        if isinstance(wake_schedule, dict):
            raw = wake_schedule
        scheduled_at = _coerce_datetime(raw.get("scheduled_at") or raw.get("next_wake_at"))
        return scheduled_at or fallback_at

    def _record_follow_up_timing(
        self,
        *,
        payload: dict[str, Any],
        decision: FollowUpTimingDecision,
        now: datetime,
    ) -> None:
        state = dict(payload.get("follow_up_state") or {})
        history = list(state.get("timing_history") or [])
        if decision.action == "defer":
            state["defer_count"] = int(state.get("defer_count") or 0) + 1
        history.append(
            {
                "decision": decision.action,
                "reason": decision.reason,
                "at": now.isoformat(),
                "next_at": _isoformat(decision.next_at),
            }
        )
        state["timing_history"] = history[-6:]
        state["last_decision"] = decision.action
        state["last_reason"] = decision.reason
        state["last_evaluated_at"] = now.isoformat()
        payload["follow_up_state"] = state
        payload["last_timing_decision"] = decision.to_payload()

    async def _write_runtime_state(
        self,
        *,
        user_id: UUID,
        conversation_id: str,
        session_id: UUID,
        checkpoint_description: str,
        blocker: dict[str, Any],
        activity_profile: dict[str, Any],
        wake_result: dict[str, Any],
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        key = f"aurora:runtime:{user_id}:{AURORA_CHECKPOINT_SURFACE}:{conversation_id}"
        payload = {
            "user_id": str(user_id),
            "surface": AURORA_CHECKPOINT_SURFACE,
            "conversation_id": conversation_id,
            "runtime_session_id": str(session_id),
            "user_model_snapshot": {
                "checkpoint_description": checkpoint_description,
                "blocker_summary": blocker.get("summary"),
            },
            "informational_tensions": [
                {
                    "domain": blocker.get("agenda_priority") or "checkpoint_gap",
                    "description": blocker.get("summary"),
                    "priority": blocker.get("urgency_score"),
                    "status": ("resolved" if wake_result.get("status") == "not_scheduled" else "open"),
                }
            ],
            "current_intent": {
                "intent_type": ("schedule_follow_up" if wake_result.get("status") == "scheduled" else "wait"),
                "target_tension_id": f"{conversation_id}:checkpoint-gap",
                "payload": {"reason": blocker.get("summary")},
            },
            "latent_threads": (
                []
                if wake_result.get("status") == "not_scheduled"
                else [
                    {
                        "thread_id": f"{conversation_id}:follow-up",
                        "salience": blocker.get("urgency_score"),
                        "context_snapshot": blocker.get("summary"),
                    }
                ]
            ),
            "activity_profile": activity_profile,
            "self_scheduled_wakes": ([] if wake_result.get("status") != "scheduled" else [wake_result]),
            "streaming_status": "idle",
            "ingress_events": [{"type": "checkpoint_debrief_completed", "at": now.isoformat()}],
            "last_decision_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": metadata,
        }
        await _redis_setex(
            self.redis,
            key,
            RUNTIME_STATE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False),
        )

    async def _load_next_pending_task(self, *, user_id: UUID, plan_id: UUID | None) -> Task | None:
        query = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
            )
            .order_by(Task.order_index.asc(), Task.created_at.asc())
            .limit(1)
        )
        if plan_id is not None:
            query = query.where(Task.plan_id == plan_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _load_aurora_preferences(self, user_id: UUID) -> tuple[dict[str, Any], str]:
        prefs_result = await self.db.execute(
            select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id).limit(1)
        )
        prefs = prefs_result.scalar_one_or_none()
        explicit = dict((prefs.explicit if prefs else {}) or {})
        aurora_prefs = dict(explicit.get("aurora_preferences") or {})
        user = await self.db.get(User, user_id)
        timezone_name = "Asia/Shanghai"
        push_preference = getattr(user, "push_preference", None) if user is not None else None
        if getattr(push_preference, "timezone", None):
            timezone_name = str(push_preference.timezone)
        return aurora_prefs, timezone_name

    def _summarize_blocker(
        self,
        *,
        checkpoint_description: str,
        first_answer: str,
        second_answer: str,
        goal_met: bool,
        next_task_title: str | None,
    ) -> dict[str, Any]:
        combined = "。".join(filter(None, [first_answer, second_answer]))
        segments = [segment.strip() for segment in re.split(r"[，,。；;！？?\n]+", combined) if segment.strip()]
        candidate = ""
        for segment in segments:
            if segment in GENERIC_SEGMENTS:
                continue
            if any(marker in segment for marker in UNDERSTANDING_MARKERS):
                candidate = segment
                break
        if not candidate:
            for segment in segments:
                if any(marker in segment for marker in NEGATIVE_MARKERS):
                    candidate = segment
                    break
        if not candidate:
            candidate = checkpoint_description.strip() or "这个检查点还没闭合"
        candidate = self._clean_segment(candidate)
        time_pressure = any(marker in combined for marker in TIME_PRESSURE_MARKERS)
        understanding_gap = any(marker in combined for marker in UNDERSTANDING_MARKERS)
        urgency_score = 0.2
        if not goal_met:
            urgency_score += 0.28
        if time_pressure:
            urgency_score += 0.18
        if understanding_gap:
            urgency_score += 0.22
        if next_task_title:
            urgency_score += 0.07
        urgency_score = max(0.1, min(0.95, round(urgency_score, 2)))
        agenda_priority = "time_management" if time_pressure and not understanding_gap else "knowledge_gap"
        if goal_met:
            agenda_priority = None
        keywords = self._extract_keywords(candidate, checkpoint_description)
        return {
            "summary": candidate,
            "keywords": keywords,
            "time_pressure": time_pressure,
            "understanding_gap": understanding_gap,
            "urgency_score": urgency_score,
            "agenda_priority": agenda_priority,
        }

    def _build_activity_profile(
        self,
        *,
        blocker: dict[str, Any],
        checkpoint_day: int,
        plan: Plan | None,
        next_task: Task | None,
        now: datetime,
    ) -> dict[str, Any]:
        if blocker["agenda_priority"] is None:
            return {
                "proactive_intensity": 0.34,
                "next_wake_at": None,
                "conversation_style": "warm",
                "expression": {
                    "tone_warmth": 0.76,
                    "directness": 0.32,
                    "brevity": 0.52,
                    "friendliness": 0.78,
                    "challenge_intensity": 0.24,
                },
                "agenda_priority": None,
                "task_density_hint": 0.72,
            }

        delay_hours = 26.0
        delay_hours -= min(checkpoint_day, 4) * 1.5
        delay_hours -= float(blocker["urgency_score"]) * 10.0
        if blocker["time_pressure"]:
            delay_hours -= 3.5
        if blocker["understanding_gap"]:
            delay_hours -= 4.0
        if next_task and int(next_task.estimated_minutes or 0) >= 60:
            delay_hours -= 2.0
        if plan and getattr(plan, "target_date", None):
            days_left = (plan.target_date - now.date()).days
            if days_left <= 2:
                delay_hours -= 4.0
            elif days_left <= 5:
                delay_hours -= 2.0
        delay_hours = max(4.0, min(42.0, delay_hours))
        next_wake_at = now + timedelta(hours=delay_hours)
        if blocker["time_pressure"]:
            expression = {
                "tone_warmth": 0.44,
                "directness": 0.86,
                "brevity": 0.82,
                "friendliness": 0.4,
                "challenge_intensity": 0.74,
            }
        elif blocker["understanding_gap"]:
            expression = {
                "tone_warmth": 0.72,
                "directness": 0.54,
                "brevity": 0.44,
                "friendliness": 0.76,
                "challenge_intensity": 0.48,
            }
        else:
            expression = {
                "tone_warmth": 0.62,
                "directness": 0.6,
                "brevity": 0.56,
                "friendliness": 0.68,
                "challenge_intensity": 0.56,
            }
        return {
            "proactive_intensity": round(min(0.9, 0.52 + float(blocker["urgency_score"]) * 0.4), 2),
            "next_wake_at": next_wake_at.isoformat(),
            "conversation_style": (
                "structured" if blocker["understanding_gap"] or blocker["time_pressure"] else "warm"
            ),
            "expression": expression,
            "agenda_priority": blocker["agenda_priority"],
            "task_density_hint": 0.38 if blocker["time_pressure"] else 0.52,
        }

    def _build_follow_up_messages(self, payload: dict[str, Any]) -> list[str]:
        blocker = str(payload.get("blocker_summary") or "上次那个检查点的卡点")
        next_task_title = str(payload.get("next_task_title") or "").strip()
        task_hint = (
            f"先别把范围摊太大，我们先盯住「{next_task_title}」里最卡的那一块。"
            if next_task_title
            else "这次先别全盘重来，我们只盯最卡的那一块。"
        )
        if payload.get("understanding_gap"):
            second = f"{task_hint} 你上次提到的「{blocker}」，现在更像是概念还没拎顺，还是题一做就散？"
        elif payload.get("time_pressure"):
            second = f"{task_hint} 你上次说卡在「{blocker}」，我更想先帮你把时间口收住。今天如果只留一个最小补口，你想补哪一小块？"
        else:
            second = f"{task_hint} 你上次提到「{blocker}」，现在这块有没有往前推进一点？"
        return [
            f"我还记着你上次 checkpoint 里提到的「{blocker}」。",
            second,
        ]

    async def _has_user_resolved_gap(
        self,
        wake: AuroraScheduledWake,
        *,
        now: datetime | None = None,
    ) -> bool:
        recent_signals = await self._collect_recent_user_signals(
            wake=wake,
            now=_naive_utc(now) or _utcnow(),
        )
        return bool(recent_signals.get("gap_closed"))

    def _evaluate_dnd(
        self,
        *,
        when: datetime,
        timezone_name: str,
        dnd_windows: list[dict[str, Any]],
        urgency_score: float,
    ) -> dict[str, Any]:
        local_dt = self._to_local_time(when, timezone_name)
        for item in dnd_windows:
            start_text = str(item.get("start") or "").strip()
            end_text = str(item.get("end") or "").strip()
            start = self._parse_clock(start_text)
            end = self._parse_clock(end_text)
            if start is None or end is None:
                continue
            if not self._is_in_window(local_dt.time(), start, end):
                continue
            if urgency_score >= 0.72:
                return {
                    "decision": "defer",
                    "next_at": self._to_utc_naive(self._window_end(local_dt, start, end) + timedelta(minutes=10)),
                }
            return {"decision": "suppress"}
        return {"decision": "allow"}

    def _extract_keywords(self, *texts: str) -> list[str]:
        keywords: list[str] = []
        for text in texts:
            cleaned = self._clean_segment(text)
            for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", cleaned):
                for marker in (
                    "也没搞定",
                    "没搞定",
                    "没完成",
                    "没做完",
                    "没时间",
                    "来不及",
                    "还没",
                    "问题",
                    "主要是",
                ):
                    token = token.replace(marker, "")
                token = token.strip("也还了在把的得就是个这那")
                if len(token) < 2 or token in GENERIC_SEGMENTS:
                    continue
                if token not in keywords:
                    keywords.append(token)
        return keywords[:5]

    def _clean_segment(self, text: str) -> str:
        result = str(text or "").strip()
        for prefix in ("主要是", "就是", "问题是", "卡在", "还在", "现在"):
            if result.startswith(prefix):
                result = result[len(prefix) :].strip()
        return result or "这个检查点还没闭合"

    def _to_local_time(self, when: datetime, timezone_name: str) -> datetime:
        tz_name = timezone_name or "Asia/Shanghai"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        base = when.replace(tzinfo=UTC) if when.tzinfo is None else when.astimezone(UTC)
        return base.astimezone(tz)

    def _to_utc_naive(self, when: datetime) -> datetime:
        return when.astimezone(UTC).replace(tzinfo=None)

    def _parse_clock(self, text: str) -> time | None:
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23 or minute > 59:
            return None
        return time(hour=hour, minute=minute)

    def _is_in_window(self, point: time, start: time, end: time) -> bool:
        if start <= end:
            return start <= point < end
        return point >= start or point < end

    def _window_end(self, local_dt: datetime, start: time, end: time) -> datetime:
        if start <= end:
            return local_dt.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if local_dt.time() >= start:
            next_day = local_dt + timedelta(days=1)
            return next_day.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        return local_dt.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
