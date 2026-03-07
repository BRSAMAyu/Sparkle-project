"""
GoalQualityEvaluator - semantic goal quality gate after sufficiency checks.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import get_configured_llm_service


@dataclass
class GoalQualityScores:
    specificity: float
    measurability: float
    time_bound: float

    def to_dict(self) -> dict[str, float]:
        return {
            "specificity": round(float(self.specificity), 3),
            "measurability": round(float(self.measurability), 3),
            "time_bound": round(float(self.time_bound), 3),
        }


@dataclass
class GoalQualityEvaluation:
    scores: GoalQualityScores
    passed: bool
    clarification_questions: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scores": self.scores.to_dict(),
            "passed": self.passed,
            "clarification_questions": list(self.clarification_questions),
            "summary": self.summary,
        }


class GoalQualityEvaluator:
    """
    Lightweight semantic evaluator for planning goals.

    Runs only after field-level sufficiency passes.
    """

    TRIGGER_INTENTS = {"create_plan", "set_goal"}
    PASS_THRESHOLD = 0.5

    async def evaluate(
        self,
        *,
        user_message: str,
        intent: str,
        conversation_context: list[dict[str, Any]] | None = None,
    ) -> GoalQualityEvaluation:
        if intent not in self.TRIGGER_INTENTS:
            return GoalQualityEvaluation(
                scores=GoalQualityScores(1.0, 1.0, 1.0),
                passed=True,
                summary="intent_not_applicable",
            )

        llm_result = await self._evaluate_with_llm(
            user_message=user_message,
            conversation_context=conversation_context or [],
        )
        if llm_result is not None:
            return llm_result

        return self._heuristic_fallback(user_message)

    async def _evaluate_with_llm(
        self,
        *,
        user_message: str,
        conversation_context: list[dict[str, Any]],
    ) -> GoalQualityEvaluation | None:
        try:
            llm = await get_configured_llm_service(
                AgentRole.ORCHESTRATOR,
                TaskType.QUICK_QUERY,
            )
            history_lines: list[str] = []
            for item in conversation_context[-4:]:
                role = str(item.get("role") or "user")
                content = str(item.get("content") or "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines) if history_lines else "无"

            prompt = f"""
你是目标质量评估器。请评估这个目标是否足够适合开始制定计划。

评估维度：
1. specificity：是否具体到能区分“完成/未完成”
2. measurability：是否有可观察的完成标准
3. time_bound：是否有明确时间边界

返回 JSON，不要输出其它文字：
{{
  "scores": {{
    "specificity": 0.0-1.0,
    "measurability": 0.0-1.0,
    "time_bound": 0.0-1.0
  }},
  "summary": "一句话概括质量判断",
  "clarification_questions": [
    "如果某维度 < 0.5，给出针对性追问；否则可为空"
  ]
}}

最近上下文：
{history_text}

用户目标：
{user_message}
""".strip()
            raw = await llm.chat(
                [
                    {"role": "system", "content": "You evaluate goal quality. Output strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            payload = json.loads(str(raw).replace("```json", "").replace("```", "").strip())
            scores_raw = payload.get("scores") or {}
            scores = GoalQualityScores(
                specificity=float(scores_raw.get("specificity", 0.0)),
                measurability=float(scores_raw.get("measurability", 0.0)),
                time_bound=float(scores_raw.get("time_bound", 0.0)),
            )
            questions = [
                str(item).strip()
                for item in (payload.get("clarification_questions") or [])
                if str(item).strip()
            ]
            passed = min(scores.specificity, scores.measurability, scores.time_bound) >= self.PASS_THRESHOLD
            return GoalQualityEvaluation(
                scores=scores,
                passed=passed,
                clarification_questions=questions[:3],
                summary=str(payload.get("summary") or "").strip(),
            )
        except Exception as exc:
            logger.warning(f"GoalQualityEvaluator LLM path failed, using heuristic fallback: {exc}")
            return None

    def _heuristic_fallback(self, user_message: str) -> GoalQualityEvaluation:
        text = (user_message or "").strip()
        lowered = text.lower()

        specificity = 0.2
        if any(token in text for token in ["高数", "托福", "雅思", "Python", "算法", "线代", "概率论"]):
            specificity = 0.75
        elif any(token in text for token in ["数学", "英语", "编程", "学习", "健身", "工作"]):
            specificity = 0.35
        if any(word in lowered for word in ["课程", "科目", "项目", "考试", "竞赛", "论文", "面试"]):
            specificity = max(specificity, 0.7)
        if re.search(r"\d+\s*(分|小时|h|章|节|套|题|次|天|周|月)", text):
            specificity = min(0.95, specificity + 0.15)

        measurability = 0.2
        if re.search(r"\d+\s*(分|小时|h|章|节|套|题|次)", text):
            measurability = 0.85
        elif any(word in lowered for word in ["完成", "达到", "通过", "考到", "拿到"]):
            measurability = 0.55

        time_bound = 0.2
        if re.search(r"(今天|明天|这周|本周|下周|本月|下个月|这学期|期末|月底|周末|\d+天内|\d+周内|\d+个月内)", text):
            time_bound = 0.85
        elif any(word in lowered for word in ["before", "within", "deadline", "target date"]):
            time_bound = 0.75

        questions: list[str] = []
        if specificity < self.PASS_THRESHOLD:
            questions.append("你提到的目标还比较宽泛。能具体到哪门课、哪个项目，或者你想完成到什么程度吗？")
        if measurability < self.PASS_THRESHOLD:
            questions.append("这个目标完成后，你希望看到什么可观察的结果？例如分数、作品、题量、时长或里程碑。")
        if time_bound < self.PASS_THRESHOLD:
            questions.append("你希望在什么时候前达到这个目标？可以给我一个明确的时间边界。")

        scores = GoalQualityScores(
            specificity=specificity,
            measurability=measurability,
            time_bound=time_bound,
        )
        passed = min(specificity, measurability, time_bound) >= self.PASS_THRESHOLD
        return GoalQualityEvaluation(
            scores=scores,
            passed=passed,
            clarification_questions=questions[:3],
            summary="heuristic_fallback",
        )


goal_quality_evaluator = GoalQualityEvaluator()
