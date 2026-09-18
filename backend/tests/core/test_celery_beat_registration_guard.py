"""EI-02 守卫：beat 调度声明的每个任务名必须出现在 worker 的任务注册表中。

背景：worker 启动时只 import `celery_app.conf.include` 列出的模块。若某任务被
beat_schedule 声明、但其定义模块不在 include 里，worker 加载不到它 —— beat 投递的
消息到达后按 "unregistered task" 被静默丢弃（acks_late 也无法挽回）。历史上
`tasks.community.send_checkin_reminders`（群组打卡提醒）正是因此全链路静默失效。

本测试模拟 worker 启动：导入 include 的全部模块 + 触发 `setup_periodic_tasks` 信号，
然后断言 beat_schedule 与任务注册表全匹配。任何"调度了但没人注册"的新任务都会在此被拦下。
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# 模拟 worker 的导入环境：生产镜像 WORKDIR=/app（backend 根）。
# EI-11 已修：include 统一为 `app.workers.signals_learning_worker` 全路径，
# 不再依赖顶层 `workers` 包（backend/workers/ 已删除）。
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.celery_schedule import setup_periodic_tasks  # noqa: E402
from app.core.celery_app import celery_app  # noqa: E402


def _import_include_module(module_path: str) -> ModuleType:
    """导入一个 include 模块。

    EI-11 修复后 include 全部为 app.* 全路径；文件路径回退保留作安全网
    （历史：pytest 进程里 conftest 把 `backend/app` 插入 sys.path 前排时，
    顶层名 `workers` 会被 `app.workers` 抢占，双根歧义下 importlib 无法
    导入真正的顶层包，需按 backend 根的文件路径显式加载）。
    """
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError:
        file_path = BACKEND_ROOT.joinpath(*module_path.split(".")).with_suffix(".py")
        if not file_path.exists():
            raise
        spec = importlib.util.spec_from_file_location(
            module_path.replace(".", "_") + "_guard_load", file_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _registered_task_names() -> set[str]:
    for module_path in celery_app.conf.include:
        _import_include_module(module_path)
    # 幂等：镜像 on_after_configure 信号的行为，覆盖信号未连接的部署形态。
    setup_periodic_tasks(celery_app)
    return set(celery_app.tasks)


def test_every_beat_scheduled_task_is_registered_in_worker() -> None:
    scheduled_tasks: dict[str, list[str]] = {}
    for entry_name, entry in celery_app.conf.beat_schedule.items():
        scheduled_tasks.setdefault(str(entry["task"]), []).append(entry_name)

    registered = _registered_task_names()

    missing = {task: entries for task, entries in scheduled_tasks.items() if task not in registered}
    assert not missing, (
        "beat 调度引用了未注册任务（消息会被 worker 静默丢弃），"
        f"请把定义模块加入 celery_app.conf.include: {missing}"
    )


def test_community_checkin_reminders_task_is_registered() -> None:
    """EI-02 回归锚点：群组打卡提醒任务必须随 worker 注册。"""
    registered = _registered_task_names()

    assert "tasks.community.send_checkin_reminders" in registered
