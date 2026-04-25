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
        "memory_inferred_write": {
            "settings_key": "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED",
            "current": "off",
            "target": "live",
            "criteria": [
                "SGW 12小时真跑完成，零硬违规，软违规<5%",
                "docs/audit/deep_audit_2026-04-22_0130_memory_service.md P0 问题全部修复",
                "Stage 39 memory write readiness report 完成（14天观察窗口）",
            ],
        },
        "bayesian_learning": {
            "settings_key": "AURORA_BAYESIAN_MODE",
            "current": "shadow",  # 已经升为shadow（本流C9做的）
            "target": "live_canary",
            "criteria": [
                "shadow 模式收集至少 500 个真实 outcome 记录",
                "shadow vs baseline divergence < 15%",
                "live_canary 限流 <= 5%",
            ],
        },
    }

    KNOWN_BLOCKERS: ClassVar[dict[str, list[str]]] = {
        "memory_inferred_write": [
            "SGW validation is still pending for inferred memory writes",
            "Memory service P0 audit fixes are not confirmed complete",
            "Stage 39 memory write readiness report and 14-day observation window are not complete",
        ],
        "bayesian_learning": [
            "Bayesian learner has just entered shadow mode and needs real outcome data",
            "Shadow vs baseline divergence has not been measured on production traffic",
            "Live canary rate limit is defined, but canary approval is not yet complete",
        ],
    }

    SUPPORTING_EVIDENCE: ClassVar[dict[str, list[str]]] = {
        "memory_inferred_write": [
            "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED remains disabled until SGW validation completes",
        ],
        "bayesian_learning": [
            "Stage 23 SQAM is complete; shadow mode is the next data-collection step",
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
