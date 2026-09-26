"""V3-FIX-215 回归锁：celery 面向量写入必须经 stamp_embedding_version 打版本标。

E-05 写入侧契约（embedding_service.stamp_embedding_version docstring）：任何
持久化向量的地方（document chunk / knowledge node）都必须打上版本标记，检索侧
才能做版本隔离。galaxy_service._process_node_background 已 stamp（E-05 主链）；
本文件钉死两条 celery 面：

- ``celery_app.generate_embedding`` —— 活跃投递面（celery_app.py 概念分析任务经
  ``dispatch_task_async("generate_embedding", ...)`` 投递，queue=high_priority）；
- ``celery_tasks.generate_node_embedding`` —— 已注册任务名（任务管理/测试管理面
  可达，test_task_manager_integration 按名断言）。

缺口后果：两路径写入的向量 embedding_model=NULL——lenient 过渡过滤
（``or_(== current, IS NULL)``）下跨模型向量可静默入检索池；strict 翻转后又被
整批排除（召回塌缩），两头都坏。删除任一 stamp 调用 → 对应用例红（变异承重）。
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.galaxy import KnowledgeNode
from app.services.embedding_service import embedding_service


def _pin_version(monkeypatch: pytest.MonkeyPatch) -> str:
    """钉住模块级全局实例的版本配置，断言值不随环境漂移（同 test_embedding_fail_closed）。"""
    monkeypatch.setattr(embedding_service, "primary_provider", "dashscope")
    monkeypatch.setattr(embedding_service, "dashscope_model", "text-embedding-v4")
    monkeypatch.setattr(embedding_service, "embedding_dim", 1024)
    return embedding_service.current_embedding_version()


def _fake_get_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(text: str, **_: Any) -> list[float]:
        return [0.1] * 1024

    monkeypatch.setattr(embedding_service, "get_embedding", _fake)


def _install_test_session(monkeypatch: pytest.MonkeyPatch) -> async_sessionmaker[AsyncSession]:
    """celery 任务在函数体内 ``from app.db.session import AsyncSessionLocal``——
    运行期解析模块属性，monkeypatch 该属性即可把任务引到内存库。"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(KnowledgeNode.__table__.create)

    asyncio.run(_create())
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", maker)
    return maker


async def _insert_node(maker: async_sessionmaker[AsyncSession]) -> str:
    async with maker() as session:
        node = KnowledgeNode(name="stamp-contract-node")
        session.add(node)
        await session.commit()
        return str(node.id)


async def _read_stamp(maker: async_sessionmaker[AsyncSession], node_id: str) -> tuple[Any, Any, Any]:
    """embedding 列是 deferred——显式列查询取数，避免 ORM 惰性加载撞 greenlet。"""
    nid = uuid.UUID(node_id)
    async with maker() as session:
        node = await session.get(KnowledgeNode, nid)
        assert node is not None
        model, dim = node.embedding_model, node.embedding_dim
    async with maker() as session:
        vector = (await session.execute(select(KnowledgeNode.embedding).where(KnowledgeNode.id == nid))).scalar_one()
    return model, dim, vector


def test_generate_embedding_task_stamps_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """celery_app.generate_embedding 写向量必须同时落 embedding_model/embedding_dim。"""
    from app.core.celery_app import generate_embedding

    expected = _pin_version(monkeypatch)
    _fake_get_embedding(monkeypatch)
    maker = _install_test_session(monkeypatch)
    node_id = asyncio.run(_insert_node(maker))

    generate_embedding.run(node_id=node_id, text="stamp contract probe", user_id="probe-user")

    model, dim, vector = asyncio.run(_read_stamp(maker, node_id))
    assert vector is not None, "任务应已写入向量（前置：fake get_embedding）"
    assert model == expected, "V3-FIX-215：向量已写入但未 stamp 版本标（embedding_model=NULL）"
    assert dim == 1024


def test_celery_tasks_generate_node_embedding_stamps_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """celery_tasks.generate_node_embedding 同契约（注册名 generate_node_embedding）。"""
    from app.core.celery_tasks import generate_node_embedding

    expected = _pin_version(monkeypatch)
    _fake_get_embedding(monkeypatch)
    maker = _install_test_session(monkeypatch)
    node_id = asyncio.run(_insert_node(maker))

    # 任务写库后跑查重检索——sqlite 无 pgvector，桩掉检索服务（函数体内按名导入）
    class _StubRetrieval:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def semantic_search_nodes(self, *__: Any, **___: Any) -> list[Any]:
            return []

    monkeypatch.setattr("app.services.galaxy.retrieval_service.KnowledgeRetrievalService", _StubRetrieval)

    generate_node_embedding.run(node_id=node_id, title="stamp contract", summary="probe", user_id="probe-user")

    model, dim, vector = asyncio.run(_read_stamp(maker, node_id))
    assert vector is not None, "任务应已写入向量（前置：fake get_embedding）"
    assert model == expected, "V3-FIX-215：向量已写入但未 stamp 版本标（embedding_model=NULL）"
    assert dim == 1024
