from __future__ import annotations

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.validator import RequestValidator


@pytest.mark.asyncio
async def test_request_validator_skips_quota_check_when_disabled():
    validator = RequestValidator(redis_client=object(), enable_quota_check=False)

    request = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message="hello",
    )

    result = await validator.validate_chat_request(request)

    assert validator.token_tracker is None
    assert result.is_valid is True
