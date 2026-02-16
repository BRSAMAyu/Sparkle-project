from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClarificationVOIResult:
    voi_score: float
    clarification_priority_points: list[dict[str, Any]]


class ClarificationVOIService:
    """Rank clarification questions by expected information gain."""

    GAP_QUESTION_MAP: dict[str, tuple[str, str, float]] = {
        "missing_goal": ("你最希望在这件事上达成的可见结果是什么？", "goal_clarity", 0.32),
        "missing_constraints": ("你的关键约束是什么（时间/精力/预算/截止日期）？", "constraints", 0.26),
        "missing_milestones": ("你希望拆成哪 2-3 个里程碑推进？", "decomposition", 0.22),
        "missing_goal_hierarchy": ("请给出愿景、12周目标、每周里程碑的层级关系。", "decomposition", 0.23),
        "broken_goal_traceability": ("请说明每个日行动分别对应哪个周里程碑。", "traceability", 0.2),
        "missing_acceptance_criteria": ("怎样才算完成？请给出可验证标准。", "verification", 0.28),
        "missing_risks": ("当前最可能失败的 1-2 个风险是什么？", "risk_awareness", 0.16),
        "missing_time_boundary": ("你期望的时间边界是多久（例如 2 周或具体日期）？", "constraints", 0.2),
        "missing_dependencies": ("这些步骤的先后依赖关系是什么？", "decomposition", 0.18),
    }

    def rank(
        self,
        *,
        contract: dict[str, Any] | None,
        ambiguity_profile: dict[str, Any] | None = None,
        uncertainty_score: float = 0.0,
        max_questions: int = 3,
    ) -> ClarificationVOIResult:
        contract_data = contract if isinstance(contract, dict) else {}
        profile = ambiguity_profile if isinstance(ambiguity_profile, dict) else {}
        gaps = [str(item) for item in (contract_data.get("gaps") or []) if str(item).strip()]
        ambiguity_score = float(profile.get("ambiguity_score", 0.0) or 0.0)
        normalized_uncertainty = max(0.0, min(float(uncertainty_score), 1.0))

        points: list[dict[str, Any]] = []
        for gap in gaps:
            mapped = self.GAP_QUESTION_MAP.get(gap)
            if not mapped:
                continue
            question, dimension, base_gain = mapped
            expected_gain = base_gain * (0.6 + 0.25 * ambiguity_score + 0.15 * normalized_uncertainty)
            points.append(
                {
                    "gap": gap,
                    "dimension": dimension,
                    "question": question,
                    "expected_gain": round(max(0.01, min(expected_gain, 1.0)), 4),
                }
            )

        points.sort(key=lambda item: float(item.get("expected_gain", 0.0)), reverse=True)
        selected = points[: max(1, min(int(max_questions), 6))]
        voi_score = sum(float(item.get("expected_gain", 0.0)) for item in selected)
        return ClarificationVOIResult(
            voi_score=round(max(0.0, min(voi_score, 1.0)), 4),
            clarification_priority_points=selected,
        )
