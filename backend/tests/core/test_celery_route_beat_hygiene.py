"""EI-07 / EI-08 守卫（P3 清扫）：celery 路由与 beat 计划卫生。

EI-07：task_routes 的每个键必须是任务注册表中的真实任务名——键名与任务
``name=`` 不一致时该条路由永不生效，任务静默落到 default 队列。R2 复核
（04-r2-engine-infra.md §3/§5）确认仍余 3 条 ``app.core.celery_tasks.*``
前缀键指向短名任务（generate_embedding / batch_error_analysis /
cleanup_old_data）。

EI-08：同一任务的多条 beat 条目只允许出现在"有意多频"白名单内
（早/晚成对、4 门课错峰、日/周胶囊，见 R2 §3）。参数演化期遗留的双源
重复条目（static conf.beat_schedule × celery_schedule.add_periodic_task）
必须清理。另含仓库扫描守卫：模块级 ``CELERYBEAT_SCHEDULE`` /
``beat_schedule =`` 死配置只允许出现在两个权威接线位置（R2 §3 建议，
封死死配置返潮口子）。
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.celery_schedule import setup_periodic_tasks  # noqa: E402
from app.core.celery_app import celery_app  # noqa: E402


def _cold_start_registry() -> set[str]:
    """模拟 worker 冷启动：导入 include 全部模块 + 显式触发周期任务注册。"""
    for module_path in celery_app.conf.include:
        try:
            importlib.import_module(module_path)
        except ModuleNotFoundError:
            # EI-11 历史债务：pytest 进程里顶层 `workers` 名被 conftest 的
            # sys.path 前排抢占，回退为按 backend 根的文件路径显式加载。
            file_path = BACKEND_ROOT.joinpath(*module_path.split(".")).with_suffix(".py")
            if not file_path.exists():
                raise
            spec = importlib.util.spec_from_file_location(
                module_path.replace(".", "_") + "_hygiene_load", file_path
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
    setup_periodic_tasks(celery_app)
    return set(celery_app.tasks)


def test_every_task_route_key_is_a_registered_task_name() -> None:
    """EI-07：task_routes 键与注册表全匹配。"""
    registered = _cold_start_registry()
    invalid = {k: v for k, v in celery_app.conf.task_routes.items() if k not in registered}
    assert not invalid, (
        "task_routes 存在指向不存在任务名的无效条目（路由永不生效，任务静默落 "
        f"default 队列）：{invalid}；请把键改为任务的真实 name= 或删除该条"
    )


# 有意多频白名单（R2-04 §3：早/晚成对、4 门课错峰、日/周胶囊）。
INTENTIONAL_MULTI_BEAT_TASKS = {
    "generate_daily_capsules_for_all",  # 日胶囊 + 周日深度胶囊
    "app.core.celery_tasks.pack_quality_analysis_task",  # 4 门课月度错峰
    "tasks.accountability.send_daily_reminders",  # 早 9:00 / 晚 21:00
    "tasks.community.send_checkin_reminders",  # 早 10:00 / 晚 20:00
}


def test_beat_entries_have_no_accidental_duplicate_frequency() -> None:
    """EI-08：同一任务的多条 beat 条目必须在有意多频白名单内。"""
    setup_periodic_tasks(celery_app)
    counts: dict[str, list[str]] = {}
    for entry_name, entry in celery_app.conf.beat_schedule.items():
        counts.setdefault(str(entry["task"]), []).append(entry_name)
    accidental = {
        task: entries
        for task, entries in counts.items()
        if len(entries) > 1 and task not in INTENTIONAL_MULTI_BEAT_TASKS
    }
    assert not accidental, (
        "以下任务被注册了多条 beat 条目（双频执行：浪费配额且 side-effect 型任务"
        f"双跑）：{accidental}；二选一保留（保留带 crontab/args 的确定性条目）"
    )


_AUTHORITATIVE_BEAT_MODULES = {
    BACKEND_ROOT / "app" / "core" / "celery_app.py",
    BACKEND_ROOT / "app" / "celery_schedule.py",
}
_BEAT_ASSIGN_RE = re.compile(r"^\s*(CELERYBEAT_SCHEDULE|beat_schedule)\s*=", re.M)


def test_no_module_level_beat_config_outside_authoritative_sources() -> None:
    """EI-08 附带守卫：模块级 beat 死配置一律禁止（生产 beat 从不读它）。"""
    offenders: list[str] = []
    for py in sorted((BACKEND_ROOT / "app").rglob("*.py")):
        if py in _AUTHORITATIVE_BEAT_MODULES:
            continue
        src = py.read_text(encoding="utf-8", errors="ignore")
        # 去注释行，避免命中文档性内容
        stripped = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
        if _BEAT_ASSIGN_RE.search(stripped):
            offenders.append(str(py.relative_to(BACKEND_ROOT)))
    assert not offenders, (
        "模块级 CELERYBEAT_SCHEDULE / beat_schedule = 是从未接线的死配置（生产 "
        f"beat 只读 app/core/celery_app.py 与 app/celery_schedule.py）：{offenders}；"
        "请删除，或改为 celery_schedule.setup_periodic_tasks 里的 add_periodic_task"
    )
