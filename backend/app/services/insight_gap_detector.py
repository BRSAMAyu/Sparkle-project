from __future__ import annotations

import re
from typing import Any

from app.orchestration.planning_intent import is_planning_like_turn
from app.orchestration.schemas import CompiledInsightState


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


class InsightGapDetector:
    """
    Insight Gap Detector - Phase A2
    Identifies missing high-signal information required for high-quality planning.
    """

    PLANNING_GAPS = {
        "baseline_mastery": "Missing current knowledge level in target domain.",
        "deadline": "Missing time constraint or target date.",
        "capacity_hours": "Missing daily or weekly time availability.",
        "goal_specificity": "Target goal is too vague for task decomposition.",
        "material_source": "Missing curriculum or source material context.",
    }

    _TIME_PATTERN = re.compile(
        r"("
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|"
        r"\b\d{1,2}[-/]\d{1,2}\b|"
        r"\b\d+\s*(day|days|week|weeks|month|months|hour|hours)\b|"
        r"\b(today|tomorrow|tonight|this week|next week|deadline|by|until|exam|test|quiz)\b|"
        r"\d+\s*(天|周|个月|月|小时)|"
        r"(今天|明天|后天|本周|下周|月底|月考|期中|期末|考试|截止|截至|在.+前)"
        r")",
        re.IGNORECASE,
    )
    _MATERIAL_PATTERN = re.compile(
        r"(教材|讲义|资料|笔记|真题|题库|课件|notes?|slides?|pdf|document|documents|textbook|materials?)",
        re.IGNORECASE,
    )
    _OUTCOME_HINT_PATTERN = re.compile(
        r"(掌握|学会|完成|冲刺|复习|通过|提高|修完|计划|规划|考试|期中|期末|review|prepare|finish|build|learn|master|exam|plan)",
        re.IGNORECASE,
    )

    async def detect_gaps(
        self,
        *,
        insight_state: CompiledInsightState,
        user_message: str = "",
        intent: str = "plan",
        planning_context: dict[str, Any] | None = None,
    ) -> list[str]:
        context = _as_dict(planning_context)
        vision = _as_dict(context.get("vision"))
        current_state = _as_dict(context.get("current_state"))

        text_corpus = self._build_text_corpus(
            user_message=user_message,
            context=context,
            vision=vision,
            current_state=current_state,
        )
        planning_like = is_planning_like_turn(
            normalized_intent=intent,
            route_intent=_strip(context.get("route_intent")),
            user_message=user_message or text_corpus,
            decision_context=_as_dict(context.get("decision_context")),
        )

        gaps: list[str] = []

        if self._needs_baseline_mastery(insight_state=insight_state, text_corpus=text_corpus, vision=vision):
            gaps.append("baseline_mastery")

        if self._needs_capacity(insight_state=insight_state, text_corpus=text_corpus, current_state=current_state):
            gaps.append("capacity_hours")

        if self._needs_deadline(insight_state=insight_state, text_corpus=text_corpus, vision=vision):
            gaps.append("deadline")

        if planning_like and self._needs_goal_specificity(text_corpus=text_corpus, vision=vision):
            gaps.append("goal_specificity")

        if planning_like and self._needs_material_source(context=context, text_corpus=text_corpus, vision=vision):
            gaps.append("material_source")

        return gaps

    def generate_questions(self, gaps: list[str]) -> list[str]:
        """Generate high-value clarification questions for missing gaps."""
        templates = {
            "baseline_mastery": "你目前对这个主题的掌握大概在哪个水平？是零基础、刚入门，还是已经做过一些题/学过一轮？",
            "deadline": "你希望在什么时间点前达成这个目标？如果有考试或截止日期，也可以直接告诉我。",
            "capacity_hours": "你这段时间每天或每周大概能稳定投入多少时间？",
            "goal_specificity": "你这次最想拿下的具体结果是什么？比如是通过考试、补某一章、还是解决某类题。",
            "material_source": "你现在有要优先依据的教材、讲义、笔记或题库吗？如果有，我可以按这些材料来规划。",
        }
        ordered = [templates[gap] for gap in gaps if gap in templates]
        return ordered[:3]

    def _build_text_corpus(
        self,
        *,
        user_message: str,
        context: dict[str, Any],
        vision: dict[str, Any],
        current_state: dict[str, Any],
    ) -> str:
        parts = [
            user_message,
            context.get("current_query"),
            context.get("context_briefing_note"),
            context.get("goal_text"),
            vision.get("primary_goal"),
            vision.get("active_plan"),
            vision.get("why_now"),
            current_state.get("snapshot"),
        ]
        return " | ".join(_strip(part) for part in parts if _strip(part))

    def _needs_baseline_mastery(
        self,
        *,
        insight_state: CompiledInsightState,
        text_corpus: str,
        vision: dict[str, Any],
    ) -> bool:
        overall_mastery = float(insight_state.current_state.get("overall_mastery") or 0.0)
        active_subjects = [item for item in (insight_state.current_state.get("active_subjects") or []) if _strip(item)]
        if overall_mastery > 0 or active_subjects:
            return False

        has_study_goal = any(_strip(value) for value in (vision.get("primary_goal"), vision.get("active_plan")))
        return has_study_goal or bool(self._OUTCOME_HINT_PATTERN.search(text_corpus))

    def _needs_capacity(
        self,
        *,
        insight_state: CompiledInsightState,
        text_corpus: str,
        current_state: dict[str, Any],
    ) -> bool:
        stable_traits = insight_state.stable_traits
        time_keys = {"available_hours", "daily_cap", "focus_time", "study_window", "weekly_hours"}
        if any(stable_traits.get(key) for key in time_keys):
            return False
        if _strip(current_state.get("capacity_signal")):
            return False
        return not bool(re.search(r"(\d+\s*(小时|h|hour|hours|分钟|min))", text_corpus, re.IGNORECASE))

    def _needs_deadline(
        self,
        *,
        insight_state: CompiledInsightState,
        text_corpus: str,
        vision: dict[str, Any],
    ) -> bool:
        if _strip(insight_state.stable_traits.get("deadline")):
            return False
        if self._TIME_PATTERN.search(text_corpus):
            return False
        return not _strip(vision.get("why_now"))

    def _needs_goal_specificity(
        self,
        *,
        text_corpus: str,
        vision: dict[str, Any],
    ) -> bool:
        goal_text = " ".join(
            _strip(item)
            for item in (vision.get("primary_goal"), vision.get("active_plan"), text_corpus)
            if _strip(item)
        )
        if not goal_text:
            return True

        cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", goal_text))
        latin_words = len(re.findall(r"[A-Za-z0-9]+", goal_text))
        has_outcome_hint = bool(self._OUTCOME_HINT_PATTERN.search(goal_text))
        has_scope_hint = bool(re.search(r"(第.+章|chapter|topic|unit|module|专题|题型|concept|概念)", goal_text, re.IGNORECASE))

        if has_outcome_hint and (has_scope_hint or cjk_chars >= 8 or latin_words >= 4):
            return False

        signal_units = cjk_chars + (latin_words * 2)
        return signal_units < 8

    def _needs_material_source(
        self,
        *,
        context: dict[str, Any],
        text_corpus: str,
        vision: dict[str, Any],
    ) -> bool:
        if self._has_material_source(context):
            return False
        if self._MATERIAL_PATTERN.search(text_corpus):
            return False

        goal_text = " ".join(_strip(item) for item in (vision.get("primary_goal"), vision.get("active_plan"), text_corpus) if _strip(item))
        if not goal_text:
            return False
        return bool(re.search(r"(exam|考试|复习|冲刺|题|习题|练习|mock)", goal_text, re.IGNORECASE))

    def _has_material_source(self, context: dict[str, Any]) -> bool:
        grounding = _as_dict(context.get("user_material_grounding"))
        if grounding.get("results"):
            return True
        if _strip(grounding.get("query")):
            return True

        file_ids = [item for item in _as_list(context.get("file_ids")) if _strip(item)]
        if file_ids:
            return True

        materials = [
            context.get("uploaded_materials"),
            context.get("attached_materials"),
            context.get("material_sources"),
        ]
        return any(_as_list(item) for item in materials)
