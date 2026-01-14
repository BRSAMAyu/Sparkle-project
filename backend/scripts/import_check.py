import ast
import importlib
import os
import sys
from pathlib import Path


def _load_v1_modules(router_path: Path) -> list[str]:
    tree = ast.parse(router_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.api.v1":
            for alias in node.names:
                modules.append(alias.name)
    return modules


def _try_import(module_name: str) -> Exception | None:
    try:
        importlib.import_module(module_name)
        return None
    except Exception as exc:
        return exc


def _find_backend_root(start: Path) -> Path | None:
    for path in [start, *start.parents]:
        if (path / "app").is_dir() and (path / "alembic.ini").exists():
            return path
    return None


def main() -> int:
    backend_root = _find_backend_root(Path(__file__).resolve())
    if not backend_root:
        print("Startup import check failed: could not locate backend root (app/ + alembic.ini).")
        return 1

    sys.path.insert(0, str(backend_root))
    router_path = backend_root / "app" / "api" / "v1" / "router.py"

    modules = ["app.main", "app.api.v1.router"]
    modules += [f"app.api.v1.{name}" for name in _load_v1_modules(router_path)]

    enable_agent_graph = str(os.getenv("ENABLE_AGENT_GRAPH_V2", "")).lower() in ("1", "true", "yes")
    optional_modules = []
    if enable_agent_graph:
        optional_modules.append("app.api.v2.agent_graph")

    errors: list[tuple[str, Exception]] = []
    warnings: list[tuple[str, Exception]] = []
    for module in modules + optional_modules:
        exc = _try_import(module)
        if exc:
            if module in optional_modules:
                warnings.append((module, exc))
            else:
                errors.append((module, exc))

    if errors:
        print("Startup import check failed:")
        for module, exc in errors:
            print(f"- {module}: {type(exc).__name__}: {exc}")
        return 1

    if warnings:
        print("Startup import check warnings (optional modules):")
        for module, exc in warnings:
            print(f"- {module}: {type(exc).__name__}: {exc}")

    print("Startup import check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
