from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.deps import get_db
from app.api.v1.galaxy import router
from app.models.galaxy import KnowledgeNode

app = FastAPI()
app.include_router(router, prefix="/api/v1")


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
async def test_get_galaxy_contribution_stats_returns_counts_and_detail_lists(db_session, test_user):
    await _ensure_mastery_audit_log(db_session)

    now = datetime.utcnow()
    activation_node = KnowledgeNode(name="函数极限", importance_level=3, is_seed=True)
    repair_node = KnowledgeNode(name="数列收敛", importance_level=3, is_seed=True)
    conversation_node = KnowledgeNode(name="导数定义", importance_level=3, is_seed=True)
    db_session.add_all([activation_node, repair_node, conversation_node])
    await db_session.flush()

    inserts = [
        {
            "node_id": str(activation_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 0,
            "new_mastery": 20,
            "reason": "task_complete",
            "created_at": now - timedelta(days=3),
        },
        {
            "node_id": str(repair_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 36,
            "new_mastery": 44,
            "reason": "error_review:remembered",
            "created_at": now - timedelta(days=2),
        },
        {
            "node_id": str(conversation_node.id),
            "user_id": str(test_user.id),
            "old_mastery": 52,
            "new_mastery": 63,
            "reason": "conversation_writeback",
            "created_at": now - timedelta(days=1),
        },
    ]

    for row in inserts:
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

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/galaxy/contribution-stats",
                params={"user_id": str(test_user.id)},
            )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["first_activation_count"] == 1
    assert payload["error_repaired_count"] == 1
    assert payload["conversation_updated_count"] == 1
    assert payload["first_activated_nodes"][0]["node_name"] == "函数极限"
    assert payload["error_repaired_nodes"][0]["node_name"] == "数列收敛"
    assert payload["conversation_updated_nodes"][0]["node_name"] == "导数定义"
