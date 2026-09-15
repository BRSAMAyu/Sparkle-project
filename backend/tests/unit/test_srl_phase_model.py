from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.srl_phase_types import INACTIVE_TIMEOUT_HOURS, SRL_EVENT_TYPES, SRLPhase, SRLPhaseState, SRL_TRANSITION_MATRIX


def test_srl_phase_enum_has_four_values() -> None:
    assert [phase.value for phase in SRLPhase] == [
        "FORETHOUGHT",
        "PERFORMANCE",
        "SELF_REFLECTION",
        "UNKNOWN",
    ]


def test_srl_phase_state_accepts_confidence_in_unit_interval() -> None:
    state = SRLPhaseState(user_id=uuid4(), confidence=0.42)
    assert state.confidence == 0.42


def test_srl_phase_state_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError):
        SRLPhaseState(user_id=uuid4(), confidence=1.1)


def test_transition_matrix_registers_every_phase_and_event() -> None:
    for phase in SRLPhase:
        assert phase in SRL_TRANSITION_MATRIX
        assert set(SRL_TRANSITION_MATRIX[phase].keys()) == set(SRL_EVENT_TYPES)


def test_state_defaults_are_timestamped() -> None:
    state = SRLPhaseState(user_id=uuid4())
    assert isinstance(state.phase_started_at, datetime)
    assert isinstance(state.updated_at, datetime)
    assert INACTIVE_TIMEOUT_HOURS == 24
