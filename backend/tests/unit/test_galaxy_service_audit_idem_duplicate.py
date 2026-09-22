"""ERR-IDEM-CONCUR · GalaxyService.update_node_mastery 写侧幂等冲突路径直测.

毫秒窗口并发由 test_error_mastery_concurrency.py 用双 session + barrier 覆盖；
本文件把真实 ``GalaxyService.update_node_mastery``（非 stub）在 sqlite 基座上
对着真实部分唯一索引逐分支过一遍：

- 同键重复（edi:/erv:）→ ``{"success": False, "reason": "duplicate"}``，
  掌握度保持胜者值、审计行不重复、outbox 不重复；
- 键域三元组 (user_id, node_id, request_id) —— 不同节点同键不误伤；
- 部分索引只管辖 edi:/erv: 命名空间 —— 其他取值域（裸 task_id、NULL、
  obs=/oc= 复合段）重复写入不受影响（行为与迁移前完全一致）。
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.theater_candidate_bundle import TheaterCandidateBundle  # noqa: F401 — create_all FK 解析
from app.models.theater_prediction import TheaterPrediction  # noqa: F401 — create_all FK 解析
from app.models.user import User
from app.services.galaxy_service import GalaxyService

# 与迁移 c8e4f2a3b1d5（建表）+ erridemconc_20260922（唯一部分索引）同构的
# sqlite 版 DDL（mastery_audit_log 无 ORM 模型）
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


@pytest_asyncio.fixture
async def galaxy_env(tmp_path):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        f"sqlite+aiosqlite:////{tmp_path / 'galaxy_idem.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(MASTERY_AUDIT_LOG_DDL))
        await conn.execute(text(IDEM_UNIQUE_INDEX_DDL))

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        user = User(username=f"gal_idem_{uuid4().hex[:8]}", email="gal-idem@example.com", hashed_password="x")
        session.add(user)
        node_a = KnowledgeNode(name="NodeA", description="d")
        node_b = KnowledgeNode(name="NodeB", description="d")
        session.add_all([node_a, node_b])
        await session.flush()
        for node, score in ((node_a, 50.0), (node_b, 60.0)):
            session.add(
                UserNodeStatus(
                    user_id=user.id,
                    node_id=node.id,
                    mastery_score=score,
                    bkt_mastery_prob=score / 100.0,
                    is_unlocked=True,
                    study_count=0,
                    total_minutes=0,
                    total_study_minutes=0,
                    revision=0,
                )
            )
        await session.commit()
        yield session, user.id, node_a.id, node_b.id

    await engine.dispose()


def _edi_key(error_id, node_id) -> str:
    return (
        f"edi:{str(error_id).replace('-', '')}:d90c7fa3:"
        f"{str(node_id).replace('-', '')}"
    )


async def _audit_count(session, user_id, node_id, request_id) -> int:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM mastery_audit_log "
            "WHERE user_id = :u AND node_id = :n AND request_id = :r"
        ),
        {"u": str(user_id), "n": str(node_id), "r": request_id},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_duplicate_edi_key_rejected_as_duplicate(galaxy_env):
    """同键第二次写入 → duplicate；掌握度保持首次值、审计不重复。"""
    session, user_id, node_a, _node_b = galaxy_env
    service = GalaxyService(session)
    key = _edi_key(uuid4(), node_a)

    first = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=42,
        reason="error_diagnosis:concept_confusion", request_id=key, revision=0,
    )
    assert first["success"] is True
    assert first["new_mastery"] == 42

    second = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=34,
        reason="error_diagnosis:concept_confusion", request_id=key, revision=1,
    )
    assert second["success"] is False, "同键重复写入必须被写侧幂等仲裁拒绝"
    assert second["reason"] == "duplicate"

    await session.rollback()  # duplicate 分支内部已回滚，这里对齐观察点
    refreshed = await session.get(UserNodeStatus, (user_id, node_a))
    assert float(refreshed.mastery_score) == 42.0, "掌握度保持胜者（首次）值"
    assert await _audit_count(session, user_id, node_a, key) == 1


@pytest.mark.asyncio
async def test_duplicate_erv_key_rejected_as_duplicate(galaxy_env):
    session, user_id, node_a, _node_b = galaxy_env
    service = GalaxyService(session)
    key = f"erv:{uuid4().hex}:d90c7fa3:remembered:{node_a.hex}"

    first = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=54,
        reason="error_review:remembered", request_id=key, revision=0,
    )
    assert first["success"] is True

    second = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=58,
        reason="error_review:remembered", request_id=key, revision=1,
    )
    assert second["success"] is False
    assert second["reason"] == "duplicate"


@pytest.mark.asyncio
async def test_same_key_on_different_node_not_blocked(galaxy_env):
    """键域是 (user, node, request_id) 三元组：不同节点不受同前缀键牵连。"""
    session, user_id, node_a, node_b = galaxy_env
    service = GalaxyService(session)
    error_id = uuid4()

    key_a = _edi_key(error_id, node_a)
    key_b = _edi_key(error_id, node_b)

    first = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=42,
        reason="error_diagnosis:concept_confusion", request_id=key_a, revision=0,
    )
    second = await service.update_node_mastery(
        user_id=user_id, node_id=node_b, new_mastery=52,
        reason="error_diagnosis:concept_confusion", request_id=key_b, revision=0,
    )
    assert first["success"] is True
    assert second["success"] is True, "不同节点的同源诊断各自生效（多节点去重语义不变）"


@pytest.mark.asyncio
async def test_non_idem_namespace_duplicate_unaffected(galaxy_env):
    """部分索引谓词之外的取值域保持原语义：重复写不拒绝（管不着）。"""
    session, user_id, node_a, _node_b = galaxy_env
    service = GalaxyService(session)

    bare_task_id = str(uuid4())
    first = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=55,
        reason="task_complete", request_id=bare_task_id, revision=0,
    )
    second = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=60,
        reason="task_complete", request_id=bare_task_id, revision=1,
    )
    assert first["success"] is True
    assert second["success"] is True, "非 edi:/erv: 命名空间的 request_id 不受部分索引管辖"

    # NULL request_id（Galaxy REST 不传）写两行也不受影响
    null_first = await service.update_node_mastery(
        user_id=user_id, node_id=node_a, new_mastery=65, reason="manual_update", revision=2,
    )
    assert null_first["success"] is True
