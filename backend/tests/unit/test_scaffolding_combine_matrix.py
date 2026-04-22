from __future__ import annotations

import pytest

from app.scaffolding.scaffolding_fsm import ScaffoldingFSM


@pytest.mark.parametrize(
    ("srl_delta", "metacog_delta", "expected"),
    [
        (1.0, 1.0, 1.0),
        (1.0, 0.5, 1.0),
        (1.0, -0.5, 1.0),
        (0.0, 0.5, 0.5),
        (0.0, 0.0, 0.0),
        (0.0, -0.5, -0.5),
        (-1.0, 1.0, -1.0),
        (-1.0, 0.5, -1.0),
        (-1.0, -0.5, -1.0),
    ],
)
def test_scaffolding_combine_matrix_is_non_additive(
    srl_delta: float,
    metacog_delta: float,
    expected: float,
) -> None:
    assert ScaffoldingFSM.combine_support_delta(srl_delta, metacog_delta) == expected
