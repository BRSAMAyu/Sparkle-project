"""
Integration: 错题录入→确定性知识归位→galaxy mastery 联动 端到端（CP-03 验收）。

闭环（LOOP1 CP-03「mastery 同步半程失败」的反证）：
  录离散数学错题（零 LLM 确定性归位写 linked_knowledge_node_ids）
  → analyze_and_link 诊断扣减星图节点 mastery
  → review 提交（remembered）→ 节点 mastery 回升。

LLM 双车道在测试中显式置断（生产降级路径），归位完全由确定性链完成——
证明 mastery 联动不再依赖 LLM 链路。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unittest.mock import AsyncMock, patch

from app.models.base import Base
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.user import User
from app.schemas.error_book import ErrorRecordCreate, ReviewAction, ReviewPerformanceEnum, SubjectEnum
from app.services.error_book_service import ErrorBookService
from app.services.galaxy_service import GalaxyService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
DM_EULER_NODE_ID = GalaxyService.sprint_node_uuid("dm.euler_hamilton")


def _coerce_ids(values) -> list:
    """读侧表示容错：prod 原生 ARRAY(UUID) 回来是 UUID，sqlite JSON 变体是字符串。"""
    from uuid import UUID

    return [UUID(str(value)) for value in (values or [])]


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user(session_factory):
    async with session_factory() as session:
        user = User(
            username="cp03_link_e2e",
            email="cp03_link_e2e@example.com",
            hashed_password="hashed",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _seed_studied_sprint_node(session_factory, user_id):
    """预置「学过欧拉图」的用户：canonical dm 节点 + mastery 40 的节点状态。

    归位后诊断扣分才会可见（0 mastery 节点按 P1-5 语义不产生负证据行）。
    """
    from app.models.galaxy import KnowledgeNode

    async with session_factory() as session:
        node = await session.get(KnowledgeNode, DM_EULER_NODE_ID)
        if node is None:
            node = KnowledgeNode(
                id=DM_EULER_NODE_ID,
                name="欧拉图与哈密顿图",
                description="Sprint Pack node: dm.euler_hamilton",
                is_seed=True,
                source_type="sprint_pack",
            )
            session.add(node)
        status = UserNodeStatus(
            user_id=user_id,
            node_id=DM_EULER_NODE_ID,
            mastery_score=40,
            is_unlocked=True,
            study_count=3,
            revision=1,
        )
        session.add(status)
        await session.commit()
    return DM_EULER_NODE_ID


@pytest.mark.asyncio
async def test_error_entry_links_and_moves_galaxy_mastery(session_factory, seeded_user):
    """录错题→归位→诊断扣分→review 回升 的完整闭环。"""
    user_id = seeded_user
    await _seed_studied_sprint_node(session_factory, user_id)

    async with session_factory() as db:
        service = ErrorBookService(db)
        error = await service.create_error(
            user_id,
            ErrorRecordCreate(
                question_text="判断下图（G）是否存在欧拉回路，并说明欧拉图成立的充分必要条件。",
                user_answer="存在欧拉回路，因为每个顶点度数都是偶数",  # 故意错的场景表述
                correct_answer="当且仅当连通图所有顶点度数均为偶数时存在欧拉回路",
                subject=SubjectEnum.DISCRETE_MATH,
                chapter="欧拉图与哈密顿图",
            ),
        )
        error_id = error.id

        # LLM 双车道显式置断：归位与分析不依赖 LLM（生产降级路径）；
        # event_bus 同步置断（测试无 Redis，避免发布重试拖慢闭环）
        with (
            patch(
                "app.services.llm.minimax_provider.minimax_provider.analyze",
                side_effect=RuntimeError("minimax lane down (test)"),
            ),
            patch(
                "app.core.llm_client.llm_client.chat_completion",
                side_effect=RuntimeError("primary lane down (test)"),
            ),
            patch(
                "app.core.event_bus.event_bus.publish",
                new=AsyncMock(),
            ),
        ):
            await service.analyze_and_link(error_id, user_id)

        await db.refresh(error)
        # ① 确定性归位写 linked_knowledge_node_ids（LOOP1 断点：此前恒空）
        assert _coerce_ids(error.linked_knowledge_node_ids) == [DM_EULER_NODE_ID]
        assert _coerce_ids([error.affected_node_id]) == [DM_EULER_NODE_ID]
        # 兜底分析面仍 schema-complete（mastery 同步读取 error_type）
        assert (error.latest_analysis or {}).get("error_type")

        # ② galaxy mastery 诊断扣分：40 → 40-10(knowledge_gap)=30
        status = (
            await db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == DM_EULER_NODE_ID
                )
            )
        ).scalar_one()
        mastery_after_diagnosis = int(status.mastery_score)
        assert mastery_after_diagnosis == 30, f"诊断扣分未生效: {mastery_after_diagnosis}"

        diagnosis_records = (
            (
                await db.execute(
                    select(StudyRecord).where(
                        StudyRecord.user_id == user_id,
                        StudyRecord.node_id == DM_EULER_NODE_ID,
                        StudyRecord.record_type == "error_diagnosis",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(diagnosis_records) == 1, "诊断证据行应恰好一条（audit trail）"

    # ③ review（remembered）→ mastery 回升 30 → 34
    async with session_factory() as db:
        service = ErrorBookService(db)
        reviewed = await service.submit_review(
            user_id, error_id, ReviewAction(performance=ReviewPerformanceEnum.REMEMBERED)
        )
        assert reviewed.review_count == 1

        status = (
            await db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == DM_EULER_NODE_ID
                )
            )
        ).scalar_one()
        assert int(status.mastery_score) == 34, f"review 回升未生效: {status.mastery_score}"

        review_records = (
            (
                await db.execute(
                    select(StudyRecord).where(
                        StudyRecord.user_id == user_id,
                        StudyRecord.node_id == DM_EULER_NODE_ID,
                        StudyRecord.record_type == "error_review",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(review_records) == 1


@pytest.mark.asyncio
async def test_error_entry_without_any_link_stays_honest(session_factory, seeded_user):
    """无任何归位信号 → linked_ids 空 + linking_hint（既有诚实 no-op 语义保持）。"""
    user_id = seeded_user

    async with session_factory() as db:
        service = ErrorBookService(db)
        error = await service.create_error(
            user_id,
            ErrorRecordCreate(
                question_text="Please analyze this completely unrelated filler text xyz.",
                subject=SubjectEnum.ENGLISH,
                chapter="完形填空",
            ),
        )
        with (
            patch(
                "app.services.llm.minimax_provider.minimax_provider.analyze",
                side_effect=RuntimeError("minimax lane down (test)"),
            ),
            patch(
                "app.core.llm_client.llm_client.chat_completion",
                side_effect=RuntimeError("primary lane down (test)"),
            ),
            patch(
                "app.core.event_bus.event_bus.publish",
                new=AsyncMock(),
            ),
        ):
            await service.analyze_and_link(error.id, user_id)

        await db.refresh(error)
        assert not error.linked_knowledge_node_ids
        assert (error.latest_analysis or {}).get("linking_hint", {}).get("code") == "missing_knowledge_links"
