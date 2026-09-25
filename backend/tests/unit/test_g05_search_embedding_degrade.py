"""G-05（wt395）搜索面降级回归：embedding 供应商故障时节点语义搜索必须显式降级，不炸穿。

缺陷背景：``KnowledgeRetrievalService.semantic_search_ranked_nodes`` 直接
``await embedding_service.get_embedding(...)``——供应商未配置/故障时
``EmbeddingNotConfiguredError`` 上抛，REST POST /galaxy/search 500。
同故障在 document_hybrid_search（E-05）的契约是显式降级：
"向量侧失败（含未配置 key）时降级为纯词法——显式记日志"。

修复口径（与 E-05 对齐）：
- EmbeddingNotConfiguredError（持久态）→ 熔断向量运行时 + 返回空;
- 其他瞬时异常 → 本次降级为空 + error 计数，不烧熔断;
- keyword_search 词法面独立可用。

sqlite 口径：pgvector 判定面被 monkeypatch（sqlite 无 vector 扩展,
须强制 ``_vector_runtime_available=True`` 才能进入被测分支）。
"""

from __future__ import annotations

import pytest

import app.services.galaxy.retrieval_service as rmod
from app.services.embedding_service import EmbeddingNotConfiguredError
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService


class _RaisingEmbedding:
    def __init__(self, exc: Exception):
        self._exc = exc

    def current_embedding_version(self) -> str:
        return "broken/test@0"

    async def get_embedding(self, text: str, text_type: str = "document") -> list[float]:
        raise self._exc


@pytest.fixture()
def vector_runtime_forced(monkeypatch):
    """sqlite 无 pgvector: 强制向量运行时可用, 隔离被测的 embedding 故障分支。"""
    monkeypatch.setattr(rmod, "_PGVECTOR_RUNTIME_ENABLED", True)

    async def available(self):
        return True

    monkeypatch.setattr(KnowledgeRetrievalService, "_vector_runtime_available", available)
    yield
    monkeypatch.setattr(rmod, "_PGVECTOR_RUNTIME_ENABLED", True)


@pytest.mark.asyncio
async def test_embedding_not_configured_degrades_and_blows_fuse(db_session, monkeypatch, vector_runtime_forced):
    monkeypatch.setattr(rmod, "embedding_service", _RaisingEmbedding(EmbeddingNotConfiguredError("供应商未配置")))
    svc = KnowledgeRetrievalService(db_session)

    ranked = await svc.semantic_search_ranked_nodes(query="TCP 拥塞控制", limit=10)

    assert ranked == []
    assert rmod._PGVECTOR_RUNTIME_ENABLED is False, "持久态供应商缺失应烧熔断, 后续调用短路"


@pytest.mark.asyncio
async def test_transient_embedding_failure_degrades_this_call_only(db_session, monkeypatch, vector_runtime_forced):
    monkeypatch.setattr(rmod, "embedding_service", _RaisingEmbedding(RuntimeError("网络抖动")))
    svc = KnowledgeRetrievalService(db_session)

    ranked = await svc.semantic_search_ranked_nodes(query="TCP 拥塞控制", limit=10)

    assert ranked == []
    assert rmod._PGVECTOR_RUNTIME_ENABLED is True, "瞬时故障不得烧熔断（下次调用仍可尝试向量）"

    # 词法回退面（keyword_search）与向量运行时无关——它走 ILIKE/JSONB 词法查询,
    # 在 sqlite 口径下不可执行（JSONB 算子），其真实可用性由 G-05 规模梯度探针
    # 在真实 PG 上断言（v3-output/WT395-G05-GALAXY graceful.keyword_fallback_still_works）。
