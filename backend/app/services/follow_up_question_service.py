from __future__ import annotations

import json
from pathlib import Path

from app.state_aggregator.schema import SufficiencySummaryValue

_TEMPLATE_PATH = Path(__file__).with_name("follow_up_question_templates.v1.json")


class FollowUpQuestionService:
    def __init__(self) -> None:
        self._templates = json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))

    def select_question(self, task_summary: SufficiencySummaryValue) -> str | None:
        missing = set(task_summary.top_missing_dimensions)
        if not missing:
            return None
        for dimension in ("target_object_resolved", "constraint_explicit", "intent_clarity"):
            if dimension in missing:
                return self._template_for_dimension(dimension)
        return self._templates[0]["message"] if self._templates else None

    def render_context_caveat(self, context_summary: SufficiencySummaryValue) -> str:
        missing = set(context_summary.top_missing_dimensions)
        parts: list[str] = []
        if "recent_user_state_known" in missing:
            parts.append("我对你近期的活跃节奏了解还有限。")
        if "relevant_memory_present" in missing:
            parts.append("我手头和这件事直接相关的记忆线索还不够完整。")
        if "social_context_loaded" in missing:
            parts.append("我对你当前涉及的社交背景掌握得不完整。")
        return " ".join(parts).strip()

    def _template_for_dimension(self, dimension: str) -> str:
        mapping = {
            "target_object_resolved": "task_need_target",
            "constraint_explicit": "task_need_constraint",
            "intent_clarity": "task_need_goal_boundary",
        }
        template_id = mapping.get(dimension)
        for item in self._templates:
            if item.get("template_id") == template_id:
                return str(item.get("message") or "")
        return str(self._templates[0]["message"] or "")
