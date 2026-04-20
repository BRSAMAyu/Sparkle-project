from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.state_aggregator.schema import UserStateV1


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


TEMPLATES_PATH = Path(__file__).resolve().with_name("push_message_templates.v1.json")


@dataclass(frozen=True)
class PushDecision:
    policy_id: str
    category: str
    evidence_token: str
    message_template_id: str
    scheduled_send_at: datetime
    title: str
    body: str
    metadata: dict[str, Any]


class PushPolicyCompiler:
    DAILY_CAP = 2

    def __init__(self) -> None:
        payload = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        self.templates = {item["id"]: item for item in payload}

    def compile(
        self,
        *,
        user_state: UserStateV1,
        push_opt_in,
        recent_delivery_count_24h: int,
        dismissed_categories_7d: set[str],
        now: datetime | None = None,
    ) -> PushDecision | None:
        if not getattr(push_opt_in, "enabled", False):
            return None
        if recent_delivery_count_24h >= self.DAILY_CAP:
            return None

        reference_time = now or _utcnow()
        commitment = self._compile_commitment_follow_up(
            user_state=user_state,
            push_opt_in=push_opt_in,
            dismissed_categories_7d=dismissed_categories_7d,
            now=reference_time,
        )
        if commitment is not None:
            return commitment

        engagement = self._compile_engagement_recovery(
            user_state=user_state,
            push_opt_in=push_opt_in,
            dismissed_categories_7d=dismissed_categories_7d,
            now=reference_time,
        )
        if engagement is not None:
            return engagement
        return None

    def _compile_commitment_follow_up(self, *, user_state: UserStateV1, push_opt_in, dismissed_categories_7d: set[str], now: datetime) -> PushDecision | None:
        if not getattr(push_opt_in, "allow_commitment_follow_up", False):
            return None
        if "commitment_follow_up" in dismissed_categories_7d:
            return None
        field = user_state.commitment_summary
        if field is None or field.value.overdue_count <= 0:
            return None
        commitment_id = field.value.pending_commitment_ids[0] if field.value.pending_commitment_ids else "commitment:unknown"
        template = self.templates["commitment_follow_up_gentle"]
        due_at = field.value.next_due_at
        due_label = due_at.strftime("%m-%d %H:%M") if due_at else "之前约定的时间"
        scheduled = self._apply_quiet_hours(now, push_opt_in.quiet_hours_start, push_opt_in.quiet_hours_end)
        body = template["body"].replace("{due_label}", due_label)
        return PushDecision(
            policy_id="CommitmentFollowUp",
            category="commitment_follow_up",
            evidence_token=f"commitment:{commitment_id}",
            message_template_id=template["id"],
            scheduled_send_at=scheduled,
            title=template["title"],
            body=body,
            metadata={"commitment_id": commitment_id, "due_label": due_label},
        )

    def _compile_engagement_recovery(self, *, user_state: UserStateV1, push_opt_in, dismissed_categories_7d: set[str], now: datetime) -> PushDecision | None:
        if not getattr(push_opt_in, "allow_engagement_recovery", False):
            return None
        if "engagement_recovery" in dismissed_categories_7d:
            return None
        field = user_state.engagement_state
        if field is None or field.value.last_active_at is None:
            return None
        if field.value.streak < 3:
            return None
        if field.value.last_active_at >= now - timedelta(hours=72):
            return None
        template = self.templates["engagement_recovery_soft"]
        scheduled = self._apply_quiet_hours(now, push_opt_in.quiet_hours_start, push_opt_in.quiet_hours_end)
        body = template["body"].replace("{streak_days}", str(field.value.streak))
        evidence_token = f"engagement:{field.value.last_active_at.isoformat()}"
        return PushDecision(
            policy_id="EngagementRecovery",
            category="engagement_recovery",
            evidence_token=evidence_token,
            message_template_id=template["id"],
            scheduled_send_at=scheduled,
            title=template["title"],
            body=body,
            metadata={"streak_days": field.value.streak, "last_active_at": field.value.last_active_at.isoformat()},
        )

    def _apply_quiet_hours(self, now: datetime, quiet_start: str, quiet_end: str) -> datetime:
        start_hour, start_minute = (int(part) for part in quiet_start.split(":"))
        end_hour, end_minute = (int(part) for part in quiet_end.split(":"))
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        in_quiet_hours = current_minutes >= start_minutes or current_minutes < end_minutes
        if in_quiet_hours:
            base = now if current_minutes < end_minutes else now + timedelta(days=1)
            return base.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        return now

