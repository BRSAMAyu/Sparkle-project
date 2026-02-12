from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.agent_profiles import get_public_agent_catalog
from app.orchestration.chat_modes import (
    CHAT_MODE_EXPERT_AUTO,
    extract_expert_id,
    is_expert_chat_mode,
    normalize_chat_mode,
)


@dataclass
class ExpertRoutingDecision:
    selected_experts: list[str]
    routing_strategy: str
    route_confidence: float
    fallback_reason: str | None
    expert_entry_source: str
    policy_id: str = "expert_strategy_v1"
    complexity_score: float = 0.0
    complexity_tier: str = "low"

    def to_metadata(self) -> dict[str, str]:
        fallback = self.fallback_reason or ""
        return {
            "selected_experts": json.dumps(self.selected_experts, ensure_ascii=False),
            "routing_strategy": self.routing_strategy,
            "fallback_reason": fallback,
            "route_confidence": f"{self.route_confidence:.2f}",
            "expert_entry_source": self.expert_entry_source,
            "policy_id": self.policy_id,
            "complexity_score": f"{self.complexity_score:.2f}",
            "complexity_tier": self.complexity_tier,
        }


class ExpertStrategyV1:
    """Lightweight expert routing strategy.

    Design goals:
    - Avoid heavy learning systems while keeping deterministic behavior.
    - Gate low-complexity queries to a single expert for latency/cost control.
    - Always provide explainable fallback reasons.
    """

    COMPLEXITY_MULTI_THRESHOLD = 0.58

    @classmethod
    def route(
        cls,
        *,
        message: str,
        chat_mode: str,
        user_preferences: dict[str, Any] | None = None,
    ) -> ExpertRoutingDecision:
        mode = normalize_chat_mode(chat_mode)
        catalog = get_public_agent_catalog()
        available = [c["id"] for c in catalog if c.get("enabled", False)]
        if not available:
            return ExpertRoutingDecision(
                selected_experts=[],
                routing_strategy="no_expert_available",
                route_confidence=0.0,
                fallback_reason="no_public_expert_enabled",
                expert_entry_source="none",
            )

        explicit_expert = extract_expert_id(mode)
        complexity = cls._score_complexity(message=message, user_preferences=user_preferences or {})
        complexity_tier = cls._complexity_tier(complexity)

        if explicit_expert:
            if explicit_expert in available:
                return ExpertRoutingDecision(
                    selected_experts=[explicit_expert],
                    routing_strategy="explicit_expert",
                    route_confidence=0.95,
                    fallback_reason=None,
                    expert_entry_source="explicit",
                    complexity_score=complexity,
                    complexity_tier=complexity_tier,
                )
            fallback = cls._fallback_expert(message, available)
            return ExpertRoutingDecision(
                selected_experts=[fallback],
                routing_strategy="explicit_expert_fallback",
                route_confidence=0.72,
                fallback_reason=f"explicit_expert_unavailable:{explicit_expert}",
                expert_entry_source="explicit",
                complexity_score=complexity,
                complexity_tier=complexity_tier,
            )

        if mode == CHAT_MODE_EXPERT_AUTO or is_expert_chat_mode(mode):
            primary = cls._fallback_expert(message, available)
            if complexity >= cls.COMPLEXITY_MULTI_THRESHOLD:
                candidates = cls._heuristic_candidates(message, available)
                selected = list(dict.fromkeys([primary, *candidates]))[:3]
                if len(selected) > 1:
                    return ExpertRoutingDecision(
                        selected_experts=selected,
                        routing_strategy="auto_multi_expert",
                        route_confidence=0.82,
                        fallback_reason=None,
                        expert_entry_source="auto",
                        complexity_score=complexity,
                        complexity_tier=complexity_tier,
                    )
            return ExpertRoutingDecision(
                selected_experts=[primary],
                routing_strategy="auto_single_expert",
                route_confidence=0.74,
                fallback_reason=None,
                expert_entry_source="auto",
                complexity_score=complexity,
                complexity_tier=complexity_tier,
            )

        return ExpertRoutingDecision(
            selected_experts=[],
            routing_strategy="not_expert_mode",
            route_confidence=0.0,
            fallback_reason="chat_mode_not_expert",
            expert_entry_source="none",
            complexity_score=complexity,
            complexity_tier=complexity_tier,
        )

    @classmethod
    def _score_complexity(cls, *, message: str, user_preferences: dict[str, Any]) -> float:
        text = (message or "").strip().lower()
        if not text:
            return 0.0
        score = 0.18
        if len(text) > 60:
            score += 0.18
        if len(text) > 140:
            score += 0.16
        if any(k in text for k in ("对比", "权衡", "tradeoff", "multi-step", "步骤", "路线图", "计划")):
            score += 0.2
        if any(k in text for k in ("为什么", "根因", "because", "proof", "推导", "debug", "诊断")):
            score += 0.14
        if text.count("?") + text.count("？") >= 2:
            score += 0.08
        if user_preferences.get("prefer_deep_analysis") is True:
            score += 0.1
        return max(0.0, min(score, 1.0))

    @staticmethod
    def _complexity_tier(score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _fallback_expert(message: str, available: list[str]) -> str:
        text = (message or "").lower()
        if any(k in text for k in ("代码", "code", "debug", "python", "java")) and "code_agent" in available:
            return "code_agent"
        if any(k in text for k in ("数学", "math", "积分", "方程")) and "math_agent" in available:
            return "math_agent"
        if any(k in text for k in ("写作", "essay", "表达")) and "writing_agent" in available:
            return "writing_agent"
        if any(k in text for k in ("错题", "error", "根因")) and "error_analyst" in available:
            return "error_analyst"
        if "deep_analyst" in available:
            return "deep_analyst"
        return available[0]

    @staticmethod
    def _heuristic_candidates(message: str, available: list[str]) -> list[str]:
        text = (message or "").lower()
        candidates: list[str] = []
        if any(k in text for k in ("知识", "概念", "前置", "knowledge")) and "galaxy_guide" in available:
            candidates.append("galaxy_guide")
        if any(k in text for k in ("考试", "exam", "mock")) and "exam_oracle" in available:
            candidates.append("exam_oracle")
        if any(k in text for k in ("计划", "schedule", "任务")) and "time_tutor" in available:
            candidates.append("time_tutor")
        if any(k in text for k in ("证据", "资料", "search", "source")) and "search_agent" in available:
            candidates.append("search_agent")
        if any(k in text for k in ("科学", "science")) and "science_agent" in available:
            candidates.append("science_agent")
        if "deep_analyst" in available:
            candidates.append("deep_analyst")
        return candidates
