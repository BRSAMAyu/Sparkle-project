"""
TTFT-CFG：思考档分档配置 + 规划链预算收敛单测（全程 mock，零真实请求）。

红绿契约（依据 v3-output/TTFT-PROBE/REPORT.md 簇 A/簇 B 根因 + 主会话产品裁决）：
1. DashScope 思考开关分档（provider 分叉，非全局替换）：
   - FAST/STANDARD/PLUS（主聊天直出层）→ 线上注入 `enable_thinking: false`
   - PRO/MAX/TOP（深度分析层）→ 不注入（provider 默认思考开 = 保留思考，永不发 true
     以避免非流式/非混合模型 400）
   - DashScope 车道不再叠加 GLM 风格 `thinking:{"type":…}`（对 DashScope 无效——簇 B 根因）
   - GLM 车道 `thinking:{}` 现有发送保持不变；非 DashScope 的 thinking_mode 车道原样
2. planner 预算收敛：_LANGGRAPH_PLANNER_TIMEOUT_SECONDS 10s → 3s
3. 规划前置链 FAST 化 + 预算：
   - check_goal_quality LLM 走 force_tier=FAST，LLM 段 5s 封顶（超时落既有启发式兜底）
   - check_sufficiency LLM 精化走 FAST 车道，check 段 5s 封顶（超时继续通用链路）
   - asyncio.timeout 使用 `async with` 正确形态（上一卡修过 `asyncio.timeout(N)(fn)(…) 死码`）
"""

from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.config import settings
from app.core.llm_router import (
    ModelProvider,
    dashscope_enable_thinking_param,
    llm_router,
)
from app.services.llm_service import LLMService

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _rebuild_router() -> "object":
    from app.core.llm_router import LLMRouter

    with patch.object(settings, "DASHSCOPE_API_KEY", "test-dash-key"), patch.object(
        settings, "MINIMAX_API_KEY", ""
    ):
        return LLMRouter()


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """环境无关化：清空 .env 注入的 *_API_KEY 与 LLM_TIER_* override（防主仓钉死穿透）。"""
    field_names = set(getattr(settings, "model_fields", None) or getattr(settings, "__fields__", {}))
    for k in field_names:
        if k.endswith("_API_KEY") or k.startswith("LLM_TIER_"):
            monkeypatch.setattr(settings, k, "")


@pytest.fixture(autouse=True)
def _restore_global_router():
    """恢复全局单例快照，防重建污染同进程后续测试。"""
    saved = dict(llm_router.__dict__)
    yield
    llm_router.__dict__.clear()
    llm_router.__dict__.update(saved)


def _capture_handler(captured: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
        )

    return handler


async def _capture_wire_body(base_url: str, extra_body: dict) -> dict:
    """按引擎真实路径（get_openai_client_kwargs → SDK create）捕获线上 JSON payload。"""
    captured: dict = {}
    client = AsyncOpenAI(
        api_key="test-key",
        base_url=base_url,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(_capture_handler(captured))),
    )
    await client.chat.completions.create(
        model="model-test",
        messages=[{"role": "user", "content": "hi"}],
        extra_body=extra_body,
    )
    await client.close()
    return captured["body"]


# ---------------------------------------------------------------------------
# 1. 裁决一：DashScope 思考分档（enable_thinking 三态 + provider 分叉）
# ---------------------------------------------------------------------------


def test_dashscope_enable_thinking_param_three_states():
    """三态纯函数：主聊天直出层显式关；深思考层不注入；永不返回 True。"""
    assert dashscope_enable_thinking_param(ModelTier.FAST, None) is False
    assert dashscope_enable_thinking_param(ModelTier.STANDARD, "enabled") is False
    assert dashscope_enable_thinking_param(ModelTier.PLUS, None) is False
    # PRO/MAX/TOP 保留思考：不注入（None），即使 registered thinking_mode="enabled"
    assert dashscope_enable_thinking_param(ModelTier.PRO, "enabled") is None
    assert dashscope_enable_thinking_param(ModelTier.MAX, "enabled") is None
    assert dashscope_enable_thinking_param(ModelTier.TOP, "enabled") is None
    # 非能力层维持原状
    assert dashscope_enable_thinking_param(ModelTier.GLM_BATCH, None) is None
    assert dashscope_enable_thinking_param(ModelTier.FREE, None) is None
    # 契约：永不注入 true（规避非流式/非混合模型 400）
    values = {
        dashscope_enable_thinking_param(t, m)
        for t in ModelTier
        for m in (None, "enabled", "disabled")
    }
    assert True not in values


