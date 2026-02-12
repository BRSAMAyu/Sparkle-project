from __future__ import annotations

import json
from pathlib import Path

from app.orchestration.task_decomposition_contract import build_task_decomposition_contract


def _load_cases() -> list[dict]:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "task_decomposition_benchmark.jsonl"
    rows: list[dict] = []
    with fixture.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_task_decomposition_contract_benchmark_guardrail() -> None:
    failures: list[str] = []
    for case in _load_cases():
        contract = build_task_decomposition_contract(
            message=case["message"],
            intent=case.get("intent"),
            extracted_entities={},
            conversation_context=[],
        )
        min_score = float(case.get("min_score", 0.0))
        if contract.score < min_score:
            failures.append(
                f"{case['case_id']}: score={contract.score:.2f} < min={min_score:.2f}"
            )
        for gap in case.get("must_not_have_gaps", []):
            if gap in contract.gaps:
                failures.append(f"{case['case_id']}: unexpected gap={gap}")
    assert not failures, " ; ".join(failures)
