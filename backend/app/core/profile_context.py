from __future__ import annotations

"""
Profile Context - Sparkle 用户画像域统一读模型

这是 Sparkle 用户画像域的统一读接口返回值。
所有需要读取用户画像的消费方应通过
ProfileContextService.get_profile_context() 获取此对象，
而不是直接查询 UserPreferencesCenter、BehaviorPattern、UserNodeStatus 等底层模型。

数据来源：
- preferences: UserPreferencesCenter.explicit (唯一主写模型)
- knowledge_summary: UserNodeStatus + StudyRecord + KnowledgeNode
- cognitive_summary: BehaviorPattern（经 PATTERN_POLICY_MAP 映射为 policy_signals）

缓存策略：Redis，TTL 5 分钟，在偏好/知识/认知变更事件时清除
写入路径：所有偏好变更通过 ProfileWriteService (不通过此类)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.user_insight_state import BigFiveTraits, UserInsightState
from app.profile.projection_contract import UserProjectionContract


class WeakSpot(BaseModel):
    node_id: str
    node_name: str
    mastery: float
    last_attempt_at: datetime | None = None


class MasteryChange(BaseModel):
    node_id: str
    node_name: str
    old_mastery: float | None = None
    new_mastery: float | None = None
    changed_at: datetime


class ActivePattern(BaseModel):
    pattern_name: str
    pattern_type: str
    confidence: float
    policy_signals: list[str] = Field(default_factory=list)


class KnowledgeSummary(BaseModel):
    overall_mastery: float = 0.0
    weak_spots: list[WeakSpot] = Field(default_factory=list)
    recent_mastery_changes: list[MasteryChange] = Field(default_factory=list)
    active_learning_subjects: list[str] = Field(default_factory=list)


class CognitiveSummary(BaseModel):
    active_patterns: list[ActivePattern] = Field(default_factory=list)
    dominant_pattern_type: str | None = None
    risk_signals: list[str] = Field(default_factory=list)


class ProfileContext(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    preference_version: int = 0
    knowledge_summary: KnowledgeSummary = Field(default_factory=KnowledgeSummary)
    cognitive_summary: CognitiveSummary = Field(default_factory=CognitiveSummary)
    error_summary: dict[str, Any] = Field(default_factory=dict)
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)
    traits_prior: BigFiveTraits = Field(default_factory=BigFiveTraits)
    trait_observation_state: dict[str, Any] = Field(default_factory=dict)
    traits_coldstart_completed_at: datetime | None = None
    user_insight_state: UserInsightState | None = None
    user_projection_contract: UserProjectionContract | None = None
    metacognition_profile: dict[str, Any] = Field(default_factory=dict)
    metacognition_dashboard: dict[str, Any] = Field(default_factory=dict)
    metacognition_process_scaffolding: dict[str, Any] | None = None
    idiographic_summary: dict[str, Any] | None = None
    user_state_v1: dict[str, Any] | None = None

    def to_prompt_context(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
