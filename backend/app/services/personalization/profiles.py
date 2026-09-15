"""
策略配置数据类 - 各模块的个性化参数
"""
from dataclasses import dataclass, field


@dataclass
class PolicyExplanation:
    """Human-readable explanation for an applied policy."""

    signal: str
    effect: str
    source_pattern: str


@dataclass
class LLMProfile:
    """AI 系统策略配置"""

    system_prompt_additions: str
    verbosity_target: str
    temperature: float
    should_ask_clarifying: bool
    should_provide_examples: bool
    exploration_level: str
    tone: str
    applied_policies: list[PolicyExplanation] = field(default_factory=list)


@dataclass
class PushPolicyProfile:
    """推送系统策略配置"""

    daily_cap: int
    min_interval_minutes: int
    pressure_tolerance: float
    memory_urgency_threshold: float
    curiosity_frequency: str
    silent_during_focus: bool
    active_hours: list[int]
    timezone: str
    preference_version: int
    applied_policies: list[PolicyExplanation] = field(default_factory=list)


@dataclass
class TaskPlanProfile:
    """任务规划策略配置"""

    preferred_task_duration: int
    difficulty_gradient: float
    micro_task_friendly: bool
    exploration_ratio: float
    review_priority: str
    fragmented_time_slots: list[dict]
    applied_policies: list[PolicyExplanation] = field(default_factory=list)
