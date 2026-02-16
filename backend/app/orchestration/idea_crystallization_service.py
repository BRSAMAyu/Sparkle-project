from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.orchestration.task_decomposition_contract import build_task_decomposition_contract


@dataclass
class IdeaCrystallizationResult:
    intent_hypotheses: list[dict[str, Any]]
    ambiguity_profile: dict[str, Any]
    draft_goal_contract: dict[str, Any]


class IdeaCrystallizationService:
    """Convert fuzzy user ideas into structured planning hypotheses."""

    AMBIGUOUS_TOKENS = (
        "随便",
        "差不多",
        "你看着办",
        "whatever",
        "something",
        "maybe",
        "先试试",
        "以后再说",
    )

    INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "study_plan": ("学习计划", "复习计划", "学习", "study", "plan"),
        "error_diagnosis": ("错题", "错误", "诊断", "error", "debug"),
        "deep_analysis": ("深度分析", "深入", "原理", "analysis", "root cause"),
        "writing": ("写作", "文章", "写稿", "outline", "draft"),
        "general": ("任务", "项目", "goal", "roadmap", "执行"),
    }

    def crystallize(
        self,
        *,
        message: str,
        intent: str | None = None,
        extracted_entities: dict[str, Any] | None = None,
        conversation_context: list[dict[str, Any]] | None = None,
    ) -> IdeaCrystallizationResult:
        text = str(message or "").strip()
        normalized_intent = str(intent or "").strip().lower()
        entities = extracted_entities if isinstance(extracted_entities, dict) else {}
        context = conversation_context if isinstance(conversation_context, list) else []

        contract = build_task_decomposition_contract(
            message=text,
            intent=normalized_intent,
            extracted_entities=entities,
            conversation_context=context,
        ).to_dict()

        intent_hypotheses = self._build_intent_hypotheses(
            message=text,
            intent=normalized_intent,
        )
        ambiguity_profile = self._build_ambiguity_profile(
            message=text,
            contract=contract,
        )

        return IdeaCrystallizationResult(
            intent_hypotheses=intent_hypotheses,
            ambiguity_profile=ambiguity_profile,
            draft_goal_contract=contract,
        )

    def _build_intent_hypotheses(self, *, message: str, intent: str) -> list[dict[str, Any]]:
        lowered = message.lower()
        candidates: list[dict[str, Any]] = []
        for intent_id, keywords in self.INTENT_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword.lower() in lowered:
                    score += 0.2
            if intent and intent == intent_id:
                score += 0.35
            score = max(0.0, min(score, 1.0))
            if score <= 0:
                continue
            candidates.append(
                {
                    "intent_id": intent_id,
                    "confidence": round(score, 4),
                    "reason": f"keyword_match={sum(1 for keyword in keywords if keyword.lower() in lowered)}",
                }
            )

        if not candidates:
            candidates = [{"intent_id": "general", "confidence": 0.5, "reason": "fallback"}]

        candidates.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        return candidates[:3]

    def _build_ambiguity_profile(
        self,
        *,
        message: str,
        contract: dict[str, Any],
    ) -> dict[str, Any]:
        lowered = message.lower()
        ambiguous_token_hits = [token for token in self.AMBIGUOUS_TOKENS if token in lowered]
        gaps = [str(item) for item in (contract.get("gaps") or []) if str(item).strip()]
        contract_score = float(contract.get("score", 0.0) or 0.0)
        hierarchy_score = float(contract.get("goal_hierarchy_score", 0.0) or 0.0)
        has_goal = bool(str(contract.get("goal", "")).strip())
        has_acceptance = bool((contract.get("acceptance_criteria") or []))
        has_time_boundary = any(
            token in str(item).lower()
            for item in (contract.get("constraints") or [])
            for token in ("天", "周", "月", "hour", "day", "week", "deadline", "截止")
        )

        ambiguity_score = (
            0.25 * (1.0 - contract_score)
            + 0.2 * (1.0 - hierarchy_score)
            + 0.25 * min(1.0, len(gaps) / 6.0)
            + 0.15 * (0.0 if has_goal else 1.0)
            + 0.1 * (0.0 if has_acceptance else 1.0)
            + 0.05 * (0.0 if has_time_boundary else 1.0)
        )
        if ambiguous_token_hits:
            ambiguity_score = min(1.0, ambiguity_score + 0.12)

        dimensions: list[str] = []
        if not has_goal or "missing_goal" in gaps:
            dimensions.append("goal_clarity")
        if "missing_constraints" in gaps or not has_time_boundary:
            dimensions.append("constraints")
        if "missing_milestones" in gaps or "missing_goal_hierarchy" in gaps:
            dimensions.append("decomposition")
        if "missing_acceptance_criteria" in gaps:
            dimensions.append("verification")
        if "missing_risks" in gaps:
            dimensions.append("risk_awareness")
        if ambiguous_token_hits:
            dimensions.append("language_ambiguity")

        return {
            "ambiguity_score": round(max(0.0, min(ambiguity_score, 1.0)), 4),
            "ambiguous_dimensions": dimensions,
            "ambiguous_tokens": ambiguous_token_hits,
            "gaps": gaps,
            "contract_score": round(contract_score, 4),
        }
