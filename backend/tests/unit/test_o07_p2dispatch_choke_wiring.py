"""O-07 P2DISPATCH · 统一投递面接线测试（直发点收口 + 背压生效断言）.

O-07 只在 ``celery_dispatch.dispatch_task_async``（投递 choke point）上有队列
背压；worker 侧自续任务曾以 12+ 处直发 ``send_task``/``.delay`` 绕过它。
P2DISPATCH 把全部直发点改接统一投递面。本文件断言：

- 新面 ``submit_task_sync`` / ``submit_task_async``：超限丢弃（不 send_task、
  drops 指标）、未超限照常投递、探测失败有界降级（probe_failures）；
- 同步孪生 ``check_queue_backpressure_sync`` 与 async 版策略同形
  （共用 get_queue_limit / 指标 / 裁决，仅探测通道不同）；
- ``schedule_long_task`` 契约保持：被丢弃/失败 → ``RuntimeError``
  （调用方 DB-persist fallback 语义不变）；
- 代表性改造点（async fire-and-forget / 事件消费者）在背压超限时不再发出
  消息且不抛异常（丢弃与既有失败语义同形）；
- 静态守卫：``app/`` 下除登记保留点外禁止直发 ``send_task``/``.delay``/
  ``.apply_async``（防止未来新增漏防线）。

无 .env 环境：全部通过 monkeypatch.setattr(settings, ...) 注入（setattr
fixture 模式，与 test_o07_queue_backpressure.py 一致）；探测经
``_llen_via_celery`` / ``_llen_off_loop`` 桩注入，不触网。
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.core import queue_backpressure as qbp

_APP_ROOT = Path(__file__).resolve().parents[2] / "app"

# 登记保留的直发点（REPORT「特殊语义登记」）：
# - users.py purge_deleted_account：30 天 ETA 任务，背压丢弃 = 静默取消 GDPR
#   硬删除，语义不可接受；每用户注销 1 条无洪泛面。
# - celery_dispatch.py 是投递面本体（内部 send_task 是唯一合法出口）。
_DIRECT_DISPATCH_ALLOWLIST = {
    "app/api/v1/users.py",
    "app/core/celery_dispatch.py",
}

_DIRECT_DISPATCH_PATTERN = re.compile(r"celery_app\.send_task\(|\.delay\(|\.apply_async\(")


def _patch_caps(monkeypatch, caps_json: str = '{"default": 5}') -> None:
    monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)
    monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", caps_json)


class TestSubmitTaskSync:
    """P2 新面：同步上下文投递（worker 任务体 / sync 服务方法）。"""

    def test_over_cap_drops_and_records_metric(self, monkeypatch):
        _patch_caps(monkeypatch)

        def _over(_queue):
            return 99

        monkeypatch.setattr(qbp, "_llen_via_celery", _over)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_sync

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        before = qbp.QUEUE_BACKPRESSURE_DROPS_TOTAL.labels(queue="default")._value.get()
        result = submit_task_sync("app.core.celery_tasks.spine_snapshot_task", args=("u1",), queue="default")
        assert result is None
        sent.assert_not_called()  # 丢弃 = 消息不入队（漏防线被掐断）
        after = qbp.QUEUE_BACKPRESSURE_DROPS_TOTAL.labels(queue="default")._value.get()
        assert after == before + 1

    def test_over_cap_drops_without_send_sync_probe(self, monkeypatch):
        _patch_caps(monkeypatch)

        def _over(_queue):
            return 99

        monkeypatch.setattr(qbp, "_llen_via_celery", _over)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_sync

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        result = submit_task_sync("app.core.celery_tasks.spine_snapshot_task", args=("u1",), queue="default")
        assert result is None
        sent.assert_not_called()

    def test_under_cap_sends_with_queue_and_ignore_result(self, monkeypatch):
        _patch_caps(monkeypatch)

        def _under(_queue):
            return 2

        monkeypatch.setattr(qbp, "_llen_via_celery", _under)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_sync

        sent = MagicMock(return_value=MagicMock(id="task-1"))
        monkeypatch.setattr(celery_app, "send_task", sent)

        result = submit_task_sync("generate_embedding", args=("node-1",), queue="high_priority")
        assert result is not None
        assert result.id == "task-1"
        assert sent.call_count == 1
        kwargs = sent.call_args.kwargs
        assert kwargs["queue"] == "high_priority"
        assert kwargs["ignore_result"] is True

    def test_probe_failure_degrades_bounded_allow(self, monkeypatch):
        _patch_caps(monkeypatch)

        def _boom(_queue):
            raise ConnectionError("broker down")

        monkeypatch.setattr(qbp, "_llen_via_celery", _boom)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_sync

        sent = MagicMock(return_value=MagicMock(id="task-2"))
        monkeypatch.setattr(celery_app, "send_task", sent)

        before = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="default")._value.get()
        result = submit_task_sync("some_task", queue="default")
        assert result is not None  # 有界降级：探测失败放行（broker 挂则 send_task 自败）
        after = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="default")._value.get()
        assert after == before + 1
        sent.assert_called_once()


class TestSubmitTaskAsync:
    """P2 新面：需要 task_id 的异步投递（process_stored_file 等结果路径）。"""

    async def test_over_cap_returns_none_without_send(self, monkeypatch):
        _patch_caps(monkeypatch)

        async def _over(_queue):
            return 99

        monkeypatch.setattr(qbp, "_llen_off_loop", _over)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_async

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        result = await submit_task_async(
            "process_stored_file",
            kwargs={"file_id": "f1"},
            queue="default",
        )
        assert result is None
        sent.assert_not_called()

    async def test_under_cap_returns_result_for_task_id(self, monkeypatch):
        _patch_caps(monkeypatch)

        async def _under(_queue):
            return 1

        monkeypatch.setattr(qbp, "_llen_off_loop", _under)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import submit_task_async

        sent = MagicMock(return_value=MagicMock(id="task-9"))
        monkeypatch.setattr(celery_app, "send_task", sent)

        result = await submit_task_async("process_stored_file", kwargs={"file_id": "f1"}, queue="default")
        assert result is not None
        assert result.id == "task-9"
        sent.assert_called_once()


class TestSyncTwinParity:
    """同步孪生与 async 版策略同形（disabled 短路 / 探测失败记账）。"""

    def test_disabled_flag_allows_without_probe(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", False)

        def _must_not_probe(_queue):
            raise AssertionError("disabled 时不得探测")

        monkeypatch.setattr(qbp, "_llen_via_celery", _must_not_probe)
        decision = qbp.check_queue_backpressure_sync("default")
        assert decision.allowed is True
        assert decision.reason == "disabled"

    def test_probe_failure_records_and_allows(self, monkeypatch):
        _patch_caps(monkeypatch)

        def _boom(_queue):
            raise ConnectionError("down")

        monkeypatch.setattr(qbp, "_llen_via_celery", _boom)
        before = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="default")._value.get()
        decision = qbp.check_queue_backpressure_sync("default")
        assert decision.allowed is True
        assert decision.reason == "probe_failed"
        after = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="default")._value.get()
        assert after == before + 1


class TestScheduleLongTaskContract:
    """schedule_long_task 契约保持：成功返回 task_id；被拒/失败抛 RuntimeError。"""

    def test_over_cap_raises_runtime_error(self, monkeypatch):
        _patch_caps(monkeypatch, '{"low_priority": 5}')

        def _over(_queue):
            return 5

        monkeypatch.setattr(qbp, "_llen_via_celery", _over)

        from app.core.celery_app import celery_app, schedule_long_task

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        with pytest.raises(RuntimeError):
            schedule_long_task(
                "app.core.celery_tasks.persist_simulation_run",
                kwargs={"user_id": "u1"},
                queue="low_priority",
            )
        sent.assert_not_called()  # 丢弃路径同样不得入队

    def test_under_cap_returns_task_id(self, monkeypatch):
        _patch_caps(monkeypatch, '{"low_priority": 5}')

        def _under(_queue):
            return 1

        monkeypatch.setattr(qbp, "_llen_via_celery", _under)

        from app.core.celery_app import celery_app, schedule_long_task

        sent = MagicMock(return_value=MagicMock(id="tid-7"))
        monkeypatch.setattr(celery_app, "send_task", sent)

        task_id = schedule_long_task(
            "app.core.celery_tasks.persist_simulation_run",
            kwargs={"user_id": "u1"},
            queue="low_priority",
        )
        assert task_id == "tid-7"
        sent.assert_called_once()


class TestRepresentativeSiteWiring:
    """代表性改造点：背压超限时生产代码不再发消息且不抛异常（丢弃同失败语义）。"""

    async def test_milestone_handler_dropped_when_over_cap(self, monkeypatch):
        _patch_caps(monkeypatch)

        async def _over(_queue):
            return 99

        monkeypatch.setattr(qbp, "_llen_off_loop", _over)

        from app.core.celery_app import celery_app
        from app.services.milestone_handler import MilestoneHandler

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        handler = MilestoneHandler(db=None)
        # 不得抛异常（丢弃与既有失败语义同形：warning + 跳过）
        await handler._trigger_galaxy_update(
            user_id=None,  # type: ignore[arg-type]
            plan_id=None,  # type: ignore[arg-type]
            milestone={"id": "ms-1", "title": "t"},
        )
        sent.assert_not_called()

    async def test_group_file_consumer_dropped_when_over_cap(self, monkeypatch):
        _patch_caps(monkeypatch)

        async def _over(_queue):
            return 99

        monkeypatch.setattr(qbp, "_llen_off_loop", _over)

        from app.core.celery_app import celery_app
        from app.services.group_file_event_consumer import GroupFileEventConsumer

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        consumer = GroupFileEventConsumer(event_bus=None)  # type: ignore[arg-type]
        await consumer.handle_event(
            {
                "event_type": "group.file.shared",
                "group_id": "g1",
                "file_id": "f1",
                "shared_by_user_id": "u1",
            }
        )
        sent.assert_not_called()

    async def test_group_file_consumer_dispatches_when_under_cap(self, monkeypatch):
        _patch_caps(monkeypatch)

        async def _under(_queue):
            return 1

        monkeypatch.setattr(qbp, "_llen_off_loop", _under)

        from app.core.celery_app import celery_app
        from app.services.group_file_event_consumer import GroupFileEventConsumer

        sent = MagicMock(return_value=MagicMock(id="t"))
        monkeypatch.setattr(celery_app, "send_task", sent)

        consumer = GroupFileEventConsumer(event_bus=None)  # type: ignore[arg-type]
        await consumer.handle_event(
            {
                "event_type": "group.file.deleted",
                "group_id": "g1",
                "file_id": "f1",
            }
        )
        assert sent.call_count == 1
        kwargs = sent.call_args.kwargs
        assert kwargs["queue"] == "default"
        assert kwargs["kwargs"] == {"group_id": "g1", "file_id": "f1"}


class TestStaticNoDirectDispatchGuard:
    """静态守卫：app/ 下禁止新增直发点（登记保留清单之外）。"""

    def test_no_direct_dispatch_outside_allowlist(self):
        violations: list[str] = []
        for path in sorted(_APP_ROOT.rglob("*.py")):
            rel = "app/" + path.relative_to(_APP_ROOT).as_posix()
            if rel in _DIRECT_DISPATCH_ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if line.strip().startswith("#"):
                    continue
                if _DIRECT_DISPATCH_PATTERN.search(line):
                    violations.append(f"{rel}:{lineno}: {line.strip()}")
        assert violations == [], "发现绕过统一投递面的直发点（见 REPORT 登记规则）:\n" + "\n".join(violations)
