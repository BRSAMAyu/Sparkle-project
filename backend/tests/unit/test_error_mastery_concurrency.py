"""ERR-IDEM-CONCUR · 毫秒窗口并发双扣收口 —— 写侧唯一索引仲裁行为测试.

ERR-IDEM（a4ed7493）的幂等门是读侧先查重：两个并发请求在「彼此都还没写入
审计行」的毫秒窗口内都读到「未吸收」→ 双写双扣（50→42→34）。本卡收口 =
``mastery_audit_log`` 上的唯一部分索引（迁移 erridemconc_20260922，只管辖
``edi:``/``erv:`` 幂等键命名空间）+ 写侧审计 INSERT ``ON CONFLICT DO NOTHING
RETURNING`` → 冲突即整体回滚、以 ``{"success": False, "reason": "duplicate"}``
返回（galaxy_service.update_node_mastery），与读侧门命中同一可观察结局。

harness 与既有 ERR-IDEM 测试基建的关键差异：

- **两个独立 session**（sqlite 文件库、两条连接）模拟两个真实并发请求，
  各自持独立事务——写侧冲突/回滚只波及败者自己的事务，与生产语义一致；
- **真实 GalaxyService.update_node_mastery 写入路径**（不 stub 审计 INSERT），
  冲突检测直接对着真实部分唯一索引仲裁；
- **asyncio.Barrier 把毫秒窗口放大成确定性交错点**：两个协程都通过读侧门
  （_sync_already_applied）之后才放行写入——这正是修复前双扣发生的窗口。

断言全部写成交错无关（谁先落账都行）：恰好一方生效、恰好一行审计、
掌握度只扣/升一次。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.theater_candidate_bundle import TheaterCandidateBundle  # noqa: F401 — create_all FK 解析
from app.models.theater_prediction import TheaterPrediction  # noqa: F401 — create_all FK 解析
from app.models.user import User
from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

TEST_DATABASE_URL = "sqlite+aiosqlite://"

# 与迁移 c8e4f2a3b1d5（建表）+ erridemconc_20260922（唯一部分索引）同构的
# sqlite 版 DDL（mastery_audit_log 无 ORM 模型）。索引谓词与迁移严格一致。
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

IDEM_UNIQUE_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_mastery_audit_log_idem_key
ON mastery_audit_log(user_id, node_id, request_id)
WHERE request_id LIKE 'edi:%' OR request_id LIKE 'erv:%'
"""


# ---------------------------------------------------------------------------
# Fixtures / harness
# ---------------------------------------------------------------------------


class _ConcurrentRig:
    """两个独立 session（两条连接）+ 共享 schema 的并发测试台。"""

    def __init__(self, engine):
        self.engine = engine

    def session_factory(self):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        return async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def rig(tmp_path):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        f"{TEST_DATABASE_URL}//{tmp_path / 'erridem_conc.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(MASTERY_AUDIT_LOG_DDL))
        await conn.execute(text(IDEM_UNIQUE_INDEX_DDL))

    yield _ConcurrentRig(engine)
    await engine.dispose()


async def _seed_node(rig, *, mastery_score: float = 50.0):
    """Seed user/node/status/error via its own session, then commit."""
    factory = rig.session_factory()
    async with factory() as session:
        user = User(username=f"conc_{uuid4().hex[:8]}", email="conc@example.com", hashed_password="x")
        session.add(user)
        node = KnowledgeNode(name="ConcNode", description="d")
        session.add(node)
        await session.flush()
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
        session.add(status)
        error = ErrorRecord(
            user_id=user.id,
            subject_code="math",
            question_text="What is the derivative of sin(x)?",
            user_answer="cos(x^2)",
            correct_answer="cos(x)",
            linked_knowledge_node_ids=[str(node.id)],
            latest_analysis={"error_type": "concept_confusion"},
            mastery_level=0.3,
            review_count=0,
        )
        session.add(error)
        await session.commit()
        return user.id, node.id, error.id


