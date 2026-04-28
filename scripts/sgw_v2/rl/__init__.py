"""SGW v2 RL module — MDP formalization, policy, reward, guardrails, DPO.

Public surface used by meta-loop integrations and tests.
"""
from .spec import (
    ACTION_SPECS,
    BANDIT_ARMS,
    PROTECTED_PARAMETERS,
    Action,
    ActionSpec,
    EpisodeConfig,
    EpisodeResult,
    EpisodeTerminationReason,
    FailureSignal,
    GuardrailId,
    IterationOutcome,
    PolicyStage,
    PopulationStats,
    RewardSignal,
    RewardWeights,
    DEFAULT_REWARD_WEIGHTS,
    REWARD_SCALE,
    RunContext,
    StateVector,
    StrategyRecommendation,
    check_config_novelty,
    check_direction_history,
    clamp_amplitude,
    compute_config_hash,
    should_explore,
    state_from_summary,
    validate_action,
)
from .reward import (
    RewardComponents,
    RewardConfig,
    compute_reward,
    load_reward_config,
)
from .policy import (
    LinUCBBandit,
    PolicyRouter,
    RulePolicy,
    ThompsonSamplingBandit,
)
from .features import FeatureExtractor
from .loops import MetaLoopCoordinator, OuterLoopResult
from .overfitting import (
    AdversarialSelfPlay,
    DiversityMetrics,
    ExplorationBudget,
    HoldoutGuard,
    TemperatureSchedule,
)
from .rollout import RolloutGate, RolloutStage, GateResult
from .environment import (
    BUILTIN_RECIPES,
    PolicySnapshot,
    PolicyZoo,
    ScenarioRecipe,
    SimulationEnv,
)
from .changepoint import CUSUMDetector, VarianceShiftDetector, Changepoint
from .causal import CausalAttributor, CausalEffect
from .pattern_miner import MinedPattern, PatternMiner
from .dashboard import generate_dashboard
from .response_evaluator import (
    DIMENSIONS,
    DIMENSION_WEIGHTS,
    QualityDim,
    ResponseEvaluator,
    ResponseQuality,
)
from .preference_extractor import (
    ExtractionResult,
    PreferenceExtractor,
    PreferencePair,
)
from .dpo_trainer import (
    DPOModel,
    DPOTrainer,
    DPOTrainingConfig,
    DPOTrainingResult,
)
from .dpo_policy import DPOPolicy, StrategyPreference

__all__ = [
    # spec
    "ACTION_SPECS", "BANDIT_ARMS", "PROTECTED_PARAMETERS",
    "Action", "ActionSpec", "EpisodeConfig", "EpisodeResult",
    "EpisodeTerminationReason", "FailureSignal", "GuardrailId",
    "IterationOutcome", "PolicyStage", "PopulationStats",
    "RewardSignal", "RewardWeights", "DEFAULT_REWARD_WEIGHTS", "REWARD_SCALE",
    "RunContext", "StateVector", "StrategyRecommendation",
    "check_config_novelty", "check_direction_history", "clamp_amplitude",
    "compute_config_hash", "should_explore", "state_from_summary",
    "validate_action",
    # reward
    "RewardComponents", "RewardConfig", "compute_reward", "load_reward_config",
    # policy
    "LinUCBBandit", "PolicyRouter", "RulePolicy", "ThompsonSamplingBandit",
    # loops / features / overfitting
    "FeatureExtractor", "MetaLoopCoordinator", "OuterLoopResult",
    "AdversarialSelfPlay", "DiversityMetrics", "ExplorationBudget",
    "HoldoutGuard", "TemperatureSchedule",
    # rollout / environment
    "RolloutGate", "RolloutStage", "GateResult",
    "BUILTIN_RECIPES", "PolicySnapshot", "PolicyZoo", "ScenarioRecipe", "SimulationEnv",
    # analysis
    "CUSUMDetector", "VarianceShiftDetector", "Changepoint",
    "CausalAttributor", "CausalEffect",
    "MinedPattern", "PatternMiner",
    "generate_dashboard",
    # DPO pipeline
    "DIMENSIONS", "DIMENSION_WEIGHTS", "QualityDim",
    "ResponseEvaluator", "ResponseQuality",
    "ExtractionResult", "PreferenceExtractor", "PreferencePair",
    "DPOModel", "DPOTrainer", "DPOTrainingConfig", "DPOTrainingResult",
    "DPOPolicy", "StrategyPreference",
]
