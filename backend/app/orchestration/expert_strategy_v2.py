from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.core.agent_capability_registry import get_expert_capability_catalog
from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_STUDY_PLAN,
    extract_expert_id,
    is_expert_chat_mode,
    normalize_chat_mode,
)
from app.orchestration.expert_strategy import ExpertRoutingDecision


@dataclass(frozen=True)
class _StrategyPack:
    pack_id: str
    high_complexity_threshold: float
    medium_complexity_threshold: float
    min_selected_score: float
    semantic_weight: float
    affinity_weight: float
    success_weight: float
    complexity_weight: float
    decomposition_weight: float
    latency_weight: float
    preferred_experts: tuple[str, ...] = ()
    preferred_boost: float = 0.0


class ExpertStrategyV2:
    """Scored expert strategy (v2).

    Dimensions:
    - task complexity
    - semantic match
    - user preference affinity (session + long-term)
    - historical success rate
    - latency budget penalty
    """

    GENERAL_PACK = _StrategyPack(
        pack_id="general_v2",
        high_complexity_threshold=0.75,
        medium_complexity_threshold=0.5,
        min_selected_score=0.34,
        semantic_weight=0.38,
        affinity_weight=0.22,
        success_weight=0.2,
        complexity_weight=0.12,
        decomposition_weight=0.08,
        latency_weight=0.08,
    )
    STUDY_PLAN_PACK = _StrategyPack(
        pack_id="study_plan_v1",
        high_complexity_threshold=0.68,
        medium_complexity_threshold=0.46,
        min_selected_score=0.31,
        semantic_weight=0.34,
        affinity_weight=0.2,
        success_weight=0.18,
        complexity_weight=0.14,
        decomposition_weight=0.18,
        latency_weight=0.07,
        preferred_experts=("time_tutor", "study_buddy", "exam_oracle"),
        preferred_boost=0.05,
    )
    ERROR_DIAGNOSIS_PACK = _StrategyPack(
        pack_id="error_diagnosis_v1",
        high_complexity_threshold=0.62,
        medium_complexity_threshold=0.42,
        min_selected_score=0.3,
        semantic_weight=0.36,
        affinity_weight=0.18,
        success_weight=0.22,
        complexity_weight=0.14,
        decomposition_weight=0.12,
        latency_weight=0.08,
        preferred_experts=("error_analyst", "deep_analyst", "study_buddy"),
        preferred_boost=0.06,
    )
    DEEP_ANALYSIS_PACK = _StrategyPack(
        pack_id="deep_analysis_v1",
        high_complexity_threshold=0.72,
        medium_complexity_threshold=0.52,
        min_selected_score=0.35,
        semantic_weight=0.42,
        affinity_weight=0.18,
        success_weight=0.2,
        complexity_weight=0.14,
        decomposition_weight=0.08,
        latency_weight=0.08,
        preferred_experts=("deep_analyst", "galaxy_guide", "search_agent"),
        preferred_boost=0.05,
    )

    @classmethod
    def route(
        cls,
        *,
        message: str,
        chat_mode: str,
        user_preferences: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        session_weight: float = 0.65,
        long_term_weight: float = 0.35,
        policy_id_override: str | None = None,
        pack_overrides: dict[str, Any] | None = None,
    ) -> ExpertRoutingDecision:
        mode = normalize_chat_mode(chat_mode)
        strategy_pack = cls._resolve_strategy_pack(mode=mode, message=message)
        strategy_pack = cls._apply_pack_overrides(strategy_pack, pack_overrides=pack_overrides)
        policy_id = str(policy_id_override or f"expert_strategy_v2:{strategy_pack.pack_id}")
        catalog = [item for item in get_expert_capability_catalog() if item.get("enabled")]
        if not catalog:
            return ExpertRoutingDecision(
                selected_experts=[],
                routing_strategy="no_expert_available",
                route_confidence=0.0,
                fallback_reason="no_public_expert_enabled",
                expert_entry_source="none",
                policy_id=policy_id,
            )

        prefs = user_preferences if isinstance(user_preferences, dict) else {}
        context = user_context if isinstance(user_context, dict) else {}
        complexity = cls._score_complexity(message=message, user_preferences=prefs)
        complexity_tier = cls._complexity_tier(complexity, pack=strategy_pack)
        decomposition_signals = cls._extract_decomposition_signals(user_context=context)
        signal_complexity_boost = cls._signal_complexity_boost(decomposition_signals)
        complexity = max(0.0, min(complexity + signal_complexity_boost, 1.0))
        complexity_tier = cls._complexity_tier(complexity, pack=strategy_pack)

        score_rows = cls.score_experts(
            message=message,
            chat_mode=mode,
            user_preferences=prefs,
            user_context=context,
            complexity_score=complexity,
            session_weight=session_weight,
            long_term_weight=long_term_weight,
            strategy_pack=strategy_pack,
        )
        available = [str(item["id"]) for item in catalog]

        explicit_expert = extract_expert_id(mode)
        if explicit_expert:
            if explicit_expert in available:
                return ExpertRoutingDecision(
                    selected_experts=[explicit_expert],
                    routing_strategy="explicit_expert",
                    route_confidence=0.97,
                    fallback_reason=None,
                    expert_entry_source="explicit",
                    policy_id=policy_id,
                    complexity_score=complexity,
                    complexity_tier=complexity_tier,
                )

            fallback = score_rows[0]["expert_id"] if score_rows else available[0]
            return ExpertRoutingDecision(
                selected_experts=[fallback],
                routing_strategy="explicit_expert_fallback",
                route_confidence=0.78,
                fallback_reason=f"explicit_expert_unavailable:{explicit_expert}",
                expert_entry_source="explicit",
                policy_id=policy_id,
                complexity_score=complexity,
                complexity_tier=complexity_tier,
            )

        if mode == CHAT_MODE_EXPERT_AUTO or is_expert_chat_mode(mode):
            if not score_rows:
                fallback = available[0]
                return ExpertRoutingDecision(
                    selected_experts=[fallback],
                    routing_strategy="auto_v2_single_expert",
                    route_confidence=0.5,
                    fallback_reason="score_rows_empty",
                    expert_entry_source="auto",
                    policy_id=policy_id,
                    complexity_score=complexity,
                    complexity_tier=complexity_tier,
                )

            ideal_count = cls._target_expert_count(complexity, pack=strategy_pack)
            budget_penalty = cls._latency_budget_penalty(message=message, user_preferences=prefs)
            fallback_reasons: list[str] = []

            if budget_penalty >= 0.7 and ideal_count > 1:
                fallback_reasons.append("degrade_parallelism_for_latency_budget")
                ideal_count = max(1, ideal_count - 1)

            selected: list[str] = []
            for row in score_rows:
                if row["final_score"] < strategy_pack.min_selected_score and selected:
                    continue
                selected.append(row["expert_id"])
                if len(selected) >= ideal_count:
                    break

            if not selected:
                selected = [score_rows[0]["expert_id"]]

            if len(selected) < cls._target_expert_count(complexity, pack=strategy_pack):
                fallback_reasons.append("reduce_expert_count_low_signal")

            strategy = "auto_v2_multi_expert" if len(selected) > 1 else "auto_v2_single_expert"
            confidence = score_rows[0]["final_score"] if score_rows else 0.5
            fallback_reason = ";".join(fallback_reasons) if fallback_reasons else None
            return ExpertRoutingDecision(
                selected_experts=selected,
                routing_strategy=strategy,
                route_confidence=max(0.0, min(confidence, 0.98)),
                fallback_reason=fallback_reason,
                expert_entry_source="auto",
                policy_id=policy_id,
                complexity_score=complexity,
                complexity_tier=complexity_tier,
            )

        return ExpertRoutingDecision(
            selected_experts=[],
            routing_strategy="not_expert_mode",
            route_confidence=0.0,
            fallback_reason="chat_mode_not_expert",
            expert_entry_source="none",
            policy_id=policy_id,
            complexity_score=complexity,
            complexity_tier=complexity_tier,
        )

    @classmethod
    def score_experts(
        cls,
        *,
        message: str,
        chat_mode: str | None = None,
        user_preferences: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        complexity_score: float | None = None,
        session_weight: float = 0.65,
        long_term_weight: float = 0.35,
        strategy_pack: _StrategyPack | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        prefs = user_preferences if isinstance(user_preferences, dict) else {}
        context = user_context if isinstance(user_context, dict) else {}
        mode = normalize_chat_mode(chat_mode or CHAT_MODE_EXPERT_AUTO)
        pack = strategy_pack or cls._resolve_strategy_pack(mode=mode, message=message)
        complexity = complexity_score if complexity_score is not None else cls._score_complexity(message=message, user_preferences=prefs)
        decomposition_signals = cls._extract_decomposition_signals(user_context=context)

        session_affinity, long_term_affinity = cls._extract_affinity_maps(prefs, context)
        success_rate = cls._extract_success_rate_map(prefs, context)
        budget_penalty = cls._latency_budget_penalty(
            message=message,
            user_preferences=prefs,
            decomposition_signals=decomposition_signals,
        )

        rows: list[dict[str, Any]] = []
        for expert in get_expert_capability_catalog():
            if not expert.get("enabled"):
                continue
            expert_id = str(expert["id"])
            semantic = cls._semantic_match_score(message=message, expert=expert)
            affinity = (
                session_weight * session_affinity.get(expert_id, 0.5)
                + long_term_weight * long_term_affinity.get(expert_id, 0.5)
            )
            success = success_rate.get(expert_id, 0.55)
            complexity_fit = cls._complexity_fit(expert_id=expert_id, expert=expert, complexity=complexity)
            decomposition_fit = cls._decomposition_fit(
                expert_id=expert_id,
                complexity=complexity,
                decomposition_signals=decomposition_signals,
            )

            latency_penalty = budget_penalty * cls._latency_penalty_factor(expert_id=expert_id)
            score = (
                pack.semantic_weight * semantic
                + pack.affinity_weight * affinity
                + pack.success_weight * success
                + pack.complexity_weight * complexity_fit
                + pack.decomposition_weight * decomposition_fit
                - pack.latency_weight * latency_penalty
            )
            if expert_id in pack.preferred_experts:
                score += pack.preferred_boost
            rows.append(
                {
                    "expert_id": expert_id,
                    "display_name": expert.get("display_name", expert_id),
                    "semantic_score": round(semantic, 4),
                    "affinity_score": round(affinity, 4),
                    "success_score": round(success, 4),
                    "complexity_fit": round(complexity_fit, 4),
                    "decomposition_fit": round(decomposition_fit, 4),
                    "latency_penalty": round(latency_penalty, 4),
                    "final_score": max(0.0, min(round(score, 4), 1.0)),
                }
            )

        rows.sort(key=lambda item: item["final_score"], reverse=True)
        return rows[:top_k]

    @classmethod
    def _target_expert_count(cls, complexity: float, *, pack: _StrategyPack | None = None) -> int:
        active_pack = pack or cls.GENERAL_PACK
        if complexity >= active_pack.high_complexity_threshold:
            return 3
        if complexity >= active_pack.medium_complexity_threshold:
            return 2
        return 1

    @classmethod
    def _score_complexity(cls, *, message: str, user_preferences: dict[str, Any]) -> float:
        text = (message or "").strip().lower()
        if not text:
            return 0.0
        score = 0.16
        if len(text) > 70:
            score += 0.16
        if len(text) > 140:
            score += 0.15
        if len(text) > 220:
            score += 0.12
        if any(k in text for k in ("对比", "权衡", "tradeoff", "architecture", "design", "路线图", "多阶段")):
            score += 0.18
        if any(k in text for k in ("debug", "根因", "proof", "推导", "诊断", "why", "为什么")):
            score += 0.16
        if any(k in text for k in ("并且", "同时", "and also", "另外")):
            score += 0.07
        if text.count("?") + text.count("？") >= 2:
            score += 0.06
        if user_preferences.get("prefer_deep_analysis") is True:
            score += 0.1
        return max(0.0, min(score, 1.0))

    @classmethod
    def _complexity_tier(cls, score: float, *, pack: _StrategyPack | None = None) -> str:
        active_pack = pack or cls.GENERAL_PACK
        if score >= active_pack.high_complexity_threshold:
            return "high"
        if score >= active_pack.medium_complexity_threshold:
            return "medium"
        return "low"

    @classmethod
    def _resolve_strategy_pack(cls, *, mode: str, message: str) -> _StrategyPack:
        if mode == CHAT_MODE_STUDY_PLAN:
            return cls.STUDY_PLAN_PACK
        if mode == CHAT_MODE_ERROR_DIAGNOSIS:
            return cls.ERROR_DIAGNOSIS_PACK
        if mode == CHAT_MODE_DEEP_ANALYSIS:
            return cls.DEEP_ANALYSIS_PACK

        text = (message or "").lower()
        if any(token in text for token in ("错题", "error", "root cause", "诊断")):
            return cls.ERROR_DIAGNOSIS_PACK
        if any(token in text for token in ("学习计划", "里程碑", "阶段计划", "study plan")):
            return cls.STUDY_PLAN_PACK
        if any(token in text for token in ("深度分析", "tradeoff", "framework", "证据链")):
            return cls.DEEP_ANALYSIS_PACK
        return cls.GENERAL_PACK

    @staticmethod
    def _apply_pack_overrides(
        pack: _StrategyPack,
        *,
        pack_overrides: dict[str, Any] | None = None,
    ) -> _StrategyPack:
        if not isinstance(pack_overrides, dict):
            return pack
        weights = pack_overrides.get("weights") if isinstance(pack_overrides.get("weights"), dict) else {}
        thresholds = pack_overrides.get("thresholds") if isinstance(pack_overrides.get("thresholds"), dict) else {}

        def _coerce(value: Any, fallback: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return fallback

        updated = replace(
            pack,
            high_complexity_threshold=_coerce(thresholds.get("high_complexity_threshold"), pack.high_complexity_threshold),
            medium_complexity_threshold=_coerce(thresholds.get("medium_complexity_threshold"), pack.medium_complexity_threshold),
            min_selected_score=_coerce(thresholds.get("min_selected_score"), pack.min_selected_score),
            semantic_weight=_coerce(weights.get("semantic_weight"), pack.semantic_weight),
            affinity_weight=_coerce(weights.get("affinity_weight"), pack.affinity_weight),
            success_weight=_coerce(weights.get("success_weight"), pack.success_weight),
            complexity_weight=_coerce(weights.get("complexity_weight"), pack.complexity_weight),
            decomposition_weight=_coerce(weights.get("decomposition_weight"), pack.decomposition_weight),
            latency_weight=_coerce(weights.get("latency_weight"), pack.latency_weight),
        )
        return updated

    @staticmethod
    def _semantic_match_score(*, message: str, expert: dict[str, Any]) -> float:
        text = (message or "").lower()
        expert_id = str(expert.get("id", ""))
        tags = [str(tag).lower() for tag in expert.get("tags", [])]

        score = 0.2
        if expert_id and expert_id in text:
            score += 0.45

        expert_tokens = [token for token in expert_id.split("_") if token]
        if any(token in text for token in expert_tokens):
            score += 0.12

        matched_tags = sum(1 for tag in tags if tag and tag in text)
        score += 0.13 * matched_tags

        keyword_map = {
            "code_agent": ("代码", "code", "python", "java", "debug"),
            "math_agent": ("数学", "math", "方程", "微积分"),
            "writing_agent": ("写作", "表达", "essay", "rewrite"),
            "search_agent": ("资料", "证据", "search", "source"),
            "study_buddy": ("陪伴", "鼓励", "聊天", "support"),
            "deep_analyst": ("分析", "论证", "tradeoff", "framework"),
            "error_analyst": ("错题", "根因", "remediation", "error"),
            "time_tutor": ("计划", "schedule", "任务", "番茄"),
        }
        if any(token in text for token in keyword_map.get(expert_id, ())):
            score += 0.2

        return max(0.0, min(score, 1.0))

    @staticmethod
    def _extract_affinity_maps(
        user_preferences: dict[str, Any],
        user_context: dict[str, Any],
    ) -> tuple[dict[str, float], dict[str, float]]:
        def _to_float_map(value: Any) -> dict[str, float]:
            if not isinstance(value, dict):
                return {}
            result: dict[str, float] = {}
            for key, raw in value.items():
                try:
                    result[str(key)] = max(0.0, min(float(raw), 1.0))
                except (TypeError, ValueError):
                    continue
            return result

        session_candidates = [
            user_preferences.get("expert_affinity_session"),
            (user_preferences.get("session") or {}).get("expert_affinity") if isinstance(user_preferences.get("session"), dict) else None,
            user_context.get("expert_session_affinity"),
        ]
        long_term_candidates = [
            user_preferences.get("expert_affinity"),
            (user_preferences.get("inferred") or {}).get("expert_affinity") if isinstance(user_preferences.get("inferred"), dict) else None,
            ((user_context.get("profile") or {}).get("preferences") or {}).get("expert_affinity") if isinstance((user_context.get("profile") or {}).get("preferences"), dict) else None,
            (((user_context.get("profile") or {}).get("preferences") or {}).get("inferred") or {}).get("expert_affinity")
            if isinstance((((user_context.get("profile") or {}).get("preferences") or {}).get("inferred")), dict)
            else None,
        ]

        session_map: dict[str, float] = {}
        long_term_map: dict[str, float] = {}
        for candidate in session_candidates:
            parsed = _to_float_map(candidate)
            if parsed:
                session_map = parsed
                break
        for candidate in long_term_candidates:
            parsed = _to_float_map(candidate)
            if parsed:
                long_term_map = parsed
                break
        return session_map, long_term_map

    @staticmethod
    def _extract_success_rate_map(user_preferences: dict[str, Any], user_context: dict[str, Any]) -> dict[str, float]:
        def _to_float_map(value: Any) -> dict[str, float]:
            if not isinstance(value, dict):
                return {}
            out: dict[str, float] = {}
            for k, v in value.items():
                try:
                    out[str(k)] = max(0.0, min(float(v), 1.0))
                except (TypeError, ValueError):
                    continue
            return out

        candidates = [
            user_preferences.get("expert_success_rate"),
            (user_preferences.get("inferred") or {}).get("expert_success_rate") if isinstance(user_preferences.get("inferred"), dict) else None,
            user_context.get("expert_success_rate"),
        ]
        for candidate in candidates:
            parsed = _to_float_map(candidate)
            if parsed:
                return parsed
        return {}

    @staticmethod
    def _latency_budget_penalty(
        *,
        message: str,
        user_preferences: dict[str, Any],
        decomposition_signals: dict[str, Any] | None = None,
    ) -> float:
        signals = decomposition_signals if isinstance(decomposition_signals, dict) else {}
        base_penalty = 0.2
        budget_minutes = signals.get("time_budget_minutes_per_day")
        if isinstance(budget_minutes, (int, float)) and budget_minutes >= 180:
            base_penalty = 0.25

        budget_ms = user_preferences.get("latency_budget_ms")
        if isinstance(budget_ms, (int, float)):
            if budget_ms <= 1500:
                base_penalty = 0.85
            elif budget_ms <= 2500:
                base_penalty = 0.55
            else:
                base_penalty = 0.2

        if user_preferences.get("latency_sensitive") is True:
            base_penalty = max(base_penalty, 0.8)

        # Short asks are usually latency-sensitive in chat.
        text = (message or "").strip()
        if len(text) <= 20:
            base_penalty = max(base_penalty, 0.7)
        elif len(text) <= 60:
            base_penalty = max(base_penalty, 0.45)

        # Search-budget-aware penalty to avoid over-parallel experts under tight planning budget.
        search_budget_ms = user_preferences.get("plan_search_time_budget_ms")
        if not isinstance(search_budget_ms, (int, float)):
            search_budget_ms = signals.get("search_budget_ms")
        if isinstance(search_budget_ms, (int, float)):
            if search_budget_ms <= 900:
                base_penalty = min(1.0, base_penalty + 0.2)
            elif search_budget_ms <= 1200:
                base_penalty = min(1.0, base_penalty + 0.12)
            elif search_budget_ms <= 1800:
                base_penalty = min(1.0, base_penalty + 0.06)

        return max(0.0, min(base_penalty, 1.0))

    @staticmethod
    def _extract_decomposition_signals(user_context: dict[str, Any]) -> dict[str, Any]:
        direct = user_context.get("decomposition_signals")
        if isinstance(direct, dict):
            return direct
        plan_context = user_context.get("plan_context")
        if isinstance(plan_context, dict):
            nested = plan_context.get("decomposition_signals")
            if isinstance(nested, dict):
                return nested
        return {}

    @staticmethod
    def _signal_complexity_boost(decomposition_signals: dict[str, Any]) -> float:
        boost = 0.0
        if not isinstance(decomposition_signals, dict):
            return 0.0
        cognitive_load = decomposition_signals.get("cognitive_load")
        if isinstance(cognitive_load, (int, float)) and cognitive_load >= 0.7:
            boost += 0.07
        strain_index = decomposition_signals.get("strain_index")
        if isinstance(strain_index, (int, float)) and strain_index >= 0.65:
            boost += 0.05
        rhythm = decomposition_signals.get("historical_execution_rhythm")
        if isinstance(rhythm, (int, float)) and rhythm < 0.45:
            boost += 0.04
        return boost

    @staticmethod
    def _decomposition_fit(
        *,
        expert_id: str,
        complexity: float,
        decomposition_signals: dict[str, Any],
    ) -> float:
        if not isinstance(decomposition_signals, dict):
            return 0.55
        rhythm = decomposition_signals.get("historical_execution_rhythm")
        if isinstance(rhythm, (int, float)) and rhythm < 0.4:
            if expert_id in {"time_tutor", "study_buddy"}:
                return 0.9
        cognitive_load = decomposition_signals.get("cognitive_load")
        if isinstance(cognitive_load, (int, float)) and cognitive_load > 0.75:
            if expert_id in {"time_tutor", "error_analyst"}:
                return 0.88
        if complexity >= 0.72 and expert_id in {"deep_analyst", "exam_oracle", "code_agent"}:
            return 0.85
        return 0.6

    @staticmethod
    def _latency_penalty_factor(*, expert_id: str) -> float:
        if expert_id in {"deep_analyst", "error_analyst", "exam_oracle"}:
            return 1.0
        if expert_id in {"galaxy_guide", "search_agent"}:
            return 0.8
        return 0.55

    @staticmethod
    def _complexity_fit(*, expert_id: str, expert: dict[str, Any], complexity: float) -> float:
        tags = [str(tag).lower() for tag in expert.get("tags", [])]
        if complexity >= 0.75:
            if expert_id in {"deep_analyst", "error_analyst", "exam_oracle"}:
                return 0.95
            if any(tag in {"reasoning", "analysis", "evidence"} for tag in tags):
                return 0.85
            return 0.55
        if complexity >= 0.5:
            if expert_id in {"galaxy_guide", "time_tutor", "code_agent", "math_agent"}:
                return 0.82
            return 0.62
        if expert_id in {"study_buddy", "search_agent", "time_tutor"}:
            return 0.8
        return 0.58
