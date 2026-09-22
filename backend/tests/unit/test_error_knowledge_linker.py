"""
Unit: ErrorKnowledgeLinker — 错题→知识节点确定性归位（CP-03）。

覆盖：考纲 pack 词典（label 包含 + 章节提示）、科目 scope、星图节点名匹配、
concept_hints（LLM recommended_knowledge 的零 LLM 消费面）、诚实 none、幂等、
MAX_LINKED_NODES 封顶。DB 面用内存 SQLite 走真实 ensure_sprint_node 语义。
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.error_knowledge_linker import (
    MAX_LINKED_NODES,
    ErrorKnowledgeLinker,
    KnowledgeLinkMatch,
)
from app.services.galaxy_service import GalaxyService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class _FakeError:
    """ErrorRecord 的最小鸭子类型（linker 只读 subject_code/chapter/question_text）。"""

    def __init__(self, subject_code=None, chapter=None, question_text=None):
        self.subject_code = subject_code
        self.chapter = chapter
        self.question_text = question_text


# ---------------------------------------------------------------------------
# 纯匹配逻辑（不触 DB）
# ---------------------------------------------------------------------------


def test_pack_label_and_hint_matching_scoped():
    """离散数学 scope：label 包含命中 + 章节提示命中，特异性降序。"""
    linker = ErrorKnowledgeLinker(db=None)
    hits = linker._match_pack_nodes("discrete_mathematics", "欧拉图与哈密顿图的基本判定")
    assert hits, "欧拉图文本必须命中 dm 词典"
    assert hits[0][0] == "dm.euler_hamilton"

    hint_hits = linker._match_pack_nodes("discrete_mathematics", "第三章组合计数与鸽巢原理")
    assert any(ext == "dm.combinatorics" for ext, _detail in hint_hits)


def test_pack_scoping_prevents_cross_subject_leak():
    """科目已知时不得跨科误链：离散数学错题即便提到 Prim 也只落 dm 节点。"""
    linker = ErrorKnowledgeLinker(db=None)
    hits = linker._match_pack_nodes("discrete_mathematics", "用Prim算法求最小生成树")
    ext_ids = [ext for ext, _detail in hits]
    assert ext_ids, "生成树在 dm 词典有归属（dm.trees）"
    assert all(ext.startswith("dm.") for ext in ext_ids), f"跨科泄漏: {ext_ids}"


def test_pack_global_scan_when_subject_unknown():
    """科目未知/other 时全局扫 pack 词典（提示词足够特异，不会泛滥）。"""
    linker = ErrorKnowledgeLinker(db=None)
    hits = linker._match_pack_nodes(None, "TCP三次握手与拥塞控制的过程")
    ext_ids = [ext for ext, _detail in hits]
    assert "cn.tcp_three_way" in ext_ids
    assert "cn.tcp_congestion_control" in ext_ids


def test_pack_no_match_returns_empty():
    linker = ErrorKnowledgeLinker(db=None)
    assert linker._match_pack_nodes("discrete_mathematics", "完全无关的内容xyz") == []


# ---------------------------------------------------------------------------
# DB 面（内存 SQLite：真实 ensure_sprint_node / 节点名扫描）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_via_pack_creates_canonical_sprint_node(db_session):
    """离散数学错题归位到 canonical dm.* 星图节点（缺失才建，确定性 uuid5）。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(
        subject_code="discrete_math",
        chapter="欧拉图与哈密顿图",
        question_text="判断下图是否存在欧拉回路，并说明理由。",
    )

    matches = await linker.link_error(user_id=user_id, error=error)

    assert matches, "确定性归位必须命中"
    expected_id = GalaxyService.sprint_node_uuid("dm.euler_hamilton")
    assert matches[0].node_id == expected_id
    assert matches[0].source == "sprint_pack"

    node = await db_session.get(KnowledgeNode, expected_id)
    assert node is not None, "ensure_sprint_node 应按需创建 canonical 节点"
    assert node.is_seed is True
    assert node.source_type == "sprint_pack"


