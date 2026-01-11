#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path


ALLOWED_TYPES = {"reversible", "forward_only", "destructive"}
REQUIRED_KEYS = {"type", "rollback_plan", "verification_query", "owner"}


def git_changed_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_contract(lines: list[str]) -> dict[str, str]:
    contract_started = False
    values: dict[str, str] = {}
    for line in lines:
        if line.strip().startswith("# Migration Contract:"):
            contract_started = True
            continue
        if not contract_started:
            continue
        if not line.strip().startswith("#"):
            break
        match = re.match(r"#\s+([a-z_]+):\s*(.+)", line)
        if match:
            key = match.group(1).strip()
            values[key] = match.group(2).strip()
    return values


def validate_contract(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    contract = parse_contract(lines)
    missing = REQUIRED_KEYS - contract.keys()
    errors = []
    if missing:
        errors.append(f"{path}: missing keys: {', '.join(sorted(missing))}")
        return errors
    if contract["type"] not in ALLOWED_TYPES:
        errors.append(f"{path}: invalid type '{contract['type']}'")
    if contract["type"] == "destructive":
        if contract["rollback_plan"].lower() in {"n/a", "na", "none"}:
            errors.append(f"{path}: destructive requires rollback_plan")
        if contract["verification_query"].lower() in {"n/a", "na", "none"}:
            errors.append(f"{path}: destructive requires verification_query")
    return errors


def main() -> int:
    base_ref = os.getenv("BASE_REF", "origin/main")
    changed = git_changed_files(base_ref)
    migration_files = [
        Path(p)
        for p in changed
        if p.startswith("backend/alembic/versions/") and p.endswith(".py")
    ]

    if not migration_files:
        print("No changed migration files.")
        return 0

    errors: list[str] = []
    for path in migration_files:
        errors.extend(validate_contract(path))

    if errors:
        for err in errors:
            print(err)
        return 1

    print("Migration contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
