"""
ExecutionTrustEngine - 三级信任评估引擎。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.execution_intent import TrustLevel


@dataclass
class TrustEvaluation:
    """信任评估结果。"""

    trust_level: TrustLevel
    validation_passed: int = 0
    validation_total: int = 0
    quality_score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    blocked_fields: list[str] = field(default_factory=list)

    @property
    def can_update_task(self) -> bool:
        return self.trust_level in {TrustLevel.VALIDATED, TrustLevel.TRUSTED}

    @property
    def can_update_plan_record(self) -> bool:
        return self.trust_level in {TrustLevel.VALIDATED, TrustLevel.TRUSTED}

    @property
    def can_emit_behavior_signals(self) -> bool:
        return self.trust_level == TrustLevel.TRUSTED


class ExecutionTrustEngine:
    """评估外部执行结果的可信度，防止脏数据进入主链。"""

    def __init__(
        self,
        *,
        auto_trust_min_history: int = 5,
        auto_trust_success_rate: float = 0.85,
        auto_trust_min_quality: float = 0.7,
    ):
        self._auto_trust_min_history = auto_trust_min_history
        self._auto_trust_success_rate = auto_trust_success_rate
        self._auto_trust_min_quality = auto_trust_min_quality

    def evaluate(
        self,
        *,
        raw_result: dict[str, Any],
        success_criteria: dict[str, Any],
        result_contract: dict[str, Any],
        executor_history: dict[str, Any] | None = None,
        user_confirmed: bool = False,
    ) -> TrustEvaluation:
        reasons: list[str] = []
        blocked_fields: list[str] = []

        if not raw_result:
            return TrustEvaluation(
                trust_level=TrustLevel.RAW,
                reasons=["empty_result"],
            )

        safety_issues = self._check_content_safety(raw_result)
        if safety_issues:
            blocked_fields.extend(safety_issues)
            return TrustEvaluation(
                trust_level=TrustLevel.RAW,
                reasons=[f"safety_blocked:{len(safety_issues)}_fields"],
                blocked_fields=blocked_fields,
            )

        validation_passed, validation_total = self._validate_schema(raw_result, result_contract)
        criteria_met = self._check_success_criteria(raw_result, success_criteria)
        quality_score = self._calculate_quality(
            validation_ratio=validation_passed / max(validation_total, 1),
            criteria_met=criteria_met,
            raw_result=raw_result,
        )

        if validation_total > 0 and validation_passed < validation_total * 0.5:
            trust_level = TrustLevel.RAW
            reasons.append("schema_validation_below_50pct")
        elif not criteria_met:
            trust_level = TrustLevel.RAW
            reasons.append("success_criteria_not_met")
        elif quality_score < 0.3:
            trust_level = TrustLevel.RAW
            reasons.append("quality_too_low")
        else:
            trust_level = TrustLevel.VALIDATED
            reasons.append("schema_and_criteria_passed")

            if user_confirmed:
                trust_level = TrustLevel.TRUSTED
                reasons.append("user_confirmed")
            elif self._can_auto_promote(executor_history, quality_score):
                trust_level = TrustLevel.TRUSTED
                reasons.append("auto_promoted_by_history")

        return TrustEvaluation(
            trust_level=trust_level,
            validation_passed=validation_passed,
            validation_total=validation_total,
            quality_score=quality_score,
            reasons=reasons,
            blocked_fields=blocked_fields,
        )

    def _check_content_safety(self, result: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        sensitive_keys = {
            "password",
            "secret",
            "api_key",
            "token",
            "credit_card",
            "ssn",
            "social_security",
        }
        injection_patterns = ["<script", "javascript:", "eval(", "exec("]

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    key_text = str(key).strip().lower()
                    if key_text in sensitive_keys:
                        issues.append(f"sensitive_content:{key_text}")
                    walk(value)
                return

            if isinstance(node, list):
                for item in node:
                    walk(item)
                return

            if isinstance(node, str):
                lowered = node.lower()
                for pattern in sensitive_keys:
                    if pattern in lowered:
                        issues.append(f"sensitive_content:{pattern}")
                for pattern in injection_patterns:
                    if pattern in lowered:
                        issues.append(f"injection_attempt:{pattern}")

        walk(result)

        return issues

    def _validate_schema(self, result: dict[str, Any], contract: dict[str, Any]) -> tuple[int, int]:
        required_fields = contract.get("required_fields", [])
        if not required_fields:
            return (0, 0)

        passed = 0
        for field_name in required_fields:
            if result.get(field_name) is not None:
                passed += 1
        return (passed, len(required_fields))

    def _check_success_criteria(self, result: dict[str, Any], criteria: dict[str, Any]) -> bool:
        criteria_type = criteria.get("type")
        if not criteria_type:
            return True

        if criteria_type == "structured_output":
            required_fields = criteria.get("required_fields", [])
            return all(result.get(field_name) is not None for field_name in required_fields)

        if criteria_type == "contains_text":
            expected_text = str(criteria.get("expected_text", "")).strip()
            output_text = str(result.get("output", ""))
            return bool(expected_text) and expected_text.lower() in output_text.lower()

        if criteria_type == "non_empty":
            output = result.get("output") or result.get("parsed_output")
            return bool(output)

        return True

    def _calculate_quality(
        self,
        *,
        validation_ratio: float,
        criteria_met: bool,
        raw_result: dict[str, Any],
    ) -> float:
        schema_score = validation_ratio * 0.4
        criteria_score = 0.3 if criteria_met else 0.0

        output = raw_result.get("output") or raw_result.get("parsed_output") or {}
        if isinstance(output, dict):
            richness_score = min(len(output) / 5.0, 1.0) * 0.3
        elif isinstance(output, str):
            richness_score = min(len(output.strip()) / 200.0, 1.0) * 0.3
        else:
            richness_score = 0.1 if output else 0.0

        return round(schema_score + criteria_score + richness_score, 3)

    def _can_auto_promote(self, history: dict[str, Any] | None, current_quality: float) -> bool:
        if not history:
            return False

        total_runs = int(history.get("total_runs", 0) or 0)
        success_rate = float(history.get("success_rate", 0.0) or 0.0)

        if total_runs < self._auto_trust_min_history:
            return False
        if success_rate < self._auto_trust_success_rate:
            return False
        if current_quality < self._auto_trust_min_quality:
            return False
        return True
