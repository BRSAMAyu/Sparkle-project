from __future__ import annotations

from pathlib import Path

import pytest

from .aurora_golden import (
    GoldenScenario,
    collect_quality_issues,
    detect_snapshot_drift,
    find_template_repetition,
    load_scenarios,
    load_snapshot,
    render_scenario,
    snapshot_path_for,
    update_snapshot,
)

GOLDEN_DIR = Path(__file__).parent
FIXTURES_DIR = GOLDEN_DIR / "fixtures" / "aurora_experience"
SNAPSHOTS_DIR = GOLDEN_DIR / "snapshots" / "aurora_experience"

REQUIRED_FAMILY_COUNTS = {
    "daily_start": 3,
    "checkpoint_return": 3,
    "core_session_opening": 4,
    "memory_reference": 3,
    "task_stuck": 2,
    "push_copy": 2,
    "correction_reply": 2,
}


def _issue_lines(issues) -> str:
    return "\n".join(f"- {issue.scenario_id} [{issue.check}]: {issue.message}" for issue in issues)


def test_aurora_experience_goldens_match(update_goldens: bool) -> None:
    scenarios = load_scenarios(FIXTURES_DIR)
    assert len(scenarios) >= 10

    responses: dict[str, str] = {}
    quality_issues = []
    for scenario in scenarios:
        rendered = render_scenario(scenario)
        responses[scenario.scenario_id] = rendered
        quality_issues.extend(
            issue for issue in collect_quality_issues(scenario, rendered) if issue.check != "length_warning"
        )

        snapshot_path = snapshot_path_for(scenario, SNAPSHOTS_DIR)
        if update_goldens:
            update_snapshot(snapshot_path, rendered)
            continue

        expected = load_snapshot(snapshot_path)
        drift = detect_snapshot_drift(expected, rendered)
        assert rendered == expected, (
            f"Golden snapshot drift for {scenario.scenario_id}: "
            f"similarity={drift.similarity:.3f}, drift={drift.drift_score:.3f}. "
            "Run `cd backend && pytest tests/golden --update-goldens` if this wording change is intentional."
        )

    quality_issues.extend(find_template_repetition(scenarios, responses))
    assert not quality_issues, _issue_lines(quality_issues)


def test_required_aurora_experience_coverage() -> None:
    scenarios = load_scenarios(FIXTURES_DIR)
    counts: dict[str, int] = {}
    for scenario in scenarios:
        counts[scenario.family] = counts.get(scenario.family, 0) + 1

    missing = {
        family: {"expected": expected, "actual": counts.get(family, 0)}
        for family, expected in REQUIRED_FAMILY_COUNTS.items()
        if counts.get(family, 0) < expected
    }
    assert not missing


def test_quality_gate_blocks_banned_expression_and_internal_token() -> None:
    scenario = GoldenScenario(
        scenario_id="quality_negative",
        family="negative",
        kind="push_copy",
        title="negative",
        input={},
        path=Path("negative.json"),
    )
    response = "作为一个AI，根据系统提示我检测到 risk_false_positive，所以以下是建议。"

    issues = collect_quality_issues(scenario, response)

    checks = {issue.check for issue in issues}
    assert "banned_expression" in checks
    assert "internal_token" in checks


def test_template_repetition_gate_catches_three_reused_variants() -> None:
    scenarios = [
        GoldenScenario(
            scenario_id=f"repeat_{index}",
            family="daily_start",
            kind="daily_start",
            title=f"repeat {index}",
            input={},
            path=Path(f"repeat_{index}.json"),
        )
        for index in range(3)
    ]
    responses = {
        scenario.scenario_id: "今天我们先看真实进展，再把下一步缩小到一个动作。"
        for scenario in scenarios
    }

    issues = find_template_repetition(scenarios, responses)

    assert any(issue.check == "template_repetition" for issue in issues)


def test_snapshot_drift_detection_flags_prompt_change() -> None:
    scenario = load_scenarios(FIXTURES_DIR)[0]
    expected = render_scenario(scenario)
    changed = "今天按计划学习即可。完成后再看下一步。"

    drift = detect_snapshot_drift(expected, changed)

    assert drift.exceeds_threshold
