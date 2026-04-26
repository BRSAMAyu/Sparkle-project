"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P0-1 FirstMinuteSnapshot

ExamRescueDetector — 检测新用户首次消息中的考试紧急情况。
目标：60 秒内让用户感到被理解，不需要填完整表单。

检测信号：考试紧迫 + 基础薄弱 → exam_rescue 判断。
输出：FirstMinuteSnapshot → exam_rescue mode → 低成本下一步。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid

# ── 紧迫信号模式 ──────────────────────────────────────────────────
_DEADLINE_PATTERNS = (
    r"(\d+)\s*天\s*(后|内|之内|就)",
    r"还有\s*(\d+)\s*天",
    r"\b(\d+)\s*(days?|d)\s*(after|before|left|until)\b",
    r"\b(exam|test|final)\s*(in|after|within)\s*(\d+)\s*(days?|d)\b",
)

_BASELINE_PATTERNS = (
    r"(零基础|没学|没怎么学|基本不会|完全不懂|什么都不会|白板|没上过课)",
    r"(零|0)\s*(基础|掌握)",
    r"(挂科|不挂|先过|及格|过线|别挂|不想挂|求过|保过|60\s*分)",
    r"\b(fail|pass|barely|zero|nothing)\b",
)

_SUBJECT_PATTERNS = (
    r"(计网|计算机网络|computer\s*net)",
    r"(高数|高等数学|微积分|calculus|math)",
    r"(线代|线性代数|linear\s*algebra)",
    r"(概率|概率论|probability)",
    r"(数据结构|data\s*structure)",
    r"(操作系统|os|operating\s*system)",
    r"(编译原理|compiler)",
    r"(离散|离散数学|discrete)",
    r"(数据库|database)",
    r"(算法|algorithm)",
    r"(物理|physics)",
    r"(化学|chemistry)",
    r"(政治|毛概|马原|思政)",
    r"(四六级|英语|cet|ielts|toefl)",
)

_SUBJECT_MAP: dict[str, str] = {
    "计网": "computer_networks",
    "计算机网络": "computer_networks",
    "computer net": "computer_networks",
    "高数": "advanced_mathematics",
    "高等数学": "advanced_mathematics",
    "微积分": "calculus",
    "线代": "linear_algebra",
    "线性代数": "linear_algebra",
    "概率": "probability",
    "概率论": "probability",
    "数据结构": "data_structures",
    "操作系统": "operating_systems",
    "编译原理": "compilers",
    "离散": "discrete_mathematics",
    "数据库": "databases",
    "算法": "algorithms",
    "物理": "physics",
    "化学": "chemistry",
    "政治": "politics",
    "毛概": "politics",
    "马原": "politics",
    "四六级": "english_cet",
    "英语": "english",
}

_ENEMY_OF_GOOD_ENOUGH = (
    r"(冲高分|90\s*分|95\s*分|满分|first\s*class|distinction|A\+?)",
)


@dataclass
class FirstMinuteSnapshot:
    """P0-1: 新用户首次消息解析结果。"""
    detected_mode: str              # "exam_rescue" | "exam_build" | "standard"
    path_mode: str                  # "minimum_pass" | "solid_pass" | "high_score" | "exploration"
    deadline_days: int | None       # 从消息推断的天数
    baseline: str                   # "near_zero" | "weak" | "moderate" | "unknown"
    subject: str | None             # 学科标识
    next_best_action: str           # 建议的下一步
    first_user_visible_hypothesis: str  # 60 秒啊哈
    confidence: float
    signal_id: str | None = None    # 如果生成了 ActionableSignal

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_mode": self.detected_mode,
            "path_mode": self.path_mode,
            "deadline_days": self.deadline_days,
            "baseline": self.baseline,
            "subject": self.subject,
            "next_best_action": self.next_best_action,
            "first_user_visible_hypothesis": self.first_user_visible_hypothesis,
            "confidence": self.confidence,
            "signal_id": self.signal_id,
        }


def _extract_deadline_days(text: str) -> int | None:
    """从文本中提取 deadline 天数。"""
    for pattern in _DEADLINE_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            # Try each group to find the digit group
            for group in m.groups():
                if group and group.isdigit():
                    return int(group)
    return None


def _detect_subject(text: str) -> str | None:
    """从文本中识别学科。优先匹配更具体 key（如'四六级' > '英语'）。"""
    # First pass: check all map keys against full text, longest first
    text_lower = text.lower()
    for key in sorted(_SUBJECT_MAP, key=len, reverse=True):
        if key in text_lower:
            return _SUBJECT_MAP[key]
    # Fallback: regex patterns
    for pattern in _SUBJECT_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            matched = m.group(0).lower().strip()
            for key in sorted(_SUBJECT_MAP, key=len, reverse=True):
                if key in matched:
                    return _SUBJECT_MAP[key]
    return None


def _is_high_score_target(text: str) -> bool:
    """用户目标是冲高分。"""
    return bool(re.search("|".join(_ENEMY_OF_GOOD_ENOUGH), text, flags=re.IGNORECASE))


