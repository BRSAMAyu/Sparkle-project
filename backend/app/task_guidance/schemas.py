"""Stage 4 candidate primitive: TaskGuidance sidecar schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskGuidanceAudience(StrEnum):
    """Supported TaskGuidance audiences."""

    HUMAN = "human"
    AI = "ai"


class TaskGuidanceFormat(StrEnum):
    """Client-renderable TaskGuidance content formats."""

    MARKDOWN = "markdown"
    PLAINTEXT = "plaintext"


class TaskGuidance(BaseModel):
    """Cache-backed sidecar object for Stage 4 task guidance."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(description="Stable TaskGuidance sidecar ID")
    task_id: UUID = Field(description="UUID reference to the owning task")
    user_id: UUID = Field(description="UUID reference to the owning user")
    audience: TaskGuidanceAudience = Field(description="Target audience for the guidance body")
    content: str = Field(description="Rendered guidance content")
    generated_by: str = Field(description="Decision mechanism or generator label")
    policy_version: str = Field(description="Stage 4 policy/version label used at generation time")
    content_format: TaskGuidanceFormat = Field(
        default=TaskGuidanceFormat.MARKDOWN,
        description="Content format understood by downstream clients",
    )
    source_guidance_id: UUID | None = Field(
        default=None,
        description="Optional UUID reference to an upstream guidance sidecar",
    )
    source_task_updated_at: datetime | None = Field(
        default=None,
        description="Task.updated_at snapshot used to build this guidance",
    )
    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: datetime = Field(description="UTC last-write timestamp")
