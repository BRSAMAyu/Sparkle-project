"""P2-J (daily-flow R2): lowercase task-type aliases must work on update too.

TaskCreate already normalized aliases ("learning", "error_fix", "study", ...)
through coerce_task_type; TaskUpdate accepted only canonical enum values, so
the same payload shape 422'd on a partial update. The wire format itself
(uppercase enum values, e.g. "LEARNING") is the mobile contract and must not
change.
"""

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskUpdate


@pytest.mark.parametrize("alias,expected", [
    ("learning", "LEARNING"),
    ("LEARNING", "LEARNING"),
    ("Learning", "LEARNING"),
    ("error_fix", "ERROR_FIX"),
    ("errorfix", "ERROR_FIX"),
    ("study", "LEARNING"),
    ("review", "TRAINING"),
    ("practice", "TRAINING"),
    ("homework", "PLANNING"),
])
def test_task_create_accepts_lowercase_aliases(alias, expected):
    payload = TaskCreate(title="t", type=alias, estimated_minutes=30)
    assert payload.type.value == expected


@pytest.mark.parametrize("alias,expected", [
    ("learning", "LEARNING"),
    ("error_fix", "ERROR_FIX"),
    ("reflection", "REFLECTION"),
])
def test_task_update_accepts_lowercase_aliases(alias, expected):
    payload = TaskUpdate(type=alias)
    assert payload.type is not None and payload.type.value == expected


def test_task_update_none_type_stays_none():
    assert TaskUpdate().type is None
    assert TaskUpdate(type=None).type is None


def test_task_update_rejects_unknown_type():
    with pytest.raises(ValidationError):
        TaskUpdate(type="not-a-type")


def test_canonical_uppercase_wire_format_is_unchanged():
    """The serialization contract the mobile app relies on."""
    assert TaskCreate(title="t", type="TRAINING", estimated_minutes=30).model_dump()["type"] == "TRAINING"
