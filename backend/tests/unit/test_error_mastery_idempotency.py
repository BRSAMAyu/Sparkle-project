"""ERR-IDEM · 错题 re-analyze 重复扣分幂等化 —— 幂等门行为测试.

背景：用户对同一道错题再次触发分析（POST /errors/{id}/analyze →
analyze_and_link → ErrorBookMasterySyncService.apply_error_diagnosis）时，
error_diagnosis 负反馈会被再次应用 —— 同一错题把星图节点掌握度扣两次。
北极星「期末一周」场景里反复查看错题是正常行为，重复罚分直接损害
「星图诚实反映掌握度」。

本文件锁定幂等语义（吸收侧，键 = mastery_audit_log.request_id，天然键 +
诊断内容指纹）：

1. 同一错题（内容未变）重复分析 → 只扣一次（第二条 error_diagnosis 被跳过，
   不写 StudyRecord、不发 node_mastery_updated）；
2. 同一错题同一表现的重复复盘 → 只升一次（不同表现仍然各自生效，SM-2 的
   error_review:remembered 与 :fuzzy 是不同的逻辑证据）；
3. 内容变了（用户改了题目/答案/图片）→ 指纹变化 → 允许产生新的诊断扣分
   （新证据），并重置该错题的复盘回升额度（新代际）；
4. 新加入关联的节点按新键生效（部分去重，不影响其他节点）；
5. 幂等门不可读（表缺失/查询异常）→ fail-open 保持既有行为（宁可放行，
   不因门故障静默吞掉全部掌握度同步）。

harness 说明：内存 sqlite + 真实 ORM 模型；GalaxyService 写入桥按其真实
契约 stub —— 更新 UserNodeStatus 并向 mastery_audit_log 追加一行带
request_id 的审计行（galaxy_service.update_node_mastery 第 B 步同款）。
mastery_audit_log 无 ORM 模型（迁移 c8e4f2a3b1d5 裸表），这里用同构 DDL。
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.user import User
from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 与迁移 c8e4f2a3b1d5 同构的 sqlite 版 DDL（mastery_audit_log 无 ORM 模型）
MASTERY_AUDIT_LOG_DDL = """
CREATE TABLE mastery_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    old_mastery INTEGER NOT NULL,
    new_mastery INTEGER NOT NULL,
    reason VARCHAR(100) NOT NULL,
    request_id VARCHAR(100),
    revision INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Fixtures / harness
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(MASTERY_AUDIT_LOG_DDL))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession) -> User:
    user = User(
        username="err_idem_user",
        email="err-idem@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_node(
    db_session: AsyncSession,
    user: User,
    *,
    name: str = "Node",
    mastery_score: float = 50.0,
) -> tuple[KnowledgeNode, UserNodeStatus]:
    node = KnowledgeNode(name=name, description=f"Description for {name}")
    db_session.add(node)
    await db_session.flush()

    status = UserNodeStatus(
        user_id=user.id,
        node_id=node.id,
        mastery_score=mastery_score,
        bkt_mastery_prob=mastery_score / 100.0,
        is_unlocked=True,
        study_count=0,
        total_minutes=0,
        total_study_minutes=0,
        revision=0,
    )
    db_session.add(status)
    await db_session.commit()
    await db_session.refresh(node)
    await db_session.refresh(status)
    return node, status


def _make_error(
    db_session: AsyncSession,
    user: User,
    linked_node_ids: list,
    *,
    error_type: str = "concept_confusion",
    question_text: str = "What is the derivative of sin(x)?",
    user_answer: str = "cos(x^2)",
    correct_answer: str = "cos(x)",
    question_image_url: str | None = None,
) -> ErrorRecord:
    error = ErrorRecord(
        user_id=user.id,
        subject_code="math",
        question_text=question_text,
        question_image_url=question_image_url,
        user_answer=user_answer,
        correct_answer=correct_answer,
        linked_knowledge_node_ids=[str(nid) for nid in linked_node_ids],
        latest_analysis={"error_type": error_type},
        mastery_level=0.3,
        review_count=0,
    )
    db_session.add(error)
    return error


