#!/usr/bin/env python3
"""
Rule BJ: Dead Import Detection

Detects Python modules in backend/app/ that have zero production imports.
A module is "dead" when no other production module imports it.

Exceptions (modules that don't need explicit imports):
- __init__.py files (re-export, transitively imported)
- Auto-discovery dirs: tools/, tasks/, api/v1/ (FastAPI/Celery/pkgutil)
- Proto-generated: gen/ (imported via nested paths like gen.agent.v1)
- Entry points: main.py, grpc_server.py, celery_app.py
- CLI scripts: files with argparse or __main__ guard
- Files with ``# rule-bj: exempt <reason>`` or ``# rule-at: orphan-by-design <reason>``
- Test files (excluded from scan entirely)

Incremental mode (default in CI): only checks files changed vs origin/HEAD.
Full mode (--full): scans all files — useful for audit.

Exit: 0 on pass, non-zero if violations found.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

EXEMPT_PATTERN = re.compile(
    r"#\s*rule-(?:bj|at)\s*:\s*(?:exempt|orphan-by-design)\s+(?P<reason>.+)"
)

AUTO_DISCOVERY_DIRS = {
    # Module-name prefixes (dots, not slashes) for auto-discovery directories
    "app.tools",
    "app.tasks",
    "app.api.v1",
    "app.api.v2",
    "app.api.internal",
    "app.gen.agent",
    "app.gen.galaxy",
    "app.gen.stt",
    "app.gen.sparkle",
    "app.gen.proto",
    "app.gen.userstate",
    "app.gen.ws",
    "app.services.analytics",
    "app.services.compliance",
    "app.services.personalization",
    "app.services.push_strategies",
    "app.services.skill_share",
    "app.services.skill_store",
}

ENTRY_POINT_MODULES = {
    # Module names that are entry points (not imported by other modules)
    "app.main",
    "app.grpc_server",
    "app.config.settings",
    "app.config.aurora",
    "app.db.session",
    "app.db.base",
    "app.agents.base_agent",
    "app.agents.enhanced_orchestrator",
    "app.agents.search_agent",
    "app.agents.specialist_agents",
    "app.aurora.llm_bridge",
    "app.aurora.signal_processor",
    "app.aurora.observability.metrics",
    "app.aurora.bayesian.learner",
    "app.aurora.bayesian.update",
    "app.aurora.decision_fns.backbone",
    "app.aurora.decision_fns.fallback",
    "app.aurora.decision_fns.materiality",
    "app.aurora.decision_fns.triggers",
    "app.core.database_pool_config",
    "app.core.galaxy_event_bridge",
    "app.core.tracing",
    "app.signals.deployment_health",
    "app.signals.domain_pack",
    "app.learning.ab_test_framework",
    "app.learning.retrieval",
    "app.learning.seed_bridge",
    "app.data.shop_seeds",
    "app.task_assistant.refresh_rules",
}

PROTO_DIRS = {
    "app.gen",
}

EXEMPT_FILES = {
    "backend/app/config/__init__.py",
    "backend/app/db/__init__.py",
    "backend/app/services/llm/__init__.py",
    "backend/app/services/__init__.py",
    "backend/app/orchestration/__init__.py",
    "backend/app/signals/__init__.py",
    "backend/app/utils/__init__.py",
    "backend/app/workers/__init__.py",
    "backend/app/working_memory/__init__.py",
    "backend/app/semantic/__init__.py",
    "backend/app/scaffolding/__init__.py",
    "backend/app/scenario_packs/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/profile/__init__.py",
    "backend/app/adapters/__init__.py",
    "backend/app/adapters/openclaw/__init__.py",
    "backend/app/task_assistant/__init__.py",
    "backend/app/task_guidance/__init__.py",
    "backend/app/tools/__init__.py",
    "backend/app/state_aggregator/__init__.py",
    "backend/app/aurora/__init__.py",
    "backend/app/causal/__init__.py",
    "backend/app/consumers/__init__.py",
    "backend/app/services/analysis/__init__.py",
    "backend/app/services/cognitive/__init__.py",
    "backend/app/services/ml/__init__.py",
    "backend/app/services/openclaw/__init__.py",
    "backend/app/services/report/__init__.py",
    "backend/app/services/simulation/__init__.py",
    "backend/app/services/theater/__init__.py",
    "backend/app/services/card_protocol/__init__.py",
}


def _is_scannable(path: Path) -> bool:
    """Check if a Python file should be scanned for dead imports."""
    if path.suffix != ".py":
        return False
    parts = path.parts
    if "__pycache__" in parts:
        return False
    if "tests" in parts or path.name.startswith("test_"):
        return False
    return True


def _module_name(path: Path, backend_app: Path) -> str:
    """Convert a file path to its Python module name."""
    rel = path.relative_to(backend_app).with_suffix("")
    return ".".join(("app", *rel.parts))


def _in_auto_discovery_dir(module: str) -> bool:
    """Check if module is in an auto-discovery directory."""
    for adir in AUTO_DISCOVERY_DIRS:
        if module.startswith(adir + ".") or module == adir:
            return True
    return False


def _is_entry_point(module: str) -> bool:
    """Check if a module is a known entry point."""
    return module in ENTRY_POINT_MODULES


def _is_proto_generated(module: str) -> bool:
    """Check if module is in a proto-generated directory (module dot-notation)."""
    for pdir in PROTO_DIRS:
        if module == pdir or module.startswith(pdir + "."):
            return True
    return False


def _is_cli_script(filepath: Path) -> bool:
    """Check if a file is a CLI script (has __main__ guard or argparse)."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return False
    return bool(
        re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', text)
        or "argparse" in text
    )