@pytest.mark.asyncio
async def test_dashscope_main_chat_lanes_wire_enable_thinking_false():
    """FAST/STANDARD/PLUS 三条主聊天车道 → 线上 payload 含 enable_thinking=false。"""
    router = _rebuild_router()
    for key in ("dashscope_fast", "dashscope_standard_thinking", "dashscope_chat"):
        selection = router.select_specific_model(key, agent_role=AgentRole.ROUTER)
        assert selection.config.provider == ModelProvider.DASHSCOPE
        kwargs = router.get_openai_client_kwargs(selection)
        body = await _capture_wire_body(selection.config.base_url, kwargs.get("extra_body") or {})
        assert body["enable_thinking"] is False, f"{key} 必须显式关思考"
        assert "thinking" not in body, f"{key} 不得携带 GLM 风格 thinking 参数"


@pytest.mark.asyncio
async def test_dashscope_deep_lanes_no_thinking_injection():
    """PRO/MAX/TOP 深度分析车道 → 不注入 enable_thinking（保留 provider 默认思考）。"""
    router = _rebuild_router()
    for key in ("dashscope_reason", "qwen3_8_max", "qwen3_8_max_top"):
        selection = router.select_specific_model(key, agent_role=AgentRole.ROUTER)
        kwargs = router.get_openai_client_kwargs(selection)
        assert kwargs.get("extra_body") is None, f"{key} 不应注入思考参数"
        body = await _capture_wire_body(selection.config.base_url, {})
        assert "enable_thinking" not in body
        assert "thinking" not in body


def test_glm_lane_wire_params_unchanged():
    """GLM 车道红线：thinking:{} 现有发送不被 DashScope 分叉波及。"""
    router = _rebuild_router()
    selection = router.select_specific_model("glm_4_7_no_thinking", agent_role=AgentRole.ROUTER)
    assert selection.config.provider == ModelProvider.ZHIPU
    kwargs = router.get_openai_client_kwargs(selection)
    assert kwargs["extra_body"] == {
        "clear_thinking": True,
        "thinking": {"type": "disabled"},
    }


def test_non_dashscope_thinking_mode_lane_unchanged():
    """非 DashScope（如 MIMO）带 thinking_mode → 仍走原 GLM 风格分支，不受分叉影响。"""
    from app.core.llm_router import LLMSelection

    selection = LLMSelection(
        model_key="xiaomi_chat",
        config=SimpleNamespace(
            provider=ModelProvider.XIAOMI,
            model_name="mimo-test",
            base_url="https://x.test",
            api_key="k",
            temperature=0.7,
            max_tokens=None,
            clear_thinking=None,
            tier=ModelTier.FAST,
            thinking_mode="enabled",
        ),
        agent_role=AgentRole.ROUTER,
        task_type=None,
        reason="test",
    )
    kwargs = llm_router.get_openai_client_kwargs(selection)
    assert "enable_thinking" not in kwargs  # 分叉只作用于 DASHSCOPE


class _FakeRawProvider:
    """暴露 .client 供 raw 路径捕获最终请求参数。"""

    def __init__(self, captured: dict, stream: bool = False):
        self.captured = captured
        self._stream = stream
        self.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=self._create))
        )

    async def _create(self, **params):
        self.captured.update(params)
        if self._stream:
            async def _gen():
                yield SimpleNamespace(choices=[])

            return _gen()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], usage=None
        )


@pytest.mark.asyncio
async def test_raw_stream_dashscope_sends_enable_thinking_not_glm_thinking():
    """主聊天流式路径（chat_stream_with_tools 底座）：DashScope 车道发 enable_thinking，不发 GLM 风格 thinking。"""
    router = _rebuild_router()
    selection = router.select_specific_model("dashscope_standard_thinking", agent_role=AgentRole.ROUTER)
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)
    service._current_selection = selection
    captured: dict = {}
    service._provider = _FakeRawProvider(captured, stream=True)

    chunks = [chunk async for chunk in service._create_raw_stream(selection, {"messages": []})]

    assert len(chunks) == 1
    assert captured["extra_body"] == {"enable_thinking": False}
    assert "thinking" not in captured["extra_body"]


