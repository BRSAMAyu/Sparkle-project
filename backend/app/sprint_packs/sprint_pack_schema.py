"""Pydantic schema for validating Sprint Pack JSON assets."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeNode(BaseModel):
    """A single knowledge node inside a Sprint Pack."""

    model_config = ConfigDict(extra="allow")

    node_id: str
    label: str
    exam_weight: float = Field(ge=0.0, le=1.0)
    frequency: float = Field(ge=0.0, le=1.0)
    trainability: float = Field(ge=0.0, le=1.0)
    time_cost: int = Field(ge=1)
    difficulty: int = Field(ge=1, le=5)
    minimum_pass_required: bool
    common_mistakes: list[str] = Field(default_factory=list)
    recommended_action: str = ""


class TaskCardTemplate(BaseModel):
    """Reusable task card template used by Sprint Pack plan generation."""

    model_config = ConfigDict(extra="allow")

    template_id: str
    label: str
    description: str
    steps: list[str] = Field(min_length=1)
    done_criteria: str
    duration_minutes: int = Field(ge=1)


class SprintPackV1(BaseModel):
    """Top-level Sprint Pack v1 schema."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str
    subject: str
    knowledge_nodes: list[KnowledgeNode]
    mistake_types: list[dict[str, Any]]
    question_archetypes: list[dict[str, Any]]
    paths: dict[str, Any]
    strategy_presets: dict[str, Any]
    last_24h_strategy: dict[str, Any]
    aurora_rules: dict[str, Any]
    task_card_templates: list[TaskCardTemplate] = Field(default_factory=list)
    checkpoint_rules: dict[str, Any]