def _build_service(session) -> ErrorBookMasterySyncService:
    """ErrorBookMasterySyncService with real GalaxyService write path.

    GalaxyService.update_node_mastery 在 sqlite 上走非 PG 分支（ORM 更新 +
    审计 INSERT ON CONFLICT DO NOTHING RETURNING + 提交），是本卡的被测
    写入路径，不做 stub。计划压力评估等与幂等正交的副作用按 ERR-IDEM
    基建同款 mock 掉。
    """
    with patch("app.services.error_book_mastery_sync_service.GalaxyStatsService") as MockStatsCls:
        mock_stats = MagicMock()
        mock_stats._calculate_next_review = MagicMock(
            return_value=datetime.now(UTC) + timedelta(days=3)
        )
        MockStatsCls.return_value = mock_stats
        service = ErrorBookMasterySyncService(session)

    service._evaluate_impacted_plans = AsyncMock()
    service._count_recent_errors_for_node = AsyncMock(return_value=0)
    service._find_impacted_active_plans = AsyncMock(return_value=set())
    return service


def _install_gate_barrier(service: ErrorBookMasterySyncService, barrier: asyncio.Barrier) -> None:
    """毫秒窗口放大器：每个协程通过读侧门后在 barrier 处等齐，再同时放行。

    修复前语义下这就是双扣窗口（双方都读到「未吸收」）；修复后写入侧由
    唯一索引仲裁出唯一胜者。
    """
    original_gate = service._sync_already_applied

    async def _gated(user_id, node_id, request_key):
        seen = await original_gate(user_id, node_id, request_key)
        await barrier.wait()
        return seen

    service._sync_already_applied = _gated


async def _audit_rows(rig, user_id, node_id) -> list[tuple]:
    factory = rig.session_factory()
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT request_id, old_mastery, new_mastery FROM mastery_audit_log "
                "WHERE user_id = :u AND node_id = :n ORDER BY id"
            ),
            {"u": str(user_id), "n": str(node_id)},
        )
        return list(result.fetchall())


async def _final_mastery(rig, user_id, node_id) -> float:
    factory = rig.session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserNodeStatus.mastery_score).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id,
            )
        )
        return float(result.scalar_one())


async def _study_record_count(rig, user_id, node_id, record_type: str) -> int:
    factory = rig.session_factory()
    async with factory() as session:
        result = await session.execute(
            select(StudyRecord.id).where(
                StudyRecord.user_id == user_id,
                StudyRecord.node_id == node_id,
                StudyRecord.record_type == record_type,
            )
        )
        return len(list(result.scalars().all()))


# ===========================================================================
# 1. 并发同键诊断（毫秒窗口）→ 恰好一扣（修复前红：50→42→34）
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_same_key_diagnosis_deducts_exactly_once(rig):
    user_id, node_id, error_id = await _seed_node(rig, mastery_score=50.0)

    barrier = asyncio.Barrier(2)
    results = await asyncio.gather(*[
        _run_diagnosis(rig, user_id, error_id, barrier)
        for _ in range(2)
    ])

    node_results = [node for r in results for node in r]  # 生效者非空，败者 == []
    assert len(node_results) == 1, f"并发同键诊断必须恰好生效一次，实际 {len(node_results)} 次"
    assert node_results[0]["delta"] == -8

    mastery = await _final_mastery(rig, user_id, node_id)
    assert mastery == 42.0, f"掌握度只允许被扣一次（50→42），实际 {mastery}"

    rows = await _audit_rows(rig, user_id, node_id)
    assert len(rows) == 1, f"同键审计行必须恰好一行，实际 {len(rows)}: {rows}"
    assert rows[0][0].startswith("edi:")

    assert await _study_record_count(rig, user_id, node_id, "error_diagnosis") == 1