class ExamRescueDetector:
    """
    检测新用户首次消息中的考试紧急情况。

    核心原则：
    - 不要求先完成完整表单
    - 60 秒内输出个性化判断
    - 给出低成本下一步
    - 给出可纠正选项
    """

    def analyze_first_message(
        self,
        message: str,
        *,
        is_new_conversation: bool = True,
        user_id: str = "",
        conversation_context: dict[str, Any] | None = None,
    ) -> FirstMinuteSnapshot | None:
        """
        分析用户首次消息，检测是否是 exam_rescue 场景。

        Returns:
            FirstMinuteSnapshot if exam urgency detected, None otherwise.
        """
        text = message.strip()
        if not text:
            return None

        # 检查 deadline 紧迫信号
        has_deadline = any(
            re.search(p, text, flags=re.IGNORECASE)
            for p in _DEADLINE_PATTERNS
        )
        # Also check for X天 + 考试 in same sentence (e.g. "7天后考试")
        if not has_deadline:
            has_deadline = bool(re.search(r"\d+\s*天.*(?:考试|考|测验|期末)", text, flags=re.IGNORECASE))
        deadline_days = _extract_deadline_days(text)

        # 检查基础薄弱信号
        has_weak_baseline = any(
            re.search(p, text, flags=re.IGNORECASE)
            for p in _BASELINE_PATTERNS
        )

        # 如果既没有 deadline 也没有基础薄弱，不是 exam_rescue
        if not has_deadline and not has_weak_baseline:
            return None

        # 检查学科
        subject = _detect_subject(text)

        # 检查目标等级
        high_score = _is_high_score_target(text)

        # 确定 mode
        if has_deadline and deadline_days is not None and deadline_days <= 14:
            detected_mode = "exam_rescue"
        elif has_deadline:
            detected_mode = "exam_build"
        elif has_weak_baseline:
            detected_mode = "exam_rescue"  # 有基础薄弱信号即进入 rescue
        else:
            return None

        # 确定 path_mode
        if high_score:
            path_mode = "high_score"
        elif has_weak_baseline:
            path_mode = "minimum_pass"
        else:
            path_mode = "solid_pass"

        # 确定 baseline
        if has_weak_baseline:
            baseline = "near_zero"
        else:
            baseline = "unknown"

        # 确定 next_best_action
        next_best_action = self._suggest_next_action(
            has_deadline=has_deadline,
            deadline_days=deadline_days,
            has_weak_baseline=has_weak_baseline,
        )

        # 生成 60 秒啊哈
        hypothesis = self._build_first_hypothesis(
            detected_mode=detected_mode,
            path_mode=path_mode,
            deadline_days=deadline_days,
            baseline=baseline,
            subject=subject,
        )

        # 计算置信度
        confidence = self._compute_confidence(
            has_deadline=has_deadline,
            deadline_days=deadline_days,
            has_weak_baseline=has_weak_baseline,
            has_subject=subject is not None,
        )

        snapshot = FirstMinuteSnapshot(
            detected_mode=detected_mode,
            path_mode=path_mode,
            deadline_days=deadline_days,
            baseline=baseline,
            subject=subject,
            next_best_action=next_best_action,
            first_user_visible_hypothesis=hypothesis,
            confidence=confidence,
        )

        logger.info(
            "FirstMinuteSnapshot: mode={} path={} deadline={}d baseline={} subject={} conf={:.2f}",
            detected_mode, path_mode, deadline_days, baseline, subject, confidence,
        )

        return snapshot

    def to_actionable_signal(
        self,
        snapshot: FirstMinuteSnapshot,
        *,
        user_id: str,
        message_id: str = "",
    ) -> ActionableSignal | None:
        """
        将 FirstMinuteSnapshot 转为 ActionableSignal。
        只有 exam_rescue 模式才生成 signal。
        """
        if snapshot.detected_mode != "exam_rescue":
            return None

        subject_label = snapshot.subject or "unknown"
        deadline_str = f"{snapshot.deadline_days} 天" if snapshot.deadline_days else "未知"

        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[message_id] if message_id else [],
            source_system="first_minute",
            state_key="goal_mode",
            claim="exam_rescue_detected",
            confidence=snapshot.confidence,
            scope="current_sprint",
            ttl_hours=168,  # 7 days
            evidence_summary=(
                f"新用户首次消息检测到考试紧迫：{subject_label}，"
                f"期限 {deadline_str}，基础 {snapshot.baseline}，"
                f"路径模式 {snapshot.path_mode}。"
            ),
            possible_effects=[
                "exam_rescue_mode",
                "skip_full_form",
                "suggest_diagnostic_or_upload",
                "set_sprint_policy",
            ],
            priority="high",
        )

        snapshot.signal_id = signal.signal_id
        logger.info("ExamRescue signal: {} for user={}", signal.signal_id, user_id)
        return signal

    def _suggest_next_action(
        self,
        *,
        has_deadline: bool,
        deadline_days: int | None,
        has_weak_baseline: bool,
    ) -> str:
        if has_weak_baseline and has_deadline:
            return "diagnostic_or_upload_materials"
        if has_weak_baseline:
            return "diagnostic"
        if has_deadline and deadline_days is not None and deadline_days <= 7:
            return "suggest_minimum_pass_path"
        return "standard_onboarding"

    def _build_first_hypothesis(
        self,
        *,
        detected_mode: str,
        path_mode: str,
        deadline_days: int | None,
        baseline: str,
        subject: str | None,
    ) -> str:
        if detected_mode == "exam_rescue" and path_mode == "minimum_pass":
            return (
                "这不是普通学习计划，而是 "
                f"{deadline_days or '?'} 天先过线抢救。"
                "普通复习计划会害你，因为它会把时间平均分给所有章节。"
            )
        if detected_mode == "exam_rescue":
            return (
                "你的基础偏弱，时间有限。"
                "我们要先找高频、可训练、最可能转成分数的部分。"
            )
        return "我看到你有考试目标。让我先理解你的情况。"

    def _compute_confidence(
        self,
        *,
        has_deadline: bool,
        deadline_days: int | None,
        has_weak_baseline: bool,
        has_subject: bool,
    ) -> float:
        score = 0.0
        if has_deadline:
            score += 0.35
            if deadline_days is not None and deadline_days <= 7:
                score += 0.15
        if has_weak_baseline:
            score += 0.30
        if has_subject:
            score += 0.15
        return min(score, 0.95)
