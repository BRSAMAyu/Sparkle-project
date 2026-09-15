from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.cognitive import CognitiveFragment
from app.services.analysis.unified_analysis_service import UnifiedAnalysisService


@pytest.mark.asyncio
async def test_build_similar_text_skips_deferred_embedding_access():
    db = AsyncMock()
    service = UnifiedAnalysisService(db)
    fragment = CognitiveFragment(
        id=uuid4(),
        user_id=uuid4(),
        content="fragment without preloaded embedding",
        source_type="behavior",
        resource_type="text",
        severity=2,
    )

    result = await service._build_similar_text(fragment)

    assert result == ""
    db.execute.assert_not_awaited()
