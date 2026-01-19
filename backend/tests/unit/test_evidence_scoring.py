import pytest

from app.services.evidence_scoring import compute_score


def test_evidence_score_base():
    assert compute_score([]) == pytest.approx(0.2)


def test_evidence_score_with_primary_and_types():
    score = compute_score(
        [
            {"type": "event", "id": "evt_1"},
            {"type": "concept", "id": "node_1"},
        ]
    )
    assert score == pytest.approx(0.7)


def test_evidence_score_missing_penalty():
    score = compute_score(
        [
            {"type": "event", "id": "evt_1"},
            {"type": "concept", "id": "node_1"},
        ],
        evidence_missing=True,
    )
    assert score == pytest.approx(0.2)