async def _build_service(db_session: AsyncSession, statuses: dict):
    """ErrorBookMasterySyncService with a contract-faithful Galaxy write stub.

    The stub mirrors GalaxyService.update_node_mastery's observable contract:
    mutate UserNodeStatus (mastery/revision/unlock) AND append one
    mastery_audit_log row carrying the passed request_id (its step B).

    linked_knowledge_node_ids 存的是字符串，service 传来的 node_id 可能是
    str 或 UUID —— 索引两种键型（与真实身份映射行为一致）。
    """
    with patch("app.services.error_book_mastery_sync_service.GalaxyStatsService") as MockStatsCls:
        mock_stats = MagicMock()
        mock_stats._calculate_next_review = MagicMock(
            return_value=datetime.now(UTC) + timedelta(days=3)
        )
        MockStatsCls.return_value = mock_stats
        service = ErrorBookMasterySyncService(db_session)

    by_any_id = {}
    for key, value in statuses.items():
        by_any_id[key] = value
        by_any_id[str(key)] = value

    async def _mock_write(
        *, user_id, node_id, new_mastery, reason, request_id, revision
    ):
        status = by_any_id.get(node_id) or by_any_id.get(str(node_id))
        old_mastery = float(status.mastery_score) if status is not None else 0.0
        if status is not None:
            status.mastery_score = float(new_mastery)
            status.bkt_mastery_prob = round(float(new_mastery) / 100.0, 2)
            status.revision = (status.revision or 0) + 1
            status.updated_at = datetime.now(UTC)
            if not status.is_unlocked and float(new_mastery) > 0:
                status.is_unlocked = True
                status.first_unlock_at = datetime.now(UTC)
        if request_id:
            from sqlalchemy import String as sa_String
            from sqlalchemy import bindparam

            from app.models.base import GUID

            stmt = text(
                "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
                "VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision)"
            ).bindparams(
                bindparam("node_id", type_=GUID),
                bindparam("user_id", type_=GUID),
                bindparam("reason", type_=sa_String),
                bindparam("request_id", type_=sa_String),
            )
            await db_session.execute(
                stmt,
                {
                    "node_id": node_id,
                    "user_id": user_id,
                    "old_mastery": int(old_mastery),
                    "new_mastery": int(round(float(new_mastery))),
                    "reason": reason,
                    "request_id": request_id,
                    "revision": (status.revision if status is not None else 1) or 1,
                },
            )
        return {"success": True, "old_mastery": old_mastery, "new_mastery": float(new_mastery)}

    service._write_node_mastery_via_galaxy = _mock_write

    service._evaluate_impacted_plans = AsyncMock()
    service._count_recent_errors_for_node = AsyncMock(return_value=0)
    service._find_impacted_active_plans = AsyncMock(return_value=set())
    return service


async def _study_records(db_session: AsyncSession, user: User, node: KnowledgeNode, record_type: str) -> list:
    result = await db_session.execute(
        select(StudyRecord).where(
            StudyRecord.user_id == user.id,
            StudyRecord.node_id == node.id,
            StudyRecord.record_type == record_type,
        )
    )
    return list(result.scalars().all())


# ===========================================================================
# 1. 同一错题重复分析 → 只扣一次（红证：基线上会扣两次）
# ===========================================================================