def _has_exemption_comment(filepath: Path) -> str | None:
    """Return exemption reason if file has a valid exemption comment."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None
    match = EXEMPT_PATTERN.search(text)
    if match:
        return match.group("reason").strip()
    return None


def _iter_python_files(root: Path) -> list[Path]:
    """Iterate all scannable Python files under root."""
    return sorted(p for p in root.rglob("*.py") if _is_scannable(p))


def _changed_files(repo_root: Path) -> set[Path] | None:
    """Get set of changed Python files vs origin/HEAD. Returns None if git unavailable."""
    try:
        default_ref = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
            check=True, capture_output=True, text=True, cwd=repo_root,
        ).stdout.strip()
        merge_base = subprocess.run(
            ["git", "merge-base", "HEAD", default_ref],
            check=True, capture_output=True, text=True, cwd=repo_root,
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR",
             f"{merge_base}...HEAD", "--", "backend/app/"],
            check=True, capture_output=True, text=True, cwd=repo_root,
        ).stdout.splitlines()
        # Also include unstaged/untracked
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "backend/app/"],
            check=True, capture_output=True, text=True, cwd=repo_root,
        ).stdout.splitlines()
        for line in status:
            entry = line.strip()
            if not entry:
                continue
            if entry.startswith(("M ", "A ", "R ", "C ", "?? ")):
                path_str = entry[3:].strip()
                if " -> " in path_str:
                    path_str = path_str.split(" -> ", 1)[1].strip()
                changed.append(path_str)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    resolved: set[Path] = set()
    for item in changed:
        candidate = repo_root / item.strip()
        if candidate.exists() and _is_scannable(candidate):
            resolved.add(candidate)
    return resolved if resolved else None


def _collect_import_graph(
    app_files: list[Path],
    extra_files: list[Path],
    backend_app: Path,
) -> tuple[dict[str, Path], dict[str, set[str]]]:
    """Build module->path map and module->{importers} map.

    Scans app_files for module definitions and all_files (app + extra) for imports.
    This catches imports from files outside app/ (e.g., grpc_server.py in backend/).
    """
    module_to_path: dict[str, Path] = {}
    importers: dict[str, set[str]] = {}

    for fpath in app_files:
        mod = _module_name(fpath, backend_app)
        module_to_path[mod] = fpath
        importers.setdefault(mod, set())

    all_scanned = list(app_files) + list(extra_files)

    for fpath in all_scanned:
        if fpath in app_files:
            importer_mod = _module_name(fpath, backend_app)
        else:
            # External file — use filename as importer identifier
            importer_mod = f"<root>:{fpath.name}"

        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        except Exception:
            continue

        for node in ast.walk(tree):
            targets = _resolve_import_targets(node, module_to_path)
            for target in targets:
                if fpath in app_files:
                    target_path = module_to_path.get(target)
                    if target_path and target_path != fpath:
                        importers.setdefault(target, set()).add(importer_mod)
                else:
                    importers.setdefault(target, set()).add(importer_mod)

    return module_to_path, importers


def _find_external_importers(backend_dir: Path, backend_app: Path) -> list[Path]:
    """Find Python files outside app/ that may import from app/ (e.g., grpc_server.py)."""
    extra: list[Path] = []
    # Root backend/*.py files
    for py_file in sorted(backend_dir.glob("*.py")):
        if _is_scannable(py_file) and not str(py_file).startswith(str(backend_app)):
            # Skip files that look like test scripts
            if py_file.name.startswith("test_"):
                continue
            extra.append(py_file)
    # Alembic migrations
    alembic_dir = backend_dir / "alembic"
    if alembic_dir.exists():
        for py_file in sorted(alembic_dir.rglob("*.py")):
            if _is_scannable(py_file):
                extra.append(py_file)
    return extra


def _resolve_import_targets(
    node: ast.AST, module_to_path: dict[str, Path]
) -> list[str]:
    """Extract target module names from an AST import node."""
    resolved: list[str] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name in module_to_path:
                resolved.append(alias.name)
        return resolved

    if not isinstance(node, ast.ImportFrom):
        return resolved

    module = str(node.module or "").strip()
    if not module:
        return resolved

    # Direct import: from app.services.foo import Bar
    if module in module_to_path:
        resolved.append(module)

    # Sub-module import: from app.services.foo import Bar
    # Bar could be app.services.foo.Bar if it's a module
    for alias in node.names:
        candidate = f"{module}.{alias.name}"
        if candidate in module_to_path:
            resolved.append(candidate)

    return resolved


def _collect_init_re_exports(backend_app: Path) -> set[str]:
    """Find modules re-exported by __init__.py files."""
    re_exported: set[str] = set()
    for init_path in backend_app.rglob("__init__.py"):
        if "__pycache__" in str(init_path):
            continue
        try:
            text = init_path.read_text(encoding="utf-8")
        except Exception:
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = str(node.module or "").strip()
                if module:
                    # Relative import in __init__ → resolve to absolute
                    init_dir = init_path.parent
                    parts = list(init_dir.relative_to(backend_app).parts)
                    if module.startswith("."):
                        # Handle relative imports
                        level = len(module) - len(module.lstrip("."))
                        base_parts = parts[:-level] if level <= len(parts) else []
                        rest = module.lstrip(".")
                        full_mod = "app." + ".".join(base_parts + ([rest] if rest else []))
                        re_exported.add(full_mod)
    return re_exported


def scan_dead_imports(
    *,
    repo_root: Path | None = None,
    full_scan: bool = False,
) -> list[str]:
    """Scan for dead imports. Returns list of violation messages."""
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    backend_app = repo_root / "backend" / "app"

    if not backend_app.exists():
        return [f"BJ000 backend/app directory not found at {backend_app}"]

    all_files = _iter_python_files(backend_app)
    changed = _changed_files(repo_root) if not full_scan else None

    # Determine which files to check
    if changed is not None:
        # Incremental mode: only check changed files
        files_to_check = [f for f in all_files if f in changed]
        if not files_to_check:
            return []  # No changed Python files
        mode = "incremental"
    else:
        files_to_check = all_files
        mode = "full"

    # Build import graph (including external importers from backend/ root)
    backend_dir = backend_app.parent  # backend/
    extra_files = _find_external_importers(backend_dir, backend_app)
    module_to_path, importers = _collect_import_graph(all_files, extra_files, backend_app)
    re_exported = _collect_init_re_exports(backend_app)

    violations: list[str] = []

    for fpath in files_to_check:
        rel = fpath.relative_to(repo_root).as_posix()
        mod = _module_name(fpath, backend_app)

        # --- Exception checks ---

        # __init__.py files are transitive entry points
        if fpath.name == "__init__.py":
            continue

        # Entry points
        if _is_entry_point(mod):
            continue

        # Proto-generated
        if _is_proto_generated(mod):
            continue

        # Auto-discovery directories
        if _in_auto_discovery_dir(mod):
            continue

        # CLI scripts
        if _is_cli_script(fpath):
            continue

        # Known exempt files
        if rel in EXEMPT_FILES:
            continue

        # Explicit exemption comment
        exemption_reason = _has_exemption_comment(fpath)
        if exemption_reason:
            continue

        # Re-exported by __init__.py (transitively alive)
        if mod in re_exported:
            continue

        # Check if it has any production importers (other than self)
        prod_importers = importers.get(mod, set())
        if prod_importers:
            continue

        # DEAD: zero production imports
        line_count = len(fpath.read_text(encoding="utf-8").splitlines())
        violations.append(
            f"BJ001 {rel} ({line_count} lines) has zero production imports — "
            f"add to auto-discovery dir, wire into runtime, or add '# rule-bj: exempt <reason>'"
        )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Rule BJ: Dead Import Detection")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full scan (default: incremental — changed files only)",
    )
    args = parser.parse_args()

    violations = scan_dead_imports(full_scan=args.full)

    if violations:
        print(f"[Rule BJ] FAIL ({len(violations)} dead modules)")
        for v in violations:
            print(v)
        return 1

    print("[Rule BJ] PASS — no dead imports detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
