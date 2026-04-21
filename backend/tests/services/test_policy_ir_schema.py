from __future__ import annotations

from datetime import datetime
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.policy_ir import (
    POLICY_IR_SCHEMA_VERSION,
    POLICY_IR_VERSION,
    PendingPoliciesSummaryValue,
    PolicyAction,
    PolicyActionType,
    PolicyContext,
    PolicyRule,
    PolicyTrigger,
    PolicyTriggerType,
    policy_ir_json_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_policy_ir_version_is_frozen() -> None:
    assert POLICY_IR_VERSION == "v1"
    assert POLICY_IR_SCHEMA_VERSION == "policy_ir.v1"


def test_policy_ir_schema_contains_core_fields() -> None:
    schema = policy_ir_json_schema()

    assert {"policy_id", "commitment_id", "user_id", "trigger", "action", "constraints", "context", "version"} <= set(
        schema["properties"].keys()
    )


def test_policy_trigger_and_action_enums_expose_expected_contract() -> None:
    assert PolicyTriggerType.TIME_BEFORE_DUE.value == "time_before_due"
    assert PolicyTriggerType.PEER_MISSED.value == "peer_missed"
    assert PolicyTriggerType.SUCCESS_STREAK.value == "success_streak"
    assert PolicyActionType.NOTIFY_USER.value == "notify_user"
    assert PolicyActionType.LOWER_DIFFICULTY.value == "lower_difficulty"


def test_policy_models_forbid_extra_fields() -> None:
    with pytest.raises(Exception):
        PolicyTrigger.model_validate({"type": "time_before_due", "params": {}, "unexpected": True})

    with pytest.raises(Exception):
        PolicyContext.model_validate({"commitment_summary": "x", "unexpected": True})


def test_policy_rule_round_trips() -> None:
    rule = PolicyRule(
        policy_id="policy-1",
        commitment_id=uuid4(),
        user_id=uuid4(),
        trigger=PolicyTrigger(type=PolicyTriggerType.TIME_BEFORE_DUE, params={"offset_days": 1}),
        action=PolicyAction(type=PolicyActionType.NOTIFY_USER, params={"template_id": "policy_due_reminder_1d"}),
        context=PolicyContext(
            commitment_summary="Finish review",
            commitment_due_at=datetime(2026, 4, 24, 18, 0, 0),
        ),
        version=POLICY_IR_VERSION,
    )

    restored = PolicyRule.model_validate(rule.model_dump(mode="json"))

    assert restored == rule


def test_pending_policies_summary_contract() -> None:
    summary = PendingPoliciesSummaryValue(
        count=2,
        next_trigger_at=datetime(2026, 4, 22, 9, 0, 0),
        policy_ids=("p1", "p2"),
    )

    assert summary.count == 2
    assert summary.policy_ids == ("p1", "p2")


def test_policy_ir_schema_guard_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/stage24/check_policy_ir_schema.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
