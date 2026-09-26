"""G-05（wt395）词法搜索面回归：keyword_search 必须在 asyncpg 生产驱动上可执行。

缺陷背景：``keyword_search`` 的 ``jsonb_path_exists(keywords, <path-str>)`` 把
jsonpath 串按 varchar 绑定——asyncpg 预备语句按**类型化参数**发送，PG 找不到
``jsonb_path_exists(jsonb, varchar)`` 签名 → ``UndefinedFunctionError``。词法搜索
（语义搜索的降级回退面、auto_classify 回退、任务-节点挂靠）在生产驱动上必炸；
psql/psycopg 因未知类型字面量隐式转 jsonpath 而掩盖了该缺陷。

修复：路径串显式 ``cast(..., jsonpath)``（retrieval_service._JSONPATH）。

环境定界：本测试需要真实 PostgreSQL（缺陷本体是 asyncpg 驱动的参数类型行为，
sqlite 无 JSONB 算子不可替代）。判据顺序同 tests/_dbguard.py 纪律：
演示库 skip > 方言 skip > 探活 skip。
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import make_url

from app.config import settings
from app.models.galaxy import KnowledgeNode
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from tests import _dbguard

pytestmark = [pytest.mark.asyncio, pytest.mark.postgres]

_DATABASE_URL = settings.DATABASE_URL or ""
if _dbguard.is_demo_db_url(_DATABASE_URL):
    pytest.skip(
        "TEST-DBGUARD: 演示库隔离 " + _dbguard.demo_guard_message(_DATABASE_URL, "test_g05_keyword_jsonpath (module)"),
        allow_module_level=True,
    )
try:
    _backend = make_url(_DATABASE_URL).get_backend_name() if _DATABASE_URL else ""
except Exception:
    _backend = ""
if _backend != "postgresql":
    pytest.skip(
        "本测试钉的是 asyncpg 生产驱动的 jsonpath 参数类型行为, SQLite 不可替代"
        f"（当前 DATABASE_URL 后端={_backend or '未配置/不可解析'}）。",
        allow_module_level=True,
    )


@pytest.fixture()
async def seeded_node():
    """真实 PG 行: keywords 命中词法面; 用临时 user 关联 UserNodeStatus 满足租户面。

    引擎为本用例私有（NullPool）：全局 ``AsyncSessionLocal`` 的 asyncpg 连接池
    绑定在首个使用者的 event loop 上，pytest-asyncio 每用例新建 loop 时复用
    旧池连接会抛 ``Future attached to a different loop``（CI run 36210706955
    实锤）。本用例钉的是 asyncpg 驱动的参数类型行为，私有引擎不改变该契约。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.db.url import to_async_database_url

    engine = create_async_engine(
        to_async_database_url(_DATABASE_URL),
        poolclass=NullPool,
    )
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models.galaxy import UserNodeStatus
    from app.models.user import User

    marker = uuid4().hex[:8]
    probe_keyword = f"kwprobe-{marker}"
    try:
        async with sessionmaker() as session:
            user = User(id=uuid4(), username=f"g05kw_{marker}", email=f"g05kw_{marker}@t.local", hashed_password="x")
            session.add(user)
            await session.flush()
            node = KnowledgeNode(
                id=uuid4(),
                name=f"TCP 拥塞控制 {marker}",
                description="拥塞控制窗口调整",
                keywords=["tcp", "拥塞控制", probe_keyword],
                importance_level=3,
                is_seed=False,
                source_type="user_created",
                status="published",
            )
            session.add(node)
            await session.flush()
            session.add(UserNodeStatus(user_id=user.id, node_id=node.id, mastery_score=50, is_unlocked=True))
            await session.commit()
            yield str(user.id), node.name.lower(), sessionmaker, probe_keyword
            # teardown
            from sqlalchemy import delete as sa_delete

            await session.execute(sa_delete(UserNodeStatus).where(UserNodeStatus.user_id == user.id))
            await session.execute(sa_delete(KnowledgeNode).where(KnowledgeNode.id == node.id))
            await session.execute(sa_delete(User).where(User.id == user.id))
            await session.commit()
    finally:
        await engine.dispose()


async def test_keyword_search_executes_on_asyncpg_and_matches_keywords(seeded_node):
    user_id_str, _name, sessionmaker, probe_keyword = seeded_node
    async with sessionmaker() as session:
        svc = KnowledgeRetrievalService(session)
        # 修复点直证: jsonb_path_exists 分支在 asyncpg 上不再 UndefinedFunctionError。
        # 检索词用种子的唯一探针关键词：galaxy 种子里有同名 "TCP *" 节点
        # （keywords=[]），按 "tcp" 检索会非确定地被挤出 limit——钉确定性。
        results = await svc.keyword_search(UUID(user_id_str), probe_keyword, limit=10)
        assert isinstance(results, list)
        assert any(probe_keyword in (n.keywords or []) for n in results), [
            (n.id, n.name, n.keywords) for n in results
        ]
