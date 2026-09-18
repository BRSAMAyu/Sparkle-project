"""记忆写入 naive-UTC 归一化回归。

背景：LLM 抽取器把 LLM 返回的 ISO 时间戳（'Z'/'+00:00'）解析成 tz-aware
datetime，直接绑定到 TIMESTAMP WITHOUT TIME ZONE 列时 asyncpg 抛
DataError（can't subtract offset-naive and offset-aware datetimes），
导致 inferred_extraction 记忆写入全量回滚（验收 mr1/a2 断点）。
"""

from datetime import UTC, datetime, timedelta, timezone

from uuid import uuid4

from app.core.time_utils import ensure_naive_utc
from app.services.llm_extractor_service import LlmExtractorService
from app.services.memory_service import MemoryService


AWARE = datetime(2026, 6, 22, 0, 0, tzinfo=timezone.utc)


class TestEnsureNaiveUtc:
    def test_aware_converted_to_naive_utc(self):
        # +08:00 的 08:00 == UTC 00:00
        aware = datetime(2026, 6, 22, 8, 0, tzinfo=timezone(timedelta(hours=8)))
        out = ensure_naive_utc(aware)
        assert out.tzinfo is None
        assert (out.year, out.month, out.day, out.hour) == (2026, 6, 22, 0)

    def test_naive_passthrough(self):
        naive = datetime(2026, 6, 22, 0, 0)
        assert ensure_naive_utc(naive) is naive

    def test_none_passthrough(self):
        assert ensure_naive_utc(None) is None

    def test_utc_z_suffix(self):
        out = ensure_naive_utc(datetime(2026, 6, 22, 0, 0, tzinfo=UTC))
        assert out.tzinfo is None


class TestRecordBuilderNormalizes:
    def test_build_episodic_memory_record_strips_tzinfo(self):
        record = MemoryService._build_episodic_memory_record(
            user_id=uuid4(),
            summary="User's favorite movie is Interstellar.",
            source_type="chat",
            source_id=None,
            source_lane="inferred_extraction",
            occurred_at=AWARE,
            importance_score=0.98,
            confidence=0.98,
            tags=["stage16:auto_memory"],
            normalized_refs=[{"type": "chat_turn", "id": "tok"}],
            evidence_snapshot=None,
            embedding=None,
            evidence_score=0.2,
            evidence_token="tok",
            decay_policy="30d",
            semantic_key="favorite_movie:interstellar",
            subject_type="self",
            due_at=AWARE,
            resolved_at=None,
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=None,
        )
        assert record.occurred_at.tzinfo is None
        assert record.due_at.tzinfo is None
        # UTC 语义保留
        assert record.occurred_at.year == 2026 and record.occurred_at.month == 6


class TestLLMExtractorSource:
    def test_build_candidate_parses_z_suffix_to_naive(self):
        service = LlmExtractorService.__new__(LlmExtractorService)
        candidate = service._build_candidate(
            raw={
                "candidate_text": "User's favorite movie is Interstellar.",
                "subject_type": "self",
                "semantic_key": "favorite_movie:interstellar",
                "confidence": 0.98,
                "occurred_at": "2026-06-22T00:00:00Z",
            },
            evidence_token="tok",
            occurred_at=datetime(2026, 9, 18, 0, 0),
        )
        assert candidate is not None
        assert candidate.occurred_at.tzinfo is None
        assert (candidate.occurred_at.year, candidate.occurred_at.month, candidate.occurred_at.day) == (2026, 6, 22)

    def test_build_candidate_offset_suffix_to_naive(self):
        service = LlmExtractorService.__new__(LlmExtractorService)
        candidate = service._build_candidate(
            raw={
                "candidate_text": "考试在下周三",
                "subject_type": "commitment",
                "semantic_key": "exam:ds_midterm",
                "confidence": 0.9,
                "occurred_at": "2026-09-23T09:00:00+08:00",
                "due_at": "2026-09-23T09:00:00+08:00",
            },
            evidence_token="tok",
            occurred_at=datetime(2026, 9, 18, 0, 0),
        )
        assert candidate is not None
        assert candidate.occurred_at.tzinfo is None
        assert candidate.occurred_at.hour == 1  # +08:00 09:00 == UTC 01:00
        assert candidate.due_at is not None and candidate.due_at.tzinfo is None
