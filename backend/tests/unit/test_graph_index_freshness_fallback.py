"""V4-D06 · GraphRAG 时效（watermark）与关系型 fallback。

卡面验收（必须可失败）：
1. 新资料立即有明确版本/索引中状态 —— 未覆盖（uncovered）时关系型立即作答，
   metadata 带关系型版本串与降级原因；AGE 不会被询问旧索引。
2. AGE 旧数据不能压过更新/删除的关系型事实 —— stale 门拦下已删关系的 AGE
   旧行（水位不等）；fresh 面存在性/软删守卫兜住水位窗口内的删除（删除不复活）。
3. 对同题关系型/AGE 来源可复算，失败保留 —— recompute_graph_sources 双源
   并列复算，AGE 故障原文保留（match=None），不静默。

工程口径：SECRET_KEY=ci-test-key DATABASE_URL=sqlite://；AGE 一律 mock
（sqlite 无 AGE，AGE 相关面按守卫豁免口径以可测的 mock 契约面覆盖）。
每个验收面一正一反；monkeypatch cache_service.redis=None → 覆盖水位走
进程内本地缓存（业务键，AUTH-DEEP A-2 允许），隔离且确定。
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.orchestration.graph_rag import GraphRAGRetriever
from app.services.graph_index_watermark import (
    STATE_FRESH,
    STATE_STALE,
    STATE_UNCOVERED,
    STATE_UNKNOWN,
    GraphIndexState,
    GraphIndexWatermark,
    recompute_graph_sources,
    relational_one_hop,
)
from app.workers.graph_sync_worker import GraphSyncWorker

_MIN_STRENGTH = 0.3


async def _make_relation(db, *, src_name: str, tgt_name: str, strength: float = 0.9, relation_type: str = "RELATED"):
    src = KnowledgeNode(name=src_name, importance_level=1)
    tgt = KnowledgeNode(name=tgt_name, importance_level=1)
    db.add_all([src, tgt])
    await db.flush()
    rel = NodeRelation(source_node_id=src.id, target_node_id=tgt.id, relation_type=relation_type, strength=strength)
    db.add(rel)
    await db.flush()
    return src, tgt, rel


def _retriever(db) -> GraphRAGRetriever:
    """graph_search 面只消费 knowledge_service.db；AGE 客户端由用例 patch。"""
    return GraphRAGRetriever(SimpleNamespace(db=db))


def _age_row(src, tgt, *, strength: float = 0.9, relation_type: str = "RELATED") -> dict:
    return {
        "start_id": str(src.id),
        "start_name": src.name,
        "id": str(tgt.id),
        "name": tgt.name,
        "description": tgt.description,
        "relation_type": relation_type,
        "strength": strength,
        "sector": "VOID",
    }


@pytest.fixture
def no_redis(monkeypatch):
    """覆盖水位走 cache_service 进程内本地缓存（业务键允许本地兜底）。"""
    monkeypatch.setattr(cache_service, "redis", None)
    return cache_service


# ---------------------------------------------------------------------------
# 水位判定面（GraphIndexWatermark）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relational_watermark_changes_on_new_relation(db_session, no_redis):
    """正：新资料立即翻版本（watermark 含表名/计数/时间戳）。"""
    wm_before = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm_before is not None
    await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    wm_after = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm_after != wm_before
    assert ":n2:r1" in wm_after  # 双表计数可见（2 节点 1 关系）


@pytest.mark.asyncio
async def test_relational_watermark_changes_on_delete_of_non_latest_row(db_session, no_redis):
    """正：删除非最新行（max(updated_at) 不变）仍翻版本——E-05 delete-isolation
    判例复用，删除绝不留下"水位没动"的假新鲜。"""
    _, _, rel_old = await _make_relation(db_session, src_name="A1", tgt_name="B1")
    await _make_relation(db_session, src_name="A2", tgt_name="B2")
    rel_old.updated_at = datetime(2026, 1, 1)  # 压旧，使另一行是 max
    await db_session.flush()
    wm_before = await GraphIndexWatermark(db_session).relational_watermark()

    await db_session.delete(rel_old)
    await db_session.flush()
    wm_after = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm_after != wm_before
    assert wm_after.endswith(":n4:r1")  # 关系计数 2→1（节点计数不变）


@pytest.mark.asyncio
async def test_resolve_state_uncovered_without_coverage(db_session, no_redis):
    """新功能首启/无覆盖记录 → uncovered（不假称 fresh）。"""
    state = await GraphIndexWatermark(db_session).resolve_state()
    assert state.state == STATE_UNCOVERED
    assert state.reason == "index_uncovered"
    assert state.relational_watermark is not None
    assert state.age_watermark is None


@pytest.mark.asyncio
async def test_resolve_state_stale_on_mismatch(db_session, no_redis):
    """覆盖水位落后 → stale（AGE 不得作答）。注意空库水位恰为
    ``gtsms:0:n0:r0``，故先造真实数据再记录一个确定落后的旧水位。"""
    await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    wm = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm is not None and wm != "gtsms:0:n0:r0"
    await GraphIndexWatermark(db_session).record_age_coverage("gtsms:0:n0:r0")  # 旧水位
    state = await GraphIndexWatermark(db_session).resolve_state()
    assert state.state == STATE_STALE
    assert state.reason == "watermark_mismatch"
    assert state.age_watermark == "gtsms:0:n0:r0"
    assert state.relational_watermark == wm


@pytest.mark.asyncio
async def test_resolve_state_fresh_when_covered(db_session, no_redis):
    wm = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm is not None
    await GraphIndexWatermark(db_session).record_age_coverage(wm)
    state = await GraphIndexWatermark(db_session).resolve_state()
    assert state.state == STATE_FRESH
    assert state.reason == "index_covered"


@pytest.mark.asyncio
async def test_resolve_state_unknown_when_db_absent(no_redis):
    """反：DB 缺席解析失败 → unknown（保守回关系型），不猜 fresh。"""
    state = await GraphIndexWatermark(None).resolve_state()
    assert state.state == STATE_UNKNOWN
    assert state.reason == "resolution_failed"


# ---------------------------------------------------------------------------
# graph_search 时效门（sqlite 真关系型 + mock AGE）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_relation_answered_immediately_with_index_status(db_session, no_redis):
    """验收1 正：新资料（AGE 尚无覆盖记录）立即由关系型作答，metadata 明确
    展示版本与 indexing 状态；旧 AGE 索引不被询问。"""
    src, tgt, _ = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")

    retriever = _retriever(db_session)
    age_mock = AsyncMock()
    retriever.age_client = age_mock

    results, relationships = await retriever.graph_search(["Alpha"])

    age_mock.execute_cypher.assert_not_awaited()  # uncovered：不问旧索引
    assert len(results) == 1
    assert results[0]["name"] == tgt.name
    assert results[0]["source"] == "graph_relational"
    assert relationships[0]["from_id"] == str(src.id)

    gi = retriever.last_graph_index
    assert gi is not None
    assert gi["state"] == STATE_UNCOVERED
    assert gi["mode"] == "relational_fallback"
    assert gi["fallback_reason"] == "index_uncovered"
    assert gi["relational_watermark"]  # 明确版本串
    assert gi["relational_result_count"] == 1


@pytest.mark.asyncio
async def test_stale_age_rows_cannot_override_relational_delete(db_session, no_redis):
    """验收2 反例：关系已被关系型删除、AGE 仍返回旧行（水位停在删除前）——
    门必须拦下旧行：作答不含已删事实，state=stale、原因=watermark_mismatch。"""
    src, tgt, rel = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    wm_before_delete = await GraphIndexWatermark(db_session).relational_watermark()
    assert wm_before_delete is not None
    await GraphIndexWatermark(db_session).record_age_coverage(wm_before_delete)

    await db_session.delete(rel)  # 关系型真源删除（AGE 侧从未得知）
    await db_session.flush()

    retriever = _retriever(db_session)
    age_mock = AsyncMock()
    age_mock.execute_cypher.return_value = [_age_row(src, tgt)]  # AGE 旧数据仍在
    retriever.age_client = age_mock

    results, relationships = await retriever.graph_search(["Alpha"])

    age_mock.execute_cypher.assert_not_awaited()  # stale：AGE 根本不作答
    assert results == []
    assert relationships == []
    gi = retriever.last_graph_index
    assert gi["state"] == STATE_STALE
    assert gi["fallback_reason"] == "watermark_mismatch"
    assert gi["age_watermark"] == wm_before_delete
    assert gi["relational_watermark"] != wm_before_delete


@pytest.mark.asyncio
async def test_soft_deleted_node_dropped_by_fresh_guard(db_session, no_redis):
    """验收2 纵深：水位窗口内的软删（读门判定时点尚未落水位的并发删除），
    fresh 面存在性/软删守卫兜住——已删节点不复活。"""
    src, tgt, _ = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    wm = await GraphIndexWatermark(db_session).relational_watermark()

    tgt.deleted_at = datetime.now(UTC).replace(tzinfo=None)  # 并发软删（未推进覆盖水位）
    await db_session.flush()

    retriever = _retriever(db_session)
    age_mock = AsyncMock()
    age_mock.execute_cypher.return_value = [_age_row(src, tgt)]
    retriever.age_client = age_mock

    frozen = GraphIndexState(
        state=STATE_FRESH,
        relational_watermark=wm,
        age_watermark=wm,
        reason="index_covered",
    )
    with (
        patch.object(retriever, "_resolve_graph_index_state", AsyncMock(return_value=frozen)),
        patch.object(retriever, "_relational_watermark", AsyncMock(return_value=wm)),
    ):
        results, relationships = await retriever.graph_search(["Alpha"])

    age_mock.execute_cypher.assert_awaited_once()  # fresh 面确实询问了 AGE
    assert results == []
    assert relationships == []
    assert retriever.last_graph_index["stale_guard_dropped"] == 1


@pytest.mark.asyncio
async def test_age_outage_in_fresh_mode_falls_back_explicitly(db_session, no_redis):
    """AGE 故障降级正例：fresh 面 AGE 全挂 → 关系型补答真实行，AGE 失败原文
    保留在 metadata（降级可观测，不静默空结果）。"""
    src, tgt, _ = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    wm = await GraphIndexWatermark(db_session).relational_watermark()

    retriever = _retriever(db_session)
    age_client = SimpleNamespace(execute_cypher=AsyncMock(side_effect=RuntimeError("AGE connection refused")))
    retriever.age_client = age_client

    frozen = GraphIndexState(state=STATE_FRESH, relational_watermark=wm, age_watermark=wm, reason="index_covered")
    with (
        patch.object(retriever, "_resolve_graph_index_state", AsyncMock(return_value=frozen)),
        patch.object(retriever, "_relational_watermark", AsyncMock(return_value=wm)),
    ):
        results, relationships = await retriever.graph_search(["Alpha"])

    assert len(results) == 1
    assert results[0]["name"] == tgt.name
    assert results[0]["source"] == "graph_relational"
    assert relationships[0]["to_id"] == str(tgt.id)
    assert age_client.execute_cypher.await_count == 1
    gi = retriever.last_graph_index
    assert gi["age_errors"] == ["Alpha: RuntimeError: AGE connection refused"]
    assert gi["relational_filled_entities"] == ["Alpha"]
    assert gi["mode"] == "age"  # fresh 面整体未降级，仅失败实体补答


@pytest.mark.asyncio
async def test_resolution_failure_degrades_without_silent_success(db_session, no_redis):
    """反：解析链路失败（无 db）→ unknown 显式降级；关系型也不可用时结果为空
    但失败原文保留（不是无信号的假空）。"""
    retriever = _retriever(None)
    age_mock = AsyncMock()
    retriever.age_client = age_mock

    results, relationships = await retriever.graph_search(["Alpha"])

    age_mock.execute_cypher.assert_not_awaited()
    assert results == []
    assert relationships == []
    gi = retriever.last_graph_index
    assert gi["state"] == STATE_UNKNOWN
    assert gi["fallback_reason"] == "resolution_failed"
    assert gi["relational_errors"] == ["no db session on knowledge_service"]


@pytest.mark.asyncio
async def test_gate_disabled_restores_legacy_age_path(db_session, no_redis):
    """回滚开关：关门 → 旧 AGE-always 路径（不做时效判定），metadata 标注。"""
    src, tgt, _ = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")

    retriever = _retriever(db_session)
    age_mock = AsyncMock()
    age_mock.execute_cypher.return_value = [_age_row(src, tgt)]
    retriever.age_client = age_mock

    with patch.object(settings, "GRAPH_INDEX_WATERMARK_GATE_ENABLED", False):
        results, _ = await retriever.graph_search(["Alpha"])

    age_mock.execute_cypher.assert_awaited_once()
    assert results[0]["source"] == "graph"
    assert retriever.last_graph_index == {
        "state": "gate_disabled",
        "mode": "age",
        "reason": "gate_disabled",
    }


@pytest.mark.asyncio
async def test_relational_one_hop_is_soft_delete_safe(db_session, no_redis):
    """关系型主真源作答面的软删安全：软删节点/关系不再出现在一跳邻接里。"""
    src, tgt, rel = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta")
    assert len(await relational_one_hop(db_session, "Alpha", min_strength=_MIN_STRENGTH)) == 1

    tgt.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await db_session.flush()
    assert await relational_one_hop(db_session, "Alpha", min_strength=_MIN_STRENGTH) == []

    tgt.deleted_at = None
    rel.deleted_at = datetime.now(UTC).replace(tzinfo=None)  # 关系行软删同样过滤
    await db_session.flush()
    assert await relational_one_hop(db_session, "Alpha", min_strength=_MIN_STRENGTH) == []


# ---------------------------------------------------------------------------
# worker 覆盖水位推进（保守规则：零积压才推进）
# ---------------------------------------------------------------------------


def _worker(redis_stub) -> GraphSyncWorker:
    worker = GraphSyncWorker.__new__(GraphSyncWorker)  # 既有判例：跳过 __init__ 的连接面
    worker.redis = redis_stub
    worker.age_client = SimpleNamespace(add_vertex=AsyncMock(return_value="v1"))
    worker.stream_key = "stream:graph_sync"
    worker.group_name = "graph_sync_group"
    return worker


def _node_created_msg(watermark: str) -> dict:
    return {
        "type": b"node_created",
        "data": json.dumps(
            {
                "id": str(uuid.uuid4()),
                "name": "N",
                "description": "",
                "sector": "VOID",
                "importance": 1,
                "keywords": "",
                "source_type": "seed",
            }
        ).encode(),
        "watermark": watermark.encode(),
    }


@pytest.mark.asyncio
async def test_worker_returns_and_records_watermark_when_no_backlog(no_redis):
    redis_stub = SimpleNamespace(
        xack=AsyncMock(return_value=1),
        xpending=AsyncMock(return_value={"pending": 0}),
    )
    worker = _worker(redis_stub)
    covered = await worker._process_message(b"1-1", _node_created_msg("gtsms:7:n1:r1"))
    assert covered == "gtsms:7:n1:r1"

    await worker._advance_age_watermark(covered)
    record = await cache_service.get("graph:index:age_watermark")
    assert record == {"covered": "gtsms:7:n1:r1", "synced_at": record["synced_at"]}


@pytest.mark.asyncio
async def test_worker_holds_watermark_while_backlog(no_redis):
    """反：流内仍有积压 → 不推进（保守不越权声称覆盖未处理消息）。"""
    redis_stub = SimpleNamespace(
        xack=AsyncMock(return_value=1),
        xpending=AsyncMock(return_value={"pending": 2}),
    )
    worker = _worker(redis_stub)
    covered = await worker._process_message(b"1-1", _node_created_msg("gtsms:7:n1:r1"))
    assert covered == "gtsms:7:n1:r1"

    await worker._advance_age_watermark(covered)
    assert await cache_service.get("graph:index:age_watermark") is None


@pytest.mark.asyncio
async def test_legacy_message_without_watermark_records_nothing(no_redis):
    """旧格式消息（无 watermark 字段）不推进覆盖——不假称覆盖未知版本。"""
    redis_stub = SimpleNamespace(xack=AsyncMock(return_value=1))
    worker = _worker(redis_stub)
    msg = _node_created_msg("gtsms:7:n1:r1")
    msg.pop("watermark")
    covered = await worker._process_message(b"1-1", msg)
    assert covered is None
    assert await cache_service.get("graph:index:age_watermark") is None


# ---------------------------------------------------------------------------
# 同题双源复算（验收3）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recompute_graph_sources_match(db_session, no_redis):
    """正：同题关系型/AGE 两路可复算，一致 → match=True。"""
    src, tgt, _ = await _make_relation(db_session, src_name="Alpha", tgt_name="Beta", strength=0.9)
    age_client = SimpleNamespace(execute_cypher=AsyncMock(return_value=[_age_row(src, tgt, strength=0.9)]))
    report = await recompute_graph_sources(db_session, age_client, "Alpha", min_strength=_MIN_STRENGTH)

    assert report["relational_error"] is None
    assert report["age_error"] is None
    assert report["match"] is True
    assert len(report["relational"]) == 1
    assert len(report["age"]) == 1
    assert report["relational"][0]["id"] == str(tgt.id)


@pytest.mark.asyncio
async def test_recompute_graph_sources_keeps_age_failure(db_session, no_redis):
    """反：AGE 故障原文保留（age_error 非 None、match=None），关系型侧照常
    给出真实结果——失败保留，不静默、不冒充。"""
    await _make_relation(db_session, src_name="Alpha", tgt_name="Beta", strength=0.9)
    age_client = SimpleNamespace(execute_cypher=AsyncMock(side_effect=RuntimeError("AGE down")))
    report = await recompute_graph_sources(db_session, age_client, "Alpha", min_strength=_MIN_STRENGTH)

    assert report["age"] is None
    assert "RuntimeError: AGE down" in report["age_error"]
    assert report["match"] is None
    assert len(report["relational"]) == 1


@pytest.mark.asyncio
async def test_recompute_graph_sources_keeps_relational_failure(no_redis):
    """反：关系型侧失败同样原文保留（db 为 None），AGE 侧不受牵连。"""
    age_client = SimpleNamespace(execute_cypher=AsyncMock(return_value=[]))
    report = await recompute_graph_sources(None, age_client, "Alpha", min_strength=_MIN_STRENGTH)

    assert report["relational"] is None
    assert report["relational_error"] is not None
    assert report["age"] == []
    assert report["age_error"] is None
    assert report["match"] is None
