from __future__ import annotations

from app.services.evidence import (
    EvidenceDirection,
    EvidenceTarget,
    build_task_feedback_evidence,
    build_task_outcome_evidence,
)


def test_task_completion_generates_capacity_and_completion_evidence() -> None:
    event = {
        "event_type": "task.completed",
        "user_id": "u1",
        "task_id": "t1",
        "completion_rate": 1.0,
        "estimated_minutes": 30,
        "actual_minutes": 25,
        "difficulty": 4,
    }

    evidence = build_task_outcome_evidence(event, completed=True)
    targets = {item.target_latent_variable for item in evidence}

    assert EvidenceTarget.TASK_COMPLETION_STATE in targets
    assert EvidenceTarget.EXECUTION_CAPACITY in targets
    assert any(
        item.target_latent_variable == EvidenceTarget.TASK_AVERSION and item.direction == EvidenceDirection.DECREASE
        for item in evidence
    )


def test_task_abandonment_generates_aversion_load_and_emotional_evidence() -> None:
    event = {
        "event_type": "task.abandoned",
        "user_id": "u1",
        "task_id": "t1",
        "reason": "太难了，我有点崩溃",
        "estimated_minutes": 30,
        "time_spent": 5,
    }

    evidence = build_task_outcome_evidence(event, completed=False)
    targets = {item.target_latent_variable for item in evidence}

    assert EvidenceTarget.TASK_COMPLETION_STATE in targets
    assert EvidenceTarget.TASK_AVERSION in targets
    assert EvidenceTarget.COGNITIVE_LOAD in targets
    assert EvidenceTarget.EMOTIONAL_BLOCK in targets


def test_task_feedback_too_difficult_generates_load_evidence() -> None:
    event = {
        "event_type": "task.feedback_submitted",
        "user_id": "u1",
        "task_id": "t1",
        "category": "too_difficult",
        "feedback_text": "这一步太难了",
    }

    evidence = build_task_feedback_evidence(event)

    assert any(item.target_latent_variable == EvidenceTarget.COGNITIVE_LOAD for item in evidence)
    assert all(item.source_type == "outcome" for item in evidence)
