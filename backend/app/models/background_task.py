"""
Background Task Model
For tracking async operations like AI generation, data sync, etc.
"""
import enum

from sqlalchemy import JSON, Column, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class BackgroundTaskType(str, enum.Enum):
    """Background task types"""
    AI_GENERATION = "AI_GENERATION"
    DATA_SYNC = "DATA_SYNC"
    PLAN_GENERATION = "PLAN_GENERATION"
    GALAXY_EXPANSION = "GALAXY_EXPANSION"
    TASK_BATCH = "TASK_BATCH"


class BackgroundTaskStatus(str, enum.Enum):
    """Background task status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BackgroundTask(BaseModel):
    """Background task model for tracking async operations"""
    __tablename__ = "background_tasks"

    user_id = Column(GUID(), nullable=False, index=True)

    # Task identification
    task_type = Column(Enum(BackgroundTaskType), nullable=False)
    name = Column(String(255), nullable=False)

    # Status tracking
    status = Column(Enum(BackgroundTaskStatus), default=BackgroundTaskStatus.PENDING, nullable=False, index=True)

    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    progress_message = Column(Text, nullable=True)

    # Result and error data
    result_data = Column(JSONBCompat, nullable=True)
    error_message = Column(Text, nullable=True)

    # Related entity IDs (for linking to tasks, plans, etc.)
    related_entity_id = Column(GUID(), nullable=True)
    related_entity_type = Column(String(50), nullable=True)

    # Celery/async task ID for external job tracking
    external_task_id = Column(String(255), nullable=True, index=True)

    def __repr__(self):
        return f"<BackgroundTask(id={self.id}, type={self.task_type}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_type": self.task_type.value,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "related_entity_id": str(self.related_entity_id) if self.related_entity_id else None,
            "related_entity_type": self.related_entity_type,
            "external_task_id": self.external_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# Create indexes
from sqlalchemy import Index

Index("idx_background_tasks_user_status", BackgroundTask.user_id, BackgroundTask.status)
Index("idx_background_tasks_type", BackgroundTask.task_type)
