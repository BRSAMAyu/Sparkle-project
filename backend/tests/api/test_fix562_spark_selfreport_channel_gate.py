"""FIX-562 · spark 客户端自报 outcome 过 D04 能力通道门（API 面融合封死）.

D04 一审 F-2：``POST /nodes/{node_id}/spark`` 曾接受客户端自报 outcome
（quiz/value/confidence，仅 pydantic 界校验）并直接贝叶斯融合掌握度——绕过
D04 能力通道分类（自报主张真相面 = SELF_REPORTED → PRACTICED，永不融合），
且后果可达成就光子（mastery ≥80 → NODE_MASTERED）。

修复语义（更严不更松）：

- 客户端自报主张经 D04 通道权威（``CLIENT_SELF_REPORT_CHANNEL``，等价引用
  封闭词表 ``TRUTH_CLASS_CHANNELS[SELF_REPORTED]``）判定 → PRACTICED——
  融合面封死，主张降级进自评独立观察通道（``MasteryEvidenceType.SELF_REPORT``：
  融合权重 0、fuse_mastery 只记账不融合、账本重放跳过），claim 留观测溯源；
- 词表漂移防御面：通道权威判 VERIFIED 即 422 拒绝（fail-closed，该面永不
  融合客户端主张）；
- 服务端核验的独立检验不受影响：G-01 服务级 outcome 融合（内部可信面）与
  G-02 吸收器 VERIFIED 通道照常（不削弱合法面）。

每面一正一反可失败。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import text

from app.api.deps import get_current_user_id, get_db
from app.api.v1 import galaxy as galaxy_api
from app.models.galaxy import KnowledgeNode
from app.services.galaxy.capability_channel import CLIENT_SELF_REPORT_CHANNEL, CapabilityChannel
from app.services.galaxy.mastery_evidence import EvidenceObservation, MasteryEvidenceType
from app.services.galaxy.stats_service import GalaxyStatsService

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

app = FastAPI()
app.include_router(galaxy_api.router, prefix="/api/v1")


async def _ensure_tables(db_session) -> None:
    for ddl in (_AUDIT_DDL, _OUTBOX_DDL, _COUNTERS_DDL):
        await db_session.execute(text(ddl))
    await db_session.commit()


@pytest_asyncio.fixture()
async def spark_env(db_session, test_user):
    await _ensure_tables(db_session)
    node = KnowledgeNode(name=f"FIX562 自报通道{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield db_session, test_user, node, ac
    finally:
        app.dependency_overrides = {}


async def _audit_rows(db, node_id) -> list[tuple]:
    return (
        await db.execute(
            text("SELECT reason, effect_kind FROM mastery_audit_log WHERE node_id = :node_id"),
            {"node_id": str(node_id)},
        )
    ).fetchall()


async def test_self_reported_quiz_claim_never_fuses_mastery(spark_env):
    """正例（修复前红）：自报 quiz 主张过通道门——零融合，只有参与足迹 + 观测溯源.

    修复前该主张以 quiz 名义直接贝叶斯融合（90/0.9 一击把新节点推到 ~81，
    越过 mastered 门槛发光子）；修复后掌握度分毫不动。
    """
    db, user, node, ac = spark_env
    resp = await ac.post(
        f"/api/v1/galaxy/nodes/{node.id}/spark",
        json={
            "study_minutes": 30,
            "trigger_expansion": False,
            "outcome": {"evidence_type": "quiz", "value": 90, "confidence": 0.9},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 融合面封死：掌握度零增长（响应面 + 存量面双断言）
    assert body["spark_event"]["new_mastery"] == 0.0
    assert body["spark_event"]["is_level_up"] is False
    assert body["updated_status"]["mastery_score"] == 0.0
    # 参与足迹照常可见（PRACTICED 语义：解锁 + 活动痕迹）
    assert body["updated_status"]["is_unlocked"] is True
    assert body["updated_status"]["total_study_minutes"] == 30

    rows = await _audit_rows(db, node.id)
    reasons = [r[0] for r in rows]
    # 无 quiz 融合证据行——主张不得以检验名义入账
    assert "evidence:quiz" not in reasons
    # 主张留观测溯源：自评独立通道行存在（重放跳过，零掌握度效果）
    self_report_rows = [r for r in rows if r[0] == "evidence:self_report"]
    assert len(self_report_rows) == 1
    # FIX-576：该行 kind='evidence'（重放记账面），但 G-01 计数谓词显式排除
    # evidence:self_report——双方言（sqlite 测试 / PG 生产）下都不计入真实
    # 证据存在性，自报**不清** legacy 旗（若谓词排除回退，此断言转红）。
    assert self_report_rows[0][1] == "evidence"
    assert await GalaxyStatsService(db).get_evidence_counts_by_node(user.id) == {}


async def test_repeated_self_report_claims_cannot_reach_mastered(spark_env):
    """反例：反复自报主张永远推不出「已掌握」（奖励面越权不可达）.

    修复前 5 次 95 分自报即可让掌握度收敛到门槛以上并触发光子；修复后无论
    自报多少次，掌握度恒为零、状态标签永不升级为 mastered、真实证据计数为零。
    """
    db, user, node, ac = spark_env
    for _ in range(5):
        resp = await ac.post(
            f"/api/v1/galaxy/nodes/{node.id}/spark",
            json={
                "study_minutes": 10,
                "trigger_expansion": False,
                "outcome": {"evidence_type": "task_outcome", "value": 95, "confidence": 0.99},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["updated_status"]["mastery_score"] == 0.0
        assert body["updated_status"]["status"] != "mastered"
    rows = await _audit_rows(db, node.id)
    assert all(r[0] != "evidence:task_outcome" for r in rows), "自报主张不得以检验名义入账"
    # 5 条自报观测行确实存在（kind='evidence'，重放记账面）——但 FIX-576 起
    # G-01 计数谓词显式排除 evidence:self_report：双方言下真实证据计数恒为
    # 零，自报**不清** legacy 旗（谓词排除回退 → 计数为 {node:5}，此断言转红）。
    self_report_rows = [r for r in rows if r[0] == "evidence:self_report"]
    assert len(self_report_rows) == 5
    assert all(r[1] == "evidence" for r in self_report_rows)
    assert await GalaxyStatsService(db).get_evidence_counts_by_node(user.id) == {}


async def test_channel_authority_drift_refuses_claim(spark_env, monkeypatch):
    """fail-closed 防御面：通道权威漂移到 VERIFIED 时，路由拒绝主张（422）而非融合.

    词表封闭性被破坏的假想世界里，该面依旧不得融合客户端主张——宁可拒绝，
    不猜不放过。
    """
    db, user, node, ac = spark_env
    monkeypatch.setattr(galaxy_api, "CLIENT_SELF_REPORT_CHANNEL", CapabilityChannel.VERIFIED)
    resp = await ac.post(
        f"/api/v1/galaxy/nodes/{node.id}/spark",
        json={
            "study_minutes": 30,
            "trigger_expansion": False,
            "outcome": {"evidence_type": "quiz", "value": 90, "confidence": 0.9},
        },
    )
    assert resp.status_code == 422
    rows = await _audit_rows(db, node.id)
    assert rows == [], "拒绝面不得写入任何审计行"
    assert CLIENT_SELF_REPORT_CHANNEL is CapabilityChannel.PRACTICED


async def test_service_level_verified_outcome_still_fuses(spark_env):
    """反例（不削弱合法面）：封死只在 API 客户端主张面——服务级 outcome 融合照常.

    内部可信面（服务端产出的真实观察）经 G-01 贝叶斯融合仍是掌握度后验的
    唯一推进方式之一；本修复不得波及（D04 语义更严不更松的「不误伤」面）。
    """
    db, user, node, _ac = spark_env
    result = await GalaxyStatsService(db).spark_node(
        user.id,
        node.id,
        study_minutes=0,
        outcome=EvidenceObservation(
            evidence_type=MasteryEvidenceType.QUIZ,
            value=90.0,
            confidence=0.9,
        ),
    )
    assert result.updated_status is not None
    assert result.updated_status.mastery_score > 0.0


async def test_real_quiz_evidence_counts_in_g01_presence(spark_env):
    """正例（FIX-576 真空消除）：真实 quiz 证据在 G-01 存在性计数中可见.

    修复前 ``get_evidence_counts_by_node`` 裸 SQL 直绑 UUID 对象——sqlite 测试
    方言 ProgrammingError 被 ``except`` 吞掉降级 `{}`，本断言（`== {node:1}`）
    在旧代码下真空转红不可能：计数恒 `{}`。FIX-576 起计数查询用 GUID-typed
    bindparam（双方言真实执行）+ 结果键归一 UUID——真实证据行双方言下都
    如实计数，同时自报行被谓词排除（见上两例的 `== {}` 面）。
    """
    db, user, node, _ac = spark_env
    result = await GalaxyStatsService(db).spark_node(
        user.id,
        node.id,
        study_minutes=0,
        outcome=EvidenceObservation(
            evidence_type=MasteryEvidenceType.QUIZ,
            value=90.0,
            confidence=0.9,
        ),
    )
    assert result.updated_status is not None
    counts = await GalaxyStatsService(db).get_evidence_counts_by_node(user.id)
    # 双方言真实执行：quiz 证据行存在即计数 1，键为节点 UUID
    assert counts == {node.id: 1}
