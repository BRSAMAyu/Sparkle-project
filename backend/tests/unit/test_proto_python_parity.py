from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.gen import user_state_pb2
from app.state_aggregator.schema import UserStateV1


def test_generated_python_user_state_pb2_is_available() -> None:
    assert hasattr(user_state_pb2, "UserStateV1")


def test_proto_exposes_stage29_5_wire_fields() -> None:
    fields = user_state_pb2.UserStateV1.DESCRIPTOR.fields_by_name
    assert fields["active_skills_summary"].number == 17
    assert fields["achievement_summary"].number == 18
    assert fields["calendar_context"].number == 19


def test_proto_wrapper_types_match_expected_messages() -> None:
    fields = user_state_pb2.UserStateV1.DESCRIPTOR.fields_by_name
    assert fields["active_skills_summary"].message_type.name == "ActiveSkillsSummaryField"
    assert fields["achievement_summary"].message_type.name == "AchievementSummaryField"
    assert fields["calendar_context"].message_type.name == "CalendarContextField"


def test_python_schema_exposes_stage29_5_fields() -> None:
    annotations = UserStateV1.__annotations__
    assert "active_skills_summary" in annotations
    assert "achievement_summary" in annotations
    assert "calendar_context" in annotations


def test_calendar_context_keeps_struct_exam_urgency() -> None:
    exam_urgency = user_state_pb2.CalendarContextValue.DESCRIPTOR.fields_by_name["exam_urgency"]
    assert exam_urgency.message_type.full_name == "google.protobuf.Struct"


def test_user_id_and_schema_version_remain_scalar_proto_fields() -> None:
    fields = user_state_pb2.UserStateV1.DESCRIPTOR.fields_by_name
    assert fields["user_id"].type == fields["user_id"].TYPE_STRING
    assert fields["schema_version"].type == fields["schema_version"].TYPE_STRING
