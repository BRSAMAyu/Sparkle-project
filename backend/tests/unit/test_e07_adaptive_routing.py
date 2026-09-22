"""E-07 三维自适应路由反馈环（quality/latency/cost）守卫。

红线契约（adaptive_routing.py 模块 docstring 的可测化）：
- 冷启动零介入：样本 < MIN_SAMPLES 或可比分 < 2 → 候选序 = E-02 既有策略输出；
- 只在已组装候选链内部稳定重排：输出恒为输入排列（永不引入新候选/跨 tier 提升）；
- 滞回 margin：首位分差 < MARGIN 不交换（评分抖动不引起候选顺序抖动）；
- 三维权重可调且归一；显式质量信号优先于成功率；窗口有界；未注册 key 拒收。

变异锚：把 reorder_candidates 的 margin 比较改为无条件交换 → margin 用例必红；
把候选过滤/引入逻辑加进重排 → 排列用例必红。
"""

from __future__ import annotations

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.core import routing_audit
from app.core.adaptive_routing import adaptive_routing_engine
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import llm_router


@pytest.fixture(autouse=True)
def _deterministic_router():
    """环境无关化（E-06 同款坑）：主仓 shell 若带 .env 真实 key，路由器池按
    key 过滤后与无 key 环境不同——清空全部 *_API_KEY 重建路由器，测试用
    确定性默认池；对象属性级替换（import 绑定不受影响），yield 后恢复。"""
    from app.config import settings as _s
    from app.core.llm_router import LLMRouter

    saved_state = dict(llm_router.__dict__)
    key_names = [k for k in vars(_s) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]
    saved_keys = {k: getattr(_s, k) for k in key_names}
    for k in key_names:
        setattr(_s, k, "")
    try:
        llm_router.__dict__.update(LLMRouter().__dict__)
        yield
    finally:
        llm_router.__dict__.clear()
        llm_router.__dict__.update(saved_state)
        for k, v in saved_keys.items():
            setattr(_s, k, v)

FAST_MODELS = list(llm_router._tier_mapping[ModelTier.FAST])
HEAD = "dashscope_fast"  # 2026-09 主力切 Qwen 后的 FAST 首位（原 deepseek_fast 降为次位）
RIVAL = "deepseek_fast"


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """隔离自适应统计/路由器健康态/审计 ring，防跨测试污染。"""
    saved_stats = dict(adaptive_routing_engine._stats)
    saved_health = dict(llm_router._model_health)
    adaptive_routing_engine._stats.clear()
    llm_router._model_health.clear()
    routing_audit.clear()
    yield
    adaptive_routing_engine._stats.clear()
    adaptive_routing_engine._stats.update(saved_stats)
    llm_router._model_health.clear()
    llm_router._model_health.update(saved_health)
    routing_audit.clear()


def _feed(
    model_key: str,
    n: int,
    *,
    latency_ms: float = 100.0,
    success: bool = True,
    cost_per_1k: float | None = 0.0001,
    quality: float | None = None,
) -> None:
    for _ in range(n):
        adaptive_routing_engine.record_outcome(
            model_key,
            latency_ms=latency_ms,
            success=success,
            quality=quality,
            cost_per_1k=cost_per_1k,
        )


def _reorder_counter() -> float:
    value = REGISTRY.get_sample_value("sparkle_llm_adaptive_reorder_total", {"trigger": "desirability"})
    return value or 0.0


# ---------------------------------------------------------------------------
# 冷启动零介入（E-02 语义保全）
# ---------------------------------------------------------------------------


def test_cold_start_no_samples_zero_intervention():
    """无任何样本：候选序必须原样返回（E-02 决策真源不被触碰）。"""
    candidates = list(FAST_MODELS)
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


