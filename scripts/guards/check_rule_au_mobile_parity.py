#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "backend/app/state_aggregator/schema.py"
DART_MODEL_PATH = REPO_ROOT / "mobile/lib/core/models/user_state_models.dart"
BACKEND_ONLY_DOC_PATH = REPO_ROOT / "docs/aurora/stage35_backend_only_fields.md"
EXCEPTIONS_DOC_PATH = REPO_ROOT / "docs/aurora/rule_au_exceptions.md"
PROFILE_SCREEN = REPO_ROOT / "mobile/lib/features/user/presentation/screens/profile_screen.dart"
TRAITS_PRIOR_CARD = REPO_ROOT / "mobile/lib/features/user/presentation/widgets/traits_prior_card.dart"
SRL_PHASE_CARD = REPO_ROOT / "mobile/lib/features/user/presentation/widgets/srl_phase_badge_card.dart"
IDIOGRAPHIC_CARD = REPO_ROOT / "mobile/lib/features/user/presentation/widgets/idiographic_summary_card.dart"
MEMORY_PANEL_SCREEN = REPO_ROOT / "mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart"
ACCOUNTABILITY_DETAIL_SCREEN = (
    REPO_ROOT / "mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart"
)


RENDER_TARGETS: dict[str, tuple[tuple[Path, str], ...]] = {
    "pending_policies": (
        (ACCOUNTABILITY_DETAIL_SCREEN, "_PendingPoliciesCard(summary: dashboard.pendingPolicies)"),
    ),
    "recent_reflections": (
        (ACCOUNTABILITY_DETAIL_SCREEN, "_RecentReflectionsCard("),
        (ACCOUNTABILITY_DETAIL_SCREEN, "dashboard.recentReflections"),
    ),
    "recent_scenes": (
        (MEMORY_PANEL_SCREEN, "_buildRecentSceneTile"),
        (MEMORY_PANEL_SCREEN, "_recentScenes"),
    ),
    "foresight_hint": ((PROFILE_SCREEN, "userState.foresightHint"),),
    "engagement_state": ((PROFILE_SCREEN, "userState.engagementState"),),
    "working_memory_snapshot": ((PROFILE_SCREEN, "userState.workingMemorySnapshot"),),
    "active_skills_summary": ((PROFILE_SCREEN, "userState.activeSkillsSummary"),),
    "achievement_summary": ((PROFILE_SCREEN, "userState.achievementSummary"),),
    "traits_prior": ((TRAITS_PRIOR_CARD, "userInsightState['traits_prior']"),),
    "srl_phase": ((SRL_PHASE_CARD, "userInsightState['srl_phase']"),),
    "metacognition_profile": ((PROFILE_SCREEN, "userState.metacognitionProfile"),),
    "idiographic_summary": ((IDIOGRAPHIC_CARD, "profileContext['idiographic_summary']"),),
}


@dataclass(frozen=True)
class FieldStatus:
    name: str
    status: str
    reason: str

def parse_schema_fields(path: Path = SCHEMA_PATH) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"class UserStateV1:\n(?P<body>.*?)(?:\n@dataclass|\Z)", text, re.S)
    if not match:
        raise RuntimeError("Could not locate UserStateV1 in schema.py")

    fields: list[str] = []
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        if name in {"user_id", "schema_version"}:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            fields.append(name)
    return fields


def parse_backend_only_annotations(path: Path = DART_MODEL_PATH) -> dict[str, str]:
    annotations: dict[str, str] = {}
    pending_reason: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        comment = re.search(r"//\s*@BackendOnly:\s*(.+)", line)
        if comment:
            pending_reason = comment.group(1).strip()
            continue
        if pending_reason is None:
            continue
        field_match = re.search(r"final\s+[^;]+\s+([A-Za-z0-9_]+);", line)
        if field_match:
            annotations[camel_to_snake(field_match.group(1))] = pending_reason
            pending_reason = None
        elif line.strip():
            pending_reason = None
    return annotations


def camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def parse_doc_section(section_title: str, path: Path = BACKEND_ONLY_DOC_PATH) -> dict[str, str]:
    rows: dict[str, str] = {}
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            active = line.strip() == section_title
            continue
        if not active or not line.startswith("| `"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if not columns:
            continue
        field = columns[0].strip("` ")
        reason = columns[-1]
        rows[field] = reason
    return rows


def has_render_target(field_name: str) -> tuple[bool, str]:
    targets = RENDER_TARGETS.get(field_name)
    if not targets:
        return False, "no render mapping"
    for path, token in targets:
        text = path.read_text(encoding="utf-8")
        if token not in text:
            return False, f"missing token `{token}` in {path.relative_to(REPO_ROOT)}"
    return True, "mapped widget/screen token present"


def scan_rule_au() -> tuple[list[FieldStatus], list[str], float]:
    schema_fields = parse_schema_fields()
    backend_only = parse_backend_only_annotations()
    registry_fields = parse_doc_section("## Backend-Only Registry")
    declared_fields = parse_doc_section("## Declared Exceptions")
    exceptions_text = EXCEPTIONS_DOC_PATH.read_text(encoding="utf-8")
    violations: list[str] = []
    statuses: list[FieldStatus] = []

    for field in backend_only:
        if field not in registry_fields:
            violations.append(
                f"AU001 {field} is annotated @BackendOnly in Dart but missing from stage35_backend_only_fields.md registry"
            )
        if f"`{field}`" not in exceptions_text:
            violations.append(
                f"AU002 {field} is annotated @BackendOnly in Dart but missing from docs/aurora/rule_au_exceptions.md"
            )

    black_hole = 0
    denominator = 0
    for field in schema_fields:
        if field in declared_fields:
            statuses.append(FieldStatus(field, "declared", declared_fields[field]))
            continue
        if field in backend_only:
            statuses.append(FieldStatus(field, "backend-only", backend_only[field]))
            continue
        denominator += 1
        rendered, reason = has_render_target(field)
        if rendered:
            statuses.append(FieldStatus(field, "rendered", reason))
        else:
            black_hole += 1
            statuses.append(FieldStatus(field, "black-hole", reason))

    rate = 0.0 if denominator == 0 else black_hole / denominator
    if rate > 0.10:
        violations.append(
            f"AU003 black-hole rate {black_hole}/{denominator} = {rate:.3%} exceeds 10%"
        )
    return statuses, violations, rate


def main() -> int:
    statuses, violations, rate = scan_rule_au()
    black_holes = [status for status in statuses if status.status == "black-hole"]
    for status in statuses:
        print(f"{status.name}\t{status.status}\t{status.reason}")
    if violations:
        print("[Rule AU] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print(
        f"[Rule AU] PASS - black-hole rate={rate:.3%} black-holes={len(black_holes)} total={len(statuses)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
