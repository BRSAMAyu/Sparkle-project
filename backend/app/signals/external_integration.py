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


# ── P3-6: External Integration v1 ────────────────────────────────────────────


@dataclass
class ExternalRawEvent:
    """All external data MUST first become an ExternalRawEvent before entering Spine.

    Iron rule: external signals cannot bypass the Spine. Every external event
    is a RawEvent in the Spine's causal chain.
    """
    event_id: str
    source: str               # "calendar" | "file" | "email" | "github" | "tool"
    source_detail: str         # e.g. "google_calendar", "pdf_upload", "gmail"
    goal_id: str | None = None  # Which goal this event is bound to
    raw_payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    user_visible: bool = True  # User must see this came from external source
    revocable: bool = True     # User can disconnect the integration
    integration_id: str = ""   # For disconnect tracking

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "source_detail": self.source_detail,
            "goal_id": self.goal_id,
            "raw_payload": self.raw_payload,
            "timestamp": self.timestamp,
            "user_visible": self.user_visible,
            "revocable": self.revocable,
            "integration_id": self.integration_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExternalRawEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class FileReference:
    """A file/document reference from an external source."""
    file_id: str
    file_name: str
    source: str              # "upload" | "drive" | "onedrive" | "dropbox" | "email_attachment"
    mime_type: str
    size_bytes: int = 0
    uploaded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    goal_id: str | None = None
    parsed_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "source": self.source,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "uploaded_at": self.uploaded_at,
            "goal_id": self.goal_id,
            "parsed_summary": self.parsed_summary,
        }


@dataclass
class EmailDeadlineHint:
    """Deadline extracted from email content."""
    hint_id: str
    source_email_id: str
    subject_hint: str
    extracted_date: str | None = None  # ISO date if parsed
    extracted_keywords: list[str] = field(default_factory=list)
    confidence: float = 0.5
    goal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "hint_id": self.hint_id,
            "source_email_id": self.source_email_id,
            "subject_hint": self.subject_hint,
            "extracted_date": self.extracted_date,
            "extracted_keywords": self.extracted_keywords,
            "confidence": self.confidence,
            "goal_id": self.goal_id,
        }


@dataclass
class GitHubRepoSummary:
    """Summary of a GitHub repo for goal-bound project context."""
    repo_id: str
    repo_name: str
    owner: str
    recent_commits: int = 0
    open_prs: int = 0
    open_issues: int = 0
    last_activity: str = ""
    goal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "repo_name": self.repo_name,
            "owner": self.owner,
            "recent_commits": self.recent_commits,
            "open_prs": self.open_prs,
            "open_issues": self.open_issues,
            "last_activity": self.last_activity,
            "goal_id": self.goal_id,
        }


class FileIntegration:
    """Files/docs → ExternalRawEvent → Spine.

    Detects file uploads and converts them into ExternalRawEvents for the Spine.
    Does NOT directly write to user state — all state changes go through Spine policies.
    """

    def on_file_received(self, file_ref: FileReference) -> ExternalRawEvent:
        """Convert a file upload into a RawEvent for the Spine."""
        return ExternalRawEvent(
            event_id=_uid("ext_file"),
            source="file",
            source_detail=file_ref.source,
            goal_id=file_ref.goal_id,
            raw_payload={
                "action": "file_received",
                "file_name": file_ref.file_name,
                "mime_type": file_ref.mime_type,
                "size_bytes": file_ref.size_bytes,
                "parsed_summary": file_ref.parsed_summary,
            },
            user_visible=True,
            revocable=True,
        )

    def detect_undiagnosed_materials(
        self,
        files: list[FileReference],
        *,
        diagnosed_file_ids: set[str] | None = None,
    ) -> list[FileReference]:
        """Find files that haven't been diagnosed/processed yet."""
        diagnosed = diagnosed_file_ids or set()
        return [f for f in files if f.file_id not in diagnosed]

    def build_file_context(
        self,
        files: list[FileReference],
        *,
        goal_id: str | None = None,
    ) -> dict[str, Any]:
        """Build file context for a specific goal."""
        goal_files = [f for f in files if goal_id is None or f.goal_id == goal_id]
        return {
            "total_files": len(goal_files),
            "files": [f.to_dict() for f in goal_files],
            "mime_types": list(set(f.mime_type for f in goal_files)),
            "undiagnosed_count": len([f for f in goal_files if not f.parsed_summary]),
        }


class EmailDeadlineExtractor:
    """Email deadline extraction → ExternalRawEvent → deadline_pressure signal.

    Extracts deadline hints from email subjects/bodies. All extracted hints
    are candidates only — confidence < 0.8 triggers requires_user_confirmation.
    """

    DEADLINE_KEYWORDS = [
        "due", "deadline", "exam", "考试", "截止", "提交",
        "submission", "final", "midterm", "期末", "期中",
        "assignment", "作业", "project", "项目",
    ]

    def extract_from_subject(
        self,
        email_id: str,
        subject: str,
        *,
        goal_id: str | None = None,
    ) -> EmailDeadlineHint | None:
        """Extract deadline hints from email subject line."""
        subject_lower = subject.lower()
        matched_keywords = [kw for kw in self.DEADLINE_KEYWORDS if kw.lower() in subject_lower]

        if not matched_keywords:
            return None

        confidence = min(0.3 + len(matched_keywords) * 0.15, 0.85)

        return EmailDeadlineHint(
            hint_id=_uid("edh"),
            source_email_id=email_id,
            subject_hint=subject,
            extracted_date=None,  # Date parsing would need NLP, deferred to L2+
            extracted_keywords=matched_keywords,
            confidence=confidence,
            goal_id=goal_id,
        )

    def to_external_event(self, hint: EmailDeadlineHint) -> ExternalRawEvent:
        """Convert an email deadline hint into an ExternalRawEvent."""
        return ExternalRawEvent(
            event_id=_uid("ext_email"),
            source="email",
            source_detail="gmail",
            goal_id=hint.goal_id,
            raw_payload={
                "action": "deadline_hint",
                "email_id": hint.source_email_id,
                "subject": hint.subject_hint,
                "keywords": hint.extracted_keywords,
                "confidence": hint.confidence,
            },
            user_visible=True,
            revocable=True,
        )

    def batch_extract(
        self,
        emails: list[dict[str, str]],
        *,
        goal_id: str | None = None,
    ) -> list[EmailDeadlineHint]:
        """Batch extract deadline hints from multiple emails."""
        hints: list[EmailDeadlineHint] = []
        for email in emails:
            hint = self.extract_from_subject(
                email_id=email.get("email_id", _uid("em")),
                subject=email.get("subject", ""),
                goal_id=email.get("goal_id", goal_id),
            )
            if hint:
                hints.append(hint)
        return hints


