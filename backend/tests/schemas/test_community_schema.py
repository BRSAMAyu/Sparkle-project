"""Regression test for ISSUE-20260505-0900-I7.

Verifies that GroupInfo response schema includes the announcement field
so it is not silently discarded by Pydantic serialization.
"""
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.community import GroupInfo


def _base_group_data(**overrides):
    return {
        "id": uuid4(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "name": "Test Group",
        "description": "A test group",
        "avatar_url": None,
        "type": "squad",
        "focus_tags": ["math"],
        "deadline": None,
        "sprint_goal": None,
        "member_count": 5,
        "total_flame_power": 100,
        "today_checkin_count": 3,
        "total_tasks_completed": 10,
        "max_members": 50,
        "is_public": True,
        "join_requires_approval": False,
        **overrides,
    }


def test_group_info_includes_announcement():
    info = GroupInfo(**_base_group_data(announcement="Welcome to the group!"))
    assert info.announcement == "Welcome to the group!"


def test_group_info_announcement_defaults_to_none():
    info = GroupInfo(**_base_group_data())
    assert info.announcement is None


def test_group_info_serializes_announcement():
    serialized = GroupInfo(**_base_group_data(announcement="Important notice")).model_dump()
    assert serialized["announcement"] == "Important notice"
