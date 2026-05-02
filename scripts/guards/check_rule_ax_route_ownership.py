#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ROUTE_TIER_RE = re.compile(r"route-tier:\s*(public|authed|internal|deprecated)")
IGNORE_RE = re.compile(r"rule-ax:\s*ignore\s+.+", re.IGNORECASE)
PY_ROUTE_RE = re.compile(r"^\s*@(?:app|router)\.(?:get|post|put|patch|delete)\(")
GO_ROUTE_RE = re.compile(
    r"(^\s*\w+\s*:=\s*\w+\.Group\()|(?<!zap)\.\s*(?:GET|POST|PUT|PATCH|DELETE|Any)\s*\(|(\bNoRoute\s*\()"
)


def _scan_python_routes(path: Path) -> list[tuple[int, str]]:
    routes: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if PY_ROUTE_RE.search(line):
            routes.append((lineno, line))
    return routes


def _scan_go_routes(path: Path) -> list[tuple[int, str]]:
    routes: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if GO_ROUTE_RE.search(line):
            routes.append((lineno, line))
    return routes


def _adjacent_comments(lines: list[str], lineno: int) -> list[str]:
    comments: list[str] = []
    for neighbor in (lineno - 1, lineno + 1):
        if neighbor < 1 or neighbor > len(lines):
            continue
        stripped = lines[neighbor - 1].strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            comments.append(stripped)
    return comments


def _default_ref(repo_root: Path) -> str | None:
    try:
        return (
            subprocess.run(
                ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                check=True,
                capture_output=True,
                text=True,
                cwd=repo_root,
            )
            .stdout.strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_diff(repo_root: Path, args: list[str]) -> str:
    try:
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _parse_changed_lines(diff_text: str) -> dict[str, set[int] | None]:
    """Parse unified diff and return exact line numbers of added/modified lines (not hunk ranges)."""
    changed: dict[str, set[int] | None] = {}
    current_file: str | None = None
    current_new_lineno: int = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            changed.setdefault(current_file, set())
            continue
        if line.startswith("@@ "):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                current_new_lineno = int(match.group(1))
            continue
        if current_file is None:
            continue
        if line.startswith("-"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            bucket = changed.setdefault(current_file, set())
            if bucket is not None:
                bucket.add(current_new_lineno)
        if not line.startswith("-"):
            current_new_lineno += 1
    return changed


def _changed_lines(repo_root: Path) -> dict[str, set[int] | None] | None:
    default_ref = _default_ref(repo_root)
    if not default_ref:
        return None
    try:
        merge_base = (
            subprocess.run(
                ["git", "merge-base", "HEAD", default_ref],
                check=True,
                capture_output=True,
                text=True,
                cwd=repo_root,
            )
            .stdout.strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    changed: dict[str, set[int] | None] = {}
    diff_commands = [
        [
            "git",
            "diff",
            "--unified=0",
            f"{merge_base}...HEAD",
            "--",
            "backend/gateway",
            "backend/app/api",
        ],
        [
            "git",
            "diff",
            "--cached",
            "--unified=0",
            "--",
            "backend/gateway",
            "backend/app/api",
        ],
        [
            "git",
            "diff",
            "--unified=0",
            "--",
            "backend/gateway",
            "backend/app/api",
        ],
    ]
    for command in diff_commands:
        for path, lines in _parse_changed_lines(_run_diff(repo_root, command)).items():
            bucket = changed.setdefault(path, set())
            if bucket is not None and lines is not None:
                bucket.update(lines)

    status_output = _run_diff(
        repo_root,
        ["git", "status", "--porcelain", "--", "backend/gateway", "backend/app/api"],
    )
    for raw_line in status_output.splitlines():
        if not raw_line.startswith("?? "):
            continue
        changed[raw_line[3:].strip()] = None

    return changed


def scan_rule_ax(*, repo_root: Path | None = None, diff_only: bool = True) -> list[str]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    changed = _changed_lines(repo_root) if diff_only else None
    candidate_paths = sorted(
        list((repo_root / "backend" / "gateway").rglob("*.go"))
        + list((repo_root / "backend" / "app" / "api").rglob("*.py"))
    )
    violations: list[str] = []
    for path in candidate_paths:
        rel = path.relative_to(repo_root).as_posix()
        if changed is not None and rel not in changed:
            continue
        if path.name.endswith("_test.go"):
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        routes = _scan_go_routes(path) if path.suffix == ".go" else _scan_python_routes(path)
        changed_lines = None if changed is None else changed.get(rel)
        for lineno, line in routes:
            if changed_lines is not None and lineno not in changed_lines:
                continue
            comments = _adjacent_comments(lines, lineno)
            if any(IGNORE_RE.search(comment) for comment in comments):
                continue
            if any(ROUTE_TIER_RE.search(comment) for comment in comments):
                continue
            violations.append(f"AX001 {rel}:{lineno} missing adjacent route-tier comment :: {line.strip()}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="scan all route lines instead of diff-only")
    args = parser.parse_args()

    violations = scan_rule_ax(diff_only=not args.full)
    if violations:
        mode = "FULL" if args.full else "DIFF"
        print(f"[Rule AX] FAIL ({mode})")
        for violation in violations:
            print(violation)
        return 1
    mode = "FULL" if args.full else "DIFF"
    print(f"[Rule AX] PASS ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
