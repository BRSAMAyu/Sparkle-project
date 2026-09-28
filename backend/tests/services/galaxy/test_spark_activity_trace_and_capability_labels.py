"""V4-D04 · 纯时长降级为活动痕迹 + 能力标签封顶（真实 DB + 纯 schema 面）.

卡面验收：只学习计时不显示掌握（旧时间增长降为活动痕迹）；
「练习过 vs 独立检验通过」视觉/数据双区分（标签不能叫精通）。
每面一正一反可失败。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.models.galaxy import KnowledgeNode
from app.schemas.galaxy import NodeWithStatus
from app.services.galaxy.mastery_evidence import EvidenceObservation, MasteryEvidenceType
from app.services.galaxy.stats_service import GalaxyStatsService
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS mastery_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    old_mastery INTEGER NOT NULL,
    new_mastery INTEGER NOT NULL,
    reason TEXT,
    request_id TEXT,
    revision INTEGER DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effect_kind TEXT
)
"""
_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS event_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id CHAR(36) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    sequence_number INTEGER NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME
)
"""
_COUNTERS_DDL = """
CREATE TABLE IF NOT EXISTS event_sequence_counters (
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id CHAR(36) NOT NULL,
    next_sequence INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (aggregate_type, aggregate_id)
)
"""


async def _ensure_tables(db_session) -> None:
    for ddl in (_AUDIT_DDL, _OUTBOX_DDL, _COUNTERS_DDL):
        await db_session.execute(text(ddl))
    await db_session.commit()


@pytest_asyncio.fixture()
async def spark_env(db_session):
    await _ensure_tables(db_session)
    user = await _make_user(db_session)
    node = KnowledgeNode(name=f"时长痕迹{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return db_session, user, node


class _FakeStatus:
    """schema 纯计算面的最小 status 载体（对齐 NodeStatus 分支所需字段）。"""

    def __init__(self, *, mastery: float, unlocked: bool = True, collapsed: bool = False):
        self.mastery_score = mastery
        self.is_unlocked = unlocked
        self.is_collapsed = collapsed
        self.total_study_minutes = 120
        self.study_count = 4
        self.is_favorite = False
        self.first_unlock_at = None
        self.last_study_at = None
        self.mastery_last_updated_at = None
        self.next_review_at = None
        self.decay_paused = False
        self.revision = 3


# ---------------------------------------------------------------------------
# 纯时长 = 活动痕迹（零掌握度增长）
# ---------------------------------------------------------------------------


async def test_time_only_spark_leaves_mastery_untouched_but_grows_trace(spark_env):
    """正例：无 outcome 的 spark → 解锁 + 参与计数增长，掌握度分毫不动。"""
    db, user, node = spark_env
    service = GalaxyStatsService(db)

    result = await service.spark_node(user.id, node.id, study_minutes=30)
    assert result.spark_event is not None
    status = result.updated_status
    # 活动痕迹面照常生长
    assert status.is_unlocked is True
    assert status.study_count == 1
    assert status.total_study_minutes == 30
    # 掌握度零增长（时间不显示掌握）
    assert status.mastery_score == 0.0
    assert result.spark_event.old_mastery == 0.0
    assert result.spark_event.new_mastery == 0.0
    assert result.spark_event.is_level_up is False


async def test_repeated_time_sparks_never_display_mastery(spark_env):
    """反例：反复纯时长 spark 永远推不出掌握（GLIMMER 以上不可达）。"""
    db, user, node = spark_env
    service = GalaxyStatsService(db)
    for _ in range(5):
        result = await service.spark_node(user.id, node.id, study_minutes=60)
    assert result.updated_status.mastery_score == 0.0
    # 审计行是 projection（活动痕迹，重放跳过），不是证据
    rows = (
        await db.execute(
            text("SELECT reason, effect_kind FROM mastery_audit_log WHERE node_id = :node_id"),
            {"node_id": str(node.id)},
        )
    ).fetchall()
    assert rows
    assert all(row[1] == "projection" for row in rows)
    # 证据计数（真实证据存在性）为零——时长不清 legacy 旗
    assert await service.get_evidence_counts_by_node(user.id) == {}


async def test_evidence_outcome_still_fuses_in_spark(spark_env):
    """正例（对照）：带 outcome 的 spark 仍走证据融合（掌握度可增长）。"""
    db, user, node = spark_env
    service = GalaxyStatsService(db)
    result = await service.spark_node(
        user.id,
        node.id,
        study_minutes=0,
        outcome=EvidenceObservation(
            evidence_type=MasteryEvidenceType.QUIZ,
            value=90.0,
            confidence=0.9,
        ),
    )
    assert result.updated_status.mastery_score > 0.0


# ---------------------------------------------------------------------------
# 展示双区分：能力标签封顶 + 通道字段 + 投影版本
# ---------------------------------------------------------------------------


def test_unverified_high_score_never_displays_mastery_labels():
    """反例（标签不能叫精通）：无检验证据的 95 分节点 → 封顶 SHINING，
    通道字段=practiced（数据面），亮度保留参与足迹。"""
    status = _FakeStatus(mastery=95.0)
    node = KnowledgeNode(id=uuid4(), name="n", importance_level=3, is_seed=True, global_spark_count=0)
    node_with = NodeWithStatus.from_models(
        node, status, evidence_count=0, verified_evidence_count=0
    )
    assert node_with.user_status is not None
    assert node_with.user_status.status.value == "shining"  # 封顶，非 mastered
    assert node_with.user_status.brightness > 0.5  # 存量亮度=参与足迹保留
    assert node_with.user_status.mastery_evidence is not None
    assert node_with.user_status.mastery_evidence.capability_channel == "practiced"
    assert node_with.user_status.projection_version == 3


def test_verified_high_score_keeps_mastery_labels():
    """正例：有独立检验级证据的 95 分节点 → MASTERED 标签合法 + 通道=verified。"""
    status = _FakeStatus(mastery=95.0)
    node = KnowledgeNode(id=uuid4(), name="n", importance_level=3, is_seed=True, global_spark_count=0)
    node_with = NodeWithStatus.from_models(
        node, status, evidence_count=2, verified_evidence_count=2
    )
    assert node_with.user_status is not None
    assert node_with.user_status.status.value == "mastered"
    assert node_with.user_status.mastery_evidence.capability_channel == "verified"


def test_unverified_80_score_capped_below_mastered_threshold():
    """反例：80+ 未检验 → BRILLIANT 也封顶（80 = 产品语义「已掌握」门槛）。"""
    status = _FakeStatus(mastery=85.0)
    node = KnowledgeNode(id=uuid4(), name="n", importance_level=3, is_seed=True, global_spark_count=0)
    node_with = NodeWithStatus.from_models(node, status, evidence_count=1, verified_evidence_count=0)
    assert node_with.user_status is not None
    assert node_with.user_status.status.value == "shining"


def test_unknown_verified_face_keeps_legacy_display():
    """兼容路径：未装配证据查询的面（verified=None）不封顶——D04 前行为逐字节
    一致（注册为限制：-authoritative 展示面）。"""
    status = _FakeStatus(mastery=95.0)
    node = KnowledgeNode(id=uuid4(), name="n", importance_level=3, is_seed=True, global_spark_count=0)
    node_with = NodeWithStatus.from_models(node, status)
    assert node_with.user_status is not None
    assert node_with.user_status.status.value == "mastered"
    assert node_with.user_status.mastery_evidence is None
