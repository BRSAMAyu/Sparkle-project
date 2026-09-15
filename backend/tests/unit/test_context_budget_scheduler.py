import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler, DEFAULT_BUDGETS
from app.models.context_pack import ContextBudgetProfile


@pytest.mark.asyncio
async def test_scheduler_applies_tuned_multipliers(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BUDGET_TUNING", True, raising=False)
    db_session.add_all(
        [
            ContextBudgetProfile(intent="chat", bucket="preferences", multiplier=0.8),
            ContextBudgetProfile(intent="chat", bucket="goals", multiplier=1.0),
            ContextBudgetProfile(intent="chat", bucket="episodic", multiplier=1.2),
        ]
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(db=db_session)
    budgets = await scheduler.allocate("chat")
    base_total = sum(DEFAULT_BUDGETS["chat"].values())
    assert sum(budgets.values()) == pytest.approx(base_total, rel=0.05)
    assert budgets["preferences"] >= 50
    assert budgets["goals"] >= 50
    assert budgets["episodic"] >= 50
