"""EI-11 守卫（P3 清扫）：celery include 不得引用 backend 根下的顶层 workers 包。

历史问题：``backend/workers/`` 与 ``app/workers/`` 双根并存，靠 Docker
WORKDIR=/app 同时可导入两个根。能跑，但违反仓库分层直觉，pytest 进程内
还会发生 ``workers`` 名字歧义（conftest 把 backend/app 插入 sys.path 前排，
顶层 ``import workers`` 解析到 app.workers——EI-02 守卫测试的 file-path
回退正是其现实代偿）。统一并入 ``app/workers/``。
"""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_toplevel_workers_package_removed() -> None:
    assert not (BACKEND_ROOT / "workers").exists(), (
        "backend/workers/ 顶层包应删除：signals_learning_worker 已并入 app/workers/"
    )


def test_signals_learning_worker_lives_in_app_workers() -> None:
    assert (BACKEND_ROOT / "app" / "workers" / "signals_learning_worker.py").exists()


def test_celery_include_uses_app_qualified_workers_path() -> None:
    src = (BACKEND_ROOT / "app" / "core" / "celery_app.py").read_text(encoding="utf-8")
    assert '"workers.signals_learning_worker"' not in src, (
        "celery include 仍引用顶层 workers 包（EI-11 双根）"
    )
    assert '"app.workers.signals_learning_worker"' in src
