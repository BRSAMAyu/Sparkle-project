"""C-03 · 硬过滤接线守卫（变异「去掉过滤」必红；C-02 W 系同型）。

三处接线面，每面两条守卫（行为级优先 + AST 钉住）：

- **W-K1**（galaxy ``retrieval_service._execute_hybrid_search``）：RRF 融合后、
  远程 rerank 模型前的知识权限硬筛。变异：删 ``run_hard_filter_pipeline_async``
  调用（退回「融合候选直送 rerank」）→ 他人 personal chunk 正文出现在 rerank
  入参 → 行为测试红；删调用同时 AST 红。
- **W-K2**（``graph_rag._redis_hybrid_search``）：dense/BM25 候选在 RRF 融合
  与 rerank 前过 ``prefilter_knowledge_candidates``。变异：删两处滤芯调用 →
  他人 chunk 进入 fusion/rerank → 红。
- **W-M**（``context_pack.build`` 的 M-03 接线，本卡守卫不加线）：wrong-user
  memory 候选在 rank 与语义门控（embedding 调用点）前被砍。变异：删三处
  ``prefilter_candidates`` → wrong-user 正文进入 rank 输入与 embedding 调用 → 红。

AST 钉法与 C-02 test_context_source_contract 相同（常量假守卫剪枝——删除与
``if False:`` 禁用两种变异形态都必红）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.graph_rag import GraphRAGRetriever
from app.services.galaxy import retrieval_service as retrieval_service_module

BACKEND = Path(__file__).resolve().parents[2] / "app"

USER_UUID = UUID("11111111-1111-1111-1111-111111111111")


# ---------------------------------------------------------------------------
# AST 钉法（C-02 同型：常量假守卫剪枝，删除/禁用两种变异都必红）
# ---------------------------------------------------------------------------


def _live_call_names(func_node: ast.AST) -> set[str]:
    names: set[str] = set()

    def _is_constant_falsy(test: ast.AST) -> bool:
        return isinstance(test, ast.Constant) and not test.value

    def _visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_constant_falsy(node.test):
            for sub in node.orelse:
                _visit(sub)
            return
        if isinstance(node, ast.While) and _is_constant_falsy(node.test):
            return
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(func_node)
    return names


def _called_names(path: Path, func_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == func_name:
            return _live_call_names(node)
    raise AssertionError(f"function {func_name!r} not found in {path}")


def test_wk1_ast_hybrid_search_wires_hard_filter_pipeline():
    """变异：删 _execute_hybrid_search 的 run_hard_filter_pipeline_async 调用 → 红。"""
    names = _called_names(BACKEND / "services" / "galaxy" / "retrieval_service.py", "_execute_hybrid_search")
    assert "run_hard_filter_pipeline_async" in names  # 管道入口（滤芯在管道内部）


def test_wk2_ast_graphrag_wires_knowledge_prefilter():
    """变异：删 _redis_hybrid_search 的两处 prefilter_knowledge_candidates → 红。"""
    names = _called_names(BACKEND / "orchestration" / "graph_rag.py", "_redis_hybrid_search")
    assert "prefilter_knowledge_candidates" in names


def test_wm_ast_context_pack_build_wires_m03_prefilter():
    """变异：删 context_pack.build 的三处 prefilter_candidates（M-03 接线）→ 红。
    （M-03 拥有该接线；本测试是 C-03 对 memory→语义边界的守卫钉。）"""
    names = _called_names(BACKEND / "core" / "context_pack.py", "build")
    assert "prefilter_candidates" in names


# ---------------------------------------------------------------------------
# W-K1 行为级：galaxy hybrid —— 非法候选绝不进 rerank 模型
# ---------------------------------------------------------------------------


def _redis_doc(doc_id: str, *, source_type: str, user_id: str = "", group_id: str = "", content: str = ""):
    return SimpleNamespace(
        id=doc_id,
        parent_id=f"parent-{doc_id}",
        parent_name=f"{doc_id}.pdf",
        content=content or f"CONTENT-{doc_id}",
        importance=3,
        source_type=source_type,
        user_id=user_id,
        group_id=group_id,
    )


@pytest.mark.asyncio
async def test_wk1_hybrid_search_rerank_receives_only_permitted_candidates(monkeypatch):
    """红条件：融合候选未经滤芯直送 rerank_service.rerank（含他人 personal
    chunk 正文）。真实 `_execute_hybrid_search` 路径（redis/embedding/rerank
    全部 monkeypatch，无真实模型调用）。"""
    own = _redis_doc("c-own", source_type="document_chunk", user_id=str(USER_UUID), content="OWN-DOC-CONTENT")
    foreign_personal = _redis_doc(
        "c-foreign", source_type="document_chunk", user_id="user-2", content="FOREIGN-SECRET-CONTENT"
    )
    group_doc = _redis_doc(
        "c-group", source_type="document_chunk", group_id="g-1", user_id="owner-9", content="GROUP-DOC-CONTENT"
    )
    shared_node = _redis_doc("c-node", source_type="node_description", content="SHARED-NODE-CONTENT")
    # c-node 走 BM25 面（node chunk 常由词法命中），其余走 dense 面
    dense_res = SimpleNamespace(docs=[own, foreign_personal, group_doc])
    bm25_res = SimpleNamespace(docs=[shared_node, foreign_personal])

    async def fake_hybrid_search(**kwargs):
        return dense_res

    async def fake_search(query, params=None):
        return bm25_res

    monkeypatch.setattr(retrieval_service_module.redis_search_client, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(retrieval_service_module.redis_search_client, "search", fake_search)

    async def fake_get_embedding(text, text_type=None):
        return [0.1, 0.2, 0.3, 0.4]

    monkeypatch.setattr(retrieval_service_module.embedding_service, "get_embedding", fake_get_embedding)

    rerank_inputs: list[list] = []

    async def fake_rerank(query, candidates, top_k=5, instruct=None):
        rerank_inputs.append(list(candidates))
        return list(candidates)[:top_k]

    monkeypatch.setattr(retrieval_service_module.rerank_service, "rerank", fake_rerank)

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [])
    service = retrieval_service_module.KnowledgeRetrievalService(db)

    results = await service._execute_hybrid_search(
        user_id_uuid=USER_UUID,
        query_str="calculus limit theorem",
        vector_query=None,
        subject_id=None,
        limit=5,
        threshold=0.4,
        use_reranker=True,
    )

    # rerank 必须被调用，且只见合法候选
    assert rerank_inputs, "rerank stage was never reached"
    rerank_docs = rerank_inputs[0]
    rerank_ids = {getattr(doc, "id", "") for doc in rerank_docs}
    rerank_content = " ".join(str(getattr(doc, "content", "") or "") for doc in rerank_docs)
    assert "c-foreign" not in rerank_ids, "wrong-user personal chunk reached the rerank model"
    assert "c-group" not in rerank_ids, "group chunk without accessible-group context reached the rerank model"
    assert "FOREIGN-SECRET-CONTENT" not in rerank_content, "foreign document content leaked to the rerank model"
    assert {"c-own", "c-node"} <= rerank_ids, "legal candidates (own doc / shared node) must still reach rerank"
    # 装配面无匹配 KnowledgeNode（mock db 空）→ 空结果，但那不影响本守卫
    assert results == []


@pytest.mark.asyncio
async def test_wk1_hybrid_search_reports_rejections_in_pipeline(monkeypatch):
    """滤芯计量接线：非法候选被砍时管道日志携带 reason 计数（结构化可观测）。"""
    from app.services.context_retrieval_pipeline import KnowledgeAccessContext, run_hard_filter_pipeline_async

    foreign = _redis_doc("c-foreign", source_type="document_chunk", user_id="user-2")
    legal = _redis_doc("c-own", source_type="document_chunk", user_id=str(USER_UUID))

    async def rerank(candidates):
        return list(candidates)

    result = await run_hard_filter_pipeline_async(
        knowledge_candidates=[foreign, legal],
        knowledge_ctx=KnowledgeAccessContext(user_id=str(USER_UUID)),
        rerank_fn=rerank,
    )
    knowledge_report = result.report["channels"]["knowledge"]
    assert knowledge_report["input_count"] == 2
    assert knowledge_report["allowed_count"] == 1
    assert knowledge_report["reason_counts"] == {"knowledge:wrong_user": 1}
    assert result.report["rerank"]["input_count"] == 1


# ---------------------------------------------------------------------------
# W-K2 行为级：graph_rag —— 非法候选绝不进 fusion/rerank
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wk2_graphrag_redis_hybrid_filters_before_fusion(monkeypatch):
    import app.orchestration.graph_rag as graph_rag_module

    own = _redis_doc("d-own", source_type="document_chunk", user_id="user-1", content="OWN-CHUNK-CONTENT")
    foreign = _redis_doc("d-foreign", source_type="document_chunk", user_id="user-2", content="FOREIGN-CHUNK-CONTENT")
    unattributed = _redis_doc("d-unattr", source_type="document_chunk", content="UNATTRIBUTED-CONTENT")
    shared_node = _redis_doc("d-node", source_type="node_description", content="NODE-CONTENT")

    dense_res = SimpleNamespace(docs=[own, foreign, unattributed])
    bm25_res = SimpleNamespace(docs=[shared_node, foreign])

    async def fake_hybrid_search(**kwargs):
        return dense_res

    async def fake_search(query, params=None):
        return bm25_res

    monkeypatch.setattr(graph_rag_module.redis_search_client, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(graph_rag_module.redis_search_client, "search", fake_search)

    async def fake_get_embedding(text, text_type=None):
        return [0.1, 0.2]

    monkeypatch.setattr(graph_rag_module.embedding_service, "get_embedding", fake_get_embedding)

    retriever = GraphRAGRetriever(AsyncMock())
    rerank_spy = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever, "_rerank_hybrid_results", rerank_spy)

    await retriever._redis_hybrid_search("linear algebra", top_k=5, user_id="user-1", allowed_group_ids=set())

    assert rerank_spy.await_count == 1
    # _rerank_hybrid_results(query, fused, top_k) —— fused 是第 2 个位置参数
    fused = rerank_spy.call_args[0][1]
    fused_ids = {entry["id"] for entry in fused}
    fused_text = " ".join(str(entry.get("description") or "") for entry in fused)
    assert "d-foreign" not in fused_ids, "wrong-user chunk reached fusion/rerank"
    assert "d-unattr" not in fused_ids, "unattributed chunk reached fusion/rerank (fail-open regression)"
    assert "FOREIGN-CHUNK-CONTENT" not in fused_text
    assert "d-own" in fused_ids and "d-node" in fused_ids, "legal chunks must survive"


# ---------------------------------------------------------------------------
# W-M 行为级：context_pack —— wrong-user 绝不进 rank / embedding（语义门控调用点）
# ---------------------------------------------------------------------------


async def _create_user(db_session):
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"u_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="t",
        )
    )
    await db_session.commit()
    return user_id


def _episodic_row(user_id, summary):
    from datetime import timedelta

    from app.core.time_utils import utcnow

    return EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary=summary,
        source_type="chat_turn",
        source_lane="direct_capture",
        subject_type="self",
        occurred_at=utcnow() - timedelta(hours=1),
        importance_score=0.7,
        evidence_refs=[{"type": "user_state", "id": "t"}],
    )


@pytest.mark.asyncio
async def test_wm_context_pack_never_ranks_or_embeds_illegal_memory(db_session, monkeypatch):
    """memory→语义边界守卫：wrong-user / revoked 候选不得进入 rank_items 输入，
    也不得进入语义门控的 embedding 调用（batch_embeddings 入参文本）。
    变异：删 context_pack.build 的 prefilter 接线 → 两处 spy 同时抓到非法正文 → 红。"""
    import app.core.context_pack as context_pack_module
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    from app.core.time_utils import utcnow

    wrong_user_row = _episodic_row(uuid4(), "WRONG-USER-EVENT")
    revoked_row = _episodic_row(user_id, "REVOKED-EVENT")
    revoked_row.revoked_at = utcnow()
    legal_row = _episodic_row(user_id, "LEGAL-EVENT")

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [wrong_user_row, revoked_row, legal_row]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)

    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PERSONALIZED_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUSING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SEMANTIC_GATING", True, raising=False)

    rank_inputs: list[list] = []
    original_rank = context_pack_module.rank_items

    def spy_rank(items, kind, **kwargs):
        rank_inputs.append(list(items))
        return original_rank(items, kind, **kwargs)

    monkeypatch.setattr(context_pack_module, "rank_items", spy_rank)

    embedding_inputs: list[list[str]] = []

    async def spy_batch_embeddings(texts, text_type=None, **kwargs):
        embedding_inputs.append([str(text) for text in texts])
        return [[0.1] * 8 for _ in texts]

    monkeypatch.setattr(context_pack_module.embedding_service, "batch_embeddings", spy_batch_embeddings)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="LEGAL-EVENT topic")

    ranked_summaries = [getattr(item, "summary", "") for items in rank_inputs for item in items]
    assert "WRONG-USER-EVENT" not in ranked_summaries, "wrong-user row reached ranking (prefilter removed?)"
    assert "REVOKED-EVENT" not in ranked_summaries, "revoked row reached ranking (prefilter removed?)"
    assert "LEGAL-EVENT" in ranked_summaries

    embedded_text = " ".join(" ".join(texts) for texts in embedding_inputs)
    assert embedding_inputs, "semantic gating never invoked the embedding service (test setup drift?)"
    assert "WRONG-USER-EVENT" not in embedded_text, "wrong-user row reached the embedding model call"
    assert "REVOKED-EVENT" not in embedded_text, "revoked row reached the embedding model call"
    assert "LEGAL-EVENT" in embedded_text

    pack_summaries = [m["summary"] for m in pack.episodic_memories]
    assert "WRONG-USER-EVENT" not in pack_summaries
    assert "LEGAL-EVENT" in pack_summaries
