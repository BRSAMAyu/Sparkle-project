"""V3-FIX-343: L3 closure → Spine 桥激活（裁决 a：桥本该活）。

修前三处断裂实证（均本仓可复现）：
1. ``core_session.AuroraCoreSessionService`` 只设 ``self.store``/``self.db``，
   无 ``self.redis`` → ``L3FullCoreEngine(self.redis)`` 每次 close 必抛
   AttributeError，被 ``except Exception`` 吞成 debug 日志；
2. ``L3FullCoreEngine.produce_closure`` 读 runtime_v1 议程格式
   （``agenda.agenda_items[].item_type``/``payload.user_reply``），而
   ``AuroraCoreSession.to_dict()`` 的 agenda 是 UI 投影
   ``agenda_snapshot()``（无 agenda_items/item_type）→ closure 恒空，
   桥任务根本不会创建；
3. ``SpineOrchestrator.close_aurora_session`` 先查 signals-world facade
   存储键 ``spine:aurora_session:*``，core_session 会话活在
   ``aurora:core_session:*`` → 恒 ``session_not_found`` 早退，补丁不落。

修法：闭合源改 ``CalibrationResult.to_session_closure()``（P2-23 适配器，
登记时零消费方）；``close_aurora_session`` 增显式 ``user_id`` 旁路 facade
缺席；桥透传 ``user_id``；吞异常改 error 级 + fire-and-forget 任务可观测。

测试基建注记：redis 一律用进程内 FakeRedis（transport 层桩——存储语义是
真实 dict 读写，非把模型结果伪装成真实返回）；SpineOrchestrator 真实构造，
状态寄存器断言走真实 upsert 路径。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.aurora.core_session as core_session_module
import app.services.fme_l3_closure_bridge as bridge_module
from app.aurora.core_session import AuroraCoreSessionService
from app.signals.aurora_core_session import PolicyChange, SessionClosure, StatePatch
from app.signals.spine_orchestrator import SpineOrchestrator
from tests.unit.spine._helpers import FakeRedis


class _CoreSessionFakeRedis:
    """FakeRedis matching AuroraCoreSessionStore's usage surface (setex/get/delete)."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.data.pop(key, None) is not None else 0


async def _make_session_with_semantic_reply(
    semantic_value: str,
    *,
    user_id: str = "u1",
) -> tuple[AuroraCoreSessionService, str, str]:
    """Start a session, land one semantic reply, and keep it active for close."""
    service = AuroraCoreSessionService(_CoreSessionFakeRedis())
    session = await service.start_session(
        user_id=user_id,
        conversation_id="c1",
        band_status="calibration_available",
        wake_reasons=["task_time_overrun"],
    )
    await service.respond(
        user_id=user_id,
        session_id=session.session_id,
        content="大概半小时",
        option_id="available_time_30",
        semantic_value=semantic_value,
    )
    assert session.status == "active", "预设：一轮语义回复后会追问，会话仍 active"
    return service, user_id, session.session_id


async def _drain_bridge_tasks() -> list[asyncio.Task]:
    pending = list(core_session_module._L3_BRIDGE_TASKS)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    return pending


# ── core_session.close_session 桥激活 ────────────────────────────────────


@pytest.mark.asyncio
async def test_close_session_activates_l3_closure_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    """带校准产出的会话 force-close 必须真实触发 Spine 桥（修前 AttributeError 被吞=桥死）。"""
    bridge_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(bridge_module, "apply_l3_closure_to_spine", bridge_mock)
    service, user_id, session_id = await _make_session_with_semantic_reply("available_time_30")

    closed = await service.close_session(user_id=user_id, session_id=session_id)
    assert closed.status == "abandoned"
    assert closed.calibration_result is not None
    assert any(p["state_key"] == "available_time_today" for p in closed.calibration_result.state_patches)

    pending = await _drain_bridge_tasks()
    assert pending, "close_session 应创建桥任务（修前 AttributeError 被吞，任务不存在）"
    assert bridge_mock.await_count == 1
    owner_arg = bridge_mock.await_args.args[0]
    closure_arg = bridge_mock.await_args.args[1]
    assert owner_arg == user_id
    assert isinstance(closure_arg, SessionClosure)
    assert any(p.state_key == "available_time_today" for p in closure_arg.state_patches)
    assert any(c.new_strategy == "今晚按 30 分钟处理任务" for c in closure_arg.policy_changes)


@pytest.mark.asyncio
async def test_close_session_without_calibration_output_skips_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """无校准产出（空 patches/changes）时桥不触发——守卫非空才创建任务。"""
    bridge_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(bridge_module, "apply_l3_closure_to_spine", bridge_mock)
    service = AuroraCoreSessionService(_CoreSessionFakeRedis())
    session = await service.start_session(
        user_id="u2",
        conversation_id="c2",
        band_status="calibration_available",
        wake_reasons=["plan_drift"],
    )

    closed = await service.close_session(user_id="u2", session_id=session.session_id)
    assert closed.status == "abandoned"

    await _drain_bridge_tasks()
    assert bridge_mock.await_count == 0


