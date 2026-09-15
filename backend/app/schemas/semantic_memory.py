from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrategyNodeResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    subject_code: str | None = None
    tags: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimilarErrorItem(BaseModel):
    id: UUID
    subject_code: str
    root_cause: str | None = None
    created_at: datetime


class ConceptBrief(BaseModel):
    id: UUID
    name: str
    description: str | None = None


class ErrorSemanticSummary(BaseModel):
    error_id: UUID
    root_cause: str | None = None
    linked_concepts: list[ConceptBrief]
    strategies: list[StrategyNodeResponse]
    similar_errors: list[SimilarErrorItem]
    metadata: dict[str, Any] | None = None
