"""
Task-document linking models.
"""
from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class TaskDocument(BaseModel):
    """Explicit document attachments for a task."""

    __tablename__ = "task_documents"
    __table_args__ = (
        UniqueConstraint("task_id", "file_id", name="uq_task_documents_task_file"),
    )

    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    linked_by = Column(String(16), nullable=False, default="user")
    source_reason = Column(String(500), nullable=True)
    fallback_action = Column(String(500), nullable=True)

    task = relationship("Task", back_populates="document_links")
    file = relationship("StoredFile")

    def __repr__(self) -> str:
        return f"<TaskDocument(task_id={self.task_id}, file_id={self.file_id}, linked_by={self.linked_by})>"


Index("idx_task_documents_task_created", TaskDocument.task_id, TaskDocument.created_at)
