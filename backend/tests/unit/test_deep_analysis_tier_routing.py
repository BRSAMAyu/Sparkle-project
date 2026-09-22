"""
deep_analysis 档真实路由 v4-pro（F-1）单元测试。

红绿契约（2026-09 主力切 Qwen 后更新锚点）：
- chat_mode=deep_analysis 的生成档决策默认落 MAX 层（2026-09 起 MAX 首位 =
  qwen3_8_max/qwen3.8-max；原首位 deepseek_reason→DEEPSEEK_REASON_MODEL=
  qwen3.8-flash 保留为降级候选），不再被策略路由/首触快响静默压回 flash
- DEEP_ANALYSIS_FORCE_FAST_TIER=True（延迟逃生阀）时退回 FAST 层
  （2026-09 起 FAST 首位 = dashscope_fast/qwen3.7-flash）
- standard 档语义不变：_deep_analysis_generation_tier 返回 None，
  STANDARD_CHAT_FORCE_FAST_TIER 首触快响路径保持原样
- 与免费层钳制正交：free 用户即使 deep_analysis 默认走 MAX，仍被钳到
  ceiling（fast）并带 free_tier_downgrade 标记与指标
"""
from __future__ import annotations

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import (
    LLMRouter,
    reset_request_user_tier,
    set_request_user_tier,
)


METRIC_FREE_DOWNGRADE = "sparkle_llm_router_free_tier_downgrade_total"


@pytest.fixture
def router() -> LLMRouter:
    """Fresh LLMRouter instance (isolated health state)."""
    return LLMRouter()


