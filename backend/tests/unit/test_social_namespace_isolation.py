from datetime import datetime
from uuid import uuid4

import pytest

from app.core.context_manager import ContextOrchestrator
from app.orchestration.social_context_renderer import render_social_context_lines


def test_social_context_renderer_redacts_identity_and_commitment_text():
    lines = render_social_context_lines(
        {
            "recent_person_mentions": [
                {"display_name": "老张", "summary": "老张要一起复习"},
                {"display_name": "小李", "summary": "和小李约了练题"},
            ],
            "pending_commitments_count": 2,
            "relationship_count": 1,
        }
    )

    rendered = "\n".join(lines)
    assert "老张" not in rendered
    assert "小李" not in rendered
    assert "一起复习" not in rendered
    assert "2 条到期承诺" in rendered


@pytest.mark.asyncio
async def test_context_orchestrator_rejects_social_keys_inside_community_context(db_session):
    orchestrator = ContextOrchestrator(db_session, redis_client=None)

    with pytest.raises(ValueError, match="community_context field whitelist violated"):
        orchestrator._assert_allowed_community_context(
            {
                "active_group_count": 1,
                "person_mention": [{"id": str(uuid4()), "created_at": datetime.utcnow().isoformat()}],
            }
        )
