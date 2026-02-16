"""
Seed Template Schemas
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TemplatePackScenarioEnum(str, Enum):
    STUDY_PLAN = "study_plan"
    DEEP_ANALYSIS = "deep_analysis"
    WRITING = "writing"


class TemplateVisibilityEnum(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    OFFICIAL = "official"


class TemplatePackStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class TemplateVersionStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TemplateSignalTypeEnum(str, Enum):
    LIKE = "like"
    SAVE = "save"
    REUSE = "reuse"
    REPORT = "report"
    DOWNVOTE = "downvote"
    ADOPT_SUCCESS = "adopt_success"


class SeedTemplatePackCreate(BaseModel):
    scenario_type: TemplatePackScenarioEnum
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    visibility: TemplateVisibilityEnum = TemplateVisibilityEnum.PRIVATE
    language: str = "zh"
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None


class SeedTemplatePackInfo(BaseModel):
    id: UUID
    scenario_type: TemplatePackScenarioEnum
    name: str
    description: str | None = None
    owner_id: UUID | None = None
    visibility: TemplateVisibilityEnum
    status: TemplatePackStatusEnum
    language: str
    tags: list[str] | None = Field(default_factory=list)
    quality_score: float | None = None
    adoption_score: float | None = None
    safety_score: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeedTemplateVersionCreate(BaseModel):
    body: str = Field(..., min_length=1)
    schema_json: dict[str, Any] | None = None
    variables_schema: dict[str, Any] | None = None
    change_log: str | None = None
    overwrite_draft: bool = True


class SeedTemplateVersionInfo(BaseModel):
    id: UUID
    template_id: UUID
    version_no: int
    status: TemplateVersionStatusEnum
    body: str
    schema_json: dict[str, Any] | None = None
    variables_schema: dict[str, Any] | None = None
    change_log: str | None = None
    quality_gate_report: dict[str, Any] | None = None
    moderation_report: dict[str, Any] | None = None
    moderation_status: str
    promotion_state: str
    created_by: UUID | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeedTemplateInfo(BaseModel):
    id: UUID
    pack_id: UUID
    name: str
    template_role: str
    current_version_id: UUID | None = None
    forked_from_template_id: UUID | None = None
    forked_from_version_id: UUID | None = None
    owner_id: UUID | None = None
    is_official: bool = False
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime
    current_version: SeedTemplateVersionInfo | None = None

    class Config:
        from_attributes = True


class SeedTemplateListItem(BaseModel):
    id: UUID
    pack_id: UUID
    name: str
    template_role: str
    current_version_id: UUID | None = None
    forked_from_template_id: UUID | None = None
    owner_id: UUID | None = None
    is_official: bool = False
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeedTemplateForkRequest(BaseModel):
    target_pack_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=240)


class SeedTemplatePublishRequest(BaseModel):
    version_id: UUID | None = None


class SeedTemplateSignalRequest(BaseModel):
    version_id: UUID | None = None
    signal_type: TemplateSignalTypeEnum
    score: float = 1.0
    meta: dict[str, Any] | None = None


class SeedTemplateSubscribeRequest(BaseModel):
    priority: int = Field(default=0, ge=0, le=100)


class SeedTemplateInstantiateRequest(BaseModel):
    version_id: UUID | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    template_instantiation_context: dict[str, Any] | None = None


class SeedTemplateInstantiateResponse(BaseModel):
    template_id: UUID
    template_version_id: UUID
    seed_template_pack: str
    seed_template_source: str
    rendered_body: str
    unresolved_variables: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedTemplateReviewDecisionRequest(BaseModel):
    note: str | None = None


class SeedTemplateSubscriptionInfo(BaseModel):
    id: UUID
    user_id: UUID
    template_id: UUID
    priority: int = 0
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