# ===========================================================================
# 2. 并发同键复盘（毫秒窗口）→ 恰好一升
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_same_key_review_recovers_exactly_once(rig):
    user_id, node_id, error_id = await _seed_node(rig, mastery_score=42.0)

    barrier = asyncio.Barrier(2)
    results = await asyncio.gather(*[
        _run_review(rig, user_id, error_id, "remembered", barrier)
        for _ in range(2)
    ])

    node_results = [node for r in results for node in r]
    assert len(node_results) == 1, f"并发同键复盘必须恰好生效一次，实际 {len(node_results)} 次"
    assert node_results[0]["delta"] == 4

    mastery = await _final_mastery(rig, user_id, node_id)
    assert mastery == 46.0, f"掌握度只允许回升一次（42→46），实际 {mastery}"

    rows = await _audit_rows(rig, user_id, node_id)
    assert len(rows) == 1
    assert rows[0][0].startswith("erv:")


# ===========================================================================
# 3. 并发双请求都拿到「读侧门命中」同款结局：败者结果为空
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_loser_gets_read_gate_hit_outcome(rig):
    """写侧冲突败者的返回与读侧门命中完全同形：空结果列表（无 delta 字典）。

    调用方（error_book router → analyze_and_link）对两种去重路径的处理
    因此天然一致，不需要新增分支语义。
    """
    user_id, node_id, error_id = await _seed_node(rig, mastery_score=50.0)

    barrier = asyncio.Barrier(2)
    first, second = await asyncio.gather(*[
        _run_diagnosis(rig, user_id, error_id, barrier)
        for _ in range(2)
    ])

    # 交错无关：恰好一个为空、一个生效
    assert (len(first) == 0) != (len(second) == 0), "恰好一方生效"
    assert (first == [] and len(second) == 1) or (second == [] and len(first) == 1)


# ===========================================================================
# 4. 串行重复（已提交后重放）→ 读侧门快路径仍然生效（保留不回归）
# ===========================================================================


@pytest.mark.asyncio
async def test_sequential_duplicate_still_caught_by_read_gate(rig):
    """写入侧索引上线后，读侧先查重门保持为快路径：串行重放不触达写侧。"""
    user_id, node_id, error_id = await _seed_node(rig, mastery_score=50.0)

    barrier = asyncio.Barrier(1)
    first = await _run_diagnosis(rig, user_id, error_id, barrier)
    assert len(first) == 1
    assert first[0]["delta"] == -8

    # 内容未变的第二次分析（前一次已提交）→ 读侧门直接命中
    second = await _run_diagnosis(rig, user_id, error_id, asyncio.Barrier(1))
    assert second == [], "读侧门快路径必须继续拦截已落账的同键同步"

    mastery = await _final_mastery(rig, user_id, node_id)
    assert mastery == 42.0
    assert len(await _audit_rows(rig, user_id, node_id)) == 1


# ===========================================================================
# helpers: 独立 session 里跑一次完整吸收（模拟一个真实请求）
# ===========================================================================


async def _run_diagnosis(rig, user_id, error_id, barrier) -> list[dict]:
    factory = rig.session_factory()
    async with factory() as session:
        service = _build_service(session)
        _install_gate_barrier(service, barrier)
        result = await session.execute(
            select(ErrorRecord).where(ErrorRecord.id == error_id)
        )
        error_record = result.scalar_one()
        applied = list(await service.apply_error_diagnosis(user_id, error_record))
        # 生产语义：router 在请求边界提交该 session（galaxy_service 内部已
        # 提交过掌握度主写，这里的提交落 StudyRecord 等请求级副作用）
        await session.commit()
        return applied


async def _run_review(rig, user_id, error_id, performance: str, barrier) -> list[dict]:
    factory = rig.session_factory()
    async with factory() as session:
        service = _build_service(session)
        _install_gate_barrier(service, barrier)
        result = await session.execute(
            select(ErrorRecord).where(ErrorRecord.id == error_id)
        )
        error_record = result.scalar_one()
        applied = list(await service.apply_review_feedback(user_id, error_record, performance))
        await session.commit()
        return applied
