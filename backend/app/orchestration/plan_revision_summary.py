from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


@dataclass(frozen=True)
class PlanRevisionSummary:
    why_plan_changed: str
    what_assumption_failed: str
    what_stays: str
    what_changes: str
    new_next_action: str
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "why_plan_changed": self.why_plan_changed,
            "what_assumption_failed": self.what_assumption_failed,
            "what_stays": self.what_stays,
            "what_changes": self.what_changes,
            "new_next_action": self.new_next_action,
            "created_at": self.created_at,
        }
