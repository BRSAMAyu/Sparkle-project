from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.orchestration.plan_quality_contract import (
    PLAN_MODE_FULL,
    PLAN_MODE_NEXT_STEP_ONLY,
    PLAN_MODE_PROVISIONAL,
    build_plan_quality_contract,
)
from app.services.planning_benchmark_service import (
    PlanningBenchmarkRun,
    PlanningBenchmarkScenario,
)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "no",
    "not",
    "of",
    "on",
    "or",
    "soon",
    "that",
    "the",
    "their",
    "this",
    "to",
    "too",
    "up",
    "with",
    "you",
    "your",
}

SECTION_PATTERNS = {
    "goal_frame": (
        "goal",
        "deadline",
        "exam",
        "pass",
        "target",
        "why now",
        "by ",
        "目标",
        "期限",
        "为什么是现在",
    ),
    "assumptions": (
        "assumption",
        "assuming",
        "if we assume",
        "based on what you shared",
        "for now i am assuming",
        "假设",
        "显式写出",
    ),
    "readiness_fit": (
        "full plan",
        "provisional",
        "for now",
        "next step only",
        "not giving a full plan yet",
        "完整计划",
        "暂定计划",
        "仅下一步",
        "临时诊断",
        "计划类型说明",
    ),
    "workload_model": (
        "minutes",
        "per day",
        "session",
        "capacity",
        "energy",
        "2 hours",
        "90 minutes",
        "short session",
        "时间假设",
        "精力假设",
        "难度假设",
        "分钟",
        "小时",
    ),
    "sequence": (
        "day 1",
        "week 1",
        "step 1",
        "first",
        "then",
        "next",
        "checkpoint",
        "milestone",
        "先后顺序",
        "第 1-3 天",
        "第 4-10 天",
        "步骤",
    ),
    "grounding_basis": (
        "uploaded",
        "material",
        "notes",
        "slides",
        "quiz results",
        "mistake log",
        "error book",
        ".pdf",
        ".csv",
        ".md",
        "材料",
        "约束",
        "薄弱点",
        "错题",
        "幻灯片",
    ),
    "next_action": (
        "today",
        "right now",
        "within 24 hours",
        "your next action",
        "start with",
        "do this first",
        "未来 24 小时内可执行的下一步",
        "下一步",
        "动作",
        "今天",
    ),
    "adaptation_trigger": (
        "if you miss",
        "if this slips",
        "revisit",
        "checkpoint",
        "adjust",
        "trigger",
        "if you fall behind",
        "什么信号会触发调整",
        "触发",
        "如果你落后",
        "连续 2 天未完成",
    ),
    "failure_guard": (
        "minimum version",
        "fallback",
        "if this is too much",
        "cut scope",
        "drop back",
        "smaller version",
        "太难",
        "止损策略",
        "降级策略",
        "缓冲策略",
    ),
    "scope_and_horizon": (
        "next 2 days",
        "next 3 days",
        "this week",
        "for now",
        "narrow",
        "temporary plan",
        "first version",
        "缩窄后的范围与时间窗",
        "未来 72 小时",
        "新范围",
    ),
    "fallback_uncertainty": (
        "uncertain",
        "if this assumption is wrong",
        "we may need",
        "fallback",
        "pending",
        "need to confirm",
        "暂定路径",
        "待确认点",
        "限制声明",
    ),
    "withhold_reason": (
        "not enough information",
        "cannot give a full plan yet",
        "before making a full plan",
        "i should not pretend",
        "too vague",
        "为什么现在不该给完整计划",
        "拒绝生成完整计划的理由",
        "数据缺失",
    ),
    "unlock_question": (
        "?",
        "what subject",
        "which exam",
        "how much time",
        "what is the deadline",
        "最高价值的解锁问题",
        "请诚实回答这个问题",
    ),
}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", value.lower())
        if token not in STOPWORDS
    }


def _bounded(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 4)


def _count_matches(text: str, patterns: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for pattern in patterns if pattern in lowered)


def _average(values: list[float]) -> float:
    usable = [float(value) for value in values if value is not None]
    if not usable:
        return 0.0
    return _bounded(mean(usable))


@dataclass(frozen=True)
class PlanningBenchmarkDimensionScore:
    score: float
    notes: str
    evidence_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": _bounded(self.score),
            "notes": self.notes,
            "evidence_excerpt": self.evidence_excerpt,
        }


