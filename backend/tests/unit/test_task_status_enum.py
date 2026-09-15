"""Regression test for ISSUE-20260503-2100-I1: TaskStatus enum consistency across layers.

Validates that:
1. Python TaskStatus enum contains all 7 values including RESTORE
2. Paused/Stuck/Restore are all present
"""

import pytest
from app.models.task import TaskStatus


class TestTaskStatusEnum:

    def test_task_status_has_seven_values(self):
        """All 7 task status values should be defined."""
        values = set(TaskStatus.__members__.keys())
        assert len(values) == 7, f"Expected 7 values, got {len(values)}: {values}"

    def test_task_status_includes_paused(self):
        assert TaskStatus.PAUSED == "PAUSED"
        assert TaskStatus.PAUSED in TaskStatus.__members__.values()

    def test_task_status_includes_restore(self):
        """RESTORE was missing from PostgreSQL enum before migration c27."""
        assert TaskStatus.RESTORE == "RESTORE"
        assert TaskStatus.RESTORE in TaskStatus.__members__.values()

    def test_task_status_includes_stuck(self):
        assert TaskStatus.STUCK == "STUCK"
        assert TaskStatus.STUCK in TaskStatus.__members__.values()

    def test_task_status_original_four_still_present(self):
        """Core 4 values should still be present after additions."""
        for expected in ("PENDING", "IN_PROGRESS", "COMPLETED", "ABANDONED"):
            assert expected in TaskStatus.__members__.keys(), \
                f"Original value {expected} missing from TaskStatus"

    def test_restore_value_is_string_enum(self):
        """RESTORE must be usable as a string for DB persistence."""
        assert str(TaskStatus.RESTORE) == "RESTORE"
        assert TaskStatus.RESTORE.value == "RESTORE"
