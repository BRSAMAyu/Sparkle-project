"""跨会话记忆候选排序回归。

背景：_get_past_session_memory 之前直接取 list_recent_episodic 的
occurred_at DESC top-3。occurred_at 是"事件发生时间"（LLM 抽取会给过去
日期），种子记忆（播种时刻=今天）永远挤掉刚推断入库的高价值记忆，
新会话召回只剩种子条目（验收 a2 断点）。
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.context_manager import ContextOrchestrator


def _row(summary, importance, confidence, created_at, occurred_at):
    return SimpleNamespace(
        id=f"id-{summary}",
        summary=summary,
        subject_type="self",
        source_type="chat",
        occurred_at=occurred_at,
        created_at=created_at,
        tags=[],
        importance_score=importance,
        confidence=confidence,
    )


class TestPastSessionMemoryRanking:
    @pytest.mark.asyncio
    async def test_high_value_inferred_memory_outranks_fresher_seeds(self):
        manager = ContextOrchestrator.__new__(ContextOrchestrator)
        manager.db = None
        seed = _row("completed 操作系统-死锁", 0.72, 0.72, datetime(2026, 9, 19, 3, 0, 0), datetime(2026, 9, 19, 3, 0, 0))
        movie = _row(
            "用户最喜欢的电影是《星际穿越》", 0.98, 0.98, datetime(2026, 9, 19, 3, 5, 0), datetime(2026, 6, 22, 0, 0, 0)
        )

        async def fake_get_recent(user_id, limit=3, **kwargs):
            # 模拟 SQL occurred_at DESC：种子(今天)在前，电影(6月)在最后
            return [seed, seed, seed, seed, movie]

        service_holder = SimpleNamespace(get_recent_episodic=AsyncMock(side_effect=fake_get_recent))
        import app.core.context_manager as cm

        original = cm.MemoryService
        cm.MemoryService = lambda *a, **k: service_holder
        try:
            memories = await manager._get_past_session_memory(user_id=None)  # type: ignore[arg-type]
        finally:
            cm.MemoryService = original

        assert memories, "should return memories"
        summaries = [m["summary"] for m in memories]
        assert "用户最喜欢的电影是《星际穿越》" in summaries, (
            f"high-value inferred memory must not be crowded out by seeds: {summaries}"
        )


class TestRankerFreshnessUsesIngestTime:
    def test_old_event_recent_ingest_scores_high(self):
        from types import SimpleNamespace as NS
        from datetime import datetime, timedelta
        from app.core.context_ranker import _score_item

        now = datetime(2026, 9, 19, 4, 0, 0)
        movie = NS(
            occurred_at=datetime(2026, 6, 22), created_at=now - timedelta(minutes=5),
            evidence_score=0.2, correction_count=0, confidence=0.95, importance_score=0.95,
            tags=["stage16:auto_memory"],
        )
        seed = NS(
            occurred_at=now, created_at=now - timedelta(hours=2),
            evidence_score=0.2, correction_count=0, confidence=0.72, importance_score=0.72,
            tags=[],
        )
        movie_score = _score_item(movie, kind="episodic", now=now)
        seed_score = _score_item(seed, kind="episodic", now=now)
        assert movie_score > seed_score, (
            f"recently-ingested old-event memory must outrank staler seed: movie={movie_score} seed={seed_score}"
        )
