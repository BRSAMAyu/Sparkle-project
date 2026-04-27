"""
Core: execution
Phase: sense
Stage: P3-3 External Integrations — Calendar + tool signal bridge

Bridges external data sources (calendar events, tool usage) into the
Signal Spine. Calendar events become ActionableSignals when they indicate
time pressure, deadline proximity, or scheduling conflicts.

External tool signals provide context about user activity outside the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start_time: str      # ISO 8601
    end_time: str         # ISO 8601
    event_type: str       # "exam" | "deadline" | "class" | "meeting" | "other"
    subject: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_type": self.event_type,
            "subject": self.subject,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CalendarEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExternalToolSignal:
    tool_id: str
    tool_type: str        # "ide" | "note_app" | "lms" | "browser" | "other"
    activity_type: str    # "active" | "idle" | "document_opened" | "quiz_attempted"
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_type": self.tool_type,
            "activity_type": self.activity_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class CalendarSignalBridge:
    """Convert calendar events into ActionableSignals for the Spine."""

    def detect_deadline_pressure(
        self,
        events: list[CalendarEvent],
        *,
        now: str | None = None,
        threshold_hours: int = 72,
    ) -> ActionableSignal | None:
        """Detect if any upcoming event creates deadline pressure.

        Only triggers for exam/deadline events within threshold_hours.
        """
        now_dt = datetime.fromisoformat(now) if now else datetime.now(UTC)
        threshold = now_dt + timedelta(hours=threshold_hours)

        for event in events:
            if event.event_type not in ("exam", "deadline"):
                continue
            try:
                event_dt = datetime.fromisoformat(event.start_time)
            except (ValueError, TypeError):
                continue

            if now_dt < event_dt <= threshold:
                hours_until = (event_dt - now_dt).total_seconds() / 3600
                urgency = "high" if hours_until < 24 else "medium"
                return ActionableSignal(
                    signal_id=_uid("sig"),
                    source_event_ids=[event.event_id],
                    source_system="calendar_bridge",
                    state_key="deadline_pressure",
                    claim="upcoming_deadline",
                    confidence=0.95,
                    scope="current_sprint",
                    ttl_hours=int(hours_until) + 1,
                    evidence_summary=f"{event.title} 在 {hours_until:.0f} 小时后",
                    possible_effects=["adjust_plan_density", "prioritize_review"],
                    priority=urgency,
                )

        return None

    def detect_schedule_conflict(
        self,
        events: list[CalendarEvent],
        *,
        planned_study_windows: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect conflicts between planned study and calendar events.

        Returns list of conflict descriptions.
        """
        if not planned_study_windows:
            return []

        conflicts = []
        for window in planned_study_windows:
            try:
                win_start = datetime.fromisoformat(window.get("start", ""))
                win_end = datetime.fromisoformat(window.get("end", ""))
            except (ValueError, TypeError):
                continue

            for event in events:
                try:
                    ev_start = datetime.fromisoformat(event.start_time)
                    ev_end = datetime.fromisoformat(event.end_time)
                except (ValueError, TypeError):
                    continue

                # Check overlap
                if ev_start < win_end and ev_end > win_start:
                    conflicts.append({
                        "study_window": window,
                        "conflicting_event": event.to_dict(),
                        "conflict_type": "overlap",
                    })

        return conflicts

    def build_time_context(
        self,
        events: list[CalendarEvent],
        *,
        now: str | None = None,
    ) -> dict[str, Any]:
        """Build a time context packet from upcoming events.

        Returns structured context for downstream consumption.
        """
        now_dt = datetime.fromisoformat(now) if now else datetime.now(UTC)
        next_24h = now_dt + timedelta(hours=24)
        next_7d = now_dt + timedelta(days=7)

        upcoming_24h = []
        upcoming_7d = []
        nearest_deadline = None
        nearest_deadline_hours = float("inf")

        for event in events:
            try:
                event_dt = datetime.fromisoformat(event.start_time)
            except (ValueError, TypeError):
                continue

            if now_dt < event_dt <= next_24h:
                upcoming_24h.append(event.to_dict())
            if now_dt < event_dt <= next_7d:
                upcoming_7d.append(event.to_dict())

            if event.event_type in ("exam", "deadline") and now_dt < event_dt:
                hours = (event_dt - now_dt).total_seconds() / 3600
                if hours < nearest_deadline_hours:
                    nearest_deadline_hours = hours
                    nearest_deadline = event.to_dict()

        return {
            "upcoming_24h_count": len(upcoming_24h),
            "upcoming_24h": upcoming_24h,
            "upcoming_7d_count": len(upcoming_7d),
            "nearest_deadline": nearest_deadline,
            "nearest_deadline_hours": round(nearest_deadline_hours, 1) if nearest_deadline else None,
            "has_time_pressure": nearest_deadline is not None and nearest_deadline_hours < 72,
        }


class ExternalToolBridge:
    """Convert external tool activity into spine context."""

    def detect_study_session(self, signals: list[ExternalToolSignal]) -> dict[str, Any] | None:
        """Detect an active study session from tool signals.

        Returns session summary if activity pattern indicates studying.
        """
        if not signals:
            return None

        active_tools = [s for s in signals if s.activity_type == "active"]
        if not active_tools:
            return None

        tool_types = set(s.tool_type for s in active_tools)

        study_indicators = {"ide", "lms", "note_app"}
        is_study = bool(tool_types & study_indicators)

        if not is_study:
            return None

        return {
            "session_active": True,
            "active_tool_types": list(tool_types),
            "activity_types": list(set(s.activity_type for s in active_tools)),
            "signal_count": len(signals),
            "study_confidence": 0.7 if len(tool_types) == 1 else 0.9,
        }

    def build_tool_context(
        self,
        signals: list[ExternalToolSignal],
    ) -> dict[str, Any]:
        """Build context from recent tool signals."""
        if not signals:
            return {"recent_activity": False}

        tool_counts: dict[str, int] = {}
        activity_types: set[str] = set()
        latest = ""

        for s in signals:
            tool_counts[s.tool_type] = tool_counts.get(s.tool_type, 0) + 1
            activity_types.add(s.activity_type)
            if s.timestamp > latest:
                latest = s.timestamp

        return {
            "recent_activity": True,
            "tool_usage": tool_counts,
            "activity_types": list(activity_types),
            "latest_activity": latest,
            "total_signals": len(signals),
        }
