from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class FeatureReadiness:
    feature_key: str
    current_mode: str  # "off" | "shadow" | "live"
    target_mode: str  # 下一个推荐状态
    ready_for_promotion: bool
    blocking_reasons: list[str] = field(default_factory=list)  # 为空时 ready_for_promotion=True
    promotion_criteria: list[str] = field(default_factory=list)  # 升级所需条件
    evidence: list[str] = field(default_factory=list)  # 支持当前判断的证据


class KillSwitchReadinessService:
    """
    为每个 Aurora kill switch 提供"是否可以升级"的判断。

    这是架构师的决策支持工具，不是自动升级器。
    输出供人工审核，不自动修改配置。
    """

    FEATURE_CATALOG: ClassVar[dict[str, dict[str, Any]]] = {
        "stage18_aggregator": {
            "settings_key": "AURORA_STAGE18_AGGREGATOR_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "State aggregator writes are isolated per Rule K",
                "Push policy and delivery are gated independently",
            ],
        },
        "stage19_working_memory": {
            "settings_key": "AURORA_STAGE19_WM_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Working memory consolidation respects user opt-out",
                "LLM extractor does not leak PII into memory payloads",
            ],
        },
        "stage21_skill_system": {
            "settings_key": "AURORA_STAGE21_SKILL_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Skill store CRUD passes authorization checks",
                "Skill share respects visibility boundaries",
            ],
        },
        "bayesian_learning": {
            "settings_key": "AURORA_BAYESIAN_MODE",
            "current": "shadow",
            "target": "live_canary",
            "criteria": [
                "Shadow mode collects at least 500 real outcome records",
                "Shadow vs baseline divergence < 15%",
                "Live canary rate limit <= 5%",
            ],
        },
        "stage24_policy": {
            "settings_key": "AURORA_STAGE24_POLICY_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Policy compiler output is validated before application",
                "Accountability policy respects user preferences",
            ],
        },
        "stage25_reflection": {
            "settings_key": "AURORA_STAGE25_REFLECTION_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Reflection wire produces user-visible receipts",
                "Trigger toggles are independently controllable",
            ],
        },
        "stage26_scene": {
            "settings_key": "AURORA_STAGE26_SCENE_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Scene detection does not overclaim context",
                "Detour handling preserves main conversation thread",
            ],
        },
        "stage27_foresight": {
            "settings_key": "AURORA_STAGE27_FORESIGHT_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Foresight predictions are association-only (no causal claims)",
                "Feature-level kill switches are independently operable",
            ],
        },
        "stage28_traits": {
            "settings_key": "AURORA_STAGE28_TRAITS_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "NLP observer respects user cold-start corrections",
                "Trait merge produces explainable results",
            ],
        },
        "stage29_srl": {
            "settings_key": "AURORA_STAGE29_SRL_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "SRL phase transitions have observable evidence",
                "Scaffolding consumption respects kill switch boundaries",
            ],
        },
        "stage30_metacognition": {
            "settings_key": "AURORA_STAGE30_METACOGNITION_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Bias unification produces confidence proxies, not absolute scores",
                "Process scaffolding gates are individually controllable",
            ],
        },
        "stage31_idiographic": {
            "settings_key": "AURORA_STAGE31_IDIOGRAPHIC_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Idiographic correlations are association-only (Rule AP)",
                "Within-person analysis does not generalize across users",
            ],
        },
        "stage33_journey": {
            "settings_key": "AURORA_STAGE33_JOURNEY_MODE",
            "current": "live",
            "target": "live",
            "criteria": [
                "Journey events are idempotent and deduplicated",
                "Feature-level kill switches are independently operable",
            ],
        },
        "memory_inferred_write": {
            "settings_key": "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED",
            "current": "live",
            "target": "live",
            "criteria": [
                "Rule Y guard passes before inferred writes are enabled",
                "User-level allow_inferred_episodic opt-out remains enforced",
                "Privacy redaction and evidence-token paths remain active",
            ],
        },
    }

    KNOWN_BLOCKERS: ClassVar[dict[str, list[str]]] = {
        "bayesian_learning": [
            "Bayesian learner has just entered shadow mode and needs real outcome data",
            "Shadow vs baseline divergence has not been measured on production traffic",
            "Live canary rate limit is defined, but canary approval is not yet complete",
        ],
    }

    SUPPORTING_EVIDENCE: ClassVar[dict[str, list[str]]] = {
        "stage18_aggregator": [
            "Stage 18 SQAM complete; aggregator is live with push policy/delivery gated independently",
        ],
        "stage19_working_memory": [
            "Stage 19 SQAM complete; WM consolidation is live with LLM extractor gated",
        ],
        "stage21_skill_system": [
            "Stage 21 SQAM complete; skill store/share/select are live",
        ],
        "bayesian_learning": [
            "Stage 23 SQAM is complete; shadow mode is the next data-collection step",
        ],
        "stage24_policy": [
            "Stage 24 SQAM complete; policy compiler is live",
        ],
        "stage25_reflection": [
            "Stage 25 SQAM complete; reflection wire is live with trigger toggles",
        ],
        "stage26_scene": [
            "Stage 26 SQAM complete; scene detection is live",
        ],
        "stage27_foresight": [
            "Stage 27 SQAM complete; foresight predictions are live",
        ],
        "stage28_traits": [
            "Stage 28 SQAM complete; traits NLP/coldstart are live",
        ],
        "stage29_srl": [
            "Stage 29 SQAM complete; SRL tracker/bridge/scaffolding are live",
        ],
        "stage30_metacognition": [
            "Stage 30 SQAM complete; metacognition with bias unification is live",
        ],
        "stage31_idiographic": [
            "Stage 31 SQAM complete; idiographic associations are live",
        ],
        "stage33_journey": [
            "Stage 33 SQAM complete; journey events are live with feature-level kill switches",
        ],
        "memory_inferred_write": [
            "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED is enabled after Rule Y guard validation",
        ],
    }

    async def get_readiness_report(self, settings: Any) -> dict[str, FeatureReadiness]:
        """返回所有 kill switch 的就绪状态"""
        report: dict[str, FeatureReadiness] = {}
        for key, catalog in self.FEATURE_CATALOG.items():
            report[key] = self._evaluate(key, catalog, settings)
        return report

    def _evaluate(self, key: str, catalog: dict[str, Any], settings: Any) -> FeatureReadiness:
        current_mode = self._current_mode(catalog, settings)
        target_mode = str(catalog["target"])
        blocking_reasons = self._blocking_reasons(key, catalog, current_mode)
        evidence = self._evidence(key, catalog, settings, current_mode)

        return FeatureReadiness(
            feature_key=key,
            current_mode=current_mode,
            target_mode=target_mode,
            ready_for_promotion=not blocking_reasons,
            blocking_reasons=blocking_reasons,
            promotion_criteria=list(catalog["criteria"]),
            evidence=evidence,
        )

    def _current_mode(self, catalog: dict[str, Any], settings: Any) -> str:
        settings_key = str(catalog["settings_key"])
        fallback = str(catalog.get("current", "off"))
        raw_value = getattr(settings, settings_key, fallback)

        if isinstance(raw_value, bool):
            return "live" if raw_value else "off"
        return self._normalize_mode(raw_value, fallback=fallback)

    def _blocking_reasons(self, key: str, catalog: dict[str, Any], current_mode: str) -> list[str]:
        reasons: list[str] = []
        expected_current = str(catalog.get("current", "off"))
        if current_mode != expected_current:
            settings_key = str(catalog["settings_key"])
            reasons.append(
                f"{settings_key} is {current_mode!r}; expected {expected_current!r} before evaluating promotion"
            )
        reasons.extend(self.KNOWN_BLOCKERS.get(key, ()))
        return reasons

    def _evidence(self, key: str, catalog: dict[str, Any], settings: Any, current_mode: str) -> list[str]:
        settings_key = str(catalog["settings_key"])
        raw_value = getattr(settings, settings_key, None)
        return [
            f"{settings_key}={raw_value!r} resolves to current_mode={current_mode!r}",
            *self.SUPPORTING_EVIDENCE.get(key, ()),
        ]

    @staticmethod
    def _normalize_mode(value: Any, *, fallback: str = "off") -> str:
        normalized = str(value or fallback).strip().lower()
        if normalized in {"off", "shadow", "live"}:
            return normalized
        return fallback
