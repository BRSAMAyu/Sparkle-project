from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import check_rule_ag_baseline_prerequisite as rule_ag


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _configure_paths(tmp_path, monkeypatch, *, coverage_ratio: str = "0.909", trigger_count: int = 6, rows: bool = True, cohort_ok: bool = True):
    precheck = _write(
        tmp_path / "stage22_precheck.md",
        (
            "# Stage 22 Precheck\n\n"
            "| item | status | evidence |\n"
            "| --- | --- | --- |\n"
            "| trigger_type_count | PASS | ok |\n"
            "| registered_trigger_types | PASS | ok |\n"
            f"| cohort_fallback_registered | {'PASS' if cohort_ok else 'FAIL'} | ok |\n"
            "| baseline_gate | PASS | ok |\n"
        )
        if rows
        else "# Stage 22 Precheck\n",
    )
    baseline = _write(
        tmp_path / "stage22_prompt_coverage_baseline.md",
        f"# Stage 22 Prompt Coverage Baseline\n\n- coverage_ratio: {coverage_ratio}\n",
    )
    trigger_entries = ",\n".join(f'"type_{index}"' for index in range(trigger_count))
    error_replan = _write(
        tmp_path / "error_replan_bridge.py",
        f'TRIGGERING_ERROR_TYPES = {{\n{trigger_entries}\n}}\n',
    )
    learner = _write(
        tmp_path / "intervention_strategy_learner.py",
        "goal_type_only = cohort_profile.get('goal_type')\nknowledge_level = cohort_profile.get('knowledge_level')\n"
        if cohort_ok
        else "goal_type = cohort_profile.get('goal_type')\n",
    )
    verifier = _write(
        tmp_path / "outcome_verifier.py",
        'for key in ("goal_type", "knowledge_level", "learning_style"):\n    pass\n'
        if cohort_ok
        else "pass\n",
    )

    monkeypatch.setattr(rule_ag, "PRECHECK_PATH", precheck)
    monkeypatch.setattr(rule_ag, "BASELINE_PATH", baseline)
    monkeypatch.setattr(rule_ag, "ERROR_REPLAN_PATH", error_replan)
    monkeypatch.setattr(rule_ag, "LEARNER_PATH", learner)
    monkeypatch.setattr(rule_ag, "OUTCOME_VERIFIER_PATH", verifier)


def test_rule_ag_passes_with_registered_baseline(tmp_path, monkeypatch) -> None:
    _configure_paths(tmp_path, monkeypatch)
    assert rule_ag.check_rule_ag() == []


def test_rule_ag_fails_when_coverage_ratio_drops_below_threshold(tmp_path, monkeypatch) -> None:
    _configure_paths(tmp_path, monkeypatch, coverage_ratio="0.650")
    violations = rule_ag.check_rule_ag()
    assert any(item.startswith("AG003") for item in violations)


def test_rule_ag_fails_when_trigger_registry_is_too_small(tmp_path, monkeypatch) -> None:
    _configure_paths(tmp_path, monkeypatch, trigger_count=4)
    violations = rule_ag.check_rule_ag()
    assert any(item.startswith("AG005") for item in violations)


def test_rule_ag_fails_when_precheck_rows_are_missing(tmp_path, monkeypatch) -> None:
    _configure_paths(tmp_path, monkeypatch, rows=False)
    violations = rule_ag.check_rule_ag()
    assert any(item.startswith("AG004") for item in violations)
