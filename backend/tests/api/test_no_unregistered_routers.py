"""EI-10 守卫（P3 清扫）：app/api/v1 下定义模块级 router 的文件必须被 router.py 注册。

历史问题：``health.py`` 与 ``errors.py`` 是完整但从未 include 的死 router——
health.py 的 DB 健康检查实现被 health_production.py 顶替（main.py 只借用
``set_start_time``），errors.py 的错题端点与 error_book.py（真正挂在 ``/errors``
前缀的实现）重叠。死 router 误导维护者，其端点列表还会向客户端宣传不存在的契约。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
V1_DIR = BACKEND_ROOT / "app" / "api" / "v1"

# 未注册但有意保留的模块（须注明理由）
# - router: 聚合器自身（定义 api_router）
# - _experience: 经 app/api/v1/experience/__init__.py 间接注册
#   （`from app.api.v1._experience import router` → router.py:200 include experience.router）
ALLOWLIST: set[str] = {"router", "_experience"}

_ROUTER_DEF_RE = re.compile(r"^\w*router\w*\s*=\s*APIRouter\(", re.M)


def _modules_defining_router() -> set[str]:
    mods: set[str] = set()
    for f in V1_DIR.glob("*.py"):
        if f.name == "__init__.py":
            continue
        if _ROUTER_DEF_RE.search(f.read_text(encoding="utf-8", errors="ignore")):
            mods.add(f.stem)
    return mods


def _router_py_imported_modules() -> set[str]:
    tree = ast.parse((V1_DIR / "router.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app.api.v1":
                imported.update(a.name for a in node.names)
            elif node.module.startswith("app.api.v1."):
                imported.add(node.module.rsplit(".", 1)[-1])
    return imported


def test_dead_router_files_removed() -> None:
    assert not (V1_DIR / "health.py").exists(), (
        "health.py 死 router 应删除：实现被 health_production.py 顶替；"
        "set_start_time 已迁至 health_production.py"
    )
    assert not (V1_DIR / "errors.py").exists(), (
        "errors.py 死 router 应删除：/errors 的真实实现是 error_book.py"
    )


def test_set_start_time_lives_in_health_production_and_main_imports_it() -> None:
    hp_src = (V1_DIR / "health_production.py").read_text(encoding="utf-8")
    assert "def set_start_time" in hp_src
    main_src = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.api.v1.health_production import set_start_time" in main_src


def test_every_router_module_is_registered_or_allowlisted() -> None:
    unregistered = _modules_defining_router() - _router_py_imported_modules() - ALLOWLIST
    assert not unregistered, (
        f"app/api/v1 下存在未被 router.py 注册的死 router 模块: {sorted(unregistered)}；"
        "请删除或在 ALLOWLIST 登记（注明理由）"
    )
