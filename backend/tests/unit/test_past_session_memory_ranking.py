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


class TestAssistantPersistSurvivesPoisonedSharedSession:
    @pytest.mark.asyncio
    async def test_persist_uses_independent_session(self, monkeypatch):
        """共享 session poisoned（FK violation 后）时 assistant 消息仍须落库。"""
        import app.orchestration.persistence_layer as pl

        created = {}

        class _FakeMsg:
            id = "00000000-0000-0000-0000-000000000001"

        class _FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            def add(self, obj):
                created["added"] = obj

            async def flush(self):
                pass

            async def commit(self):
                created["committed"] = True

        class _PoisonedShared:
            """模拟 flush FK violation 之后的共享 session：任何操作都抛 rollback 错。"""

            async def rollback(self):
                raise RuntimeError("already rolled back")

        captured = {}

        def fake_enqueue(**kwargs):
            captured.update(kwargs)

        class _Layer(pl.PersistenceLayerMixin):
            _coerce_session_uuid = staticmethod(lambda s: s)

        monkeypatch.setattr(pl, "AsyncSessionLocal", lambda: _FakeSession(), raising=False)
        # import 在函数内，直接 patch 模块级引用无效——改为注入到 app.db.session
        import app.db.session as dbs

        monkeypatch.setattr(dbs, "AsyncSessionLocal", lambda: _FakeSession(), raising=False)
        monkeypatch.setattr(pl.MemoryInferredWriteLaneService, "enqueue_from_session", staticmethod(fake_enqueue))
        monkeypatch.setattr(pl, "ChatMessage", lambda **kw: _FakeMsg(), raising=False)
        monkeypatch.setattr(pl, "llm_service", type("L", (), {"default_model": "m"})(), raising=False)

        layer = _Layer()
        await layer._persist_assistant_message(
            active_db=_PoisonedShared(),
            user_id="11111111-1111-1111-1111-111111111111",
            session_id="22222222-2222-2222-2222-222222222222",
            full_response="已记下：下周三有数据结构期中考试",
        )
        assert created.get("committed") is True, "assistant message must persist via independent session"
        assert captured.get("assistant_message", "").startswith("已记下")


from uuid import UUID as _UUID


class TestLaneSurvivesExtractorOutage:
    @pytest.mark.asyncio
    async def test_rule_candidate_survives_llm_503(self, monkeypatch):
        """LLM 熔断 503 时规则候选/口令 fallback 必须照常入工作记忆（mr1 零条根因）。"""
        import app.services.working_memory_pipeline_service as wmp

        class _Boom:
            async def dry_run_extract(self, **kwargs):
                raise RuntimeError("503: LLM Service Temporarily Unavailable (Circuit Open)")

        class _KS:
            async def get_feature_mode(self, name):
                return "live" if name == "llm_extractor_enabled" else "live"

        class _WM:
            def __init__(self):
                self.calls = []

            async def upsert_entry(self, **kwargs):
                self.calls.append(kwargs)
                return kwargs

        class _Consol:
            def is_explicit_rejection(self, text):
                return False

            def is_explicit_confirmation(self, text):
                return False

            async def maybe_consolidate_recent_entries(self, **kwargs):
                return []

        class _Pipe(wmp.WorkingMemoryPipelineService):
            def __init__(self):
                self.llm_extractor = _Boom()
                self.kill_switches = _KS()
                self.working_memory = _WM()
                self.consolidation = _Consol()

        pipe = _Pipe()
        from app.services.memory_inferred_write_lane import InferredEpisodicCandidate
        from datetime import datetime as _dt

        rule = InferredEpisodicCandidate(
            candidate_text="用户最喜欢的电影是《星际穿越》。",
            subject_type="self",
            confidence=0.92,
            evidence_token="tok",
            decay_policy="30d",
            source_lane="inferred_extraction",
            semantic_key="k1",
            evidence_refs=[{"type": "chat_turn", "id": "tok"}],
            occurred_at=_dt(2026, 9, 19, 12, 0, 0),
            due_at=None,
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=None,
        )
        entries = await pipe.process_chat_turn(
            user_id=_UUID("11111111-1111-1111-1111-111111111111"),
            session_id=_UUID("22222222-2222-2222-2222-222222222222"),
            user_message="我最喜欢的电影是《星际穿越》，帮我记住这个。",
            assistant_message="已记住",
            evidence_token="tok",
            rule_candidate=rule,
        )
        assert entries, "rule candidate must survive LLM circuit-open 503"
