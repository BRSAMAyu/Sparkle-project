"""Regression test for ISSUE-20260504-0015-I4.

Verifies that ReportReason enum values are consistent across all layers:
- Python model enum (backend/app/models/community.py)
- Python schema enum (backend/app/schemas/community.py)
- Go schema.sql enum definition
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPO_ROOT / "backend" / "app" / "models" / "community.py"
SCHEMA_PATH = REPO_ROOT / "backend" / "app" / "schemas" / "community.py"
GO_SCHEMA_PATH = REPO_ROOT / "backend" / "gateway" / "internal" / "db" / "schema.sql"
MIGRATION_PATH = REPO_ROOT / "backend" / "alembic" / "versions" / "c28_20260504_add_hate_speech_to_reportreason.py"


def _extract_python_enum_values(path: Path, class_name: str) -> set[str]:
    source = path.read_text()
    lines = source.split("\n")
    values = set()
    inside = False
    for line in lines:
        if re.match(rf"class {class_name}\(", line):
            inside = True
            continue
        if inside:
            if re.match(r"\s*class\s+\w+", line):
                break
            m = re.match(r'\s+\w+\s*=\s*["\'](\w+)["\']', line)
            if m:
                values.add(m.group(1))
    assert values, f"Could not find {class_name} in {path}"
    return values


def _extract_go_enum_values(path: Path, type_name: str) -> set[str]:
    source = path.read_text()
    pattern = rf"CREATE TYPE {type_name} AS ENUM \((.*?)\);"
    match = re.search(pattern, source, re.DOTALL)
    assert match, f"Could not find {type_name} in {path}"
    values = set(re.findall(r"'(\w+)'", match.group(1)))
    return values


def test_model_and_schema_report_reason_match():
    model_values = _extract_python_enum_values(MODEL_PATH, "ReportReason")
    schema_values = _extract_python_enum_values(SCHEMA_PATH, "ReportReasonEnum")
    assert model_values == schema_values, (
        f"Model enum {model_values} != Schema enum {schema_values}"
    )


def test_go_schema_has_hate_speech():
    go_values = _extract_go_enum_values(GO_SCHEMA_PATH, "reportreason")
    assert "HATE_SPEECH" in go_values, f"Go schema missing HATE_SPEECH: {go_values}"


def test_migration_file_exists():
    assert MIGRATION_PATH.exists(), "Migration c28 must exist to add HATE_SPEECH to DB"
    content = MIGRATION_PATH.read_text()
    assert "HATE_SPEECH" in content, "Migration must reference HATE_SPEECH"


def test_all_three_layers_have_hate_speech():
    model_values = _extract_python_enum_values(MODEL_PATH, "ReportReason")
    schema_values = _extract_python_enum_values(SCHEMA_PATH, "ReportReasonEnum")
    go_values = _extract_go_enum_values(GO_SCHEMA_PATH, "reportreason")

    assert "hate_speech" in model_values, f"Python model missing hate_speech: {model_values}"
    assert "hate_speech" in schema_values, f"Python schema missing hate_speech: {schema_values}"
    assert "HATE_SPEECH" in go_values, f"Go schema missing HATE_SPEECH: {go_values}"
