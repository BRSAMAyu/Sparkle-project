"""wt396 F7（P-05 轮3）· 评估引擎事件通道隔离 —— 红绿契约锁.

轮3判据（v3-output/WT391-HUNT-R3 REPORT F7）：``PersonaWorld`` 只重定向
``AsyncSessionLocal``（DB 面隔离成立），但评估运行内的真实服务链
（``TaskService.complete → capture_task_outcome → emit_outcome_recorded`` 等）
向**全局单例** ``event_bus`` 发布事件 → ``_publish_once`` 发现 ``redis is None``
就自动连 ``settings.REDIS_URL`` 并 XADD 真 ``sparkle_events``；publish 失败时
DLQ 回退路径经模块级 ``AsyncSessionLocal`` 写**真 Postgres**。在配置了可达
REDIS_URL 的机器上无人值守跑 P-05 runner = 伪 user uuid / 回拨时间线事件污染
真实 dev Redis / dev 读模型。

修法口径（卡面）：评估引擎在 PersonaWorld 生命周期内给全局 event_bus 单例注入
隔离通道（内存 stub redis + connect/DLQ 中和），退出时恢复——**生产路径零改动**。

红测判据：一次最小评估运行（baseline 组 + 内在自发重启完成一个待办）期间，
``EventBus.connect``（真实 REDIS_URL 拨号入口）与 DLQ 的真实 DB 工厂
（``app.core.event_bus.AsyncSessionLocal`` 绑定）**零触达**；同时 stub 通道
确实承接了评估事件（隔离 ≠ 静默丢弃）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.proactive_longitudinal.engine import PersonaWorld
from tests.proactive_longitudinal.persona import build_population, with_decision_script

pytestmark = pytest.mark.asyncio


def _baseline_persona_with_intrinsic_day0() -> Any:
    specs = build_population(seed=20260925, per_arc=4, days=8)
    for spec in specs:
        if not spec.persona_id.startswith("stalled"):
            continue
        if 0 in spec.intrinsic_restart_days:
            return spec
    raise AssertionError("no stalled persona with intrinsic restart on day 0")


async def test_eval_run_never_dials_real_redis_or_real_dlq_db(monkeypatch: pytest.MonkeyPatch):
    """评估运行全程：真实 Redis 拨号 0 次、真实 DLQ DB 工厂触达 0 次、事件进隔离 stub."""
    import app.core.event_bus as event_bus_module
    from app.core.event_bus import EventBus

    connect_calls: list[str] = []
    dlq_factory_calls: list[int] = []

    async def _spy_connect(self: EventBus) -> None:
        connect_calls.append(self.redis_url)
        raise RuntimeError("wt396 F7: 评估运行不得拨号真实 REDIS_URL（event_bus.connect 被触达）")

    class _SpyDlqFactory:
        def __call__(self) -> Any:
            dlq_factory_calls.append(1)
            raise RuntimeError("wt396 F7: 评估运行不得触达真实 DLQ Postgres 工厂")

    monkeypatch.setattr(EventBus, "connect", _spy_connect)
    monkeypatch.setattr(event_bus_module, "AsyncSessionLocal", _SpyDlqFactory())
    # 失败重试退避只影响红跑时长，不影响判据；压到最快
    monkeypatch.setattr(event_bus_module.event_bus, "max_retries", 0)
    monkeypatch.setattr(event_bus_module.event_bus, "publish_base_delay_ms", 0)
    monkeypatch.setattr(event_bus_module.event_bus, "publish_max_delay_ms", 0)

    spec = with_decision_script(_baseline_persona_with_intrinsic_day0(), {})
    async with PersonaWorld(spec, group="baseline", days=2) as world:
        records = await world.run()

    # 前提自证：内在自发重启真实发生（完成管线真的跑过 → 发布链路真的被触达过）
    assert any(
        r["kind"] == "lifecycle" and r.get("event") == "intrinsic_restart" for r in records
    ), "场景前提失效：没有内在完成，红测判据不成立"

    # 修前红：publish → connect 自动拨 settings.REDIS_URL（spy 记录到真实 URL）
    assert connect_calls == [], f"评估运行触达了真实 REDIS_URL 拨号入口：{connect_calls}"
    # 修前红（同族）：publish 失败回退 DLQ 写真实 Postgres
    assert dlq_factory_calls == [], "评估运行触达了真实 DLQ DB 工厂（event_bus.AsyncSessionLocal）"

    # 隔离 ≠ 丢弃：事件必须进入 PersonaWorld 注入的内存 stub 通道
    stub = world.event_bus_stub
    assert stub is not None
    published = [entry for entries in stub.streams.values() for entry in entries]
    assert published, "评估事件必须被隔离 stub 通道承接（否则隔离变成了静默丢事件）"
    assert all("schema_version" in entry for entry in published), "stub 记录必须保持真实发布 wire 形状"
