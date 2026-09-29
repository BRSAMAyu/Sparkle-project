"""V4-FIX-573 —— 引擎计量缺陷族修复（Q04 验收揪出的产品面缺陷闭环）。

两缺陷（证据：v4/evidence/V4-Q04/review_r1.md 四红项归属表）：
1. 红项① no_generation 带 token：L2-r1/r3/r4-08 三行
   `no_generation_model_estimated` 携带 216/216/277 token——no_generation 桶
   本意是「零生成」。产生路径 = `_cleanup` 合成估算发生在归因判定之后：
   真实生成发生过而模型键未回填 → 估算 token 错挂 no_generation 家族标签。
   修复 = 该形态改记 `unattributed_model` 正确桶（有真实用量、模型键未知），
   成本可见性保留（estimated 降级如实、cost=None 未核价）。
2. 红项② 取消轮次记账归零：L2-CANCEL 服务端续生成（t=20.366s usage 帧
   13,320 tok 帧级收据早于取消）但终态记账 0tok。产生路径 =
   `_execute_graph` token 累积是生成器局部变量、仅在图正常完成后写入
   result_holder；客户端取消（GeneratorExit）时局部累积丢失，orchestrator
   finally 以 0 token 进 `_cleanup`。修复 = 帧级收据即时落 result_holder +
   GeneratorExit 排空已入队收据 + orchestrator finally 恢复收据入账。

边界铁律：不破坏 I09 fastlane 0tok 承诺面与 I10 检出桶语义
（bisect 函数与其计数器原样保留，仅产生面不再产出该形状）。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from prometheus_client import REGISTRY

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration import execution_engine as ee_module
from app.orchestration import response_builder as rb_module
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.response_builder import (
    METERING_MODEL_NO_GENERATION,
    ResponseBuilderMixin,
    bisect_no_generation_with_tokens,
)

# ---------------------------------------------------------------------------
# 小工具（与 I10/Deterministic-Lane 测试基建同构，本地自持）
# ---------------------------------------------------------------------------


def _counter_value(name: str, labels: dict[str, str] | None = None) -> float:
    value = REGISTRY.get_sample_value(name, labels or {})
    return float(value or 0.0)


class _CaptureTracker:
    """捕获 estimate_cost / record_usage 入参；核价走真实单一权威。"""

    def __init__(self) -> None:
        self.recorded: list[dict[str, Any]] = []

    async def estimate_cost(self, **kwargs: Any) -> float | None:
        from app.orchestration.token_tracker import estimate_model_cost_usd

        return estimate_model_cost_usd(
            int(kwargs.get("prompt_tokens", 0)),
            int(kwargs.get("completion_tokens", 0)),
            str(kwargs.get("model", "")),
        )

    async def record_usage(self, **kwargs: Any) -> int:
        self.recorded.append(kwargs)
        return int(kwargs.get("prompt_tokens", 0)) + int(kwargs.get("completion_tokens", 0))


class _CleanupStub(ResponseBuilderMixin):
    """最小持有面：_cleanup 依赖的属性全部内联，无 Orchestrator 依赖。"""

    def __init__(self, tracker: Any):
        self.token_tracker = tracker
        self.state_manager = SimpleNamespace(stop_lock_renewal=None)

    async def _release_session_lock(self, session_id: str, request_id: str) -> None:  # pragma: no cover
        return None


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


async def _run_cleanup(
    *,
    total_prompt_tokens: int = 0,
    total_completion_tokens: int = 0,
    final_state: Any = None,
    context_data_fallback: dict[str, Any] | None = None,
    request_id: str = "req-f573",
) -> tuple[_CaptureTracker, dict[str, Any]]:
    tracker = _CaptureTracker()
    stub = _CleanupStub(tracker)
    await ResponseBuilderMixin._cleanup(
        stub,
        lock_acquired=False,
        lock_renewal_task=None,
        lock_renewal_stop=None,
        session_id="sess-f573",
        request_id=request_id,
        start_time=0.0,
        user_id="user-f573",
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        final_state=final_state,
        context_data_fallback=context_data_fallback,
    )
    await asyncio.sleep(0)
    assert len(tracker.recorded) == 1
    return tracker, tracker.recorded[0]


# ---------------------------------------------------------------------------
# 缺陷①（Q04 红项①）：no_generation 行零 token——该形态改记正确桶
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_q04_red1_shape_lands_unattributed_not_no_generation(_spawn_inline):
    """正例：Q04 L2-*-08 形态（无模型键 + 真实生成 + 无 usage 帧）→ unattributed_model。

    修前该形态落 `no_generation_model_estimated`（no_generation 家族带 token
    的自相矛盾行，Q04 三行 216/216/277 tok）；修后改记正确桶，估算降级与
    未核价语义如实保留。
    """
    reattr_before = _counter_value("sparkle_metering_no_generation_reattributed_total", {"surface": "cleanup"})
    final_state = _final_state(
        {"chat_mode": "standard", "reasoning_mode": "deep"},
        assistant="这是一段真实生成后的长回答，用于估算 completion token。" * 8,
        user="请深入讲解记忆曲线的原理",
    )
    _tracker, row = await _run_cleanup(final_state=final_state)
    assert row["model"] == "unattributed_model"
    assert row["prompt_tokens"] > 0 and row["completion_tokens"] > 0
    assert row["usage_source"] == "estimated"  # 降级计量如实，不冒充实测
    assert row["cost"] is None  # 计量标签无价目 → 未核价 unknown，不填 0 不按 gpt-4 错价
    assert _counter_value("sparkle_metering_no_generation_reattributed_total", {"surface": "cleanup"}) == (
        reattr_before + 1
    )


@pytest.mark.asyncio
async def test_q04_red1_original_shape_is_red_invariant(_spawn_inline):
    """反例（复现 Q04 原始红项①形态应红）：no_generation 家族行绝不携带 token。

    不变量横跨两形态：Q04 错挂形态（有 token）与真无生成形态（澄清门/
    final_state=None，0-token 合法）。修前第一形态产出
    no_generation_model_estimated + token>0 → 本测必红；修后不变量成立。
    """
    # 形态 A：Q04 原始红项形状（无模型键 + assistant 文本 → 合成估算 token>0）
    _tracker_a, row_a = await _run_cleanup(
        final_state=_final_state({}, assistant="真实生成内容。", user="问题"),
        request_id="req-f573-inv-a",
    )
    assert not (
        str(row_a["model"]).startswith("no_generation") and (row_a["prompt_tokens"] + row_a["completion_tokens"]) > 0
    ), f"no_generation 家族行携带 token（Q04 红项①复现）：model={row_a['model']} tokens={row_a['prompt_tokens']}+{row_a['completion_tokens']}"
    # 形态 B：真无生成（final_state=None → 0-token，no_generation_model 合法保底）
    _tracker_b, row_b = await _run_cleanup(final_state=None, request_id="req-f573-inv-b")
    assert row_b["model"] == METERING_MODEL_NO_GENERATION
    assert row_b["prompt_tokens"] == 0 and row_b["completion_tokens"] == 0
    assert not (
        str(row_b["model"]).startswith("no_generation") and (row_b["prompt_tokens"] + row_b["completion_tokens"]) > 0
    )


@pytest.mark.asyncio
async def test_q04_red1_real_key_estimated_row_untouched(_spawn_inline):
    """行为不变守卫：真实模型键 + 估算 token 的行不被改挂（既有慢路估算语义）。"""
    final_state = _final_state(
        {"generation_model_key": "dashscope_chat", "generation_model_tier": "plus"},
        assistant="真模型慢路的无帧估算行。",
        user="问题",
    )
    _tracker, row = await _run_cleanup(final_state=final_state)
    assert row["model"] == "dashscope_chat"  # 归因不变，bisect 原样放行
    assert row["prompt_tokens"] > 0 and row["completion_tokens"] > 0
    assert row["usage_source"] == "estimated"


def test_bisect_detector_semantics_unchanged():
    """I10 检出桶语义保留：bisect 函数契约原样（回归防线不拆除）。"""
    assert bisect_no_generation_with_tokens(METERING_MODEL_NO_GENERATION, prompt_tokens=216, completion_tokens=216) == (
        "no_generation_model_estimated"
    )
    assert bisect_no_generation_with_tokens(METERING_MODEL_NO_GENERATION, prompt_tokens=0, completion_tokens=0) == (
        METERING_MODEL_NO_GENERATION
    )


# ---------------------------------------------------------------------------
# 缺陷②（Q04 红项②）：取消轮次按帧级收据入账
# ---------------------------------------------------------------------------


class _F573GraphHarness(ExecutionEngineMixin):
    """最小持有面：_execute_graph 只依赖 graph 与 token_tracker。"""

    def __init__(self, graph: Any) -> None:
        self.graph = graph
        self.token_tracker = None


class _HangingGraph:
    """模拟长生成段：invoke 长睡不返回（取消发生在图完成前）。"""

    def __init__(self) -> None:
        self.cancelled = False

    async def invoke(self, state: Any, resume_policy: str | None = None) -> dict[str, Any]:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return {"messages": ["done"]}


def _usage_frame(prompt_tokens: int, completion_tokens: int) -> agent_service_pb2.ChatResponse:
    return agent_service_pb2.ChatResponse(
        usage=agent_service_pb2.Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    )


@pytest.fixture
def _spawn_graph_inline(monkeypatch: pytest.MonkeyPatch):
    spawned: list[asyncio.Task] = []

    async def _spawn(coro: Any, **kwargs: Any) -> asyncio.Task:
        task = asyncio.ensure_future(coro)
        spawned.append(task)
        return task

    monkeypatch.setattr(ee_module.task_manager, "spawn", _spawn)
    return spawned


@pytest.mark.asyncio
async def test_q04_red2_cancel_keeps_frame_receipts(_spawn_graph_inline):
    """正例+反例二合一：取消后 result_holder 保留取消前帧级收据（修前必红）。

    Q04 L2-CANCEL 时序复现：usage 帧 13,320 tok 先于取消到达（已被消费），
    随后客户端断连（GeneratorExit）——此时队列里还有一张已入队未消费的
    收据，同属「取消前已产生」。修前局部累积随生成器闭合同丢失、
    result_holder 无 token（终态记账 0tok 的产生点）；修后即时落账 + 排空。
    """
    graph = _HangingGraph()
    harness = _F573GraphHarness(graph)
    queue: asyncio.Queue = asyncio.Queue()
    holder: dict[str, Any] = {}
    agen = harness._execute_graph(
        state=None,
        user_id="user-f573",
        queue=queue,
        result_holder=holder,
        frame_identity=None,
    )
    # t=20.366s 隐喻：取消前已产生并已被消费的帧级收据
    await queue.put(_usage_frame(1100, 13320))
    item = await agen.__anext__()
    assert item.HasField("usage")
    # FIX573：帧级收据即时落 result_holder（同时覆盖超时路径的可见性）
    assert holder.get("total_prompt_tokens") == 1100
    assert holder.get("total_completion_tokens") == 13320
    # 取消前已入队、未及消费的第二张收据
    await queue.put(_usage_frame(10, 20))
    # 客户端断连 → GeneratorExit
    await agen.aclose()
    assert holder.get("total_prompt_tokens") == 1110, "取消前已入队收据必须排空入账"
    assert holder.get("total_completion_tokens") == 13340, "取消前已入队收据必须排空入账"
    # 图任务收尾（cancel 需事件循环轮转才落进 invoke），不留悬挂任务告警
    await asyncio.gather(*_spawn_graph_inline, return_exceptions=True)
    assert graph.cancelled, "取消必须传播到图任务（取消后才产生的帧才归零）"


@pytest.mark.asyncio
async def test_q04_red2_cancel_cleanup_accounts_receipts(_spawn_inline):
    """取消形状的 _cleanup 收口：收据 token 入账 + 共享上下文兜底模型归因。

    orchestrator finally 恢复收据后（total_*=1100/13320），final_state=None
    但共享 WorkflowState.context_data 已被 generation 节点回填模型键——
    记账行不再是无上下文 0tok 的 no_generation_model，而是真实模型键 +
    measured 收据 + success=False（取消轮次如实记失败，成本照记）。
    """
    _tracker, row = await _run_cleanup(
        total_prompt_tokens=1100,
        total_completion_tokens=13320,
        final_state=None,
        context_data_fallback={
            "generation_model_key": "dashscope_chat",
            "generation_model_tier": "plus",
            "reasoning_mode": "deep",
            "chat_mode": "standard",
        },
        request_id="req-f573-cancel",
    )
    assert row["model"] == "dashscope_chat"
    assert row["prompt_tokens"] == 1100
    assert row["completion_tokens"] == 13320
    assert row["usage_source"] == "measured"  # 帧级收据是实测口径
    assert row["success"] is False  # 取消轮次如实记失败，但成本不归零
    assert row["cost"] is not None  # router 注册键可核价


@pytest.mark.asyncio
async def test_q04_red2_cancel_cleanup_without_context_stays_unattributed(_spawn_inline):
    """无兜底上下文的取消轮次：收据 token 照记，归因落 unattributed_model（非 0tok 无生成）。"""
    _tracker, row = await _run_cleanup(
        total_prompt_tokens=0,
        total_completion_tokens=13320,
        final_state=None,
        context_data_fallback=None,
        request_id="req-f573-cancel-noctx",
    )
    assert row["model"] == "unattributed_model"  # has_real_usage=True → 正确桶
    assert row["completion_tokens"] == 13320  # 收据入账，绝不记 0
    assert row["usage_source"] == "measured"