@pytest.mark.asyncio
async def test_raw_completion_zhipu_keeps_glm_thinking_param():
    """raw 非流式路径红线：GLM 思考车道 thinking:{} 保持原样（分叉不全局替换）。"""
    router = _rebuild_router()
    selection = router.select_specific_model("glm_4_7_thinking", agent_role=AgentRole.ROUTER)
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)
    service._current_selection = selection
    captured: dict = {}
    service._provider = _FakeRawProvider(captured)

    await service._create_raw_completion(selection, {"messages": []})

    # glm_4_7_thinking 是标准端点思考车道：clear_thinking=False 且无 thinking disabled（V3-FIX-04 既有行为）
    assert captured["extra_body"]["clear_thinking"] is False
    assert "thinking" not in captured["extra_body"]
    assert "enable_thinking" not in captured["extra_body"]


# ---------------------------------------------------------------------------
# 2. 裁决二：planner 预算收敛 10s → 3s
# ---------------------------------------------------------------------------


def test_planner_timeout_constant_is_3s():
    """execution_engine planner 硬编码超时收敛为 3s（超时走兜底是既有语义）。"""
    from app.orchestration import execution_engine

    assert execution_engine._LANGGRAPH_PLANNER_TIMEOUT_SECONDS == 3.0


def test_planner_budget_is_used_at_wait_for_site():
    """wait_for 调用点必须引用收敛后的常量（防有人回填裸数字）。"""
    from pathlib import Path

    from app.orchestration import execution_engine

    # V3-FIX-120：锚定模块真实路径（原相对 cwd 路径在 CI 从仓库根跑全量时 FileNotFoundError）
    source = Path(execution_engine.__file__).read_text()
    assert "timeout=_LANGGRAPH_PLANNER_TIMEOUT_SECONDS" in source


# ---------------------------------------------------------------------------
# 3. 裁决三：前置链 FAST 车道 + 预算封顶
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_goal_quality_llm_uses_fast_tier(monkeypatch):
    """check_goal_quality 的 LLM 段必须 force_tier=FAST（短路 profile 策略）。"""
    from app.orchestration import goal_quality_evaluator as gqe_module
    from app.orchestration.goal_quality_evaluator import GoalQualityEvaluator

    captured: dict = {}

    async def _fake_service_factory(agent_role, force_tier, task_type=None, reasoning_mode=None):
        captured["args"] = (agent_role, force_tier, task_type)

        class _StubService:
            async def chat(self, messages, **kwargs):
                return json.dumps(
                    {"scores": {"specificity": 0.9, "measurability": 0.9, "time_bound": 0.9},
                     "summary": "ok", "clarification_questions": []}
                )

        return _StubService()

    monkeypatch.setattr(gqe_module, "get_configured_llm_service_for_tier", _fake_service_factory)

    evaluator = GoalQualityEvaluator()
    result = await evaluator._evaluate_with_llm(user_message="期末前把高数提到85分", conversation_context=[])

    assert result is not None and result.passed is True
    assert captured["args"][0] == AgentRole.ORCHESTRATOR
    assert captured["args"][1] == ModelTier.FAST
    assert captured["args"][2] == TaskType.QUICK_QUERY


@pytest.mark.asyncio
async def test_goal_quality_budget_exceeded_falls_back_to_heuristic(monkeypatch):
    """goal_quality LLM 段 5s 封顶：超时落既有启发式兜底，evaluate 不抛异常。"""
    from app.orchestration import goal_quality_evaluator as gqe_module
    from app.orchestration.goal_quality_evaluator import GoalQualityEvaluator

    monkeypatch.setattr(gqe_module, "GOAL_QUALITY_LLM_BUDGET_SECONDS", 0.05)

    evaluator = GoalQualityEvaluator()

    async def _slow_llm(*args, **kwargs):
        await asyncio.sleep(1.0)
        return None

    monkeypatch.setattr(evaluator, "_evaluate_with_llm", _slow_llm)

    t0 = time.perf_counter()
    result = await evaluator.evaluate(user_message="我想学好数学", intent="create_plan")
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.6, "超时必须在预算附近返回，而不是等满 LLM 时长"
    assert result.passed is False
    assert result.clarification_questions, "启发式兜底应给出澄清问题"


