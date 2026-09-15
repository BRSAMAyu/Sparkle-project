"""Regression test for ISSUE-20260503-2101-I2: Task model and schema must
include paused_at and paused_reason fields.
"""

import datetime
import pytest
from app.schemas.task import TaskDetail, TaskPause
from app.models.task import Task


class TestTaskPausedColumns:

    def test_task_model_has_paused_at_column(self):
        """SQLAlchemy Task model must have paused_at column."""
        assert hasattr(Task, "paused_at"), "Task model missing paused_at"
        col = getattr(Task, "paused_at")
        assert col is not None

    def test_task_model_has_paused_reason_column(self):
        """SQLAlchemy Task model must have paused_reason column."""
        assert hasattr(Task, "paused_reason"), "Task model missing paused_reason"
        col = getattr(Task, "paused_reason")
        assert col is not None

    def test_task_detail_schema_has_paused_at(self):
        """Pydantic TaskDetail must have paused_at field."""
        fields = TaskDetail.model_fields
        assert "paused_at" in fields, f"TaskDetail missing paused_at field. Has: {list(fields.keys())}"

    def test_task_detail_schema_has_paused_reason(self):
        """Pydantic TaskDetail must have paused_reason field."""
        fields = TaskDetail.model_fields
        assert "paused_reason" in fields, f"TaskDetail missing paused_reason field. Has: {list(fields.keys())}"

    def test_task_detail_accepts_paused_fields(self):
        """TaskDetail construction via model_construct must accept paused_at and paused_reason."""
        now = datetime.datetime(2026, 5, 3, 12, 0, 0)
        detail = TaskDetail.model_construct(
            paused_at=now,
            paused_reason="User paused",
        )
        assert detail.paused_at == now
        assert detail.paused_reason == "User paused"

    def test_task_pause_schema_accepts_reason(self):
        """TaskPause input schema must accept a reason."""
        pause = TaskPause(reason="Taking a break")
        assert pause.reason == "Taking a break"

    def test_task_pause_reason_optional(self):
        """TaskPause reason should be optional."""
        pause = TaskPause()
        assert pause.reason is None
