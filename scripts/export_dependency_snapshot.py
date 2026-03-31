#!/usr/bin/env python3
"""Export dependency snapshot for Python, Go, and Flutter manifests."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

_REQ_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)")
_GO_REQUIRE_PATTERN = re.compile(r"^\s*([^\s]+)\s+([^\s]+)(\s+// indirect)?\s*$")


def _parse_requirements(path: Path) -> dict[str, str]:
    deps: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "--")):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            match = _REQ_PATTERN.match(line)
            if not match:
                continue
            name = match.group(1)
            version = line[len(name):].strip() or "*"
            deps[name] = version
            continue

        name = requirement.name
        if requirement.extras:
            name = f"{name}[{','.join(sorted(requirement.extras))}]"
        version = str(requirement.specifier) or "*"
        if requirement.marker is not None:
            version = f"{version} ; {requirement.marker}" if version != "*" else f"* ; {requirement.marker}"
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


def _run_command(cmd: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _format_replaced_version(version: str, replace: dict[str, object] | None) -> str:
    if not replace:
        return version
    replace_path = str(replace.get("Path", "")).strip()
    replace_version = str(replace.get("Version", "")).strip()
    replacement = replace_path
    if replace_version:
        replacement = f"{replacement} {replace_version}".strip()
    if version and version != "*":
        return f"{version} => {replacement}".strip()
    return f"=> {replacement}".strip()


def _build_go_snapshot_from_tool(repo_root: Path) -> dict[str, dict[str, str]] | None:
    raw = _run_command(["go", "mod", "edit", "-json"], cwd=repo_root / "backend" / "gateway")
    if not raw:
        return None

    payload = json.loads(raw)
    direct: dict[str, str] = {}
    indirect: dict[str, str] = {}
    replacements: dict[tuple[str, str | None], dict[str, object]] = {}
    for item in payload.get("Replace") or []:
        old = item.get("Old", {})
        old_path = str(old.get("Path", "")).strip()
        old_version = str(old.get("Version", "")).strip() or None
        if old_path:
            replacements[(old_path, old_version)] = item.get("New", {})
            replacements[(old_path, None)] = item.get("New", {})

    for item in payload.get("Require") or []:
        name = str(item.get("Path", "")).strip()
        if not name:
            continue
        version = str(item.get("Version", "")).strip() or "*"
        replacement = replacements.get((name, version)) or replacements.get((name, None))
        formatted = _format_replaced_version(version, replacement)
        target = indirect if bool(item.get("Indirect")) else direct
        target[name] = formatted
    return {
        "direct": dict(sorted(direct.items())),
        "indirect": dict(sorted(indirect.items())),
    }


def _build_flutter_snapshot_from_tool(repo_root: Path) -> dict[str, str] | None:
    mobile_dir = repo_root / "mobile"
    raw = _run_command(["dart", "pub", "deps", "--json"], cwd=mobile_dir)
    if not raw:
        raw = _run_command(["flutter", "pub", "deps", "--json"], cwd=mobile_dir)
    if not raw:
        return None

    payload = json.loads(raw)
    deps: dict[str, str] = {}
    for package in payload.get("packages", []):
        name = str(package.get("name", "")).strip()
        if not name or package.get("kind") == "root":
            continue
        deps[name] = str(package.get("version", "")).strip() or "0.0.0"
    return dict(sorted(deps.items()))


def build_snapshot(repo_root: Path) -> dict[str, object]:
    go_snapshot = _build_go_snapshot_from_tool(repo_root)
    flutter_snapshot = _parse_pubspec_lock(repo_root / "mobile" / "pubspec.lock")
    flutter_snapshot.update(_build_flutter_snapshot_from_tool(repo_root) or {})
    return {
        "python": _parse_requirements(repo_root / "backend" / "requirements.txt"),
        "go": go_snapshot or _parse_go_mod(repo_root / "backend" / "gateway" / "go.mod"),
        "flutter": flutter_snapshot,
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