class GitHubRepoBridge:
    """GitHub repo activity → ExternalRawEvent → project context for Spine.

    Summarizes GitHub activity per goal. All external signals are goal-bound
    and cannot directly write long-term model state.
    """

    def summarize_repo(
        self,
        repo_summary: GitHubRepoSummary,
    ) -> ExternalRawEvent:
        """Convert a GitHub repo summary to an ExternalRawEvent."""
        return ExternalRawEvent(
            event_id=_uid("ext_gh"),
            source="github",
            source_detail=f"{repo_summary.owner}/{repo_summary.repo_name}",
            goal_id=repo_summary.goal_id,
            raw_payload={
                "action": "repo_summary",
                "repo_name": repo_summary.repo_name,
                "recent_commits": repo_summary.recent_commits,
                "open_prs": repo_summary.open_prs,
                "open_issues": repo_summary.open_issues,
                "last_activity": repo_summary.last_activity,
            },
            user_visible=True,
            revocable=True,
        )

    def detect_project_velocity(
        self,
        summaries: list[GitHubRepoSummary],
        *,
        lookback_days: int = 7,
    ) -> dict[str, Any]:
        """Detect project velocity from recent GitHub activity."""
        active_repos = []
        stalled_repos = []

        for s in summaries:
            if s.recent_commits > 0:
                active_repos.append(s.repo_name)
            else:
                stalled_repos.append(s.repo_name)

        return {
            "active_repos": active_repos,
            "stalled_repos": stalled_repos,
            "total_commits": sum(s.recent_commits for s in summaries),
            "total_open_prs": sum(s.open_prs for s in summaries),
            "has_stalled": len(stalled_repos) > 0,
        }


class ExternalIntegrationGateway:
    """Unified entry point for all external integrations.

    ENFORCES: all external events MUST enter via ExternalRawEvent.
    ENFORCES: no external signal can bypass the Spine.
    ENFORCES: all external integrations are user-visible and revocable.
    """

    def __init__(self):
        self.calendar = CalendarSignalBridge()
        self.file_handler = FileIntegration()
        self.email_extractor = EmailDeadlineExtractor()
        self.github = GitHubRepoBridge()
        self.tool = ExternalToolBridge()
        self._connected_integrations: dict[str, dict[str, Any]] = {}

    def register_integration(
        self,
        user_id: str,
        integration_type: str,
        source_detail: str,
        *,
        goal_id: str | None = None,
    ) -> str:
        """Register a new integration. Returns integration_id."""
        iid = _uid("intg")
        self._connected_integrations[iid] = {
            "user_id": user_id,
            "integration_type": integration_type,
            "source_detail": source_detail,
            "goal_id": goal_id,
            "connected_at": datetime.now(UTC).isoformat(),
            "active": True,
        }
        logger.info(
            "Integration {} registered: type={} detail={} goal={}",
            iid, integration_type, source_detail, goal_id,
        )
        return iid

    def disconnect_integration(self, integration_id: str) -> bool:
        """Revoke an integration. Always returns True (idempotent disconnect)."""
        if integration_id in self._connected_integrations:
            self._connected_integrations[integration_id]["active"] = False
            logger.info("Integration {} disconnected", integration_id)
        return True

    def is_connected(self, integration_id: str) -> bool:
        return (
            integration_id in self._connected_integrations
            and self._connected_integrations[integration_id]["active"]
        )

    def route_to_spine(self, event: ExternalRawEvent) -> dict[str, Any]:
        """Route an ExternalRawEvent to the Spine.

        This is the SINGLE entry point. No external signal bypasses this.
        Returns a routing receipt that downstream Spine modules consume.
        """
        if not event.event_id:
            raise ValueError("ExternalRawEvent must have event_id")

        if event.source not in ("calendar", "file", "email", "github", "tool"):
            logger.warning("Unknown external source: {}", event.source)

        return {
            "event_type": "external_raw_event",
            "event_id": event.event_id,
            "source": event.source,
            "source_detail": event.source_detail,
            "goal_id": event.goal_id,
            "user_visible": event.user_visible,
            "revocable": event.revocable,
            "payload": event.raw_payload,
            "timestamp": event.timestamp,
        }

    def list_active_integrations(self, user_id: str) -> list[dict[str, Any]]:
        """List all active integrations for a user."""
        return [
            v for v in self._connected_integrations.values()
            if v["user_id"] == user_id and v.get("active", True)
        ]


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
