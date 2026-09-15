from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.services.llm_extractor_service import LlmExtractorService


async def _good_llm(*_args, **_kwargs):
    return {
        "candidates": [
            {
                "candidate_text": "本周末要复习高数真题",
                "subject_type": "commitment",
                "confidence": 0.9,
                "decay_policy": "due_at+7d",
                "semantic_key": "commitment:gaoshu",
                "occurred_at": "2026-04-21T10:00:00",
                "due_at": "2026-04-26T18:00:00",
                "mentioned_entity_hash": None,
            }
        ]
    }


@pytest.mark.asyncio
async def test_llm_extractor_returns_rule_y_validated_candidates(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED", True, raising=False)
    service = LlmExtractorService(llm_json=_good_llm)

    candidates = await service.dry_run_extract(
        user_id=uuid4(),
        session_id=uuid4(),
        user_message="这周末我要复习高数真题。",
        assistant_message="好的，我会陪你拆计划。",
        evidence_token="turn-1",
    )

    assert len(candidates) == 1
    assert candidates[0].subject_type == "commitment"
    assert candidates[0].evidence_token == "turn-1"
    assert candidates[0].due_at == datetime.fromisoformat("2026-04-26T18:00:00")


@pytest.mark.asyncio
async def test_llm_extractor_discards_invalid_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED", True, raising=False)

    async def bad_llm(*_args, **_kwargs):
        return {
            "candidates": [
                {
                    "candidate_text": "",
                    "subject_type": "commitment",
                    "confidence": 0.8,
                    "decay_policy": "due_at+7d",
                    "semantic_key": "",
                }
            ]
        }

    service = LlmExtractorService(llm_json=bad_llm)
    candidates = await service.dry_run_extract(
        user_id=uuid4(),
        session_id=uuid4(),
        user_message="明天我要交作业。",
        assistant_message="收到。",
        evidence_token="turn-2",
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_llm_extractor_enforces_session_budget(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_CALL", 200, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_SESSION", 200, raising=False)
    service = LlmExtractorService(llm_json=_good_llm)
    session_id = uuid4()

    first = await service.dry_run_extract(
        user_id=uuid4(),
        session_id=session_id,
        user_message="第一条",
        assistant_message="A",
        evidence_token="turn-a",
    )
    second = await service.dry_run_extract(
        user_id=uuid4(),
        session_id=session_id,
        user_message="第二条",
        assistant_message="B",
        evidence_token="turn-b",
    )

    assert len(first) == 1
    assert second == []


@pytest.mark.asyncio
async def test_llm_extractor_cold_dataset_precision_meets_threshold(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_SESSION", 10000, raising=False)
    service = LlmExtractorService(
        llm_json=lambda *_args, **_kwargs: _good_llm(),
    )
    total = 30
    matches = 0

    for index in range(total):
        results = await service.dry_run_extract(
            user_id=uuid4(),
            session_id=uuid4(),
            user_message=f"样本 {index}: 这周末我要复习高数真题。",
            assistant_message="收到。",
            evidence_token=f"turn-{index}",
        )
        if results and results[0].subject_type == "commitment":
            matches += 1

    precision = matches / total
    assert precision >= 0.85
