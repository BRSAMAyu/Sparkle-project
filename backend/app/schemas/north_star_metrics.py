"""Schemas for North Star metric trend APIs."""

from __future__ import annotations

from datetime import date as date_type
from typing import Any

from pydantic import BaseModel, Field


class NorthStarMetricDefinition(BaseModel):
    key: str
    label: str
    description: str
    unit: str


class NorthStarTrendPoint(BaseModel):
    date: date_type
    exam_pass_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    exam_pass_outcome_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    seven_day_goal_completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    seven_day_goals_started: int = Field(default=0, ge=0)
    seven_day_goals_completed: int = Field(default=0, ge=0)
    first_goal_profiles_created: int = Field(default=0, ge=0)
    aurora_baselines_formed: int = Field(default=0, ge=0)
    first_plan_requests: int = Field(default=0, ge=0)
    first_tasks_completed: int = Field(default=0, ge=0)


class NorthStarTrendResponse(BaseModel):
    definitions: list[NorthStarMetricDefinition]
    summary: dict[str, Any]
    series: list[NorthStarTrendPoint]
