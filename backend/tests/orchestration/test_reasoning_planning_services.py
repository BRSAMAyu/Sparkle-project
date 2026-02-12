from __future__ import annotations

import pytest

from app.orchestration.plan_search_service import PlanSearchService
from app.orchestration.reasoning_verifier_service import ReasoningVerifierService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.uncertainty_calibrator import UncertaintyCalibrator


def _sample_plan(confidence: float = 0.82) -> ExecutablePlan:
    return ExecutablePlan(
        confidence=confidence,
        tool_calls=[
            ToolCallSpec(id="call_1", name="create_plan", params={"title": "12-week roadmap"}),
            ToolCallSpec(id="call_2", name="create_task", params={"title": "week1"}, depends_on=["call_1"]),
        ],
        success_criteria={"completion_rate": 0.8},
        execution_order=[["call_1"], ["call_2"]],
    )


def test_reasoning_verifier_detects_missing_contract_fields() -> None:
    result = ReasoningVerifierService.verify(
        plan=_sample_plan(),
        contract={"goal": "通过考试", "constraints": ["30天"]},
    )
    assert result.contract_coverage < 0.85
    assert "missing_milestones" in result.verifier_fail_reasons
    assert "missing_acceptance_criteria" in result.verifier_fail_reasons


def test_uncertainty_calibrator_requests_clarification_on_low_confidence() -> None:
    result = UncertaintyCalibrator.calibrate(
        message="先试试吧，差不多就行",
        route_confidence=0.42,
        verifier_score=0.58,
        contract_coverage=0.5,
        plan_feasibility_score=0.52,
        decomposition_gap_count=3,
    )
    assert result.clarification_needed
    assert result.uncertainty_score >= 0.62


@pytest.mark.asyncio
async def test_plan_search_service_selects_better_candidate() -> None:
    base = _sample_plan(confidence=0.6)
    service = PlanSearchService()

    async def _generator(seed: ExecutablePlan, depth: int, branch_index: int) -> ExecutablePlan | None:
        _ = seed
        if depth != 1:
            return None
        if branch_index == 0:
            return _sample_plan(confidence=0.9)
        return None

    async def _score(plan: ExecutablePlan) -> float:
        return float(plan.confidence or 0.0)

    result = await service.search(
        base_plan=base,
        generate_candidate=_generator,
        score_plan=_score,
        beam_width=3,
        max_depth=4,
        time_budget_ms=1200,
    )
    assert result.best_score >= 0.9
    assert result.plan_revision_count >= 1
    assert result.search_budget_used_ms >= 0
