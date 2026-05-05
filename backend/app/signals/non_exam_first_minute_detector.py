"""
Core: execution
Phase: sense→clarify→plan→execute→reflect
Stage: Signal-to-Action Spine P1-3 Non-Exam First Minute Detector

First-minute natural language detection for non-exam goal types:
job_search, project, and habit (fitness/routine building).

Mirrors ExamRescueDetector pattern: keyword/regex matching → FirstMinuteSnapshot → ActionableSignal.
Called from SpineOrchestrator.on_first_message() as fallback when ExamRescueDetector returns None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.exam_rescue_detector import FirstMinuteSnapshot

# ── Job Search patterns ────────────────────────────────────────────

_JOB_SEARCH_INTENT = (
    "面试", "求职", "找工作", "投简历", "简历", "offer",
    "interview", "job", "career", "hire", "recruit",
    "校招", "社招", "春招", "秋招", "内推",
    "behavioral", "coding", "leetcode", "算法面", "系统设计",
    "hr面", "技术面", "终面", "一面", "二面",
)

_JOB_DEADLINE_TERMS = (
    "后天面试", "下周面试", "明天面试", "马上面试", "即将面试",
    "面试倒计时", "面试在即",
)

_JOB_STRESS = (
    "紧张", "没准备好", "怕过不了", "怕挂", "不敢面",
    "焦虑", "没自信", "不会答", "答不上来", "裸面",
    "nervous", "unprepared", "scared",
)

_JOB_PREP_KEYWORDS = (
    "刷题", "mock", "模拟面试", "准备面试", "面经", "八股文",
    "自我介绍", "项目介绍", "抗压",
)

# ── Project patterns ───────────────────────────────────────────────

_PROJECT_INTENT = (
    "项目", "交付", "上线", "部署", "发版", "迭代",
    "project", "milestone", "deliverable", "release", "deploy",
    "MVP", "mvp", "原型", "demo", "需求", "产品",
    "毕业设计", "毕设", "课程设计", "课设",
    "论文", "dissertation", "thesis",
)

_PROJECT_DEADLINE_TERMS = (
    "下周交付", "月底上线", "明天交", "后天交", "截止",
    "deadline", "due", "截止日期",
)

_PROJECT_STUCK = (
    "不知道从哪开始", "没有思路", "不知道怎么做", "卡住了", "进度落后",
    "做不完", "来不及", "需求不明确", "方向不明确",
    "stuck", "blocked", "overwhelmed",
)

_PROJECT_SCOPE = (
    "范围太大", "太大了", "拆分", "太复杂", "简化",
    "scope", "break down",
)

# ── Habit / Fitness patterns ───────────────────────────────────────

_HABIT_INTENT = (
    "健身", "减肥", "跑步", "锻炼", "运动", "早起", "早睡",
    "习惯", "坚持", "戒", "自律", "养成",
    "exercise", "workout", "fitness", "gym", "running",
    "habit", "routine", "discipline", "wake up early",
    "冥想", "读书", "阅读", "学英语", "练琴",
    "饮食", "健康", "睡眠",
)

_HABIT_STRUGGLE = (
    "坚持不下去", "总是放弃", "三天打鱼", "半途而废", "管不住自己",
    "没毅力", "拖延", "懒", "坚持不了",
    "can't stick", "keep failing", "give up", "lazy",
)

_HABIT_GOAL = (
    "每天", "每周", "养成习惯", "长期", "持续",
    "每天坚持", "打卡", "连续", "目标",
    "daily", "weekly", "consistent",
)

# ── Shared deadline extraction ─────────────────────────────────────

_DEADLINE_PATTERNS = (
    re.compile(r"(\d+)\s*天\s*(后|内|之内|就)", re.IGNORECASE),
    re.compile(r"还有\s*(\d+)\s*天", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*(?:days?|d)\s*(?:after|before|left|until)\b", re.IGNORECASE),
)

_RELATIVE_DATE_MAP: dict[str, int] = {
    "明天": 1, "后天": 2, "大后天": 3,
    "下周": 7, "下周末": 9, "这周末": 3,
    "月底": 15, "下个月": 30,
}


def _extract_deadline_days(text: str) -> int | None:
    for pat in _DEADLINE_PATTERNS:
        m = pat.search(text)
        if m:
            for g in m.groups():
                if g and g.isdigit():
                    return int(g)
    text_lower = text.lower()
    for expr, days in sorted(_RELATIVE_DATE_MAP.items(), key=lambda x: -len(x[0])):
        if expr in text_lower:
            return days
    return None


def _any_match(text: str, terms: tuple[str, ...]) -> bool:
    return any(t in text for t in terms)


# ── Detector ───────────────────────────────────────────────────────


class NonExamFirstMinuteDetector:
    """Detects non-exam goal types from the first user message.

    Covers: job_search, project, habit (fitness/routine).
    Returns FirstMinuteSnapshot reusing the exam detector's dataclass
    with goal-type-specific modes and hypotheses.
    """

    def analyze_first_message(
        self,
        message: str,
        *,
        is_new_conversation: bool = True,
        user_id: str = "",
        conversation_context: dict[str, Any] | None = None,
    ) -> FirstMinuteSnapshot | None:
        text = str(message or "").strip().lower()
        if not text:
            return None
        if len(text) > 2000:
            text = text[:2000]

        # Try each goal type in priority order
        return (
            self._detect_job_search(text)
            or self._detect_project(text)
            or self._detect_habit(text)
        )

    # ── Job Search ──────────────────────────────────────────────

    def _detect_job_search(self, text: str) -> FirstMinuteSnapshot | None:
        if not _any_match(text, _JOB_SEARCH_INTENT):
            return None

        has_deadline = _any_match(text, _JOB_DEADLINE_TERMS)
        deadline_days = _extract_deadline_days(text) if has_deadline else None
        has_stress = _any_match(text, _JOB_STRESS)
        has_prep = _any_match(text, _JOB_PREP_KEYWORDS)

        if not (has_stress or has_prep or has_deadline):
            return None

        confidence = 0.60
        if has_deadline:
            confidence += 0.15
        if has_stress:
            confidence += 0.10
        if has_prep:
            confidence += 0.10
        confidence = min(confidence, 0.92)

        mode = "job_search_urgent" if (has_deadline and has_stress) else "job_search_prep"
        hypothesis = (
            f"你正在准备面试，{'时间紧迫' if has_deadline else '需要系统准备'}。"
            "我们可以从最高频面试题和模拟练习开始，快速建立应答肌肉记忆。"
        )
        if has_prep:
            next_action = "梳理你的面试准备状态，找出最大提分点"
        elif has_deadline:
            next_action = "制定面试冲刺计划，聚焦最高频考点"
        else:
            next_action = "帮你梳理面试准备路线图"

        return FirstMinuteSnapshot(
            detected_mode=mode,
            path_mode="urgent_prep" if has_deadline else "structured_prep",
            deadline_days=deadline_days,
            baseline="unknown",
            subject="job_search",
            next_best_action=next_action,
            first_user_visible_hypothesis=hypothesis,
            confidence=confidence,
        )

    # ── Project ─────────────────────────────────────────────────

    def _detect_project(self, text: str) -> FirstMinuteSnapshot | None:
        if not _any_match(text, _PROJECT_INTENT):
            return None

        has_deadline = _any_match(text, _PROJECT_DEADLINE_TERMS)
        deadline_days = _extract_deadline_days(text) if has_deadline else None
        has_stuck = _any_match(text, _PROJECT_STUCK)
        has_scope = _any_match(text, _PROJECT_SCOPE)

        if not (has_stuck or has_scope or has_deadline):
            return None

        confidence = 0.55
        if has_deadline:
            confidence += 0.20
        if has_stuck:
            confidence += 0.15
        if has_scope:
            confidence += 0.10
        confidence = min(confidence, 0.90)

        mode = "project_rescue" if (has_deadline and has_stuck) else "project_build"
        hypothesis = (
            f"你有一个{'紧急的' if has_deadline else ''}项目需要推进。"
            "先帮你拆解成最小可执行步骤，确保每次坐下来都知道做什么。"
        )
        if has_stuck:
            next_action = "帮你厘清当前卡点和下一步行动"
        elif has_scope:
            next_action = "帮你缩小范围到最小可行交付"
        else:
            next_action = "帮你拆解项目里程碑和本周任务"

        return FirstMinuteSnapshot(
            detected_mode=mode,
            path_mode="milestone_driven" if has_deadline else "iterative",
            deadline_days=deadline_days,
            baseline="unknown",
            subject="project",
            next_best_action=next_action,
            first_user_visible_hypothesis=hypothesis,
            confidence=confidence,
        )

    # ── Habit / Fitness ─────────────────────────────────────────

    def _detect_habit(self, text: str) -> FirstMinuteSnapshot | None:
        if not _any_match(text, _HABIT_INTENT):
            return None

        has_struggle = _any_match(text, _HABIT_STRUGGLE)
        has_goal = _any_match(text, _HABIT_GOAL)

        if not (has_struggle or has_goal):
            return None

        confidence = 0.55
        if has_struggle:
            confidence += 0.20
        if has_goal:
            confidence += 0.10
        confidence = min(confidence, 0.85)

        mode = "habit_recovery" if has_struggle else "habit_build"
        hypothesis = (
            "你想养成一个新习惯。研究显示，关键不是毅力，而是降低启动门槛。"
            "我们帮你设计最小启动单元，让坚持变得自然。"
        )
        next_action = "帮你设定最小可行习惯目标和触发条件"

        return FirstMinuteSnapshot(
            detected_mode=mode,
            path_mode="micro_habit" if has_struggle else "progressive",
            deadline_days=None,
            baseline="unknown",
            subject="habit",
            next_best_action=next_action,
            first_user_visible_hypothesis=hypothesis,
            confidence=confidence,
        )

    # ── Signal conversion ───────────────────────────────────────

    def to_actionable_signal(
        self,
        snapshot: FirstMinuteSnapshot,
        *,
        user_id: str,
    ):
        """Convert snapshot to ActionableSignal for non-exam goal modes."""
        from app.signals.types import ActionableSignal, _uid

        claim_map: dict[str, str] = {
            "job_search_urgent": "job_interview_imminent",
            "job_search_prep": "job_search_detected",
            "project_rescue": "project_deadline_urgent",
            "project_build": "project_detected",
            "habit_recovery": "habit_struggle_detected",
            "habit_build": "habit_goal_detected",
        }

        effects_map: dict[str, list[str]] = {
            "job_search_urgent": ["activate_interview_sprint", "focus_high_frequency_topics", "schedule_mock"],
            "job_search_prep": ["build_interview_prep_plan", "map_skill_gaps", "practice_progression"],
            "project_rescue": ["reduce_scope", "split_to_milestones", "offer_one_next_step"],
            "project_build": ["scope_to_mvp", "define_milestones", "plan_first_sprint"],
            "habit_recovery": ["lower_activation_energy", "design_micro_trigger", "streak_recovery"],
            "habit_build": ["set_micro_goal", "design_trigger_routine", "progressive_overload"],
        }

        claim = claim_map.get(snapshot.detected_mode, "non_exam_goal_detected")
        effects = effects_map.get(snapshot.detected_mode, ["adapt_to_goal_type"])

        return ActionableSignal(
            signal_id=_uid("nefm"),
            source_event_ids=["first_message_non_exam"],
            source_system="first_minute_non_exam",
            state_key="goal_mode",
            claim=claim,
            confidence=snapshot.confidence,
            scope="current_sprint",
            ttl_hours=72,
            evidence_summary=f"User first message indicates {snapshot.detected_mode} goal.",
            possible_effects=effects,
            priority="high" if "urgent" in snapshot.detected_mode or "rescue" in snapshot.detected_mode else "medium",
        )
