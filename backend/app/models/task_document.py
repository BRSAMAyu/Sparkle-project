"""
Task-document linking models.
"""
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class TaskDocument(BaseModel):
    """Explicit document attachments for a task."""

    __tablename__ = "task_documents"
    __table_args__ = (
        UniqueConstraint("task_id", "file_id", name="uq_task_documents_task_file"),
    )

    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    linked_by: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    source_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    fallback_action: Mapped[str] = mapped_column(String(500), nullable=True)

    task = relationship("Task", back_populates="document_links")
    file = relationship("StoredFile")

    __repr_fields__ = ("task_id", "file_id", "linked_by")


Index("idx_task_documents_task_created", TaskDocument.task_id, TaskDocument.created_at)
