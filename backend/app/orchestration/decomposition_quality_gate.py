from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.orchestration.schemas import ExecutablePlan


@dataclass
class DecompositionQualityGateResult:
    passed: bool
    decomposition_contract_score: float
    plan_feasibility_score: float
    decomposition_gaps: list[str] = field(default_factory=list)
    reason: str = ""
    contract_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "decomposition_contract_score": round(float(self.decomposition_contract_score), 4),
            "plan_feasibility_score": round(float(self.plan_feasibility_score), 4),
            "decomposition_gaps": self.decomposition_gaps,
            "reason": self.reason,
            "plan_contract_version": self.contract_version,
        }


class DecompositionQualityGate:
    """Gatekeeper to prevent low-value decomposition plans from execution."""

    MIN_CONTRACT_SCORE = 0.45
    MIN_FEASIBILITY_SCORE = 0.55
    REQUIRED_CONTRACT_GAPS = {
        "missing_goal",
        "missing_constraints",
        "missing_milestones",
        "missing_acceptance_criteria",
        "missing_risks",
    }
    _TIME_BOUNDARY_TOKENS = ("天", "周", "月", "小时", "分钟", "day", "week", "month", "hour", "deadline", "截止")

    @classmethod
    def evaluate(
        cls,
        *,
        contract: dict[str, Any] | None,
        plan: ExecutablePlan | None = None,
    ) -> DecompositionQualityGateResult:
        contract_data = contract if isinstance(contract, dict) else {}
        contract_score = cls._to_float(contract_data.get("score"), default=0.0)
        contract_version = str(contract_data.get("version", "v1") or "v1")
        gaps = [
            str(item).strip()
            for item in (contract_data.get("gaps") or [])
            if str(item).strip()
        ]

        feasibility = cls._estimate_feasibility(
            contract_score=contract_score,
            plan=plan,
            gaps=gaps,
        )

        passed = True
        reason_parts: list[str] = []
        if contract_score < cls.MIN_CONTRACT_SCORE:
            passed = False
            reason_parts.append("contract_score_too_low")
        missing_required = cls._collect_missing_required(contract_data=contract_data, existing_gaps=gaps)
        if missing_required:
            passed = False
            for gap in missing_required:
                if gap not in gaps:
                    gaps.append(gap)
            reason_parts.append("missing_required_contract_fields")
        if feasibility < cls.MIN_FEASIBILITY_SCORE:
            passed = False
            reason_parts.append("plan_feasibility_too_low")
        if plan and not cls._has_acceptance_criteria(plan):
            passed = False
            if "missing_acceptance_criteria" not in gaps:
                gaps.append("missing_acceptance_criteria")
            reason_parts.append("missing_plan_acceptance_criteria")
        if not cls._has_time_boundary(contract_data):
            passed = False
            if "missing_time_boundary" not in gaps:
                gaps.append("missing_time_boundary")
            reason_parts.append("missing_time_boundary")
        if plan and not cls._has_dependency_relations(plan):
            passed = False
            if "missing_dependencies" not in gaps:
                gaps.append("missing_dependencies")
            reason_parts.append("missing_dependencies")

        reason = ",".join(reason_parts) if reason_parts else "passed"
        return DecompositionQualityGateResult(
            passed=passed,
            decomposition_contract_score=contract_score,
            plan_feasibility_score=feasibility,
            decomposition_gaps=gaps,
            reason=reason,
            contract_version=contract_version,
        )

    @classmethod
    def build_clarification_prompt(cls, gaps: list[str]) -> str:
        guidance = {
            "missing_goal": "请明确你的最终目标与期望结果。",
            "missing_constraints": "请补充关键约束（时间、精力、预算、截止日期）。",
            "missing_milestones": "请给出 2-3 个推进里程碑。",
            "missing_acceptance_criteria": "请说明怎样算达成（可量化验收标准）。",
            "missing_risks": "请补充这条路径的关键风险与规避措施。",
            "missing_time_boundary": "请提供明确时间边界（例如 14 天、6 周、截止日期）。",
            "missing_dependencies": "请确认步骤之间的先后依赖关系（先做什么，再做什么）。",
        }
        lines = [guidance[item] for item in gaps if item in guidance]
        if not lines:
            lines = ["请补充更具体的目标、约束和验收标准，我再生成可执行拆解方案。"]
        return "\n".join(f"- {line}" for line in lines)

    @classmethod
    def _estimate_feasibility(
        cls,
        *,
        contract_score: float,
        plan: ExecutablePlan | None,
        gaps: list[str],
    ) -> float:
        score = 0.45 + 0.4 * contract_score
        if plan:
            tool_count = len(plan.tool_calls)
            if tool_count > 0:
                score += 0.12
            if plan.execution_order:
                score += 0.08
            if plan.confidence:
                score += min(float(plan.confidence) * 0.2, 0.15)
            if tool_count > 0 and not plan.execution_order:
                score -= 0.05
            if tool_count > 5 and plan.execution_order and len(plan.execution_order) == 1:
                score -= 0.04

        score -= 0.03 * len(gaps)
        return max(0.0, min(score, 1.0))

    @staticmethod
    def _has_acceptance_criteria(plan: ExecutablePlan) -> bool:
        if plan.success_criteria:
            return True
        for step in plan.tool_calls:
            if step.success_criteria is not None:
                return True
        return False

    @classmethod
    def _has_time_boundary(cls, contract: dict[str, Any]) -> bool:
        constraints = contract.get("constraints")
        if not isinstance(constraints, list):
            return False
        for item in constraints:
            text = str(item).lower()
            if any(token in text for token in cls._TIME_BOUNDARY_TOKENS):
                return True
        return False

    @staticmethod
    def _has_dependency_relations(plan: ExecutablePlan) -> bool:
        if not plan.tool_calls:
            return False
        if len(plan.tool_calls) <= 1:
            return True
        has_dep_edges = any(tc.depends_on for tc in plan.tool_calls)
        if has_dep_edges:
            return True
        if plan.execution_order and len(plan.execution_order) > 1:
            return True
        return False

    @staticmethod
    def _to_float(value: Any, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _collect_missing_required(
        cls,
        *,
        contract_data: dict[str, Any],
        existing_gaps: list[str],
    ) -> list[str]:
        missing = set(cls.REQUIRED_CONTRACT_GAPS.intersection(existing_gaps))

        field_map = {
            "missing_goal": "goal",
            "missing_constraints": "constraints",
            "missing_milestones": "milestones",
            "missing_acceptance_criteria": "acceptance_criteria",
            "missing_risks": "risks",
        }
        for gap, field in field_map.items():
            value = contract_data.get(field)
            if isinstance(value, str):
                if not value.strip():
                    missing.add(gap)
                continue
            if isinstance(value, list):
                if not any(str(item).strip() for item in value):
                    missing.add(gap)
                continue
            if not value:
                missing.add(gap)

        return sorted(missing)
