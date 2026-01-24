import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.intervention import InterventionFeedback, InterventionRequest
from app.schemas.intervention import InterventionFeedbackType
from app.services.intervention_service import InterventionService


@pytest.mark.asyncio
async def test_record_feedback_idempotent_skips_updates():
    db = AsyncMock()
    user_id = uuid.uuid4()
    request = InterventionRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        requested_level="card",
        final_level="card",
        status="delivered",
        schema_version="v1",
    )

    existing = InterventionFeedback(
        request_id=request.id,
        user_id=user_id,
        feedback_type=InterventionFeedbackType.ACCEPT.value,
        idempotency_key="dedupe-1",
    )

    result_proxy = MagicMock()
    result_proxy.scalar_one_or_none.return_value = existing
    db.execute.return_value = result_proxy

    service = InterventionService(db)
    service._apply_feedback_policy = AsyncMock()
    service._apply_scaffolding_feedback = AsyncMock()
    service._update_template_bandit = AsyncMock()

    result = await service.record_feedback(
        request=request,
        user_id=user_id,
        feedback_type=InterventionFeedbackType.ACCEPT,
        extra_data=None,
        idempotency_key="dedupe-1",
    )

    assert result is existing
    service._apply_feedback_policy.assert_not_awaited()
    service._apply_scaffolding_feedback.assert_not_awaited()
    service._update_template_bandit.assert_not_awaited()
