from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import AdaptationRecord, AdaptiveReplanner
from app.services.plan_progress_service import PlanHealthReport


@pytest.mark.asyncio
async def test_apply_incremental_adjustment_emits_visible_update_for_noop_patch() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    report = PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="warning",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.2},
        requires_adjustment=True,
        recommended_action="adjust",
    )
    replanner.db = None
    replanner._card_bridge = None
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=SimpleNamespace(facts={"adaptive_meta": {}}, constraints={})),
        upsert_plan_state=AsyncMock(),
    )
    replanner._calculate_adjustments = lambda *args, **kwargs: {"adaptive_adjustments": {"time_multiplier": 1.1}}
    replanner.plan_adjustment_applier = SimpleNamespace(
        apply_incremental_changes=AsyncMock(
            return_value=SimpleNamespace(
                applied=True,
                affected_task_ids=[],
                inserted_task_ids=[],
                hidden_task_ids=[],
                user_facing_summary=None,
            )
        )
    )
    replanner._enqueue_adaptation_update = AsyncMock()

    records = await replanner._apply_incremental_adjustment(report, trigger="task_feedback")

    assert records == []
    replanner._enqueue_adaptation_update.assert_awaited_once()
    kwargs = replanner._enqueue_adaptation_update.await_args.kwargs
    assert kwargs["update_type"] == "plan_adaptation_evaluated"