@pytest.fixture(autouse=True)
def _deterministic_router():
    """环境无关化：清空 .env 注入的 *_API_KEY 与 LLM_TIER_* override 后
    对象属性级重建单例路由器（与 test_e07_adaptive_routing 同款——
    LLMRouter 构造时快照 key/tier，主仓 .env 会让 wt 全绿的测试假红）。"""
    import app.core.llm_router as llm_router_mod

    saved = {k: v for k, v in vars(settings).items() if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")}
    saved_module = {k: v for k, v in vars(llm_router_mod).items() if k.startswith("LLM_TIER") or k in ("_TIER_MAP",)}
    for k in saved:
        setattr(settings, k, "")
    fresh = LLMRouter()
    llm_router_mod.llm_router.__dict__.update(fresh.__dict__)
    yield
    for k, v in saved.items():
        setattr(settings, k, v)
    for k, v in saved_module.items():
        setattr(llm_router_mod, k, v)
    restored = LLMRouter()
    llm_router_mod.llm_router.__dict__.update(restored.__dict__)


@pytest.fixture(autouse=True)
def _default_switch_off():
    """保证默认关闭逃生阀（即 deep_analysis 真实路由 MAX）。"""
    original = settings.DEEP_ANALYSIS_FORCE_FAST_TIER
    settings.DEEP_ANALYSIS_FORCE_FAST_TIER = False
    token = set_request_user_tier(None)
    yield
    settings.DEEP_ANALYSIS_FORCE_FAST_TIER = original
    reset_request_user_tier(token)


def _make_state(chat_mode: str, reasoning_mode: str = "balanced"):
    """构造最小 WorkflowState（仅用到 context_data 的两个字段）。"""
    from app.agents.standard_workflow import WorkflowState

    return WorkflowState(
        messages=[{"role": "user", "content": "帮我制定考研40天冲刺计划"}],
        context_data={"chat_mode": chat_mode, "reasoning_mode": reasoning_mode},
    )


def _free_downgrade_count(labels: dict[str, str]) -> float:
    # O-04：counter 增加 plan 有界维度；本文件的钳制计数断言均在 free plan 下发生。
    value = REGISTRY.get_sample_value(METRIC_FREE_DOWNGRADE, {**labels, "plan": "free"})
    return value or 0.0


# ---------------------------------------------------------------------------
# 档位决策（纯函数）
# ---------------------------------------------------------------------------


def test_deep_analysis_defaults_to_max_tier():
    from app.agents.standard_workflow import _deep_analysis_generation_tier

    assert _deep_analysis_generation_tier(_make_state("deep_analysis")) is ModelTier.MAX


def test_deep_analysis_escape_hatch_returns_fast(monkeypatch: pytest.MonkeyPatch):
    from app.agents.standard_workflow import _deep_analysis_generation_tier

    monkeypatch.setattr(settings, "DEEP_ANALYSIS_FORCE_FAST_TIER", True)
    assert _deep_analysis_generation_tier(_make_state("deep_analysis")) is ModelTier.FAST


def test_standard_chat_mode_returns_none():
    """standard 档不受影响：决策函数返回 None，保留首触快响/策略路由原语义。"""
    from app.agents.standard_workflow import (
        _deep_analysis_generation_tier,
        _should_force_fast_first_touch,
    )

    state = _make_state("standard", reasoning_mode="fast")
    assert _deep_analysis_generation_tier(state) is None
    # standard + fast 首触快响语义保持不变（STANDARD_CHAT_FORCE_FAST_TIER=True）
    assert getattr(settings, "STANDARD_CHAT_FORCE_FAST_TIER", True) is True
    assert _should_force_fast_first_touch(
        state, explicit_runtime=None, task_type=TaskType.STANDARD_RESPONSE
    )


# ---------------------------------------------------------------------------
# 路由选择（selection 落 MAX 层 v4-pro）
# ---------------------------------------------------------------------------


def test_deep_analysis_selection_lands_v4_pro(router: LLMRouter):
    """deep_analysis 生成 selection 必须落 MAX 层首位 qwen3_8_max（2026-09 主力切 Qwen）。"""
    state = _make_state("deep_analysis")
    from app.agents.standard_workflow import (
        _deep_analysis_generation_tier,
        _resolve_generation_task_type,
    )

    tier = _deep_analysis_generation_tier(state)
    assert tier is ModelTier.MAX

    selection = router.select_model(
        AgentRole.GENERATION,
        task_type=_resolve_generation_task_type(state),
        force_tier=tier,
        reasoning_mode="balanced",
        allow_max=tier == ModelTier.MAX,
    )
    # selection 归属高档（池条目自带 tier 标签可能是 MAX 或 PRO；本质断言是 model 与降级语义）
    assert selection.config.tier in (ModelTier.MAX, ModelTier.PRO)
    assert selection.model_key == "qwen3_8_max"  # MAX 层首位（2026-09 主力切 Qwen）
    assert selection.free_tier_downgrade is False


def test_deep_analysis_escape_hatch_selection_lands_flash(router: LLMRouter):
    """逃生阀开启时 selection 退回 FAST 层 dashscope_fast（首 token 延迟取向；2026-09 切 Qwen）。"""
    from app.agents.standard_workflow import (
        _deep_analysis_generation_tier,
        _resolve_generation_task_type,
    )

    settings.DEEP_ANALYSIS_FORCE_FAST_TIER = True
    state = _make_state("deep_analysis")

    tier = _deep_analysis_generation_tier(state)
    assert tier is ModelTier.FAST

    selection = router.select_model(
        AgentRole.GENERATION,
        task_type=_resolve_generation_task_type(state),
        force_tier=tier,
        reasoning_mode="balanced",
        allow_max=tier == ModelTier.MAX,
    )
    assert selection.config.tier == ModelTier.FAST
    assert selection.model_key == "dashscope_fast"  # FAST 首位（2026-09 主力切 Qwen）


# ---------------------------------------------------------------------------
# 与免费层钳制的组合（正交性）
# ---------------------------------------------------------------------------


def test_free_user_deep_analysis_still_clamped_to_fast(router: LLMRouter):
    """免费层钳制与 deep_analysis MAX 路由正交：free 用户仍被钳到 fast ceiling。"""
    set_request_user_tier("free")
    labels = {"agent_role": "generation", "from_tier": "max", "to_tier": "fast"}
    before = _free_downgrade_count(labels)

    from app.agents.standard_workflow import (
        _deep_analysis_generation_tier,
        _resolve_generation_task_type,
    )

    tier = _deep_analysis_generation_tier(_make_state("deep_analysis"))
    assert tier is ModelTier.MAX  # 决策不受用户分层影响

    selection = router.select_model(
        AgentRole.GENERATION,
        task_type=TaskType.DEEP_REASONING,
        force_tier=tier,
        reasoning_mode="balanced",
        allow_max=tier == ModelTier.MAX,
    )
    assert selection.config.tier == ModelTier.FAST  # 但钳制仍生效
    assert selection.model_key == "dashscope_fast"  # FAST 首位（2026-09 主力切 Qwen）
    assert selection.free_tier_downgrade is True
    assert "free_tier_downgrade(max->fast)" in selection.reason
    assert _free_downgrade_count(labels) == pytest.approx(before + 1)
