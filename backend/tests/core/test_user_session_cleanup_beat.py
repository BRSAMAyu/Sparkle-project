"""SESSION-GC — user_sessions 过期清理任务的 celery 接线断言。

全局一致性（beat 任务都必须已注册、路由键全匹配、无意外双频）由既有的
EI-02/EI-07/EI-08 守卫（tests/core/test_celery_*_hygiene*.py）覆盖；本文件
钉住本任务自身的四条接线。注意：不模仿守卫的 worker 全量冷启动导入——
该链路在本仓需要 `make proto-gen` 产物（app.gen），缺失时守卫测试整体
不可运行（基线固有状态）；本文件只导入本任务模块，任何环境可运行。
"""

from __future__ import annotations

import importlib

from app.core.celery_app import celery_app

TASK_NAME = "tasks.cleanup_expired_user_sessions"
TASK_MODULE = "app.tasks.user_session_cleanup"
EXPECTED_QUEUE = "low_priority"


def test_session_cleanup_module_is_in_worker_include() -> None:
    """模块必须在 include 里（worker 启动即加载；否则 beat 消息被静默丢弃）。"""
    assert TASK_MODULE in celery_app.conf.include


def test_session_cleanup_task_name_registers_on_import() -> None:
    """导入任务模块后，tasks.* 全名必须出现在 celery 任务注册表中。"""
    importlib.import_module(TASK_MODULE)
    assert TASK_NAME in celery_app.tasks


def test_session_cleanup_has_single_daily_beat_entry_with_explicit_queue() -> None:
    """beat 有且仅有一条日级条目，且显式 queue（路由纪律：双处显式注册）。"""
    entries = [
        (name, entry) for name, entry in celery_app.conf.beat_schedule.items() if str(entry["task"]) == TASK_NAME
    ]
    assert len(entries) == 1, f"expect exactly one beat entry for {TASK_NAME}, got {entries}"
    _name, entry = entries[0]
    assert entry["options"]["queue"] == EXPECTED_QUEUE
    assert "schedule" in entry


def test_session_cleanup_route_is_explicitly_registered() -> None:
    """task_routes 显式 queue 且键为真实任务名（EI-07：键不匹配即路由静默失效）。"""
    assert celery_app.conf.task_routes.get(TASK_NAME) == {"queue": EXPECTED_QUEUE}
