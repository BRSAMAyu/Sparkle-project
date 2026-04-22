#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


EXEMPTION_PATTERN = re.compile(r"#\s*rule-at:\s*orphan-by-design\s+(?P<reason>.+)")


def _is_scannable(path: Path) -> bool:
    return (
        path.suffix == ".py"
        and path.name != "__init__.py"
        and "_deprecated" not in path.parts
        and "tests" not in path.parts
    )


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if _is_scannable(path))


def _module_name(path: Path, backend_app: Path) -> str:
    rel = path.relative_to(backend_app).with_suffix("")
    return ".".join(("app", *rel.parts))


def _load_exemption_doc(exceptions_doc: Path) -> str:
    if not exceptions_doc.exists():
        return ""
    return exceptions_doc.read_text(encoding="utf-8")


def _extract_exemption_reason(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = EXEMPTION_PATTERN.search(text)
    if not match:
        return None
    return match.group("reason").strip()


def _changed_python_files(repo_root: Path) -> set[Path] | None:
    try:
        default_ref = (
            subprocess.run(
                ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                check=True,
                capture_output=True,
                text=True,
                cwd=repo_root,
            )
            .stdout.strip()
        )
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
        changed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                f"{merge_base}...HEAD",
                "--",
                "backend/app/services",
                "backend/app/consumers",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        ).stdout.splitlines()
        changed.extend(
            subprocess.run(
                ["git", "status", "--porcelain", "--", "backend/app/services", "backend/app/consumers"],
                check=True,
                capture_output=True,
                text=True,
                cwd=repo_root,
            ).stdout.splitlines()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    resolved: set[Path] = set()
    for item in changed:
        entry = item.strip()
        if not entry:
            continue
        if entry.startswith(("M ", "A ", "R ", "C ", "?? ")):
            path_str = entry[3:].strip()
            if " -> " in path_str:
                path_str = path_str.split(" -> ", 1)[1].strip()
        else:
            path_str = entry
        candidate = repo_root / path_str
        if candidate.exists() and _is_scannable(candidate):
            resolved.add(candidate)
    return resolved


def _resolve_import_targets(node: ast.AST, module_to_path: dict[str, Path]) -> list[Path]:
    resolved: list[Path] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            target = module_to_path.get(alias.name)
            if target is not None and target not in resolved:
                resolved.append(target)
        return resolved

    if not isinstance(node, ast.ImportFrom):
        return resolved

    module = str(node.module or "").strip()
    if module:
        direct = module_to_path.get(module)
        if direct is not None and direct not in resolved:
            resolved.append(direct)

    for alias in node.names:
        candidate = f"{module}.{alias.name}" if module else alias.name
        target = module_to_path.get(candidate)
        if target is not None and target not in resolved:
            resolved.append(target)
    return resolved


def scan_rule_at(*, repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    backend_app = repo_root / "backend" / "app"
    target_roots = (
        backend_app / "services",
        backend_app / "consumers",
    )
    exceptions_doc = repo_root / "docs" / "aurora" / "rule_at_exceptions.md"
    candidate_files = [
        path
        for root in target_roots
        if root.exists()
        for path in _iter_python_files(root)
    ]
    changed_candidates = _changed_python_files(repo_root)
    if changed_candidates is not None:
        candidate_files = [path for path in candidate_files if path in changed_candidates]
    module_to_path = {_module_name(path, backend_app): path for path in _iter_python_files(backend_app)}
    reverse_refs: dict[Path, set[Path]] = {path: set() for path in candidate_files}
    violations: list[str] = []
    exceptions_doc_text = _load_exemption_doc(exceptions_doc)

    for importer in _iter_python_files(backend_app):
        tree = ast.parse(importer.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            for resolved in _resolve_import_targets(node, module_to_path):
                if resolved in reverse_refs and resolved != importer:
                    reverse_refs[resolved].add(importer)

    for path in candidate_files:
        rel = path.relative_to(repo_root).as_posix()
        if rel in exceptions_doc_text:
            continue

        reason = _extract_exemption_reason(path)
        if reason:
            if rel not in exceptions_doc_text:
                violations.append(
                    f"AT002 {rel} declares orphan-by-design but docs/aurora/rule_at_exceptions.md is missing an entry"
                )
            continue

        if reverse_refs.get(path):
            continue
        violations.append(
            f"AT001 {rel} has no runtime import outside tests/_deprecated"
        )

    return violations


def main() -> int:
    violations = scan_rule_at()
    if violations:
        print("[Rule AT] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule AT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
