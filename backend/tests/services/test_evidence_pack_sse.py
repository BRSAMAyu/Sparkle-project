import uuid
from unittest.mock import AsyncMock

import pytest

from app.schemas.galaxy import NodeBase, SearchResultItem, SectorCode
from app.services.knowledge_service import KnowledgeService


@pytest.mark.asyncio
async def test_retrieve_context_emits_evidence_pack(monkeypatch):
    node_id = uuid.uuid4()
    node = NodeBase(
        id=node_id,
        name="Test Node",
        description="Sample description",
        importance_level=1,
        sector_code=SectorCode.COSMOS,
        is_seed=False,
    )
    result = SearchResultItem(node=node, similarity=0.9, user_status=None)

    service = KnowledgeService(db_session=AsyncMock())
    service.galaxy_service.hybrid_search = AsyncMock(return_value=[result])

    send_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.knowledge_service.sse_manager.send_to_user",
        send_mock,
    )

    context = await service.retrieve_context(
        user_id=uuid.uuid4(),
        query="regular query for evidence",
        limit=1,
    )

    assert "Relevant Knowledge Base" in context
    send_mock.assert_awaited()
    args = send_mock.await_args.args
    assert args[1] == "evidence_pack"
    payload = args[2]
    assert payload["nodes"][0]["node_id"] == str(node_id)
