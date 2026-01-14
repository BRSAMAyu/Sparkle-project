import ast
import importlib
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


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    router_path = repo_root / "app" / "api" / "v1" / "router.py"

    modules = ["app.main", "app.api.v1.router"]
    modules += [f"app.api.v1.{name}" for name in _load_v1_modules(router_path)]

    errors: list[tuple[str, Exception]] = []
    for module in modules:
        exc = _try_import(module)
        if exc:
            errors.append((module, exc))

    if errors:
        print("Startup import check failed:")
        for module, exc in errors:
            print(f"- {module}: {type(exc).__name__}: {exc}")
        return 1

    print("Startup import check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
