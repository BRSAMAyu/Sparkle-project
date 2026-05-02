from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.core.data_minimization import (
    TARGET_MODEL_SCOPES,
    DataMinimizationAuditor,
    DataMinimizationViolation,
    canonical_target_model,
    resolve_data_minimization_mode,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_required_full_vision_scopes_are_registered() -> None:
    required = {
        "achievement",
        "causal_trace",
        "chronicle",
        "cohort_aggregate",
        "growth_chronicle",
        "intervention_episode",
        "knowledge_node",
        "policy_decision",
        "recall_opportunity",
        "relationship_model",
        "return_case_file",
        "skill_entry",
        "source_asset",
        "sprint_pack",
        "user_profile",
    }

    assert required.issubset(TARGET_MODEL_SCOPES)


def test_registered_model_strips_fields_outside_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPARKLE_DATA_MINIMIZATION_MODE", "enforce")
    auditor = DataMinimizationAuditor()

    filtered = auditor.check_before_store(
        user_id="u-1",
        target_model="achievement",
        data={
            "achievement_id": "streak_7",
            "unlocked_at": "2026-05-02T00:00:00Z",
            "email": "learner@example.test",
            "raw_content": "full prompt transcript",
        },
    )

    assert filtered == {
        "achievement_id": "streak_7",
        "unlocked_at": "2026-05-02T00:00:00Z",
    }


def test_aliases_resolve_to_canonical_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARKLE_DATA_MINIMIZATION_MODE", "enforce")
    auditor = DataMinimizationAuditor()

    assert canonical_target_model("user_achievements") == "achievement"
    assert auditor.check_before_store(
        user_id="u-1",
        target_model="user_achievements",
        data={"achievement_id": "sprint_first", "share_count": 2},
    ) == {"achievement_id": "sprint_first"}


def test_unknown_model_passes_through_in_audit_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPARKLE_DATA_MINIMIZATION_MODE", "audit")
    auditor = DataMinimizationAuditor()

    data = {"raw": "kept for discovery"}

    assert auditor.check_before_store("u-1", "new_shadow_model", data) == data


def test_unknown_model_raises_in_enforce_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARKLE_DATA_MINIMIZATION_MODE", "enforce")
    auditor = DataMinimizationAuditor()

    with pytest.raises(DataMinimizationViolation) as exc_info:
        auditor.check_before_store(
            user_id="u-1",
            target_model="new_shadow_model",
            data={"email": "learner@example.test", "note": "unsafe"},
        )

    violation = exc_info.value
    assert violation.audit_record["event"] == "data_minimization_violation"
    assert violation.audit_record["fallback_data"] == {}
    assert violation.fields == ["email", "note"]


def test_production_defaults_to_enforce_without_explicit_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPARKLE_DATA_MINIMIZATION_MODE", raising=False)

    assert resolve_data_minimization_mode(environment="production") == "enforce"
    assert resolve_data_minimization_mode(environment="development") == "audit"


def test_data_minimization_guard_is_registered_and_passes() -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/run_all_rule_guards.sh"),
            "--rule",
            "GOV-DATA-MIN",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