def test_cold_start_below_min_samples_zero_intervention(monkeypatch):
    """样本不足 MIN_SAMPLES：即使延迟差异悬殊也不介入。"""
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_MIN_SAMPLES", 8, raising=False)
    _feed(HEAD, 7, latency_ms=8000.0)
    _feed(RIVAL, 7, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


def test_single_scored_model_zero_intervention():
    """可比分 < 2（只有 1 个模型有样本）：无比较基准，零介入。"""
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


def test_disabled_flag_zero_intervention(monkeypatch):
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_ENABLED", False, raising=False)
    _feed(HEAD, 10, latency_ms=8000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


# ---------------------------------------------------------------------------
# 重排安全性：恒为排列、不跨层、无分排后
# ---------------------------------------------------------------------------


def test_reorder_output_is_permutation_never_introduces_models():
    """输出必须是输入的排列——重排永不引入被策略剔除的候选（红线）。"""
    _feed(HEAD, 10, latency_ms=8000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL, "xiaomi_chat"]
    result = adaptive_routing_engine.reorder_candidates(candidates)
    assert sorted(result) == sorted(candidates)
    assert set(result) <= set(llm_router._tier_mapping[ModelTier.FAST])  # 未跨 tier


def test_unscored_models_rank_after_scored_models():
    """有分模型排前（按分降序），冷启动模型保持原相对序排后。"""
    _feed(HEAD, 10, latency_ms=6000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL, "xiaomi_chat"]  # xiaomi_chat 无样本（冷启动）
    result = adaptive_routing_engine.reorder_candidates(candidates)
    assert result == [RIVAL, HEAD, "xiaomi_chat"]


# ---------------------------------------------------------------------------
# 滞回 margin（防评分抖动）
# ---------------------------------------------------------------------------


def test_large_score_diff_swaps_head():
    """分差 ≥ margin：首位让位（deepseek 6s 延迟 vs dashscope 100ms）。"""
    _feed(HEAD, 10, latency_ms=6000.0)  # latency_score = 0（ref 5000ms）
    _feed(RIVAL, 10, latency_ms=100.0)  # latency_score ≈ 0.98
    candidates = [HEAD, RIVAL]
    result = adaptive_routing_engine.reorder_candidates(candidates)
    assert result[0] == RIVAL


def test_small_score_diff_keeps_original_order():
    """分差 < margin（默认 0.05）：评分噪声不引起顺序抖动。"""
    _feed(HEAD, 10, latency_ms=200.0)
    _feed(RIVAL, 10, latency_ms=100.0)
    # latency_score 0.96 vs 0.98，diff*wl = 0.006 << 0.05
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


def test_margin_is_upper_bound_even_for_large_diff(monkeypatch):
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_MARGIN", 5.0, raising=False)
    _feed(HEAD, 10, latency_ms=6000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


# ---------------------------------------------------------------------------
# 三维打分语义
# ---------------------------------------------------------------------------


def test_cost_dimension_alone_swaps_head(monkeypatch):
    """同延迟同质量：更便宜的模型按 cost 维胜出（free≈1.0）。

    归一参考设为 0.0002（HEAD 真实池价），使 cost 维差异不被默认 ref 0.01 稀释。
    """
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_COST_REF_PER_1K", 0.0002, raising=False)
    _feed(HEAD, 10, latency_ms=100.0, cost_per_1k=0.0002)  # cost_score = 0
    _feed(RIVAL, 10, latency_ms=100.0, cost_per_1k=0.0001)  # cost_score = 0.5
    # diff*wc = 0.1 ≥ margin
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates)[0] == RIVAL


def test_explicit_quality_signal_beats_success_rate():
    """显式质量信号优先于窗口成功率（eval/judge 回流语义）。"""
    # HEAD：全成功（成功率 quality=1.0），无显式信号
    _feed(HEAD, 10, latency_ms=100.0, cost_per_1k=0.0001)
    # RIVAL：半失败（成功率 0.5）但显式 quality=1.0 → 同为 1.0，总分打平 → 不换头
    _feed(RIVAL, 5, latency_ms=100.0, cost_per_1k=0.0001, success=True, quality=1.0)
    _feed(RIVAL, 5, latency_ms=100.0, cost_per_1k=0.0001, success=False, quality=1.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates

    # RIVAL 显式信号跌到 0 → 反超失败，HEAD 稳住首位
    adaptive_routing_engine._stats.clear()
    _feed(HEAD, 10, latency_ms=100.0, cost_per_1k=0.0001)
    _feed(RIVAL, 10, latency_ms=100.0, cost_per_1k=0.0001, quality=0.0, success=True)
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


def test_quality_input_is_clamped():
    """显式质量信号越界值被钳到 [0,1]。"""
    _feed(HEAD, 8, latency_ms=100.0, quality=42.0)
    head_score = adaptive_routing_engine.desirability(HEAD)
    adaptive_routing_engine._stats.clear()
    _feed(HEAD, 8, latency_ms=100.0, quality=1.0)
    assert adaptive_routing_engine.desirability(HEAD) == pytest.approx(head_score)


def test_weights_normalization_quality_only(monkeypatch):
    """权重归一：latency/cost 权重清零后，延迟差不再引发交换。"""
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_WEIGHT_QUALITY", 1.0, raising=False)
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_WEIGHT_LATENCY", 0.0, raising=False)
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_WEIGHT_COST", 0.0, raising=False)
    _feed(HEAD, 10, latency_ms=6000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    assert adaptive_routing_engine.reorder_candidates(candidates) == candidates


# ---------------------------------------------------------------------------
# 有界性（内存纪律）
# ---------------------------------------------------------------------------


def test_window_is_bounded(monkeypatch):
    monkeypatch.setattr(settings, "ADAPTIVE_ROUTING_WINDOW", 5, raising=False)
    _feed(HEAD, 20, latency_ms=100.0)
    assert adaptive_routing_engine.sample_count(HEAD) == 5


def test_unregistered_key_rejected():
    """未注册 model_key 拒收（内存有界、不造幽灵统计）。"""
    adaptive_routing_engine.record_outcome("ghost_model", latency_ms=10.0, success=True)
    assert adaptive_routing_engine.sample_count("ghost_model") == 0


# ---------------------------------------------------------------------------
# 可观测：重排留痕（审计 + Prometheus）
# ---------------------------------------------------------------------------


def test_reorder_is_audited_and_counted():
    before = _reorder_counter()
    _feed(HEAD, 10, latency_ms=6000.0)
    _feed(RIVAL, 10, latency_ms=50.0)
    candidates = [HEAD, RIVAL]
    result = adaptive_routing_engine.reorder_candidates(candidates)
    assert result[0] == RIVAL

    adaptive_records = routing_audit.recent(kind="adaptive")
    assert len(adaptive_records) == 1
    rec = adaptive_records[0]
    assert rec["subtype"] == "reorder"
    assert rec["from_model_key"] == HEAD
    assert rec["to_model_key"] == RIVAL
    assert _reorder_counter() == pytest.approx(before + 1)


def test_no_reorder_writes_no_audit():
    _feed(HEAD, 10, latency_ms=200.0)
    _feed(RIVAL, 10, latency_ms=100.0)
    adaptive_routing_engine.reorder_candidates([HEAD, RIVAL])
    assert routing_audit.recent(kind="adaptive") == []


# ---------------------------------------------------------------------------
# 端到端：select_model 消费自适应重排（接线完整性）
# ---------------------------------------------------------------------------


def test_select_model_applies_adaptive_reorder_end_to_end():
    """真实调用结果回流 → 选型首位按三维分切换（不跨 tier、仍属 FAST 池）。"""
    selection = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert selection.model_key == HEAD  # 前提：E-02 既有首位

    _feed(HEAD, 10, latency_ms=6000.0, cost_per_1k=0.0002)
    _feed(RIVAL, 10, latency_ms=100.0, cost_per_1k=0.0001)

    switched = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert switched.model_key == RIVAL
    assert switched.config.tier == ModelTier.FAST  # 未跨 tier 提升


def test_select_model_cold_start_unchanged_end_to_end():
    """无回流数据时选型与 E-02 既有输出逐字节一致（零回退语义）。"""
    baseline = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    _feed("xiaomi_chat", 20, latency_ms=1.0, cost_per_1k=0.0)  # 单模型有分，无比较
    after = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert after.model_key == baseline.model_key
