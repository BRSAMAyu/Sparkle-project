"""V4-D04 · 跨用户分享不加个人能力（真实 DB）.

卡面验收：sprint奖励不读AI掌握分，跨用户分享不加个人能力。
- 正例：分享 knowledge_node → 掌握度分毫不动，参与足迹（溯源快照）留痕，
  事件 delta=0，系统消息不再声称掌握度提升；
- 反例：不写 mastery 审计行、不产生掌握度效果（含 effect_kind 面零行）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.community_signal_bridge import CommunitySignalBridge
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def share_env(db_session, monkeypatch):
    """community mode=live + 事件总线捕获（不依赖 Redis）。"""
    from app.core.event_bus import event_bus

    published: list[tuple[str, dict]] = []

    async def _capture_publish(event_name, payload, *args, **kwargs):
        published.append((event_name, payload))

    monkeypatch.setattr(event_bus, "publish", _capture_publish)

    async def _fake_mode(self):
        return "live"

    monkeypatch.setattr(CommunitySignalBridge, "_community_mode", _fake_mode)

    async def _noop_enqueue(self, user_id, update):
        return True

    monkeypatch.setattr(
        __import__(
            "app.services.system_update_service",
            fromlist=["SystemUpdateService"],
        ).SystemUpdateService,
        "enqueue",
        _noop_enqueue,
    )

    await db_session.execute(
        text(
            """
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
        )
    )
    await db_session.commit()

    user = await _make_user(db_session)
    node = KnowledgeNode(id=uuid4(), name=f"分享节点{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return db_session, user, node, published


async def test_share_records_participation_without_mastery_change(share_env):
    """正例：分享 → 掌握度不动 + 参与足迹留痕 + delta=0 事件。"""
    db, user, node, published = share_env
    status = UserNodeStatus(user_id=user.id, node_id=node.id, mastery_score=42.0)
    db.add(status)
    await db.commit()

    bridge = CommunitySignalBridge(db)
    share_id = uuid4()
    await bridge.handle_resource_shared(
        user_id=user.id,
        resource_type="knowledge_node",
        resource_id=node.id,
        target_group_id=uuid4(),
        share_id=share_id,
    )

    await db.refresh(status)
    assert float(status.mastery_score) == 42.0  # 掌握度分毫不动

    # 参与足迹：溯源快照留行（community_share，capability_effect=none）
    sources = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    share_entries = [e for e in sources if e.get("source_type") == "community_share"]
    assert share_entries and share_entries[0]["reference_id"] == str(share_id)
    assert share_entries[0]["payload"].get("capability_effect") == "none"

    # 事件面：galaxy.node.updated delta=0，不再声称掌握度回流
    node_events = [p for name, p in published if name == "galaxy.node.updated"]
    assert node_events and float(node_events[0]["delta"]) == 0.0
    assert node_events[0]["reason"] == "community_share_participation_trace"
    assert float(node_events[0]["new_mastery"]) == 42.0

    # 系统消息不再声称掌握度提升（capability_effect=none）
    # （enqueue 被 monkeypatch 捕获为 no-op——文案断言由常量面守护，见反例）


async def test_share_writes_no_mastery_effect_rows(share_env):
    """反例：分享零掌握度效果——无 mastery 审计行、无状态行创建（未学习者
    分享不证明任何学习）、无 update_node_mastery 写入。"""
    db, user, node, published = share_env

    bridge = CommunitySignalBridge(db)
    await bridge.handle_resource_shared(
        user_id=user.id,
        resource_type="knowledge_node",
        resource_id=node.id,
        target_group_id=uuid4(),
        share_id=uuid4(),
    )

    rows = (
        await db.execute(
            text("SELECT COUNT(*) FROM mastery_audit_log WHERE user_id = :u"),
            {"u": str(user.id)},
        )
    ).scalar_one()
    assert rows == 0

    result = await db.execute(
        select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node.id)
    )
    assert result.scalar_one_or_none() is None  # 不创建状态行


async def test_share_of_non_node_resource_is_event_only(share_env):
    """反例（边界）：非 knowledge_node 资源分享 → 只有 community 事件，零星图效果。"""
    db, user, node, published = share_env
    bridge = CommunitySignalBridge(db)
    await bridge.handle_resource_shared(
        user_id=user.id,
        resource_type="document",
        resource_id=uuid4(),
        target_group_id=uuid4(),
        share_id=uuid4(),
    )
    assert any(name == "community.resource_shared" for name, _ in published)
    assert not any(name == "galaxy.node.updated" for name, _ in published)
    status = await db.get(UserNodeStatus, (user.id, node.id))
    assert status is None
