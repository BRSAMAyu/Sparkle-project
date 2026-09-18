"""audit.py kill-switch readiness 端点契约测试。

红证据（修复前）：端点以无参同步方式调用 `async get_readiness_report(settings)` →
调用记录器收到的实参为空、返回 coroutine 被丢弃（API 500/TypeError）。
"""
from __future__ import annotations

import pytest

from app.api.v1 import audit


@pytest.mark.asyncio
async def test_kill_switch_readiness_awaits_service_with_settings(monkeypatch) -> None:
    calls: list[tuple] = []

    class _Report:
        pass

    async def _recorder(self, settings):  # 与服务真实签名一致
        calls.append((settings,))
        return _Report()

    monkeypatch.setattr(
        audit.KillSwitchReadinessService, "get_readiness_report", _recorder
    )

    result = await audit.get_kill_switch_readiness(_admin=object())

    assert isinstance(result, _Report)
    assert len(calls) == 1
    assert calls[0][0] is audit.settings  # 必须把运行时 settings 传给服务
