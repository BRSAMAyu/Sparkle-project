"""V4-I10 —— 根请求全调用计量与 label 真实性（全 mock，零真模型）。

三靶（B06 三缺陷）：
1. estimate_cost 未知键静默按 gpt-4 错价（token_tracker L518-519）→ 未知键
   显式 None（未核价 unknown），绝不回落 gpt-4；
2. 「带 token 的 no_generation_model」检出器缺失（V3 FIX-545 终结面）→
   bisect_no_generation_with_tokens 标签二分 + 检出计数；
3. usage 回执 cost_micro_usd 恒 0 vs 内部账有成本（B06-T1）→ 回执与内部账
   同一核价权威 estimate_model_cost_usd，不可核价显式 usage_cost_unpriced。

附：rescue 二次真实上游调用入根请求账（B06-T3），sub_calls 切片可审计；
计费重放同 request_id 只结算一次（token_usage.request_id 唯一约束）。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import func, select

from app.agents.standard_workflow import _build_usage_receipt
from app.orchestration import response_builder as rb_module
from app.orchestration.response_builder import (
    METERING_MODEL_DEGRADED_ESTIMATE,
    METERING_MODEL_NO_GENERATION,
    ResponseBuilderMixin,
    bisect_no_generation_with_tokens,
    resolve_metering_model_key,
)
from app.orchestration.token_tracker import TokenTracker, estimate_model_cost_usd

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------


def _counter_value(name: str, labels: dict[str, str] | None = None) -> float:
    value = REGISTRY.get_sample_value(name, labels or {})
    return float(value or 0.0)


class _CleanupStub(ResponseBuilderMixin):
    """最小持有面：_cleanup 依赖的属性全部内联，无 Orchestrator 依赖。"""

    def __init__(self, tracker: Any):
        self.token_tracker = tracker
        self.state_manager = SimpleNamespace(stop_lock_renewal=None)

    async def _release_session_lock(self, session_id: str, request_id: str) -> None:  # pragma: no cover
        return None


class _CaptureTracker:
    """捕获 estimate_cost / record_usage 入参；核价走真实单一权威。"""

    def __init__(self) -> None:
        self.recorded: list[dict[str, Any]] = []
        self.cost_calls: list[dict[str, Any]] = []

    async def estimate_cost(self, **kwargs: Any) -> float | None:
        self.cost_calls.append(kwargs)
        return estimate_model_cost_usd(
            int(kwargs.get("prompt_tokens", 0)),
            int(kwargs.get("completion_tokens", 0)),
            str(kwargs.get("model", "")),
        )

    async def record_usage(self, **kwargs: Any) -> int:
        self.recorded.append(kwargs)
        return int(kwargs.get("prompt_tokens", 0)) + int(kwargs.get("completion_tokens", 0))


def _final_state(context_data: dict[str, Any] | None = None, *, assistant: str = "", user: str = "") -> Any:
    messages: list[dict[str, Any]] = []
    if user:
        messages.append({"role": "user", "content": user})
    if assistant:
        messages.append({"role": "assistant", "content": assistant})
    return SimpleNamespace(context_data=context_data or {}, messages=messages)


@pytest.fixture
def _spawn_inline(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        rb_module.task_manager,
        "spawn",
        lambda coro, **kwargs: asyncio.ensure_future(coro),
    )


# ---------------------------------------------------------------------------
# 靶2：estimate_cost 未知键绝不静默回落 gpt-4（B06-A4）
# ---------------------------------------------------------------------------


def test_estimate_cost_unknown_key_returns_none_not_gpt4_price():
    """未知模型键 → None（未核价），绝不静默按 gpt-4 价目计算。"""
    tokens_p, tokens_c = 10, 32
    unpriced = estimate_model_cost_usd(tokens_p, tokens_c, "totally_unknown_model")
    assert unpriced is None
    # B06-A4 反例锚定：同样 token 按旧逻辑会被错价成 gpt-4 价（$0.00246），
    # 修后必须为 None 且不得等于 gpt-4 legacy 价。
    gpt4_reference = (tokens_p * 0.03 + tokens_c * 0.06) / 1000
    assert unpriced != round(gpt4_reference, 6)


def test_estimate_cost_metering_labels_unpriced():
    """计量标签（no_generation_model/unattributed_model）永无价目 → None。"""
    assert estimate_model_cost_usd(42, 0, METERING_MODEL_NO_GENERATION) is None
    assert estimate_model_cost_usd(42, 0, "unattributed_model") is None
    assert estimate_model_cost_usd(0, 0, "") is None


def test_estimate_cost_legacy_keys_still_priced():
    """显式 legacy OpenAI 键保留 legacy 价（行为不变面）。"""
    assert estimate_model_cost_usd(1000, 0, "gpt-4") == pytest.approx(0.03)
    assert estimate_model_cost_usd(0, 1000, "gpt-3.5-turbo") == pytest.approx(0.002)


def test_estimate_cost_router_registered_key_uses_router_price(monkeypatch):
    """router 注册模型走注册价（行为不变面）。"""
    fake_config = SimpleNamespace(cost_per_1k_tokens=0.002)
    monkeypatch.setattr(
        "app.orchestration.token_tracker.llm_router",
        SimpleNamespace(_available_models={"dashscope_fast": fake_config}),
        raising=False,
    )
    assert estimate_model_cost_usd(1500, 500, "dashscope_fast") == pytest.approx(0.004)


@pytest.mark.asyncio
async def test_tracker_estimate_cost_returns_none_for_unknown():
    tracker = TokenTracker(redis_client=SimpleNamespace())
    assert await tracker.estimate_cost(prompt_tokens=42, completion_tokens=0, model="no_generation_model") is None
    assert await tracker.estimate_cost(prompt_tokens=42, completion_tokens=0, model="unknown-model-x") is None


# ---------------------------------------------------------------------------
# 靶3：FIX545 终结面 —— 带 token 的 no_generation_model 检出 + 标签二分
# ---------------------------------------------------------------------------


def test_bisect_zero_token_stays_no_generation():
    """真无模型（0-token 澄清门/模板直出）保持 no_generation_model。"""
    assert (
        bisect_no_generation_with_tokens(METERING_MODEL_NO_GENERATION, prompt_tokens=0, completion_tokens=0)
        == METERING_MODEL_NO_GENERATION
    )


def test_bisect_with_tokens_relabeled_degraded_estimate():
    """带 token（S06 七条错挂形状）二分为显式降级计量标签。"""
    assert (
        bisect_no_generation_with_tokens(METERING_MODEL_NO_GENERATION, prompt_tokens=2, completion_tokens=42)
        == METERING_MODEL_DEGRADED_ESTIMATE
    )
    assert (
        bisect_no_generation_with_tokens(METERING_MODEL_NO_GENERATION, prompt_tokens=0, completion_tokens=7)
        == METERING_MODEL_DEGRADED_ESTIMATE
    )


def test_bisect_real_keys_pass_through():
    assert bisect_no_generation_with_tokens("dashscope_fast", prompt_tokens=9, completion_tokens=1) == "dashscope_fast"
    assert bisect_no_generation_with_tokens("unattributed_model", prompt_tokens=0, completion_tokens=0) == (
        "unattributed_model"
    )


@pytest.mark.asyncio
async def test_cleanup_synthetic_estimate_detected_and_relabeled(_spawn_inline, monkeypatch):
    """FIX545 产生面端到端：无模型键 + 合成估算 token>0 → 检出计数 + 改标降级计量。

    修前形状（B06 §4.5）：判定先于估算，产出 no_generation_model + token>0 的
    自相矛盾行；修后该行被检出（计数器递增）并以显式标签落账，cost=None
    （未核价不填 0 也不按 gpt-4 错价），usage_source=estimated 不冒充实测。
    """
    surface_before = _counter_value(
        "sparkle_metering_no_generation_with_tokens_total", {"surface": "cleanup"}
    )
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)
    # 无 generation_model_key/model_used → resolve 产 no_generation_model；
    # messages 非空 → 合成估算产 token>0 → FIX545 形状。
    final_state = _final_state({"chat_mode": "standard"}, assistant="这是一段兜底回答内容。", user="用户问题")

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-i10-1",
        request_id="req-i10-1",
        start_time=0.0,
        user_id="user-i10-1",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=final_state,
    )
    await asyncio.sleep(0)

    assert len(tracker.recorded) == 1
    row = tracker.recorded[0]
    assert row["model"] == METERING_MODEL_DEGRADED_ESTIMATE
    assert row["prompt_tokens"] > 0 and row["completion_tokens"] > 0
    assert row["usage_source"] == "estimated"
    assert row["cost"] is None  # 未核价 unknown 语义，绝不填 gpt-4 错价也不填 0 冒充
    surface_after = _counter_value(
        "sparkle_metering_no_generation_with_tokens_total", {"surface": "cleanup"}
    )
    assert surface_after == surface_before + 1, "FIX545 with-tokens 检出必须可计数"


@pytest.mark.asyncio
async def test_cleanup_true_no_generation_zero_token_unchanged(_spawn_inline):
    """0-token 真无模型（final_state=None）保持 no_generation_model，不误报检出。"""
    surface_before = _counter_value(
        "sparkle_metering_no_generation_with_tokens_total", {"surface": "cleanup"}
    )
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-i10-2",
        request_id="req-i10-2",
        start_time=0.0,
        user_id="user-i10-2",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=None,
    )
    await asyncio.sleep(0)

    assert len(tracker.recorded) == 1
    row = tracker.recorded[0]
    assert row["model"] == METERING_MODEL_NO_GENERATION
    assert row["prompt_tokens"] == 0 and row["completion_tokens"] == 0
    assert _counter_value(
        "sparkle_metering_no_generation_with_tokens_total", {"surface": "cleanup"}
    ) == surface_before


@pytest.mark.asyncio
async def test_cleanup_measured_row_real_key_passes_bisect(_spawn_inline):
    """实测行 + 真实模型键：bisect 原样放行（行为不变守卫）。"""
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)
    final_state = _final_state(
        {"generation_model_key": "dashscope_chat", "generation_model_tier": "plus"},
    )

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-i10-3",
        request_id="req-i10-3",
        start_time=0.0,
        user_id="user-i10-3",
        total_prompt_tokens=100,
        total_completion_tokens=20,
        final_state=final_state,
    )
    await asyncio.sleep(0)

    row = tracker.recorded[0]
    assert row["model"] == "dashscope_chat"
    assert row["usage_source"] == "measured"
    assert row["cost"] is not None  # router 注册键可核价


# ---------------------------------------------------------------------------
# 靶4：rescue 二次真实上游调用入根请求账（B06-T3）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_folds_rescue_subcall_and_attributes_truthfully(_spawn_inline):
    """主生成无实测帧 + rescue 顶替：整行归因 rescue 模型/层，sub_calls 切片留痕。"""
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)
    context_data = {
        "chat_mode": "standard",
        "generation_model_key": "dashscope_fast",  # 失败的主生成选择
        "generation_model_tier": "fast",
        "rescue_metering": {
            "lane": "generation_rescue",
            "model_key": "glm_4_7_flash",
            "model_tier": "fast",
            "calls": 1,
            "prompt_tokens": 120,
            "completion_tokens": 60,
        },
    }
    final_state = _final_state(context_data, assistant="rescue 生成的回答", user="你好")

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-i10-4",
        request_id="req-i10-4",
        start_time=0.0,
        user_id="user-i10-4",
        total_prompt_tokens=0,
        total_completion_tokens=0,
        final_state=final_state,
    )
    await asyncio.sleep(0)

    row = tracker.recorded[0]
    # lane/model/tier 与实际一致：真实成功面是 rescue，不是失败的主生成选择
    assert row["model"] == "glm_4_7_flash"
    assert row["model_tier"] == "fast"
    assert row["prompt_tokens"] == 120 and row["completion_tokens"] == 60
    assert row["usage_source"] == "estimated"
    sub_calls = row["sub_calls"]
    assert isinstance(sub_calls, list) and len(sub_calls) == 1
    assert sub_calls[0]["lane"] == "generation_rescue"
    assert sub_calls[0]["model_key"] == "glm_4_7_flash"
    assert sub_calls[0]["usage_source"] == "estimated"
    # 无合成估算双计：救援子调用已计量后不再叠加消息文本估算
    assert row["prompt_tokens"] + row["completion_tokens"] == 180


@pytest.mark.asyncio
async def test_cleanup_rescue_plus_measured_frames_adds_up(_spawn_inline):
    """主生成实测帧 + 泄漏替换型 rescue：两段消耗都入账，归因保持主模型。"""
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)
    context_data = {
        "generation_model_key": "dashscope_chat",
        "generation_model_tier": "plus",
        "rescue_metering": {
            "lane": "generation_rescue",
            "model_key": "dashscope_fast",
            "model_tier": "fast",
            "calls": 1,
            "prompt_tokens": 30,
            "completion_tokens": 12,
        },
    }

    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-i10-5",
        request_id="req-i10-5",
        start_time=0.0,
        user_id="user-i10-5",
        total_prompt_tokens=500,
        total_completion_tokens=80,
        final_state=_final_state(context_data),
    )
    await asyncio.sleep(0)

    row = tracker.recorded[0]
    assert row["model"] == "dashscope_chat"  # 主生成有实测，归因不变
    assert row["prompt_tokens"] == 530
    assert row["completion_tokens"] == 92
    assert row["sub_calls"][0]["prompt_tokens"] == 30  # 独立开销可切片


def test_rescue_metering_accumulates_across_multiple_rescues():
    """多次 rescue（泄漏/低信息替换连发）累计进同一 context_data 槽位。"""
    from app.agents.standard_workflow import _meter_generation_rescue_subcall

    state = SimpleNamespace(context_data={})

    class _Sel:
        model_key = "glm_4_7_flash"

        class config:  # noqa: N801 — SimpleNamespace 静态形
            tier = SimpleNamespace(value="fast")

    class _LLM:
        def get_current_selection(self) -> Any:
            return _Sel()

    _meter_generation_rescue_subcall(
        state, _LLM(), rescue_prompt="系统提示 词", rescue_response="回答一", rescue_tier=SimpleNamespace(value="fast")
    )
    _meter_generation_rescue_subcall(
        state, _LLM(), rescue_prompt="系统提示 词", rescue_response="回答二", rescue_tier=SimpleNamespace(value="fast")
    )
    info = state.context_data["rescue_metering"]
    assert info["calls"] == 2
    assert info["model_keys"] == ["glm_4_7_flash", "glm_4_7_flash"]
    assert info["completion_tokens"] > 0


# ---------------------------------------------------------------------------
# 靶1：usage 回执与内部账同价同源（B06-T1）
# ---------------------------------------------------------------------------


def test_usage_receipt_priced_key_carries_real_cost(monkeypatch):
    """可核价键：回执 micro = 单一权威核价结果（两账口径统一）。"""
    fake_config = SimpleNamespace(cost_per_1k_tokens=0.002)
    monkeypatch.setattr(
        "app.orchestration.token_tracker.llm_router",
        SimpleNamespace(_available_models={"dashscope_fast": fake_config}),
        raising=False,
    )
    micro, meta = _build_usage_receipt(prompt_tokens=1369, completion_tokens=72, model_key="dashscope_fast")
    assert micro == int(round(((1369 + 72) * 0.002 / 1000) * 1_000_000))
    assert meta == {}


def test_usage_receipt_unpriced_key_marks_unknown():
    """不可核价键：cost=0 但显式 usage_cost_unpriced 标记（wire 无法表达 unknown）。"""
    micro, meta = _build_usage_receipt(prompt_tokens=100, completion_tokens=5, model_key="unknown-model-x")
    assert micro == 0
    assert meta == {"usage_cost_unpriced": "true"}
    micro, meta = _build_usage_receipt(prompt_tokens=10, completion_tokens=2, model_key="")
    assert micro == 0 and meta == {"usage_cost_unpriced": "true"}


# ---------------------------------------------------------------------------
# 计费重放幂等：重复重放不重复结算
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_replay_same_request_id_settles_once():
    """同 request_id 重放（flush 后批未清/回队重放）只落一行——不重复结算。"""
    import uuid

    from app.models.chat import TokenUsage
    from app.services.billing_worker import BillingWorker

    worker = BillingWorker(db_url="sqlite+aiosqlite://")
    try:
        async with worker.engine.begin() as conn:
            await conn.run_sync(TokenUsage.__table__.create)
        record = {
            "user_id": str(uuid.uuid4()),
            "session_id": "sess-i10-9",
            "request_id": "req-i10-dup",
            "model": "dashscope_fast",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.01,
            "timestamp": 1700000000.0,
        }
        worker._batch = [dict(record), dict(record)]  # 同 request_id 重放两份
        await worker._flush_to_db()  # 批量撞唯一约束 → 逐条重试跳过重复

        async with worker.async_session_factory() as session:
            count = (await session.execute(select(func.count()).select_from(TokenUsage))).scalar_one()
        assert count == 1, "重复重放必须只结算一次"
        assert worker._batch == []
    finally:
        await worker.engine.dispose()


@pytest.mark.asyncio
async def test_billing_unpriced_cost_persists_as_null_not_zero():
    """未核价（cost=None）落库为 NULL 而非 0——「免费」与「未核价」可区分。"""
    import uuid

    from app.models.chat import TokenUsage
    from app.services.billing_worker import BillingWorker

    worker = BillingWorker(db_url="sqlite+aiosqlite://")
    try:
        async with worker.engine.begin() as conn:
            await conn.run_sync(TokenUsage.__table__.create)
        worker._batch = [
            {
                "user_id": str(uuid.uuid4()),
                "session_id": "sess-i10-10",
                "request_id": "req-i10-unpriced",
                "model": "no_generation_model_estimated",
                "prompt_tokens": 2,
                "completion_tokens": 42,
                "total_tokens": 44,
                "cost": None,
                "timestamp": 1700000000.0,
            }
        ]
        await worker._flush_to_db()
        async with worker.async_session_factory() as session:
            row = (
                await session.execute(select(TokenUsage).where(TokenUsage.request_id == "req-i10-unpriced"))
            ).scalar_one()
        assert row.cost is None, "未核价必须是 NULL（unknown 语义），不得填 0 冒充免费"
    finally:
        await worker.engine.dispose()


# ---------------------------------------------------------------------------
# 归因面回归守卫：resolve 语义不变
# ---------------------------------------------------------------------------


def test_resolve_metering_semantics_unchanged():
    assert resolve_metering_model_key({"generation_model_key": "dashscope_chat"}) == "dashscope_chat"
    assert resolve_metering_model_key({}, has_real_usage=False) == METERING_MODEL_NO_GENERATION
    assert resolve_metering_model_key({}, has_real_usage=True) == "unattributed_model"