@pytest.mark.asyncio
async def test_link_is_idempotent_on_relink(db_session):
    """同一错题重复归位 → 同一节点集，不累积不重复（幂等）。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code="discrete_math", chapter="欧拉图", question_text="欧拉回路判定条件")

    first = await linker.link_error(user_id=user_id, error=error)
    second = await linker.link_error(user_id=user_id, error=error)

    assert [m.node_id for m in first] == [m.node_id for m in second]
    ids = [m.node_id for m in second]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_link_via_galaxy_node_name(db_session):
    """错题章节/题目命中用户星图既有节点名（P0-1 同款可见性：种子或已解锁）。"""
    user_id = uuid4()
    node = KnowledgeNode(
        id=uuid4(),
        name="TCP 拥塞控制",
        name_en="TCP Congestion Control",
        is_seed=True,
        source_type="seed",
    )
    db_session.add(node)
    await db_session.commit()

    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code="computer_networks", chapter="传输层", question_text="TCP 拥塞控制的四个算法")

    matches = await linker.link_error(user_id=user_id, error=error)

    node_ids = [m.node_id for m in matches]
    assert node.id in node_ids, "应命中既有星图节点而非新建"
    by_source = {m.source for m in matches if m.node_id == node.id}
    assert "node_name" in by_source


@pytest.mark.asyncio
async def test_link_honest_none_when_no_signal(db_session):
    """匹配不到 → 诚实空列表（不造节点），mastery 同步走既有 no-op+hint 语义。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code="english", chapter="完形填空", question_text="完全无关的文本内容")

    matches = await linker.link_error(user_id=user_id, error=error)
    assert matches == []


@pytest.mark.asyncio
async def test_link_cap_at_three_nodes(db_session):
    """归位结果封顶 MAX_LINKED_NODES=3（与 mastery sync 的 top-3 对齐）。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(
        subject_code="discrete_math",
        chapter="命题逻辑与谓词逻辑、集合及其运算、二元关系",
        question_text="命题逻辑等价式、谓词逻辑量词、集合运算与二元关系综合题",
    )

    matches = await linker.link_error(user_id=user_id, error=error)
    assert len(matches) <= MAX_LINKED_NODES
    assert len({m.node_id for m in matches}) == len(matches)


@pytest.mark.asyncio
async def test_link_with_concept_hints_only(db_session):
    """concept_hints（LLM recommended_knowledge）走零 LLM 字符串匹配。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code="other", chapter=None, question_text=None)

    matches = await linker.link_error(user_id=user_id, error=error, concept_hints=["欧拉图", "哈密顿图"])

    assert matches, "概念提示必须可归位"
    assert all(m.source == "sprint_pack" for m in matches)
    assert GalaxyService.sprint_node_uuid("dm.euler_hamilton") in [m.node_id for m in matches]


@pytest.mark.asyncio
async def test_link_requires_text_signal(db_session):
    """无章节、无题目文本、无概念提示 → 不归位。"""
    user_id = uuid4()
    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code="discrete_math")
    assert await linker.link_error(user_id=user_id, error=error) == []


@pytest.mark.asyncio
async def test_link_match_dataclass_shape():
    """KnowledgeLinkMatch 结构契约（source 词表固定，供日志/观测消费）。"""
    match = KnowledgeLinkMatch(node_id=UUID(int=0), source="sprint_pack", detail="hint:dm.trees")
    assert match.source in {"sprint_pack", "node_name"}
    assert match.detail == "hint:dm.trees"


@pytest.mark.asyncio
async def test_link_galaxy_scan_visible_only(db_session):
    """节点名匹配遵守可见性：他人私有节点（无 UserNodeStatus、非种子）不可见。"""
    owner_id = uuid4()
    stranger_id = uuid4()
    private_node = KnowledgeNode(id=uuid4(), name="欧拉图与哈密顿图专项", is_seed=False, source_type="user")
    db_session.add(private_node)
    await db_session.flush()
    db_session.add(UserNodeStatus(user_id=owner_id, node_id=private_node.id, mastery_score=10))
    await db_session.commit()

    linker = ErrorKnowledgeLinker(db_session)
    error = _FakeError(subject_code=None, chapter=None, question_text="欧拉图与哈密顿图专项练习")

    matches = await linker.link_error(user_id=stranger_id, error=error)
    assert private_node.id not in [m.node_id for m in matches], "他人私有节点必须不可见"
