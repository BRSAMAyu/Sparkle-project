#!/usr/bin/env python3
"""Export dependency snapshot for Python, Go, and Flutter manifests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


_REQ_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)")
_GO_REQUIRE_PATTERN = re.compile(r"^\s*([^\s]+)\s+([^\s]+)(\s+// indirect)?\s*$")


def _parse_requirements(path: Path) -> dict[str, str]:
    deps: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _REQ_PATTERN.match(line)
        if not match:
            continue
        name = match.group(1)
        version = line[len(name):].strip() or "*"
        deps[name] = version
    return dict(sorted(deps.items()))


def _parse_go_mod(path: Path) -> dict[str, dict[str, str]]:
    direct: dict[str, str] = {}
    indirect: dict[str, str] = {}
    in_require_block = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "require (":
            in_require_block = True
            continue
        if in_require_block and stripped == ")":
            in_require_block = False
            continue
        if stripped.startswith("require ") and not in_require_block:
            stripped = stripped[len("require "):]
        elif not in_require_block:
            continue
        match = _GO_REQUIRE_PATTERN.match(stripped)
        if not match:
            continue
        name, version, indirect_marker = match.groups()
        target = indirect if indirect_marker else direct
        target[name] = version
    return {
        "direct": dict(sorted(direct.items())),
        "indirect": dict(sorted(indirect.items())),
    }


def _parse_pubspec_lock(path: Path) -> dict[str, str]:
    deps: dict[str, str] = {}
    in_packages = False
    current_name: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("packages:"):
            in_packages = True
            continue
        if not in_packages:
            continue
        if raw_line.startswith("sdks:"):
            break
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and raw_line.strip().endswith(":"):
            current_name = raw_line.strip()[:-1]
            continue
        if current_name and raw_line.startswith("    version:"):
            deps[current_name] = raw_line.split(":", 1)[1].strip().strip('"')
            current_name = None
    return dict(sorted(deps.items()))


def build_snapshot(repo_root: Path) -> dict[str, object]:
    return {
        "python": _parse_requirements(repo_root / "backend" / "requirements.txt"),
        "go": _parse_go_mod(repo_root / "backend" / "gateway" / "go.mod"),
        "flutter": _parse_pubspec_lock(repo_root / "mobile" / "pubspec.lock"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export dependency snapshot")
    parser.add_argument("--output", default="docs/contracts/dependency_snapshot.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    snapshot = build_snapshot(repo_root)
    output_path = repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Dependency snapshot exported: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
