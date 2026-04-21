"""Simulation environment base class: reusable RL test harness.

Provides a standardized interface for running SGW simulations with
different configurations, scenarios, and policies. Designed for:
- Scenario recipes (predefined test configurations)
- Policy zoo (snapshot + restore of policy state)
- Multi-scenario evaluation
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .spec import (
    StateVector, Action, EpisodeConfig, EpisodeResult,
    PolicyStage, IterationOutcome, EpisodeTerminationReason,
    RewardWeights, DEFAULT_REWARD_WEIGHTS,
    compute_config_hash,
)
from .policy import PolicyRouter, ThompsonSamplingBandit, LinUCBBandit, RulePolicy
from .features import FeatureExtractor
from .overfitting import (
    HoldoutGuard, ExplorationBudget, TemperatureSchedule,
    AdversarialSelfPlay,
)
from .loops import MetaLoopCoordinator


# ── Scenario Recipe ───────────────────────────────────────


@dataclass
class ScenarioRecipe:
    """A predefined test scenario with fixed configuration.

    Recipes allow instantiating a SimulationEnv with specific parameters
    for reproducible testing.
    """
    recipe_id: str
    description: str
    scenario_id: str = "stage_16_rule_y"
    config_overrides: dict[str, Any] = field(default_factory=dict)
    reward_weights: RewardWeights = field(default_factory=RewardWeights)
    episode_config: EpisodeConfig = field(default_factory=EpisodeConfig)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "description": self.description,
            "scenario_id": self.scenario_id,
            "config_overrides": self.config_overrides,
            "reward_weights": {
                "w_soft": self.reward_weights.w_soft,
                "w_auth": self.reward_weights.w_auth,
                "w_hard": self.reward_weights.w_hard,
                "w_session": self.reward_weights.w_session,
                "w_diversity": self.reward_weights.w_diversity,
            },
            "episode_config": {
                "max_iterations": self.episode_config.max_iterations,
                "convergence_window": self.episode_config.convergence_window,
                "explore_every_n": self.episode_config.explore_every_n,
            },
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioRecipe:
        rw = data.get("reward_weights", {})
        ec = data.get("episode_config", {})
        return cls(
            recipe_id=data["recipe_id"],
            description=data.get("description", ""),
            scenario_id=data.get("scenario_id", "stage_16_rule_y"),
            config_overrides=data.get("config_overrides", {}),
            reward_weights=RewardWeights(
                w_soft=rw.get("w_soft", 0.30),
                w_auth=rw.get("w_auth", 0.35),
                w_hard=rw.get("w_hard", 0.20),
                w_session=rw.get("w_session", 0.10),
                w_diversity=rw.get("w_diversity", 0.05),
            ),
            episode_config=EpisodeConfig(
                max_iterations=ec.get("max_iterations", 20),
                convergence_window=ec.get("convergence_window", 5),
                explore_every_n=ec.get("explore_every_n", 10),
            ),
            tags=data.get("tags", []),
        )


# Predefined recipes
BUILTIN_RECIPES: dict[str, ScenarioRecipe] = {
    "default": ScenarioRecipe(
        recipe_id="default",
        description="Default SGW RL configuration with balanced weights",
        tags=["baseline"],
    ),
    "compliance_focus": ScenarioRecipe(
        recipe_id="compliance_focus",
        description="Optimize for compliance (soft violation rate)",
        reward_weights=RewardWeights(w_soft=0.50, w_auth=0.20, w_hard=0.20, w_session=0.05, w_diversity=0.05),
        tags=["compliance"],
    ),
    "authenticity_focus": ScenarioRecipe(
        recipe_id="authenticity_focus",
        description="Optimize for conversation authenticity",
        reward_weights=RewardWeights(w_soft=0.15, w_auth=0.50, w_hard=0.20, w_session=0.05, w_diversity=0.10),
        tags=["authenticity"],
    ),
    "fast_iteration": ScenarioRecipe(
        recipe_id="fast_iteration",
        description="Quick iteration for testing (5 iterations, convergence=3)",
        episode_config=EpisodeConfig(max_iterations=5, convergence_window=3),
        tags=["testing", "fast"],
    ),
    "stress_test": ScenarioRecipe(
        recipe_id="stress_test",
        description="Stress test with adversarial self-play and high exploration",
        episode_config=EpisodeConfig(max_iterations=30, explore_every_n=5),
        reward_weights=RewardWeights(w_diversity=0.15),
        tags=["stress", "adversarial"],
    ),
}


# ── Policy Zoo ────────────────────────────────────────────


@dataclass
class PolicySnapshot:
    """A frozen snapshot of policy state for comparison and rollback."""
    snapshot_id: str
    created_at: str
    policy_stage: PolicyStage
    bandit_state: dict[str, Any] = field(default_factory=dict)
    temperature_state: dict[str, float] = field(default_factory=dict)
    config_at_snapshot: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "policy_stage": self.policy_stage.value,
            "bandit_state": self.bandit_state,
            "temperature_state": self.temperature_state,
            "config_at_snapshot": self.config_at_snapshot,
            "performance": self.performance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicySnapshot:
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            policy_stage=PolicyStage(data.get("policy_stage", "rule")),
            bandit_state=data.get("bandit_state", {}),
            temperature_state=data.get("temperature_state", {}),
            config_at_snapshot=data.get("config_at_snapshot", {}),
            performance=data.get("performance", {}),
        )


class PolicyZoo:
    """Manages policy snapshots: save, restore, list, compare.

    Snapshots are stored as JSON files in a zoo directory.
    """

    def __init__(self, zoo_dir: Path):
        self.zoo_dir = zoo_dir
        self.zoo_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        *,
        policy_router: PolicyRouter,
        temperature: TemperatureSchedule,
        current_config: dict[str, Any],
        performance: dict[str, float] | None = None,
        snapshot_id: str | None = None,
    ) -> PolicySnapshot:
        """Save current policy state as a snapshot."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

        snap = PolicySnapshot(
            snapshot_id=snapshot_id or f"snap_{compute_config_hash(current_config)}_{now[:10]}",
            created_at=now,
            policy_stage=policy_router.current_stage,
            bandit_state=policy_router.bandit.to_dict(),
            temperature_state=temperature.to_dict(),
            config_at_snapshot=dict(current_config),
            performance=performance or {},
        )

        path = self.zoo_dir / f"{snap.snapshot_id}.json"
        path.write_text(json.dumps(snap.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return snap

    def load_snapshot(self, snapshot_id: str) -> PolicySnapshot | None:
        """Load a snapshot by ID."""
        path = self.zoo_dir / f"{snapshot_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return PolicySnapshot.from_dict(data)

    def restore_snapshot(self, snapshot_id: str) -> tuple[PolicyRouter, TemperatureSchedule, dict] | None:
        """Restore policy state from a snapshot."""
        snap = self.load_snapshot(snapshot_id)
        if snap is None:
            return None

        bandit = ThompsonSamplingBandit.from_dict(snap.bandit_state)
        contextual = LinUCBBandit()
        router = PolicyRouter(
            rule=RulePolicy(),
            bandit=bandit,
            contextual=contextual,
        )
        temperature = TemperatureSchedule.from_dict(snap.temperature_state)
        return (router, temperature, snap.config_at_snapshot)

    def list_snapshots(self) -> list[PolicySnapshot]:
        """List all saved snapshots."""
        snapshots = []
        for path in sorted(self.zoo_dir.glob("snap_*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshots.append(PolicySnapshot.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                pass
        return snapshots

    def compare_snapshots(self, id_a: str, id_b: str) -> dict[str, Any] | None:
        """Compare two snapshots."""
        snap_a = self.load_snapshot(id_a)
        snap_b = self.load_snapshot(id_b)
        if not snap_a or not snap_b:
            return None

        return {
            "a": {"id": snap_a.snapshot_id, "stage": snap_a.policy_stage.value, "perf": snap_a.performance},
            "b": {"id": snap_b.snapshot_id, "stage": snap_b.policy_stage.value, "perf": snap_b.performance},
            "config_diff": {
                k: {"a": snap_a.config_at_snapshot.get(k), "b": snap_b.config_at_snapshot.get(k)}
                for k in set(snap_a.config_at_snapshot) | set(snap_b.config_at_snapshot)
                if snap_a.config_at_snapshot.get(k) != snap_b.config_at_snapshot.get(k)
            },
        }


# ── SimulationEnv ─────────────────────────────────────────


class SimulationEnv:
    """Reusable RL simulation environment.

    Wraps all RL components into a single interface for running
    experiments with different recipes and policies.

    Usage:
        env = SimulationEnv(run_db, config)
        env.configure(recipe=BUILTIN_RECIPES["compliance_focus"])
        result = env.run_episode()
    """

    def __init__(
        self,
        run_db: Any,  # RunDB — avoiding circular import
        current_config: dict[str, Any],
        *,
        zoo_dir: Path | None = None,
    ):
        from ..storage.db import RunDB
        self.run_db: RunDB = run_db
        self.current_config = current_config
        self.feature_extractor = FeatureExtractor(run_db)
        self.policy_router = PolicyRouter()
        self.zoo = PolicyZoo(zoo_dir or Path(".sgw_state/policy_zoo"))

        # Anti-overfitting components
        self.holdout = HoldoutGuard()
        self.exploration = ExplorationBudget()
        self.temperature = TemperatureSchedule()
        self.adversarial = AdversarialSelfPlay()

        self._coordinator: MetaLoopCoordinator | None = None
        self._recipe: ScenarioRecipe | None = None

    def configure(self, *, recipe: ScenarioRecipe) -> None:
        """Configure environment from a recipe."""
        self._recipe = recipe
        # Apply config overrides
        for key, value in recipe.config_overrides.items():
            if key in self.current_config:
                self.current_config[key] = value

        # Create coordinator with recipe settings
        self._coordinator = MetaLoopCoordinator(
            feature_extractor=self.feature_extractor,
            policy_router=self.policy_router,
            episode_config=recipe.episode_config,
            holdout_guard=self.holdout,
            exploration_budget=self.exploration,
            temperature_schedule=self.temperature,
            adversarial_play=self.adversarial,
        )

    def get_coordinator(self) -> MetaLoopCoordinator:
        """Get or create the loop coordinator."""
        if self._coordinator is None:
            self.configure(recipe=BUILTIN_RECIPES["default"])
        return self._coordinator

    def save_policy_snapshot(self, *, performance: dict[str, float] | None = None) -> PolicySnapshot:
        """Save current policy state."""
        return self.zoo.save_snapshot(
            policy_router=self.policy_router,
            temperature=self.temperature,
            current_config=self.current_config,
            performance=performance,
        )

    def restore_policy_snapshot(self, snapshot_id: str) -> bool:
        """Restore policy from a snapshot."""
        result = self.zoo.restore_snapshot(snapshot_id)
        if result is None:
            return False
        router, temp, config = result
        self.policy_router = router
        self.temperature = temp
        self.current_config = config
        return True