@dataclass(frozen=True)
class PlanningBenchmarkScenarioScore:
    scenario_id: str
    variant: str
    model_key: str
    dimensions: dict[str, PlanningBenchmarkDimensionScore]
    overall_score: float
    inferred_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "variant": self.variant,
            "model_key": self.model_key,
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "overall_score": _bounded(self.overall_score),
            "inferred_mode": self.inferred_mode,
        }


class PlanningBenchmarkEvaluator:
    """Deterministically score Phase B benchmark outputs against rubric v1."""

    def __init__(self) -> None:
        self.contract = build_plan_quality_contract()

    @staticmethod
    def load_results(path: str | Path) -> dict[str, Any]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}

    def evaluate_run(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        run: PlanningBenchmarkRun,
    ) -> PlanningBenchmarkScenarioScore:
        text = _strip(run.output_text)
        inferred_mode = self._infer_mode(text)
        section_ratio = self._section_coverage_ratio(text=text, mode=scenario.expected_plan_mode)
        dimensions = {
            "understanding_fit": self._score_understanding_fit(
                scenario=scenario,
                text=text,
                inferred_mode=inferred_mode,
                section_ratio=section_ratio,
            ),
            "behavior_compliance": self._score_behavior_compliance(
                scenario=scenario,
                text=text,
                inferred_mode=inferred_mode,
            ),
            "response_shape_compliance": self._score_response_shape(
                scenario=scenario,
                text=text,
                inferred_mode=inferred_mode,
                section_ratio=section_ratio,
            ),
            "constraint_realism": self._score_constraint_realism(
                scenario=scenario,
                text=text,
                inferred_mode=inferred_mode,
            ),
            "plan_sequence_quality": self._score_sequence(
                scenario=scenario,
                text=text,
                inferred_mode=inferred_mode,
                section_ratio=section_ratio,
            ),
            "grounding_quality": self._score_grounding(scenario=scenario, text=text),
            "next_action_usefulness": self._score_next_action(scenario=scenario, text=text),
            "adaptation_fallback_quality": self._score_adaptation(scenario=scenario, text=text),
            "non_expert_usability": self._score_usability(scenario=scenario, text=text),
            "trustworthiness": self._score_trust(scenario=scenario, text=text, inferred_mode=inferred_mode),
            "trust_tone_compliance": self._score_trust_tone(scenario=scenario, text=text, inferred_mode=inferred_mode),
        }
        overall = _average([item.score for item in dimensions.values()])
        return PlanningBenchmarkScenarioScore(
            scenario_id=run.scenario_id,
            variant=run.variant,
            model_key=run.model_key,
            dimensions=dimensions,
            overall_score=overall,
            inferred_mode=inferred_mode,
        )

    def evaluate_results(
        self,
        *,
        scenarios: list[PlanningBenchmarkScenario],
        runs: list[PlanningBenchmarkRun],
        tie_margin: float = 0.01,
    ) -> dict[str, Any]:
        scenario_map = {item.scenario_id: item for item in scenarios}
        scenario_scores: list[PlanningBenchmarkScenarioScore] = []
        for run in runs:
            scenario = scenario_map.get(run.scenario_id)
            if scenario is None:
                continue
            scenario_scores.append(self.evaluate_run(scenario=scenario, run=run))

        by_variant: dict[str, list[float]] = {}
        by_scenario: dict[str, list[PlanningBenchmarkScenarioScore]] = {}
        win_tie_loss = {"wins": 0, "ties": 0, "losses": 0}
        scenario_outcomes: list[dict[str, Any]] = []

        for score in scenario_scores:
            label = self.variant_label(score.variant, score.model_key)
            by_variant.setdefault(label, []).append(score.overall_score)
            by_scenario.setdefault(score.scenario_id, []).append(score)

        for scenario_id, scores in by_scenario.items():
            ordered = sorted(scores, key=lambda item: item.overall_score, reverse=True)
            winner = ordered[0]
            target_variant = "semantic_doctrine" if any(item.variant == "semantic_doctrine" for item in ordered) else "sparkle_phase_b"
            phase_b = next((item for item in ordered if item.variant == target_variant), None)
            best_non_phase_b = next((item for item in ordered if item.variant != target_variant), None)
            outcome = "loss"
            if phase_b is not None and best_non_phase_b is not None:
                delta = phase_b.overall_score - best_non_phase_b.overall_score
                if delta > tie_margin:
                    outcome = "win"
                    win_tie_loss["wins"] += 1
                elif abs(delta) <= tie_margin:
                    outcome = "tie"
                    win_tie_loss["ties"] += 1
                else:
                    win_tie_loss["losses"] += 1
            scenario_outcomes.append(
                {
                    "scenario_id": scenario_id,
                    "winner": self.variant_label(winner.variant, winner.model_key),
                    "winner_score": _bounded(winner.overall_score),
                    "phase_b_outcome": outcome,
                    "target_variant": target_variant,
                    "scores": [
                        {
                            "label": self.variant_label(item.variant, item.model_key),
                            "overall_score": _bounded(item.overall_score),
                            "inferred_mode": item.inferred_mode,
                        }
                        for item in ordered
                    ],
                }
            )

        variant_summary = {
            label: {
                "average_overall_score": _bounded(_average(scores)),
                "scenario_count": len(scores),
            }
            for label, scores in sorted(by_variant.items())
        }
        benchmark_target_label = (
            "semantic_doctrine:dashscope_chat"
            if "semantic_doctrine:dashscope_chat" in variant_summary
            else "sparkle_phase_b:dashscope_chat"
        )
        phase_b_average = variant_summary.get(benchmark_target_label, {}).get("average_overall_score", 0.0)
        strongest_baseline = max(
            (
                item["average_overall_score"]
                for label, item in variant_summary.items()
                if label != benchmark_target_label
            ),
            default=0.0,
        )
        credible_win_profile = phase_b_average > strongest_baseline and win_tie_loss["wins"] >= max(1, len(by_scenario) // 2)

        return {
            "proof_level": "benchmark_v1",
            "human_eval_required": True,
            "fairness_notes": [
                "Sparkle Phase B is evaluated as a system-level planning stack with compiled planning strategy in its prompt.",
                "Raw baselines receive plain dossier prompts and remain useful comparative signals, not final product truth.",
                "This deterministic evaluator is a regression and comparison layer, not a substitute for human product evaluation.",
            ],
            "scenario_scorecards": [item.to_dict() for item in scenario_scores],
            "variant_summary": variant_summary,
            "scenario_outcomes": scenario_outcomes,
            "phase_b_vs_field": win_tie_loss,
            "benchmark_target_label": benchmark_target_label,
            "credible_win_profile": credible_win_profile,
        }

    @staticmethod
    def variant_label(variant: str, model_key: str) -> str:
        if variant == "raw_baseline":
            return f"raw_baseline:{model_key}"
        return f"{variant}:{model_key}"

    def _infer_mode(self, text: str) -> str:
        lowered = text.lower()
        step_markers = len(re.findall(r"(^|\n)\s*(?:[-*]|\d+\.)\s+", text))
        temporal_markers = _count_matches(
            lowered,
            ("day 1", "day 2", "week 1", "week 2", "checkpoint", "milestone", "then"),
        )
        if (
            "not enough information" in lowered
            or "full plan yet" in lowered
            or "what subject" in lowered
            or "为什么现在不该给完整计划" in text
            or "拒绝生成完整计划的理由" in text
        ):
            return PLAN_MODE_NEXT_STEP_ONLY
        if "完整计划" in text and "暂定计划" not in text and "临时诊断" not in text:
            return PLAN_MODE_FULL
        if step_markers >= 3 and temporal_markers >= 2:
            return PLAN_MODE_FULL
        if (
            "provisional" in lowered
            or "for now" in lowered
            or "temporary plan" in lowered
            or "first version" in lowered
            or "暂定计划" in text
            or "临时诊断" in text
            or "暂定恢复计划" in text
        ):
            return PLAN_MODE_PROVISIONAL
        return PLAN_MODE_FULL

    def _section_coverage_ratio(self, *, text: str, mode: str) -> float:
        required_sections = self.contract.get_required_sections(mode)
        hits = 0
        for section in required_sections:
            patterns = SECTION_PATTERNS.get(section, ())
            if _count_matches(text, patterns) > 0:
                hits += 1
        if not required_sections:
            return 0.0
        return _bounded(hits / len(required_sections))

    def _score_understanding_fit(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
        section_ratio: float,
    ) -> PlanningBenchmarkDimensionScore:
        dossier_tokens = _tokens(" ".join([scenario.user_goal, scenario.baseline_state, *scenario.constraints]))
        output_tokens = _tokens(text)
        overlap = len(dossier_tokens & output_tokens) / max(len(dossier_tokens), 1)
        mode_bonus = 0.15 if inferred_mode == scenario.expected_plan_mode else 0.0
        score = 0.35 + overlap * 1.4 + section_ratio * 0.2 + mode_bonus
        notes = f"Keyword overlap={overlap:.2f}; inferred_mode={inferred_mode}; expected_mode={scenario.expected_plan_mode}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_behavior_compliance(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        question_count = text.count("?") + text.count("？")
        if scenario.expected_plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            score = 0.88 if inferred_mode == PLAN_MODE_NEXT_STEP_ONLY and question_count == 1 else 0.35
        elif scenario.phase_a_readiness_action == "provisional":
            score = 0.88 if inferred_mode == PLAN_MODE_PROVISIONAL else 0.45
        else:
            score = 0.86 if inferred_mode == scenario.expected_plan_mode else 0.5
        if "push harder" in lowered and "low energy" in lowered:
            score -= 0.18
        notes = f"inferred_mode={inferred_mode}; expected_mode={scenario.expected_plan_mode}; question_count={question_count}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_response_shape(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
        section_ratio: float,
    ) -> PlanningBenchmarkDimensionScore:
        question_count = text.count("?") + text.count("？")
        if scenario.expected_plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            score = 0.45 + section_ratio * 0.35 + (0.2 if question_count == 1 else 0.0)
        else:
            score = 0.35 + section_ratio * 0.55 + (0.1 if inferred_mode == scenario.expected_plan_mode else 0.0)
        notes = f"required_section_ratio={section_ratio:.2f}; question_count={question_count}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_constraint_realism(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        constraint_hits = sum(1 for item in scenario.constraints if self._mentions_phrase(text, item))
        constraint_ratio = constraint_hits / max(len(scenario.constraints), 1)
        overload_guard = 0.1 if any(term in lowered for term in ("short session", "low energy", "90 minutes", "2 hours")) else 0.0
        mode_fit = 0.2 if inferred_mode == scenario.expected_plan_mode else -0.1
        score = 0.3 + constraint_ratio * 0.5 + overload_guard + mode_fit
        notes = f"Constraint hits={constraint_hits}/{len(scenario.constraints)}; mode_fit={inferred_mode == scenario.expected_plan_mode}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_sequence(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
        section_ratio: float,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        step_markers = len(re.findall(r"(^|\n)\s*(?:[-*]|\d+\.)\s+", text))
        temporal_markers = _count_matches(
            lowered,
            ("day 1", "day 2", "week 1", "week 2", "today", "tomorrow", "checkpoint", "milestone", "then"),
        )
        if scenario.expected_plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            score = 0.8 if inferred_mode == PLAN_MODE_NEXT_STEP_ONLY and step_markers <= 3 else 0.45
        else:
            score = 0.25 + min(step_markers, 6) * 0.07 + min(temporal_markers, 5) * 0.08 + section_ratio * 0.15
        notes = f"Step markers={step_markers}; temporal markers={temporal_markers}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_grounding(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        if not scenario.materials:
            score = 0.85 if "uploaded" not in lowered or "none" in lowered else 0.72
            notes = "No uploaded materials required for this dossier."
            return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

        exact_mentions = sum(1 for material in scenario.materials if material.lower() in lowered)
        generic_hits = _count_matches(
            lowered,
            ("uploaded", "materials", "notes", "slides", "quiz results", "mistake log", "error book"),
        )
        ratio = exact_mentions / max(len(scenario.materials), 1)
        score = 0.2 + ratio * 0.55 + min(generic_hits, 3) * 0.08
        notes = f"Material mentions={exact_mentions}/{len(scenario.materials)}; generic grounding hits={generic_hits}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_next_action(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        time_hits = _count_matches(lowered, ("today", "tonight", "within 24 hours", "next 30 minutes", "tomorrow morning"))
        time_hits += _count_matches(text, ("未来 24 小时", "15 分钟", "24 小时内", "今天"))
        action_hits = _count_matches(lowered, ("start", "do", "write", "review", "solve", "open", "spend"))
        action_hits += _count_matches(text, ("打开", "复习", "分析", "写下", "开始", "圈出", "标记"))
        question_count = text.count("?")
        question_count += text.count("？")
        if scenario.expected_plan_mode == PLAN_MODE_NEXT_STEP_ONLY:
            score = 0.7 + min(time_hits, 1) * 0.15 + (0.1 if question_count == 1 else 0.0)
        else:
            score = 0.3 + min(time_hits, 2) * 0.18 + min(action_hits, 4) * 0.08
        notes = f"Time hits={time_hits}; action hits={action_hits}; question_count={question_count}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_adaptation(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        fallback_hits = _count_matches(
            lowered,
            ("if you miss", "if this is too much", "fallback", "cut scope", "adjust", "revisit", "if you fall behind"),
        )
        fallback_hits += _count_matches(text, ("触发", "止损策略", "降级策略", "缓冲策略", "如果", "调整"))
        continuity_hits = _count_matches(lowered, ("what stays", "what changes", "keep", "preserve", "still keep"))
        continuity_hits += _count_matches(text, ("保持不变", "发生变化", "什么变了", "什么没变"))
        score = 0.2 + min(fallback_hits, 4) * 0.16 + min(continuity_hits, 2) * 0.12
        if "preserve continuity" in " ".join(scenario.constraints).lower():
            score += 0.08
        notes = f"Fallback hits={fallback_hits}; continuity hits={continuity_hits}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_usability(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
    ) -> PlanningBenchmarkDimensionScore:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        bullet_lines = sum(1 for line in lines if re.match(r"^(?:[-*]|\d+\.)\s+", line))
        avg_line_len = mean([len(line) for line in lines]) if lines else 0.0
        simple_language_bonus = 0.1 if any(term in text.lower() for term in ("plainly", "simple", "today", "first")) else 0.0
        score = 0.35 + min(bullet_lines, 6) * 0.06 + simple_language_bonus
        if avg_line_len and avg_line_len < 120:
            score += 0.15
        if "ordinary user" in " ".join(scenario.constraints).lower() and bullet_lines == 0:
            score -= 0.08
        notes = f"Bullet lines={bullet_lines}; avg_line_len={avg_line_len:.1f}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_trust(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        honesty_hits = _count_matches(
            lowered,
            ("assumption", "uncertain", "not enough information", "for now", "based on what you shared", "if this is wrong"),
        )
        honesty_hits += _count_matches(text, ("不假装确定性", "数据缺失", "限制声明", "基于当前信息", "无法直接读取"))
        materials_needed = bool(scenario.materials)
        grounding_bonus = 0.12 if (not materials_needed or any(material.lower() in lowered for material in scenario.materials)) else -0.1
        mode_bonus = 0.2 if inferred_mode == scenario.expected_plan_mode else -0.15
        score = 0.35 + min(honesty_hits, 4) * 0.08 + grounding_bonus + mode_bonus
        notes = f"Honesty hits={honesty_hits}; materials_needed={materials_needed}; mode_fit={inferred_mode == scenario.expected_plan_mode}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    def _score_trust_tone(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        text: str,
        inferred_mode: str,
    ) -> PlanningBenchmarkDimensionScore:
        lowered = text.lower()
        punitive_hits = _count_matches(lowered, ("push harder", "no excuses", "must", "strict"))
        supportive_hits = _count_matches(lowered, ("for now", "realistic", "if this is too much", "adjust", "plainly"))
        score = 0.55 + min(supportive_hits, 3) * 0.1 - min(punitive_hits, 3) * 0.14
        if scenario.expected_plan_mode == PLAN_MODE_NEXT_STEP_ONLY and inferred_mode != PLAN_MODE_NEXT_STEP_ONLY:
            score -= 0.12
        notes = f"supportive_hits={supportive_hits}; punitive_hits={punitive_hits}; inferred_mode={inferred_mode}."
        return PlanningBenchmarkDimensionScore(score=_bounded(score), notes=notes, evidence_excerpt=self._excerpt(text))

    @staticmethod
    def _excerpt(text: str, max_chars: int = 220) -> str:
        compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
        return compact[:max_chars]

    @staticmethod
    def _mentions_phrase(text: str, phrase: str) -> bool:
        phrase_tokens = _tokens(phrase)
        if not phrase_tokens:
            return False
        text_tokens = _tokens(text)
        overlap = len(phrase_tokens & text_tokens)
        return overlap >= max(1, len(phrase_tokens) // 2)
