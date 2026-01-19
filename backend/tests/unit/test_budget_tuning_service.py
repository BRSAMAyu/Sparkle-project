import pytest

from app.services.budget_tuning_service import BudgetTuningService, MIN_MULTIPLIER, MAX_MULTIPLIER, TARGET_SUM


@pytest.mark.asyncio
async def test_budget_tuning_apply_feedback_normalizes(db_session):
    service = BudgetTuningService(db_session)
    multipliers = await service.apply_feedback(
        "chat",
        reasons=["verbose", "misaligned"],
        score=-1.0,
    )
    total = sum(multipliers.values())
    assert total == pytest.approx(TARGET_SUM)
    for value in multipliers.values():
        assert MIN_MULTIPLIER <= value <= MAX_MULTIPLIER
