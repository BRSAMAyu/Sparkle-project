from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.models.galaxy import KnowledgeNode
from app.services.galaxy_service import GalaxyService


async def _ensure_mastery_audit_log(db_session) -> None:
    await db_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS mastery_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                old_mastery INTEGER NOT NULL,
                new_mastery INTEGER NOT NULL,
                reason TEXT,
                request_id TEXT,
                revision INTEGER DEFAULT 1,
                created_at DATETIME NOT NULL
            )
        """)
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_user_contribution_stats_groups_mastery_history_by_reason(db_session, test_user):
    await _ensure_mastery_audit_log(db_session)

    now = datetime.utcnow()
    first_node = KnowledgeNode(name="牛顿第二定律", importance_level=3, is_seed=True)
    repair_node = KnowledgeNode(name="电场强度", importance_level=3, is_seed=True)
    conversation_node = KnowledgeNode(name="热力学第一定律", importance_level=3, is_seed=True)
    shared_node = KnowledgeNode(name="麦克斯韦方程组", importance_level=4, is_seed=True)
    db_session.add_all([first_node, repair_node, conversation_node, shared_node])
    await db_session.flush()

    rows = [
        {
            "node_id": str(first_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 0,
            "new_mastery": 24,
            "reason": "task_complete",
            "created_at": now - timedelta(days=4),
        },
        {
            "node_id": str(repair_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 18,
            "new_mastery": 28,
            "reason": "error_review:remembered",
            "created_at": now - timedelta(days=3),
        },
        {
            "node_id": str(conversation_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 45,
            "new_mastery": 57,
            "reason": "knowledge_service_increment",
            "created_at": now - timedelta(days=2),
        },
        {
            "node_id": str(shared_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 0,
            "new_mastery": 16,
            "reason": "focus_session",
            "created_at": now - timedelta(days=5),
        },
        {
            "node_id": str(shared_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 16,
            "new_mastery": 26,
            "reason": "conversation_writeback",
            "created_at": now - timedelta(days=1),
        },
        {
            "node_id": str(first_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 24,
            "new_mastery": 18,
            "reason": "error_penalty",
            "created_at": now - timedelta(hours=12),
        },
    ]

    for row in rows:
        await db_session.execute(
            text("""
                INSERT INTO mastery_audit_log (
                    node_id, user_id, old_mastery, new_mastery, reason, created_at
                ) VALUES (
                    :node_id, :user_id, :old_mastery, :new_mastery, :reason, :created_at
                )
            """),
            row,
        )
    await db_session.commit()

    result = await GalaxyService(db_session).get_user_contribution_stats(test_user.id)

    assert result.first_activation_count == 2
    assert result.error_repaired_count == 1
    assert result.conversation_updated_count == 2

    assert {item.node_name for item in result.first_activated_nodes} == {
        "牛顿第二定律",
        "麦克斯韦方程组",
    }
    assert [item.node_name for item in result.error_repaired_nodes] == ["电场强度"]
    assert {item.node_name for item in result.conversation_updated_nodes} == {
        "热力学第一定律",
        "麦克斯韦方程组",
    }
