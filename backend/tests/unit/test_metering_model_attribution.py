"""V3-FIX-80（wt456）——计量盲区 default 落账归因补全红绿测试。

Q-06 复测实锤（v3-output/WT406-Q06-PERF/：raw-bench db_model 分布 +
facts-bench.json tier_ledger.default）：39/400 条 token_usage.model='default'
——32 条 0-token（澄清门模板直出，生成模型从未运行，流经 sufficiency 短路
出口后仍走 ResponseBuilderMixin._cleanup 计量漏斗）+ 7 条带 token 错挂
default（多代理流 study_plan/deep_analysis 消耗了真实用量但 context_data
既无 generation_model_key 也无 model_used）。历史漏斗
`or "default"` 把两类混成同一桶，分层成本账本对该面失明、费用被低估。

修后判据（归因补全，default 占比阈值）：
- 有模型键 → 真实模型键（行为不变）；
- 无模型键 + 无真实用量 → 显式 `no_generation_model`（区别于有消耗面）；
- 无模型键 + 有真实用量 → 显式 `unattributed_model`（盲区可见可收敛）；
- 全路径 default 产生占比 = 0（阈值断言）。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.orchestration import response_builder as rb_module
from app.orchestration.response_builder import (
    METERING_MODEL_NO_GENERATION,
    METERING_MODEL_UNATTRIBUTED,
    ResponseBuilderMixin,
    resolve_metering_model_key,
)

# ---------------------------------------------------------------------------
# 纯函数面：归因解析
# ---------------------------------------------------------------------------


def test_real_model_keys_pass_through():
    assert resolve_metering_model_key({"generation_model_key": "dashscope_chat"}) == "dashscope_chat"
    assert (
        resolve_metering_model_key({"generation_model_key": "", "model_used": "dashscope_fast"})
        == "dashscope_fast"
    )


def test_no_key_no_real_usage_labeled_no_generation():
    """澄清门/模板直出：无模型键且无真实用量帧 → 显式 no_generation_model。"""
    assert resolve_metering_model_key({}) == METERING_MODEL_NO_GENERATION
    assert (
        resolve_metering_model_key({"chat_mode": "standard"}, has_real_usage=False)
        == METERING_MODEL_NO_GENERATION
    )


def test_no_key_with_real_usage_labeled_unattributed():
    """多代理流等盲区面：无模型键但有真实用量 → 显式 unattributed_model。"""
    assert (
        resolve_metering_model_key({}, has_real_usage=True) == METERING_MODEL_UNATTRIBUTED
    )
    assert (
        resolve_metering_model_key(
            {"generation_model_key": None, "model_used": ""}, has_real_usage=True
        )
        == METERING_MODEL_UNATTRIBUTED
    )


def test_default_ratio_below_threshold():
    """红测阈值断言：代表性归因面样本中 default 产生占比必须为 0（<1% 阈值）。"""
    surfaces: list[dict[str, Any]] = [
        {},  # 澄清门 0-token
        {"chat_mode": "study_plan"},
        {"chat_mode": "deep_analysis", "reasoning_mode": "deep"},
        {"generation_model_key": "dashscope_fast"},
        {"generation_model_key": None, "model_used": "qwen3_8_max"},
        {"generation_model_key": "", "model_used": ""},
        {"generation_model_tier": "max"},  # tier 在而模型键不在的错挂形态
        {"model_used": 0},  # falsy 值不得穿透为归因
    ]
    flags = [
        resolve_metering_model_key(ctx, has_real_usage=i % 2 == 0) == "default"
        for i, ctx in enumerate(surfaces)
    ]
    default_ratio = sum(flags) / len(flags)
    assert default_ratio < 0.01, f"default 占比 {default_ratio:.2%}，归因未补全"


# ---------------------------------------------------------------------------
# 计量漏斗面：ResponseBuilderMixin._cleanup 落账
# ---------------------------------------------------------------------------


class _CleanupStub(ResponseBuilderMixin):
    """最小持有面：_cleanup 依赖的属性全部内联，无 Orchestrator 依赖。"""

    def __init__(self, tracker: Any):
        self.token_tracker = tracker
        self.state_manager = SimpleNamespace(
            stop_lock_renewal=None,
        )

    async def _release_session_lock(self, session_id: str, request_id: str) -> None:  # pragma: no cover
        return None


class _FakeTracker:
    def __init__(self) -> None:
        self.recorded: list[dict[str, Any]] = []

    async def estimate_cost(self, **kwargs: Any) -> float:
        return 0.0

    async def record_usage(self, **kwargs: Any) -> int:
        self.recorded.append(kwargs)
        return int(kwargs.get("prompt_tokens", 0)) + int(kwargs.get("completion_tokens", 0))


@pytest.mark.asyncio
async def test_cleanup_clarification_gate_zero_token_not_default(monkeypatch):
    """0-token 澄清门短路轮：计量行显式标注，不再落 default。"""
    tracker = _FakeTracker()
    stub = _CleanupStub(tracker)
    monkeypatch.setattr(
        rb_module.task_manager,
        "spawn",
        lambda coro, **kwargs: asyncio.ensure_future(coro),
    )

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-1",
        request_id="req-1",
        start_time=0.0,
        user_id="user-1",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=None,
    )
    await asyncio.sleep(0)

    assert len(tracker.recorded) == 1
    assert tracker.recorded[0]["model"] == METERING_MODEL_NO_GENERATION


@pytest.mark.asyncio
async def test_cleanup_multi_agent_real_usage_without_key_not_default(monkeypatch):
    """多代理流盲区面：有真实用量帧但无模型键 → 显式 unattributed_model。"""
    tracker = _FakeTracker()
    stub = _CleanupStub(tracker)
    monkeypatch.setattr(
        rb_module.task_manager,
        "spawn",
        lambda coro, **kwargs: asyncio.ensure_future(coro),
    )
    final_state = SimpleNamespace(context_data={"chat_mode": "study_plan"}, messages=[])

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-2",
        request_id="req-2",
        start_time=0.0,
        user_id="user-2",
        total_prompt_tokens=300,
        total_completion_tokens=38,
        final_state=final_state,
    )
    await asyncio.sleep(0)

    assert len(tracker.recorded) == 1
    assert tracker.recorded[0]["model"] == METERING_MODEL_UNATTRIBUTED
    assert tracker.recorded[0]["prompt_tokens"] == 300


@pytest.mark.asyncio
async def test_cleanup_real_model_key_passthrough(monkeypatch):
    """正常路径守卫：有模型键时归因行为不变。"""
    tracker = _FakeTracker()
    stub = _CleanupStub(tracker)
    monkeypatch.setattr(
        rb_module.task_manager,
        "spawn",
        lambda coro, **kwargs: asyncio.ensure_future(coro),
    )
    final_state = SimpleNamespace(
        context_data={
            "generation_model_key": "dashscope_chat",
            "generation_model_tier": "plus",
        },
        messages=[],
    )

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-3",
        request_id="req-3",
        start_time=0.0,
        user_id="user-3",
        total_prompt_tokens=100,
        total_completion_tokens=20,
        final_state=final_state,
    )
    await asyncio.sleep(0)

    assert len(tracker.recorded) == 1
    assert tracker.recorded[0]["model"] == "dashscope_chat"