@pytest.mark.asyncio
async def test_sufficiency_llm_refinement_uses_fast_lane(monkeypatch):
    """check_sufficiency 的 LLM 精化必须走 FAST 车道（force_tier=FAST）。"""
    from app.orchestration import sufficiency_checker as sc_module
    from app.orchestration.sufficiency_checker import sufficiency_checker

    monkeypatch.setattr(sc_module, "_FAST_LANE_SERVICE", None)
    monkeypatch.setattr(sc_module, "_FAST_LANE_SERVICE_FAILED", False)

    captured: dict = {}

    async def _fake_service_factory(agent_role, force_tier, task_type=None, reasoning_mode=None):
        captured["args"] = (agent_role, force_tier, task_type)

        class _StubService:
            async def chat(self, messages, **kwargs):
                return '{"specific": false}'

        return _StubService()

    import app.services.llm_service as llm_service_module
    monkeypatch.setattr(llm_service_module, "get_configured_llm_service_for_tier", _fake_service_factory)

    specific = await sufficiency_checker._llm_refinement("create_plan", "帮我做个计划")

    assert specific is False
    assert captured["args"][0] == AgentRole.ORCHESTRATOR
    assert captured["args"][1] == ModelTier.FAST
    assert captured["args"][2] == TaskType.QUICK_QUERY


@pytest.mark.asyncio
async def test_sufficiency_check_budget_wraps_and_continues(monkeypatch):
    """check_sufficiency 整段封顶：超预算返回 (False, intent) 继续通用链路（既有 continuing 语义）。"""
    from app.gen.agent.v1 import agent_service_pb2
    from app.orchestration import validation_engine as ve_module
    from app.orchestration.sufficiency_checker import SufficiencyCheckResult, SufficiencyStatus
    from app.orchestration.validation_engine import ValidationEngineMixin

    monkeypatch.setattr(ve_module, "SUFFICIENCY_CHECK_BUDGET_SECONDS", 0.05)

    async def _slow_check(**kwargs):
        await asyncio.sleep(1.0)
        return SufficiencyCheckResult(status=SufficiencyStatus.SUFFICIENT)

    import app.orchestration.sufficiency_checker as sc_module
    monkeypatch.setattr(sc_module.sufficiency_checker, "check", _slow_check)

    import app.services.shadow_prediction_service as sps_module
    monkeypatch.setattr(
        sps_module.shadow_prediction_service,
        "predict_intent_only",
        AsyncMock(return_value={"intent_type": "create_plan"}),
    )

    host = ValidationEngineMixin.__new__(ValidationEngineMixin)

    async def _no_preflight(**kwargs):
        return False

    host._check_phase_a_planning_preflight = _no_preflight

    t0 = time.perf_counter()
    handled, intent_type = await host._check_sufficiency(
        request=agent_service_pb2.ChatRequest(),
        user_message="帮我做一个期末冲刺计划",
        user_id="u1",
        plan_id=None,
        session_id=None,
        conversation_context=None,
        user_context_payload=None,
        plan_context=None,
        state=None,
        active_db=None,
        session_feedback_signal=None,
        stream_callback=None,
        queue=None,
    )
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.6, "超时必须在预算附近返回，而不是等满 check 时长"
    assert handled is False
    assert intent_type == "create_plan"


def test_budget_wraps_use_async_with_form_not_dead_code():
    """红线防回归：预算包装必须是 `async with asyncio.timeout(...)` 正确形态，
    不得回退到 `asyncio.timeout(N)(fn)(...)` 死码（上一卡 TTFT-PROBE 修过的陷阱）。"""
    from pathlib import Path

    import app.orchestration.goal_quality_evaluator as gqe_module
    import app.orchestration.validation_engine as ve_module

    # V3-FIX-120：锚定模块真实路径（原相对 cwd 路径在 CI 从仓库根跑全量时 FileNotFoundError）
    gqe_source = Path(gqe_module.__file__).read_text()
    ve_source = Path(ve_module.__file__).read_text()

    assert "async with asyncio.timeout(GOAL_QUALITY_LLM_BUDGET_SECONDS):" in gqe_source
    assert "async with asyncio.timeout(SUFFICIENCY_CHECK_BUDGET_SECONDS):" in ve_source
    for source in (gqe_source, ve_source):
        timeout_lines = [line.strip() for line in source.splitlines() if "asyncio.timeout" in line]
        assert not any(
            ")(" in line for line in timeout_lines
        ), "asyncio.timeout 不得作为可调用对象使用（死码形态）"
