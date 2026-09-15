import json
from pathlib import Path
from uuid import uuid4

from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService


def test_memory_subject_type_dataset_contract(db_session):
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "stage17" / "memory_subject_type_dataset.json"
    )
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert len(cases) >= 24

    service = MemoryInferredWriteLaneService(db_session)
    user_id = uuid4()

    positives = 0
    for index, case in enumerate(cases):
        candidate = service.extract_candidate(
            user_id=user_id,
            user_message=case["user_message"],
            assistant_message="收到，我会记住这个上下文。",
            evidence_token=f"stage17_{index}",
        )
        if case["label"] == "positive":
            positives += 1
            assert candidate is not None
            assert candidate.subject_type == case["subject_type"]
        else:
            assert candidate is None
    assert positives >= 20


def test_person_mention_candidate_uses_hmac_metadata(db_session):
    service = MemoryInferredWriteLaneService(db_session)
    user_id = uuid4()
    candidate = service.extract_candidate(
        user_id=user_id,
        user_message="我和老张约好这周末一起刷题。",
        assistant_message="收到。",
        evidence_token="turn_social_1",
    )

    assert candidate is not None
    assert candidate.subject_type in {"person_mention", "commitment"}
    if candidate.subject_type == "person_mention":
        assert candidate.mentioned_entity_owner_user_id == user_id
        assert candidate.mentioned_entity_hash is not None
