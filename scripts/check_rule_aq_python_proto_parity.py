#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

from google.protobuf import descriptor_pb2

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.gen import user_state_pb2  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "backend/app/state_aggregator/schema.py"
PYTHON_ONLY_EXCEPTIONS = {"emotion_hint"}
PROTO_ONLY_EXCEPTIONS = {"emotion_hint_reserved"}
EXPECTED_PROTO_TYPES = {
    "user_id": ("TYPE_STRING", None, False),
    "schema_version": ("TYPE_STRING", None, False),
    "commitment_summary": ("TYPE_MESSAGE", "CommitmentSummaryField", True),
    "pending_policies": ("TYPE_MESSAGE", "PendingPoliciesSummaryField", True),
    "recent_reflections": ("TYPE_MESSAGE", "RecentReflectionsSummaryField", True),
    "recent_scenes": ("TYPE_MESSAGE", "RecentScenesSummaryField", True),
    "foresight_hint": ("TYPE_MESSAGE", "ForesightHintSummaryField", True),
    "recent_person_mentions": ("TYPE_MESSAGE", "RecentPersonMentionsField", True),
    "engagement_state": ("TYPE_MESSAGE", "EngagementStateField", True),
    "learning_state": ("TYPE_MESSAGE", "LearningStateField", True),
    "working_memory_snapshot": ("TYPE_MESSAGE", "WorkingMemorySnapshotField", True),
    "task_sufficiency_summary": ("TYPE_MESSAGE", "SufficiencySummaryField", True),
    "context_sufficiency_summary": ("TYPE_MESSAGE", "SufficiencySummaryField", True),
    "active_skills_summary": ("TYPE_MESSAGE", "ActiveSkillsSummaryField", True),
    "achievement_summary": ("TYPE_MESSAGE", "AchievementSummaryField", True),
    "calendar_context": ("TYPE_MESSAGE", "CalendarContextField", True),
    "traits_prior": ("TYPE_MESSAGE", "TraitsPriorSummaryField", True),
    "srl_phase": ("TYPE_MESSAGE", "SRLPhaseSummaryField", True),
    "metacognition_profile": ("TYPE_MESSAGE", "MetacognitionProfileField", True),
    "idiographic_summary": ("TYPE_MESSAGE", "IdiographicSummaryField", True),
    "social_signals_summary": ("TYPE_MESSAGE", "SocialSignalsSummaryField", True),
}


def _annotation_text(node: ast.AST) -> str:
    return ast.unparse(node)


def _load_python_fields() -> dict[str, tuple[str, bool]]:
    tree = ast.parse(SCHEMA_PATH.read_text(encoding="utf-8"), filename=str(SCHEMA_PATH))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "UserStateV1":
            continue
        fields: dict[str, tuple[str, bool]] = {}
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or not isinstance(
                stmt.target, ast.Name
            ):
                continue
            name = stmt.target.id
            annotation = _annotation_text(stmt.annotation)
            fields[name] = (annotation, "| None" in annotation)
        return fields
    raise RuntimeError("UserStateV1 definition not found in schema.py")


def _proto_field_shape(field_name: str) -> tuple[str, str | None, bool]:
    descriptor = user_state_pb2.UserStateV1.DESCRIPTOR.fields_by_name[field_name]
    type_name = descriptor_pb2.FieldDescriptorProto.Type.Name(descriptor.type)
    message_name = (
        descriptor.message_type.name if descriptor.message_type is not None else None
    )
    optional = descriptor.cpp_type == descriptor.CPPTYPE_MESSAGE
    return type_name, message_name, optional


def main() -> int:
    python_fields = _load_python_fields()
    proto_fields = set(user_state_pb2.UserStateV1.DESCRIPTOR.fields_by_name)

    python_comparable = {
        name for name in python_fields if name not in PYTHON_ONLY_EXCEPTIONS
    }
    proto_comparable = {
        name for name in proto_fields if name not in PROTO_ONLY_EXCEPTIONS
    }

    violations: list[str] = []
    if python_comparable != proto_comparable:
        missing_in_proto = sorted(python_comparable - proto_comparable)
        missing_in_python = sorted(proto_comparable - python_comparable)
        if missing_in_proto:
            violations.append(f"AQ001 fields missing in proto: {missing_in_proto}")
        if missing_in_python:
            violations.append(
                f"AQ002 fields missing in Python schema: {missing_in_python}"
            )

    for field_name, (
        expected_type,
        expected_message,
        expected_optional,
    ) in EXPECTED_PROTO_TYPES.items():
        if field_name not in python_comparable or field_name not in proto_comparable:
            continue
        annotation, optional = python_fields[field_name]
        if optional != expected_optional:
            violations.append(
                f"AQ003 {field_name} optional mismatch: python={optional} expected={expected_optional}"
            )
        proto_type, proto_message, proto_optional = _proto_field_shape(field_name)
        if proto_type != expected_type:
            violations.append(
                f"AQ004 {field_name} proto type mismatch: {proto_type} != {expected_type}"
            )
        if expected_message is not None and proto_message != expected_message:
            violations.append(
                f"AQ005 {field_name} proto wrapper mismatch: {proto_message} != {expected_message}"
            )
        if proto_optional != expected_optional:
            violations.append(
                f"AQ006 {field_name} proto optional mismatch: proto={proto_optional} expected={expected_optional}"
            )
        if (
            field_name not in {"user_id", "schema_version"}
            and "StateFieldEnvelope[" not in annotation
        ):
            violations.append(
                f"AQ007 {field_name} must remain a StateFieldEnvelope optional in schema.py"
            )

    if violations:
        print("[Rule AQ] FAIL")
        for item in violations:
            print(item)
        return 1

    print(
        "[Rule AQ] PASS - Python hand-written UserStateV1 matches proto-generated user_state_pb2 "
        f"(exceptions: {sorted(PYTHON_ONLY_EXCEPTIONS | PROTO_ONLY_EXCEPTIONS)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
