from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RESIDUAL_DIAGNOSIS_VERSION = "2026-04-04.v1"

RESIDUAL_LABELS = {
    "R_e": "cognitive",
    "R_n": "normative",
    "R_c": "control",
    "R_i": "identity",
    "R_mixed": "mixed",
    "R_unknown": "unknown",
}


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


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int = 120) -> str:
    text = " ".join(_strip(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _contains_any(text: str, keywords: set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.58:
        return "medium"
    return "low"


@dataclass(frozen=True)
class ResidualDiagnosis:
    schema_version: str
    primary_residual: str
    secondary_residual: str | None
    loop_type: str
    confidence: float
    confidence_label: str
    what_matters_now: str
    grounding_priority: tuple[str, ...]
    rationale: tuple[str, ...]
    open_question: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "primary_residual": self.primary_residual,
            "primary_residual_label": RESIDUAL_LABELS.get(self.primary_residual, "unknown"),
            "secondary_residual": self.secondary_residual,
            "secondary_residual_label": RESIDUAL_LABELS.get(self.secondary_residual or "", "") or None,
            "loop_type": self.loop_type,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "what_matters_now": self.what_matters_now,
            "grounding_priority": list(self.grounding_priority),
            "rationale": list(self.rationale),
            "open_question": self.open_question,
        }


class ResidualDiagnosisRuntime:
    """Build a compact residual diagnosis artifact from current runtime context."""

    _COGNITIVE_KEYWORDS = {
        "confused",
        "don't understand",
        "do not understand",
        "misunderstand",
        "explain",
        "concept",
        "proof",
        "derive",
        "why does",
        "为什么",
        "不懂",
        "没想明白",
        "概念",
        "理解",
        "推导",
        "公式",
        "错因",
        "知识点",
    }
    _NORMATIVE_KEYWORDS = {
        "help me decide",
        "decide",
        "decision",
        "choose",
        "which should",
        "which one",
        "tradeoff",
        "worth it",
        "criteria",
        "values",
        "取舍",
        "帮我决定",
        "怎么选",
        "选择",
        "值不值",
        "标准",
        "利弊",
        "应该",
    }
    _CONTROL_KEYWORDS = {
        "too hard",
        "too much",
        "overwhelmed",
        "can't start",
        "cannot start",
        "stuck",
        "procrast",
        "burnout",
        "fatigue",
        "slow down",
        "拖延",
        "开始不了",
        "坚持不下去",
        "太难",
        "太多",
        "扛不住",
        "累",
        "降载",
        "卡住",
        "稳住",
    }
    _IDENTITY_KEYWORDS = {
        "i am lazy",
        "i'm lazy",
        "i am not the kind",
        "not cut out",
        "who i am",
        "who i want to become",
        "我就是",
        "我不行",
        "我是不是",
        "我做不到",
        "我不配",
        "没用",
        "身份",
        "成为怎样的人",
    }
    _NORMATIVE_ROUTE_INTENTS = {"decision", "decide", "choice", "planning_decision", "life_decision"}
    _TRUTH_ROUTE_INTENTS = {"knowledge", "study", "learn", "qa", "question_answering", "tutor"}

    def diagnose(
        self,
        *,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        context_briefing_note: str | None,
        visible_update_context: dict[str, Any] | None,
        session_feedback_signal: dict[str, Any] | None,
        user_strategy_state: dict[str, Any] | None,
        vision: dict[str, Any] | None,
        current_state: dict[str, Any] | None,
        primary_obstacle: dict[str, Any] | None,
        evidence: dict[str, Any] | None,
        intervention: dict[str, Any] | None,
        outcome: dict[str, Any] | None,
        sparkle_self_state: dict[str, Any] | None = None,
    ) -> ResidualDiagnosis:
        user_context = _as_dict(user_context_payload)
        plan_context = _as_dict(plan_context)
        visible_update_context = _as_dict(visible_update_context)
        session_feedback_signal = _as_dict(session_feedback_signal)
        user_strategy_state = _as_dict(user_strategy_state)
        vision = _as_dict(vision)
        current_state = _as_dict(current_state)
        primary_obstacle = _as_dict(primary_obstacle)
        evidence = _as_dict(evidence)
        intervention = _as_dict(intervention)
        outcome = _as_dict(outcome)
        sparkle_self_state = _as_dict(sparkle_self_state)

        corpus_parts = [
            user_context.get("current_query"),
            context_briefing_note,
            current_state.get("learning_state"),
            current_state.get("snapshot"),
            current_state.get("capacity_signal"),
            primary_obstacle.get("summary"),
            evidence.get("summary"),
            outcome.get("summary"),
            outcome.get("latest_signal"),
            visible_update_context.get("proactive_opening_message"),
            visible_update_context.get("pending_observation"),
            session_feedback_signal.get("signal_type"),
        ]
        corpus = " | ".join(_strip(part) for part in corpus_parts if _strip(part))

        route_intent = _strip(current_state.get("route_intent")).lower()
        focus_mode = _strip(current_state.get("focus_mode")).lower()
        obstacle_type = _strip(primary_obstacle.get("obstacle_type")).lower()
        strategy_mode = _strip(user_strategy_state.get("session_mode")).lower()
        feedback_type = _strip(session_feedback_signal.get("signal_type")).lower()
        active_patterns = _as_list(_as_dict(user_context.get("profile_context")).get("cognitive_summary", {}).get("active_patterns"))
        top_patterns = _as_list(_as_dict(user_context.get("cognitive_insights")).get("top_patterns"))
        pattern_payload = next(
            (item for item in [*top_patterns, *active_patterns] if isinstance(item, dict)),
            {},
        )
        pattern_name = _strip(pattern_payload.get("pattern_name") or pattern_payload.get("raw_pattern_name")).lower()
        pattern_type = _strip(pattern_payload.get("pattern_type")).lower()

        scores = {"R_e": 0.15, "R_n": 0.1, "R_c": 0.15, "R_i": 0.08}
        rationales: dict[str, list[str]] = {key: [] for key in scores}

        if obstacle_type in {"knowledge_gap", "skill_gap"}:
            scores["R_e"] += 0.62
            rationales["R_e"].append(f"obstacle_type={obstacle_type}")
        elif obstacle_type == "guidance_gap":
            scores["R_e"] += 0.28
            rationales["R_e"].append("guidance gap is active")
        if focus_mode == "knowledge_focus" or route_intent in self._TRUTH_ROUTE_INTENTS:
            scores["R_e"] += 0.2
            rationales["R_e"].append(f"route_intent={route_intent or focus_mode}")
        if _contains_any(corpus, self._COGNITIVE_KEYWORDS):
            scores["R_e"] += 0.24
            rationales["R_e"].append("cognitive-language cue")
        if user_strategy_state.get("retrieval_emphasis") == "user_materials":
            scores["R_e"] += 0.06
            rationales["R_e"].append("user materials already matter")

        if route_intent in self._NORMATIVE_ROUTE_INTENTS:
            scores["R_n"] += 0.5
            rationales["R_n"].append(f"route_intent={route_intent}")
        if _contains_any(corpus, self._NORMATIVE_KEYWORDS):
            scores["R_n"] += 0.46
            rationales["R_n"].append("decision-tradeoff cue")
        if feedback_type == "mismatch":
            scores["R_n"] += 0.12
            rationales["R_n"].append("user wants alignment before action")

        if obstacle_type in {"behavior_pattern", "progress_risk", "plan_risk"}:
            scores["R_c"] += 0.52
            rationales["R_c"].append(f"obstacle_type={obstacle_type}")
        if strategy_mode == "recovery":
            scores["R_c"] += 0.36
            rationales["R_c"].append("strategy mode is recovery")
        if outcome.get("status") in {"stalled", "mixed"}:
            scores["R_c"] += 0.18
            rationales["R_c"].append(f"outcome={outcome.get('status')}")
        if current_state.get("capacity_signal"):
            scores["R_c"] += 0.08
            rationales["R_c"].append("capacity signal present")
        if _contains_any(corpus, self._CONTROL_KEYWORDS):
            scores["R_c"] += 0.32
            rationales["R_c"].append("execution-friction cue")
        if pattern_type == "execution" or any(term in pattern_name for term in ("拖延", "avoid", "overwhelm", "perfection")):
            scores["R_c"] += 0.18
            rationales["R_c"].append("execution pattern active")

        if pattern_type == "identity":
            scores["R_i"] += 0.42
            rationales["R_i"].append("identity pattern active")
        if _contains_any(corpus, self._IDENTITY_KEYWORDS):
            scores["R_i"] += 0.44
            rationales["R_i"].append("identity-language cue")
        supporting_items = [_strip(item) for item in _as_list(evidence.get("supporting_items")) if _strip(item)]
        if supporting_items and _contains_any(corpus, self._IDENTITY_KEYWORDS):
            scores["R_i"] += 0.08
            rationales["R_i"].append("trajectory evidence can repair self-model")

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        primary_code, primary_score = ranked[0]
        secondary_code, secondary_score = ranked[1]
        margin = primary_score - secondary_score

        if primary_score < 0.4:
            primary_code = "R_unknown"
            secondary_code = None
            rationale = ["weak evidence, ask a clarifying question before acting strongly"]
        elif primary_score >= 0.72 and secondary_score >= 0.68 and margin <= 0.06:
            primary_code = "R_mixed"
            rationale = [*rationales[ranked[0][0]][:2], *rationales[ranked[1][0]][:2]]
        else:
            secondary_code = secondary_code if secondary_score >= 0.55 and margin <= 0.22 else None
            rationale = rationales[ranked[0][0]][:3]
            if secondary_code:
                rationale = [*rationale, *rationales[secondary_code][:1]]

        loop_type = self._choose_loop_type(
            route_intent=route_intent,
            corpus=corpus,
            primary_residual=primary_code,
        )
        confidence = self._build_confidence(
            primary_score=primary_score,
            secondary_score=secondary_score,
            margin=margin,
            sparkle_self_state=sparkle_self_state,
            rationale_count=len(rationale),
            primary_residual=primary_code,
        )
        return ResidualDiagnosis(
            schema_version=RESIDUAL_DIAGNOSIS_VERSION,
            primary_residual=primary_code,
            secondary_residual=secondary_code,
            loop_type=loop_type,
            confidence=confidence,
            confidence_label=_confidence_label(confidence),
            what_matters_now=self._build_what_matters_now(
                primary_residual=primary_code,
                loop_type=loop_type,
                vision=vision,
                primary_obstacle=primary_obstacle,
            ),
            grounding_priority=self._build_grounding_priority(
                primary_residual=primary_code,
                loop_type=loop_type,
            ),
            rationale=tuple(rationale[:4]),
            open_question=self._build_open_question(primary_residual=primary_code, loop_type=loop_type),
        )

    def _choose_loop_type(
        self,
        *,
        route_intent: str,
        corpus: str,
        primary_residual: str,
    ) -> str:
        normative_hits = 0
        truth_hits = 0
        if route_intent in self._NORMATIVE_ROUTE_INTENTS:
            normative_hits += 2
        if route_intent in self._TRUTH_ROUTE_INTENTS:
            truth_hits += 2
        if _contains_any(corpus, self._NORMATIVE_KEYWORDS):
            normative_hits += 2
        if _contains_any(corpus, self._COGNITIVE_KEYWORDS):
            truth_hits += 1
        if primary_residual == "R_n":
            normative_hits += 2
        if primary_residual == "R_e":
            truth_hits += 2
        return "normative" if normative_hits > truth_hits else "truth_seeking"

    def _build_confidence(
        self,
        *,
        primary_score: float,
        secondary_score: float,
        margin: float,
        sparkle_self_state: dict[str, Any],
        rationale_count: int,
        primary_residual: str,
    ) -> float:
        source_confidence = float(sparkle_self_state.get("confidence_estimate") or 0.5)
        confidence = 0.34 + min(primary_score, 1.0) * 0.28 + min(margin, 0.3) * 0.4 + source_confidence * 0.18
        confidence += min(rationale_count, 3) * 0.03
        if secondary_score >= primary_score - 0.05:
            confidence -= 0.05
        if primary_residual in {"R_unknown", "R_mixed"}:
            confidence -= 0.08
        return round(max(0.35, min(confidence, 0.92)), 2)

    def _build_what_matters_now(
        self,
        *,
        primary_residual: str,
        loop_type: str,
        vision: dict[str, Any],
        primary_obstacle: dict[str, Any],
    ) -> str:
        goal = _strip(vision.get("primary_goal") or vision.get("active_plan"))
        obstacle = _compact_text(primary_obstacle.get("summary") or primary_obstacle.get("label"), limit=96)
        if primary_residual == "R_e":
            return _compact_text(f"先找出真正没想通的点，并用用户材料把「{obstacle or goal or '当前问题'}」校准清楚。")
        if primary_residual == "R_n":
            return _compact_text("先把判断标准和取舍摊开，帮助用户建立自己的评分规则，而不是替他决定。")
        if primary_residual == "R_c":
            return _compact_text(f"先降低执行摩擦，让用户对「{goal or obstacle or '当前目标'}」能立刻启动并维持下去。")
        if primary_residual == "R_i":
            return _compact_text("先用连续性的证据修复自我判断，再决定下一步，不把身份痛点压扁成效率问题。")
        if primary_residual == "R_mixed":
            return _compact_text("先同时承认理解与执行的双重阻力，只做可逆的小判断，避免一次性下重手。")
        if loop_type == "normative":
            return "先澄清用户真正想守住的东西，再进入建议。"
        return "先补足最小必要信息，避免把问题诊断错层。"

    def _build_grounding_priority(self, *, primary_residual: str, loop_type: str) -> tuple[str, ...]:
        if loop_type == "normative" or primary_residual == "R_n":
            return (
                "user_values_and_constraints",
                "tradeoff_clarification",
                "decision_frameworks",
                "factual_context_if_needed",
            )
        if primary_residual == "R_e":
            return (
                "user_materials",
                "user_history_and_prior_errors",
                "current_strategy_state",
                "general_model_knowledge",
            )
        if primary_residual in {"R_c", "R_i", "R_mixed"}:
            return (
                "user_trajectory_and_evidence",
                "intervention_history",
                "self_and_strategy_state",
                "general_model_knowledge",
            )
        return (
            "current_context",
            "user_history",
            "strategy_state",
            "general_model_knowledge",
        )

    def _build_open_question(self, *, primary_residual: str, loop_type: str) -> str:
        if primary_residual == "R_e":
            return "最卡的是哪个概念、题型，或哪段材料？"
        if primary_residual == "R_n":
            return "这次决定里，你最不想牺牲的标准是什么？"
        if primary_residual == "R_c":
            return "现在更卡在开始、持续，还是任务负荷本身？"
        if primary_residual == "R_i":
            return "眼下最伤人的自我判断是什么，它和已有证据冲突在哪？"
        if loop_type == "normative":
            return "你更需要事实判断，还是先一起搭出判断标准？"
        return "这更像是没想清楚、做不动，还是需要帮你决定标准？"
