"""PHOTON-TUNE — 经济仪表日快照任务的 celery 接线断言。

形制沿用 SESSION-GC 的 test_user_session_cleanup_beat.py：只导入本任务模块，
任何环境可运行（不模仿守卫的 worker 全量冷启动导入）；include/任务名注册/
beat 单条日级条目显式 queue/task_routes 显式 queue 四条钉死。
"""

from __future__ import annotations

import importlib

from app.core.celery_app import celery_app

TASK_NAME = "tasks.economy_metrics_snapshot"
TASK_MODULE = "app.tasks.economy_metrics_snapshot"
EXPECTED_QUEUE = "low_priority"


def test_economy_snapshot_module_is_in_worker_include() -> None:
    """模块必须在 include 里（worker 启动即加载；否则 beat 消息被静默丢弃）。"""
    assert TASK_MODULE in celery_app.conf.include


def test_economy_snapshot_task_name_registers_on_import() -> None:
    """导入任务模块后，tasks.* 全名必须出现在 celery 任务注册表中。"""
    importlib.import_module(TASK_MODULE)
    assert TASK_NAME in celery_app.tasks


def test_economy_snapshot_has_single_daily_beat_entry_with_explicit_queue() -> None:
    """beat 有且仅有一条日级条目，且显式 queue（路由纪律：双处显式注册）。"""
    entries = [
        (name, entry) for name, entry in celery_app.conf.beat_schedule.items() if str(entry["task"]) == TASK_NAME
    ]
    assert len(entries) == 1, f"expect exactly one beat entry for {TASK_NAME}, got {entries}"
    _name, entry = entries[0]
    assert entry["options"]["queue"] == EXPECTED_QUEUE
    assert "schedule" in entry


def test_economy_snapshot_route_is_explicitly_registered() -> None:
    """task_routes 显式 queue 且键为真实任务名（EI-07：键不匹配即路由静默失效）。"""
    assert celery_app.conf.task_routes.get(TASK_NAME) == {"queue": EXPECTED_QUEUE}
