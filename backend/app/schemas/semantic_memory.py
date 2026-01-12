from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrategyNodeResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    subject_code: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimilarErrorItem(BaseModel):
    id: UUID
    subject_code: str
    root_cause: Optional[str] = None
    created_at: datetime


class ConceptBrief(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None


class ErrorSemanticSummary(BaseModel):
    error_id: UUID
    root_cause: Optional[str] = None
    linked_concepts: List[ConceptBrief]
    strategies: List[StrategyNodeResponse]
    similar_errors: List[SimilarErrorItem]
    metadata: Optional[Dict[str, Any]] = None