@pytest.mark.asyncio
async def test_close_session_survives_bridge_faults(monkeypatch: pytest.MonkeyPatch) -> None:
    """桥故障不得波及用户可见的 close 返回，但故障必须留在被观测的任务里。"""
    bridge_mock = AsyncMock(side_effect=RuntimeError("spine down"))
    monkeypatch.setattr(bridge_module, "apply_l3_closure_to_spine", bridge_mock)
    service, user_id, session_id = await _make_session_with_semantic_reply("available_time_45")

    closed = await service.close_session(user_id=user_id, session_id=session_id)
    assert closed.status == "abandoned"

    pending = await _drain_bridge_tasks()
    assert pending, "带校准产出的 close 应创建桥任务"
    results = await asyncio.gather(*pending, return_exceptions=True)
    assert isinstance(results[0], RuntimeError), "任务内故障应被 done callback 观测而非静默丢失"


# ── spine.close_aurora_session facade 缺席旁路 ───────────────────────────


@pytest.mark.asyncio
async def test_close_aurora_session_applies_patches_without_facade_record() -> None:
    """facade 存储无此会话时，显式 user_id 应继续落补丁（修前恒 session_not_found 早退）。"""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    result = await spine.close_aurora_session(
        "core-session-not-in-facade-store",
        state_patches=[
            {
                "state_key": "available_time_today",
                "old_value": "unknown",
                "new_value": "30_minutes",
                "reason": "L3校准: 用户确认今晚可用时间约 30 分钟",
                "confidence": 0.72,
            }
        ],
        policy_changes=[
            {
                "signal_state_key": "available_time_today",
                "old_strategy": "current",
                "new_strategy": "今晚按 30 分钟处理任务",
                "reason": "L3校准",
            }
        ],
        user_summary="已更新今晚可用时间判断。",
        user_id="u1",
    )

    assert result is not None
    assert "error" not in result
    state = await spine.state_register.get_state("u1", "available_time_today")
    assert state is not None
    assert state.value == "30_minutes"


@pytest.mark.asyncio
async def test_close_aurora_session_facade_record_path_unchanged() -> None:
    """facade 在场（signals-world 会话）的原路径行为不变——无 user_id 时不走旁路。"""
    spine = SpineOrchestrator(redis_client=FakeRedis())
    session = await spine.start_aurora_core_session(
        user_id="u9",
        goal_summary="7天计网先过",
        current_plan_summary="第3天 TCP",
        wake_reason="user_explicit_wake",
    )
    session_id = session["agenda"]["session_id"]

    result = await spine.close_aurora_session(
        session_id,
        state_patches=[
            {
                "state_key": "compat_key",
                "old_value": "old",
                "new_value": "new",
                "reason": "calibration",
                "confidence": 0.8,
            }
        ],
        user_summary="已更新判断",
    )

    assert result is not None
    assert result.get("status") == "completed"
    state = await spine.state_register.get_state("u9", "compat_key")
    assert state is not None
    assert state.value == "new"


# ── 桥本体：kill switch / 空守卫 / user_id 透传 / 策略卡 ─────────────────


def _closure_with_output() -> SessionClosure:
    return SessionClosure(
        session_id="s-1",
        state_patches=[
            StatePatch(
                state_key="goal_strategy",
                old_value="unclear",
                new_value="pass_threshold",
                reason="L3校准: 用户确认目标是先过线",
                confidence=0.72,
            )
        ],
        policy_changes=[
            PolicyChange(
                signal_state_key="goal_strategy",
                old_strategy="current",
                new_strategy="先过线",
                reason="L3校准",
            )
        ],
        user_visible_summary="用户确认先过线。",
    )


@pytest.mark.asyncio
async def test_bridge_disabled_by_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bridge_module, "read_mode", AsyncMock(return_value="off"))
    spine_mock = MagicMock()
    spine_mock.close_aurora_session = AsyncMock()
    monkeypatch.setattr(bridge_module, "get_spine_orchestrator", MagicMock(return_value=spine_mock))

    result = await bridge_module.apply_l3_closure_to_spine("u-2", _closure_with_output())

    assert result is None
    spine_mock.close_aurora_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_skips_empty_closure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bridge_module, "read_mode", AsyncMock(return_value="live"))
    spine_factory = MagicMock(side_effect=AssertionError("空 closure 不应初始化 Spine"))
    monkeypatch.setattr(bridge_module, "get_spine_orchestrator", spine_factory)

    empty = SessionClosure(session_id="s-3")
    result = await bridge_module.apply_l3_closure_to_spine("u-3", empty)

    assert result is None
    spine_factory.assert_not_called()


@pytest.mark.asyncio
async def test_bridge_passes_user_id_and_emits_strategy_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """桥必须透传 user_id（facade 旁路依赖它），并在指令再生后发策略卡。"""
    monkeypatch.setattr(bridge_module, "read_mode", AsyncMock(return_value="live"))
    spine_mock = MagicMock()
    spine_mock.close_aurora_session = AsyncMock(
        return_value={"regenerated_directives": [{"state_key": "goal_strategy", "strategy": "pass_threshold"}]}
    )
    emit_mock = AsyncMock()
    monkeypatch.setattr(bridge_module, "get_spine_orchestrator", MagicMock(return_value=spine_mock))
    monkeypatch.setattr(bridge_module, "emit_strategy_change_card", emit_mock)

    result = await bridge_module.apply_l3_closure_to_spine("u-1", _closure_with_output())

    assert result is not None
    kwargs = spine_mock.close_aurora_session.await_args.kwargs
    assert kwargs.get("user_id") == "u-1"
    assert kwargs["state_patches"][0]["state_key"] == "goal_strategy"
    assert kwargs["user_summary"] == "用户确认先过线。"
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.args[0] == "u-1"
    assert emit_mock.await_args.kwargs["old_strategy"] == "current"
    assert emit_mock.await_args.kwargs["new_strategy"] == "pass_threshold"
