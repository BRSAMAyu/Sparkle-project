from __future__ import annotations

from app.services.analytics.contextual_bandit import (
    BanditSimulationRunner,
    BeliefContext,
    ContextualThompsonBandit,
)
from app.services.analytics.user_state_model import UserArchetype


def test_contextual_thompson_bandit_updates_context_and_global_posteriors() -> None:
    bandit = ContextualThompsonBandit(seed=1)
    context = BeliefContext(
        support_pressure=0.8,
        execution_readiness=0.3,
        uncertainty=0.12,
        bucket="pressure:high|readiness:low|uncertainty:mid",
        features={},
    )

    before = bandit.global_posteriors["cognitive_first"].mean
    bandit.update(context, "cognitive_first", 1.0)
    after = bandit.global_posteriors["cognitive_first"].mean

    assert after > before
    assert bandit.context_posteriors[context.bucket]["cognitive_first"].alpha == 2.0


def test_bandit_simulation_runner_executes_in_numeric_wind_tunnel() -> None:
    report = BanditSimulationRunner(seed=5).run(
        episodes_per_archetype=2,
        steps=6,
        archetypes=[UserArchetype.FRAGILE, UserArchetype.RESILIENT],
    )

    assert report["schema_version"] == "bandit_simulation_report.v1"
    assert report["simulated_only"] is True
    assert report["steps"] > 0
    assert set(report["arm_counts"]).issubset({"execution_first", "balanced", "cognitive_first"})
