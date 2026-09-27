"""V3-FIX-510 回归钉：call-arg 族真路径修复（summarization rpush ex=、spine redis kwarg）。

mypy 批十基线（76）中的 5 条 call-arg 全部为活路径参数错位，修复于本批：
- photons.py:224 record_transaction metadata=→extra_data=（mypy 静态钉即足）
- correction_feedback.py:526 record_user_correction 两 kwarg→reason=/source=（同上）
- summarization_worker.py:324 rpush(ex=)→rpush+expire（本文件运行时钉）
- file_processing_orchestrator.py:118 get_spine_orchestrator(redis=)→redis_client=（本文件运行时钉）

后两处修前被 `except Exception`/`except (TypeError, RedisError)` 吞掉——功能
静默全死（总结日志队列恒空、Spine 文件信号恒不发），且两模块零既有测试，
故补运行时钉防回归；kwargs 回归同时仍被 mypy call-arg 静态覆盖。
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.orchestration.summarization_worker import SummarizationWorker
from app.signals import spine_orchestrator as spine_module


class _FakeAsyncRedis:
    """模拟 redis.asyncio 真实签名：rpush 只有 (name, *values)，多余 kwarg 即 TypeError。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def rpush(self, name: str, *values: object) -> int:
        self.calls.append(("rpush", (name, *values)))
        return len(values)

    async def expire(self, name: str, seconds: int) -> bool:
        self.calls.append(("expire", (name, seconds)))
        return True


@pytest.mark.asyncio
async def test_log_summary_pushes_entry_and_applies_ttl():
    """_log_summary：修前 rpush(ex=86400) TypeError 被吞、队列恒空；修后推入+TTL 两调用都在。"""
    fake = _FakeAsyncRedis()
    worker = SummarizationWorker(redis_client=fake, worker_id="wt777-test")

    await worker._log_summary("session-1", "总结内容", [{"a": 1}])

    rpush_calls = [c for c in fake.calls if c[0] == "rpush"]
    assert len(rpush_calls) == 1, f"exactly one rpush must fire, got: {fake.calls}"
    name, payload = rpush_calls[0][1]
    assert name == "logs:summarization"
    entry = json.loads(payload)
    assert entry["session_id"] == "session-1"
    assert entry["summary"] == "总结内容"
    assert entry["worker_id"] == "wt777-test"
    assert entry["original_length"] == 1
    assert ("expire", ("logs:summarization", 86400)) in fake.calls, "24h TTL must be applied after push"


def test_get_spine_orchestrator_accepts_redis_client_kwarg():
    """get_spine_orchestrator：真实形参 redis_client——修前 redis= kwarg TypeError。"""
    sentinel = MagicMock(name="redis_client")
    try:
        spine = spine_module.get_spine_orchestrator(redis_client=sentinel)
        assert spine is spine_module._spine_orchestrator
    finally:
        spine_module.reset_spine_orchestrator()
        assert spine_module._spine_orchestrator is None
