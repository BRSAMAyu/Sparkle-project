from __future__ import annotations

import json
from pathlib import Path

from app.orchestration.reasoning_verifier_service import ReasoningVerifierService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.task_decomposition_contract import build_task_decomposition_contract
from app.orchestration.uncertainty_calibrator import UncertaintyCalibrator


def _load_cases() -> list[dict]:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "reasoning_planning_benchmark.jsonl"
    rows: list[dict] = []
    with fixture.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_plan_from_message(message: str) -> ExecutablePlan:
    confidence = 0.8 if "里程碑" in message and "验收" in message else 0.45
    return ExecutablePlan(
        confidence=confidence,
        tool_calls=[
            ToolCallSpec(id="call_1", name="create_plan", params={"message": message}),
            ToolCallSpec(id="call_2", name="batch_create_tasks", params={"message": message}, depends_on=["call_1"]),
        ],
        success_criteria={"completion_rate": 0.8},
        execution_order=[["call_1"], ["call_2"]],
    )


def test_reasoning_planning_benchmark_guardrail() -> None:
    failures: list[str] = []
    for case in _load_cases():
        message = str(case["message"])
        contract = build_task_decomposition_contract(
            message=message,
            intent="create_plan",
            extracted_entities={},
            conversation_context=[],
        ).to_dict()
        plan = _build_plan_from_message(message)

        verifier = ReasoningVerifierService.verify(plan=plan, contract=contract)
        uncertainty = UncertaintyCalibrator.calibrate(
            message=message,
            route_confidence=float(case.get("route_confidence", 0.6)),
            verifier_score=verifier.verifier_score,
            contract_coverage=verifier.contract_coverage,
            plan_feasibility_score=float(plan.confidence or 0.0),
            decomposition_gap_count=len(contract.get("gaps", [])),
        )

        min_verifier_score = case.get("min_verifier_score")
        if min_verifier_score is not None and verifier.verifier_score < float(min_verifier_score):
            failures.append(
                f"{case['case_id']}: verifier_score={verifier.verifier_score:.2f} < min={float(min_verifier_score):.2f}"
            )
        max_uncertainty_score = case.get("max_uncertainty_score")
        if max_uncertainty_score is not None and uncertainty.uncertainty_score > float(max_uncertainty_score):
            failures.append(
                f"{case['case_id']}: uncertainty_score={uncertainty.uncertainty_score:.2f} > max={float(max_uncertainty_score):.2f}"
            )
        min_uncertainty_score = case.get("min_uncertainty_score")
        if min_uncertainty_score is not None and uncertainty.uncertainty_score < float(min_uncertainty_score):
            failures.append(
                f"{case['case_id']}: uncertainty_score={uncertainty.uncertainty_score:.2f} < min={float(min_uncertainty_score):.2f}"
            )

    assert not failures, " ; ".join(failures)
