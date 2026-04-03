from __future__ import annotations

from uuid import UUID

from app.config import settings

DEFAULT_BUDGETS: dict[str, dict[str, int]] = {
    "learning": {"preferences": 240, "goals": 320, "episodic": 560},
    "chat": {"preferences": 220, "goals": 260, "episodic": 500},
    "planning": {"preferences": 200, "goals": 420, "episodic": 380},
}


class ContextBudgetScheduler:
    def __init__(
        self,
        budgets: dict[str, dict[str, int]] | None = None,
        db: object | None = None,
    ) -> None:
        self.budgets = budgets or DEFAULT_BUDGETS
        self.db = db

    async def allocate(self, intent: str, user_id: UUID | None = None) -> dict[str, int]:
        intent_key = intent or "chat"
        base = dict(self.budgets.get(intent_key, self.budgets["chat"]))
        if not settings.ENABLE_BUDGET_TUNING or self.db is None:
            return base
        if settings.ENABLE_LTM_ROLLOUT and user_id is not None:
            from app.services.ltm_rollout_service import LtmRolloutService

            rollout = LtmRolloutService(self.db)
            if not await rollout.is_enabled(user_id):
                return base

        from app.services.budget_tuning_service import BudgetTuningService

        tuning = BudgetTuningService(self.db)
        multipliers = await tuning.get_multipliers(intent_key)
        tuned = {bucket: base[bucket] * multipliers.get(bucket, 1.0) for bucket in base}
        tuned = _normalize_budget(tuned, sum(base.values()))
        tuned = _apply_min_budget(tuned, min_value=50)
        return {bucket: int(round(value)) for bucket, value in tuned.items()}


def _normalize_budget(budgets: dict[str, float], target_total: float) -> dict[str, float]:
    total = sum(budgets.values())
    if total <= 0:
        return budgets
    scale = target_total / total
    return {bucket: value * scale for bucket, value in budgets.items()}


def _apply_min_budget(budgets: dict[str, float], min_value: int) -> dict[str, float]:
    adjusted = dict(budgets)
    below = {bucket for bucket, value in adjusted.items() if value < min_value}
    if not below:
        return adjusted
    deficit = sum(min_value - adjusted[bucket] for bucket in below)
    for bucket in below:
        adjusted[bucket] = min_value
    above = [bucket for bucket in adjusted if bucket not in below]
    if not above:
        return adjusted
    total_above = sum(adjusted[bucket] for bucket in above)
    if total_above <= 0:
        return adjusted
    for bucket in above:
        adjusted[bucket] = max(0.0, adjusted[bucket] - deficit * (adjusted[bucket] / total_above))
    return adjusted
