#!/usr/bin/env python3
"""Static Rule K guard for high-risk Aurora control paths.

This guard intentionally starts narrow. It scans only the most sensitive L3
control files and blocks a small set of direct write APIs that would violate
Rule K if used from those zones.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
backend_root = repo_root / "backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


CONTROLLED_PATH_PATTERNS = (
    "backend/app/aurora/**/*.py",
    "backend/app/orchestration/experience_actuator.py",
    "backend/app/orchestration/dual_core_router.py",
    "backend/app/orchestration/routing_engine.py",
    "backend/app/services/capability_knob_governor.py",
)

RULE_Z_PATH_PATTERNS = (
    "backend/app/**/*.py",
    "backend/app/**/*.sql",
)


@dataclass(frozen=True)
class RuleKViolation:
    rule_id: str
    path: str
    line_no: int
    snippet: str
    message: str


@dataclass(frozen=True)
class ViolationRule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str


VIOLATION_RULES = (
    ViolationRule(
        rule_id="RK001",
        pattern=re.compile(r"\bProfileWriteService\b"),
        message="L3 control paths must not import or use ProfileWriteService.",
    ),
    ViolationRule(
        rule_id="RK002",
        pattern=re.compile(r"\bPreferenceService\b|\.update_(?:explicit|inferred)(?:_raw)?\s*\("),
        message="L3 control paths must not write preference data directly.",
    ),
    ViolationRule(
        rule_id="RK003",
        pattern=re.compile(
            r"\bset_explicit_preference(?:s)?\s*\(|"
            r"\bremove_explicit_preference\s*\(|"
            r"\bupdate_inferred_preference\s*\(|"
            r"\bremove_inferred_preference\s*\("
        ),
        message="L3 control paths must not call profile write helpers directly.",
    ),
    ViolationRule(
        rule_id="RK004",
        pattern=re.compile(r"\bupsert_plan_state\s*\("),
        message="L3 control paths must not write PlanState directly.",
    ),
    ViolationRule(
        rule_id="RY001",
        pattern=re.compile(r"\bMemoryInferredWriteLaneService\b|\brevoke_inferred_lane\b"),
        message="L3 control paths must not call the inferred episodic write lane directly.",
    ),
    ViolationRule(
        rule_id="RY002",
        pattern=re.compile(r"source_lane\s*=\s*[\"']inferred_extraction[\"']"),
        message="L3 control paths must not construct inferred_extraction writes inline.",
    ),
)

PGW_REPORT_GLOB = "docs/product/SPARKLE_AURORA_STAGE16_PGW_REPORT_*.md"


def is_controlled_path(path: Path, repo_root: Path) -> bool:
    rel = path.resolve().relative_to(repo_root.resolve())
    rel_text = rel.as_posix()
    for pattern in CONTROLLED_PATH_PATTERNS:
        if rel.match(pattern):
            return True
    return False


def iter_controlled_paths(repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for pattern in CONTROLLED_PATH_PATTERNS:
        for path in repo_root.glob(pattern):
            if not path.is_file() or path.suffix != ".py":
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(resolved)
    return sorted(paths)


def iter_rule_z_paths(repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for pattern in RULE_Z_PATH_PATTERNS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(resolved)
    return sorted(paths)


def resolve_scan_paths(repo_root: Path, candidates: list[str] | None) -> list[Path]:
    if not candidates:
        return iter_controlled_paths(repo_root)

    paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        raw = Path(candidate)
        path = raw if raw.is_absolute() else (repo_root / raw)
        if not path.exists() or not path.is_file() or path.suffix != ".py":
            continue
        resolved = path.resolve()
        if not is_controlled_path(resolved, repo_root):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append(resolved)
    return sorted(paths)


def scan_paths(paths: list[Path], repo_root: Path) -> list[RuleKViolation]:
    violations: list[RuleKViolation] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        for line_no, line in enumerate(content, start=1):
            for rule in VIOLATION_RULES:
                if rule.pattern.search(line):
                    violations.append(
                        RuleKViolation(
                            rule_id=rule.rule_id,
                            path=rel,
                            line_no=line_no,
                            snippet=line.strip(),
                            message=rule.message,
                        )
                    )
    return violations


def scan_rule_z_paths(paths: list[Path], repo_root: Path) -> list[RuleKViolation]:
    rule_z_rules = (
        ViolationRule(
            rule_id="RZ001",
            pattern=re.compile(r"mentioned_entity_hash.*sha1|sha1\s*\(.*mentioned_entity", re.IGNORECASE),
            message="Rule Z forbids SHA-1 based mention hashing.",
        ),
        ViolationRule(
            rule_id="RZ002",
            pattern=re.compile(r"JOIN.+mentioned_entity_hash", re.IGNORECASE),
            message="Rule Z forbids cross-user joins on mentioned_entity_hash.",
        ),
        ViolationRule(
            rule_id="RZ003",
            pattern=re.compile(
                r"\b(?:mentioned_person_name|normalized_person_name)\s*=",
                re.IGNORECASE,
            ),
            message="Rule Z forbids storing raw names as lookup-key assignments.",
        ),
    )

    violations: list[RuleKViolation] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        for line_no, line in enumerate(content, start=1):
            for rule in rule_z_rules:
                if rule.pattern.search(line):
                    violations.append(
                        RuleKViolation(
                            rule_id=rule.rule_id,
                            path=rel,
                            line_no=line_no,
                            snippet=line.strip(),
                            message=rule.message,
                        )
                    )
    return violations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Rule K write-path guardrails")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional file paths. If omitted, scans the full controlled set.",
    )
    return parser


async def _production_gray_window_violation(repo_root: Path) -> str | None:
    runtime_env = str(os.getenv("SPARKLE_ENV", "")).strip().lower()
    if runtime_env != "production":
        return None

    report_paths = sorted(repo_root.glob(PGW_REPORT_GLOB))
    if report_paths:
        return None

    try:
        from sqlalchemy import func, select

        from app.db.session import AsyncSessionLocal
        from app.models.memory import EpisodicMemory
    except Exception as exc:  # noqa: BLE001
        return f"Production PGW check could not import backend DB modules: {exc}"

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count(EpisodicMemory.id)).where(
                    EpisodicMemory.source_lane == "inferred_extraction",
                    EpisodicMemory.deleted_at.is_(None),
                )
            )
            inferred_count = int(result.scalar() or 0)
    except Exception as exc:  # noqa: BLE001
        return f"Production PGW check could not query episodic memories: {exc}"

    if inferred_count > 0:
        return (
            f"Production environment has {inferred_count} inferred_extraction rows, but no PGW report matches "
            f"{PGW_REPORT_GLOB}."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    scan_targets = resolve_scan_paths(repo_root, list(args.paths))
    rule_z_targets = iter_rule_z_paths(repo_root)
    if not scan_targets and not rule_z_targets:
        print("✅ Rule K write-path guard passed (no controlled files to scan)")
        return 0

    violations = scan_paths(scan_targets, repo_root)
    violations.extend(scan_rule_z_paths(rule_z_targets, repo_root))
    if not violations:
        production_gray_violation = asyncio.run(_production_gray_window_violation(repo_root))
        if production_gray_violation:
            print("❌ Rule K write-path guard failed.")
            print(f"- [GW001] {production_gray_violation}")
            return 1
        print(
            "✅ Rule K write-path guard passed "
            f"({len(scan_targets)} controlled files + {len(rule_z_targets)} rule-z files scanned)"
        )
        return 0

    print("❌ Rule K write-path guard failed.")
    for violation in violations:
        print(
            f"- [{violation.rule_id}] {violation.path}:{violation.line_no} "
            f"{violation.message} :: {violation.snippet}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
