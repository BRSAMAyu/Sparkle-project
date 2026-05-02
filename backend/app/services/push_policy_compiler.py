from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

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
        category_dismissal_counts_7d: dict[str, int] | None = None,
        device_context: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> PushDecision | None:
        if not getattr(push_opt_in, "enabled", False):
            return None
        if recent_delivery_count_24h >= self.DAILY_CAP:
            return None

        reference_time = now or _utcnow()
        dismissal_counts = category_dismissal_counts_7d or {}
        devices = dict(device_context or {})
        commitment = self._compile_commitment_follow_up(
            user_state=user_state,
            push_opt_in=push_opt_in,
            dismissed_categories_7d=dismissed_categories_7d,
            category_dismissal_counts_7d=dismissal_counts,
            device_context=devices,
            now=reference_time,
        )
        if commitment is not None:
            return commitment

        engagement = self._compile_engagement_recovery(
            user_state=user_state,
            push_opt_in=push_opt_in,
            dismissed_categories_7d=dismissed_categories_7d,
            category_dismissal_counts_7d=dismissal_counts,
            device_context=devices,
            now=reference_time,
        )
        if engagement is not None:
            return engagement
        return None

    def _compile_commitment_follow_up(
        self,
        *,
        user_state: UserStateV1,
        push_opt_in,
        dismissed_categories_7d: set[str],
        category_dismissal_counts_7d: dict[str, int],
        device_context: dict[str, Any],
        now: datetime,
    ) -> PushDecision | None:
        category = "commitment_follow_up"
        if not getattr(push_opt_in, "allow_commitment_follow_up", False):
            return None
        intrusiveness = self._intrusiveness_level(
            category=category,
            dismissed_categories_7d=dismissed_categories_7d,
            category_dismissal_counts_7d=category_dismissal_counts_7d,
        )
        if intrusiveness is None:
            return None
        field = user_state.commitment_summary
        if field is None or field.value.overdue_count <= 0:
            return None
        commitment_id = (
            field.value.pending_commitment_ids[0] if field.value.pending_commitment_ids else "commitment:unknown"
        )
        template = self.templates["commitment_follow_up_gentle"]
        due_at = field.value.next_due_at
        due_label = due_at.strftime("%m-%d %H:%M") if due_at else "之前约定的时间"
        scheduled = self._apply_quiet_hours(now, push_opt_in.quiet_hours_start, push_opt_in.quiet_hours_end)
        body = template["body"].replace("{due_label}", due_label)
        proactive_reason = f"你有一个约定已超过 {due_label}，Aurora 只做一次轻提醒。"
        route = self._chat_route(
            f"帮我收尾这个约定：{commitment_id}。先用一句话说明为什么提醒我，再给我一个最小下一步。"
        )
        return PushDecision(
            policy_id="CommitmentFollowUp",
            category=category,
            evidence_token=f"commitment:{commitment_id}",
            message_template_id=template["id"],
            scheduled_send_at=scheduled,
            title=template["title"],
            body=body,
            metadata=self._build_metadata(
                category=category,
                evidence={"commitment_id": commitment_id, "due_label": due_label},
                proactive_reason=proactive_reason,
                destination_route=route,
                intrusiveness_level=intrusiveness,
                wake_type="accountability",
                device_context=device_context,
            ),
        )

    def _compile_engagement_recovery(
        self,
        *,
        user_state: UserStateV1,
        push_opt_in,
        dismissed_categories_7d: set[str],
        category_dismissal_counts_7d: dict[str, int],
        device_context: dict[str, Any],
        now: datetime,
    ) -> PushDecision | None:
        category = "engagement_recovery"
        if not getattr(push_opt_in, "allow_engagement_recovery", False):
            return None
        intrusiveness = self._intrusiveness_level(
            category=category,
            dismissed_categories_7d=dismissed_categories_7d,
            category_dismissal_counts_7d=category_dismissal_counts_7d,
        )
        if intrusiveness is None:
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
        proactive_reason = f"你连续 {field.value.streak} 天的节奏中断了，Aurora 想帮你用最小动作回到状态。"
        route = self._chat_route("我刚被 Aurora 轻提醒回来，请先解释提醒原因，再给我一个 5 分钟重启动作。")
        return PushDecision(
            policy_id="EngagementRecovery",
            category=category,
            evidence_token=evidence_token,
            message_template_id=template["id"],
            scheduled_send_at=scheduled,
            title=template["title"],
            body=body,
            metadata=self._build_metadata(
                category=category,
                evidence={"streak_days": field.value.streak, "last_active_at": field.value.last_active_at.isoformat()},
                proactive_reason=proactive_reason,
                destination_route=route,
                intrusiveness_level=intrusiveness,
                wake_type="comeback",
                device_context=device_context,
            ),
        )

    def _intrusiveness_level(
        self,
        *,
        category: str,
        dismissed_categories_7d: set[str],
        category_dismissal_counts_7d: dict[str, int],
    ) -> str | None:
        dismissals = int(category_dismissal_counts_7d.get(category, 0) or 0)
        if dismissals >= 2:
            return None
        if dismissals == 1 or category in dismissed_categories_7d:
            return "reduced"
        return "standard"

    def _build_metadata(
        self,
        *,
        category: str,
        evidence: dict[str, Any],
        proactive_reason: str,
        destination_route: str,
        intrusiveness_level: str,
        wake_type: str,
        device_context: dict[str, Any],
    ) -> dict[str, Any]:
        target_device_count = int(device_context.get("active_device_count") or 0)
        metadata = {
            **evidence,
            "wake_type": wake_type,
            "proactive_reason": proactive_reason,
            "destination_route": destination_route,
            "deep_link": destination_route,
            "route": destination_route,
            "primary_action": {
                "label": "查看原因",
                "route": destination_route,
                "action_type": "aurora_proactive_nudge",
                "payload": {"category": category},
            },
            "intrusiveness_level": intrusiveness_level,
            "respectfulness_reason": "recent_dismissal" if intrusiveness_level == "reduced" else "policy_match",
            "feedback_controls": [
                {
                    "action": "dismissed",
                    "label": "这次不用了",
                    "effect": "reduces_future_confidence_for_category",
                },
                {
                    "action": "disable_category",
                    "label": "以后少提醒这类",
                    "effect": "disables_or_reduces_this_category",
                },
            ],
            "target_device_count": target_device_count,
            "target_platforms": list(device_context.get("platforms") or []),
            "last_active_device_id": device_context.get("last_active_device_id"),
            "last_active_at": device_context.get("last_active_at"),
            "cross_device_state_key": f"aurora_push:{category}",
        }
        return {key: value for key, value in metadata.items() if value not in (None, "", [])}

    def _chat_route(self, prompt: str) -> str:
        return f"/chat?{urlencode({'prompt': prompt, 'source': 'aurora_proactive'})}"

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