@pytest.mark.asyncio
async def test_reanalysis_of_same_error_deducts_only_once(db_session, seeded_user):
    node, status = await _seed_node(db_session, seeded_user, mastery_score=50.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    first = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(first) == 1
    assert first[0]["delta"] == -8
    await db_session.refresh(status)
    assert status.mastery_score == 42.0

    # 用户再次触发分析（内容未变）——POST /errors/{id}/analyze 再走一次
    second = await service.apply_error_diagnosis(seeded_user.id, error)
    assert second == [], "同一错题内容未变的重复分析不得再次扣分"
    await db_session.refresh(status)
    assert status.mastery_score == 42.0, "掌握度只能被同一错题扣一次"

    # 负反馈证据（StudyRecord.error_diagnosis）也只有一条
    records = await _study_records(db_session, seeded_user, node, "error_diagnosis")
    assert len(records) == 1


# ===========================================================================
# 2. 同一错题同一表现的重复复盘 → 只升一次（红证：基线上升两次）
# ===========================================================================


@pytest.mark.asyncio
async def test_repeated_review_same_performance_recovers_only_once(db_session, seeded_user):
    node, status = await _seed_node(db_session, seeded_user, mastery_score=42.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    first = await service.apply_review_feedback(seeded_user.id, error, "remembered")
    assert len(first) == 1
    assert first[0]["delta"] == 4
    await db_session.refresh(status)
    assert status.mastery_score == 46.0

    # 同一表现重复提交（双击/重试）——回升同样只生效一次
    second = await service.apply_review_feedback(seeded_user.id, error, "remembered")
    assert second == [], "同一错题同一表现的重复复盘不得再次回升"
    await db_session.refresh(status)
    assert status.mastery_score == 46.0

    records = await _study_records(db_session, seeded_user, node, "error_review")
    assert len(records) == 1


@pytest.mark.asyncio
async def test_review_with_different_performance_still_applies(db_session, seeded_user):
    """不同表现是不同的逻辑证据：remembered 之后 fuzzy 仍允许各自生效一次。"""
    node, status = await _seed_node(db_session, seeded_user, mastery_score=42.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    await service.apply_review_feedback(seeded_user.id, error, "remembered")
    second = await service.apply_review_feedback(seeded_user.id, error, "fuzzy")

    assert len(second) == 1
    assert second[0]["delta"] == 1
    await db_session.refresh(status)
    assert status.mastery_score == 47.0


# ===========================================================================
# 3. 内容变了 → 新指纹 → 允许新的诊断扣分（设计语义：新证据）
# ===========================================================================


@pytest.mark.asyncio
async def test_content_change_reopens_diagnosis(db_session, seeded_user):
    node, status = await _seed_node(db_session, seeded_user, mastery_score=50.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    first = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(first) == 1
    await db_session.refresh(status)
    assert status.mastery_score == 42.0

    # 内容未变的重分析 → 跳过
    dup = await service.apply_error_diagnosis(seeded_user.id, error)
    assert dup == []
    await db_session.refresh(status)
    assert status.mastery_score == 42.0

    # 用户修改了答案 → 内容指纹变化 → 作为新证据再次扣分
    error.user_answer = "sin(x) + 1"
    second = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(second) == 1
    assert second[0]["delta"] == -8
    await db_session.refresh(status)
    assert status.mastery_score == 34.0

    records = await _study_records(db_session, seeded_user, node, "error_diagnosis")
    assert len(records) == 2


@pytest.mark.asyncio
async def test_content_change_reopens_review_recovery(db_session, seeded_user):
    """内容变化开启新代际：旧内容复盘额度已用完，新内容可再次回升。"""
    node, status = await _seed_node(db_session, seeded_user, mastery_score=42.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    await service.apply_review_feedback(seeded_user.id, error, "remembered")
    dup = await service.apply_review_feedback(seeded_user.id, error, "remembered")
    assert dup == []
    await db_session.refresh(status)
    assert status.mastery_score == 46.0

    error.question_text = "What is the derivative of cos(x)?"
    reopened = await service.apply_review_feedback(seeded_user.id, error, "remembered")
    assert len(reopened) == 1
    assert reopened[0]["delta"] == 4
    await db_session.refresh(status)
    assert status.mastery_score == 50.0


# ===========================================================================
# 4. 部分去重：新加入关联的节点按新键生效
# ===========================================================================


@pytest.mark.asyncio
async def test_newly_linked_node_still_receives_diagnosis(db_session, seeded_user):
    node_a, status_a = await _seed_node(db_session, seeded_user, name="NodeA", mastery_score=50.0)
    service = await _build_service(db_session, {node_a.id: status_a})

    error = _make_error(db_session, seeded_user, [node_a.id])
    await db_session.commit()

    first = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(first) == 1
    await db_session.refresh(status_a)
    assert status_a.mastery_score == 42.0

    # 重分析关联到两个节点：A 已扣过（跳过），B 是新证据（生效）
    node_b, status_b = await _seed_node(db_session, seeded_user, name="NodeB", mastery_score=60.0)
    service = await _build_service(db_session, {node_a.id: status_a, node_b.id: status_b})
    error.linked_knowledge_node_ids = [str(node_a.id), str(node_b.id)]

    second = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(second) == 1, "已扣过的节点应被去重，结果里只出现新节点"
    assert second[0]["node_id"] == str(node_b.id)
    # B 在关联列表 rank 1 → 权重 0.6 → -8*0.6 取整 -5（rank 衰减与幂等正交）
    assert second[0]["delta"] == -5
    await db_session.refresh(status_a)
    await db_session.refresh(status_b)
    assert status_a.mastery_score == 42.0, "旧节点不被二次扣分"
    assert status_b.mastery_score == 55.0, "新关联的节点按新键生效"


# ===========================================================================
# 5. 幂等门不可读 → fail-open（不吞掉合法同步）
# ===========================================================================


@pytest.mark.asyncio
async def test_gate_unreadable_fails_open(db_session, seeded_user):
    node, status = await _seed_node(db_session, seeded_user, mastery_score=50.0)
    service = await _build_service(db_session, {node.id: status})

    error = _make_error(db_session, seeded_user, [node.id])
    await db_session.commit()

    original_execute = service.db.execute

    async def _gate_broken_execute(statement, parameters=None, **kwargs):
        sql_text = str(statement)
        # 仅让幂等门的 SELECT 失败（INSERT 审计行与 ORM 查询照常）
        if "mastery_audit_log" in sql_text and sql_text.lstrip().upper().startswith("SELECT"):
            raise RuntimeError("audit gate unreadable")
        if parameters is None:
            return await original_execute(statement, **kwargs)
        return await original_execute(statement, parameters, **kwargs)

    service.db.execute = _gate_broken_execute
    try:
        results = await service.apply_error_diagnosis(seeded_user.id, error)
    finally:
        service.db.execute = original_execute

    assert len(results) == 1, "幂等门故障必须 fail-open，不得静默吞掉合法的掌握度同步"
    assert results[0]["delta"] == -8


# ===========================================================================
# 6. 幂等键构造（纯函数面）：列宽 VARCHAR(100) 约束
# ===========================================================================


def test_idempotency_request_keys_fit_column_width():
    """compact 键（uuid 去连字符 + 8 位指纹）必须 ≤ request_id VARCHAR(100)。"""
    from app.services.error_book_mastery_sync_service import (
        diagnosis_request_key,
        diagnostic_content_fingerprint,
        review_request_key,
    )

    error_id = uuid4()
    node_id = uuid4()

    class _Err:
        id = error_id
        question_text = "q" * 500
        question_image_url = None
        user_answer = "a" * 500
        correct_answer = "c" * 500

    fingerprint = diagnostic_content_fingerprint(_Err())
    assert len(fingerprint) == 8

    d_key = diagnosis_request_key(error_id, fingerprint, node_id)
    r_key = review_request_key(error_id, fingerprint, "remembered", node_id)
    assert len(d_key) <= 100, f"diagnosis key too long: {len(d_key)}"
    assert len(r_key) <= 100, f"review key too long: {len(r_key)}"

    # 确定性：同输入同键（幂等的前提）
    assert diagnosis_request_key(error_id, fingerprint, node_id) == d_key
    assert review_request_key(error_id, fingerprint, "remembered", node_id) == r_key
    # 不同表现/内容 → 不同键
    assert review_request_key(error_id, fingerprint, "fuzzy", node_id) != r_key
    assert diagnosis_request_key(error_id, fingerprint + "ff", node_id) != d_key
