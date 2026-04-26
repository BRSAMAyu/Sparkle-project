from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.api.v1.galaxy import router
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_get_galaxy_node_history_returns_mastery_and_related_errors(db_session, test_user):
    now = datetime.utcnow()
    node = KnowledgeNode(
        name="TCP 流量控制",
        description="滑动窗口与 rwnd",
        importance_level=4,
        is_seed=True,
    )
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=test_user.id,
            node_id=node.id,
            mastery_score=72,
            study_count=3,
            total_minutes=75,
            total_study_minutes=75,
            is_unlocked=True,
            last_study_at=now - timedelta(days=2),
            last_interacted_at=now - timedelta(days=2),
        )
    )
    db_session.add(
        StudyRecord(
            user_id=test_user.id,
            node_id=node.id,
            study_minutes=25,
            mastery_delta=8,
            initial_mastery=64,
            created_at=now - timedelta(days=2),
        )
    )
    for index in range(2):
        db_session.add(
            ErrorRecord(
                user_id=test_user.id,
                subject_code="computer",
                question_text=f"TCP 流量控制错题 {index + 1}",
                user_answer="把 rwnd 和 cwnd 混在一起",
                correct_answer="rwnd 是接收方窗口",
                affected_node_id=node.id,
                linked_knowledge_node_ids=[str(node.id)],
                mastery_level=0.35,
                latest_analysis={"root_cause": "窗口变量混淆"},
                created_at=now - timedelta(hours=index + 1),
                updated_at=now - timedelta(hours=index + 1),
                is_deleted=False,
            )
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
                f"/api/v1/galaxy/node/{node.id}/history",
                params={"user_id": str(test_user.id)},
            )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["mastery"] == 0.72
    assert payload["study_count"] == 3
    assert payload["node_label"] == "TCP 流量控制"
    assert len(payload["related_errors"]) == 2
    assert payload["related_errors"][0]["analysis_summary"] == "窗口变量混淆"
