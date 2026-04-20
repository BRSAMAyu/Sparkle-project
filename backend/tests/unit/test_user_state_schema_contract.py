from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest

from app.state_aggregator.schema import (
    CommitmentSummaryValue,
    StateFieldEnvelope,
    UserStateV1,
)


def test_user_state_v1_schema_is_frozen() -> None:
    state = UserStateV1(user_id=uuid4())

    with pytest.raises(FrozenInstanceError):
        state.schema_version = "user_state.v2"


def test_user_state_v1_uses_expected_schema_version() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        commitment_summary=StateFieldEnvelope(
            value=CommitmentSummaryValue(
                overdue_count=1,
                next_due_at=None,
                pending_commitment_ids=("c1",),
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("episodic:c1",),
            freshness_seconds=0,
        ),
    )

    assert state.schema_version == "user_state.v1.1"
    assert state.commitment_summary is not None
    assert state.commitment_summary.value.overdue_count == 1
