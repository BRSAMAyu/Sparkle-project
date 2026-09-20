"""E-07 健康滞回 + FIX-23 键型对齐守卫。

红绿契约：
- FIX-23：健康上报按注册 model_key（历史死键：providers 按 model_name 上报、
  选型按 model_key 查——健康态在选型侧永远查不到）。变异锚：把上报键型改回
  model_name（死键）→ 本文件 test_fix23_* 必红。
- 滞回：unhealthy 相内在途旧成功不复活熔断；probation 相内 1 次失败立即回退
  且冷却翻倍（封顶有界）；probation 连续探针成功 → healthy。
- 回退真发生：provider 故障 → 选型切换；冷却后 → probation 回切通道；恢复
  确认 → healthy（完整容错）。
- 无风暴：健康抖动（在途成功/探针失败反复）下切换次数有界、冷却单调升级。
"""

from __future__ import annotations

import time

import pytest

from app.core import routing_audit
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMRouter, llm_router


@pytest.fixture(autouse=True)
def _deterministic_router():
    """环境无关化（E-06 同款坑）：主仓 shell 若带 .env 真实 key，路由器池按
    key 过滤后与无 key 环境不同——清空全部 *_API_KEY 重建路由器，测试用
    确定性默认池；对象属性级替换（import 绑定不受影响），yield 后恢复。"""
    from app.config import settings as _s
    from app.core.llm_router import LLMRouter as _R

    saved_state = dict(llm_router.__dict__)
    key_names = [k for k in vars(_s) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]
    saved_keys = {k: getattr(_s, k) for k in key_names}
    for k in key_names:
        setattr(_s, k, "")
    try:
        llm_router.__dict__.update(_R().__dict__)
        yield
    finally:
        llm_router.__dict__.clear()
        llm_router.__dict__.update(saved_state)
        for k, v in saved_keys.items():
            setattr(_s, k, v)
from app.services.llm_service import _report_call_outcome


@pytest.fixture
def router() -> LLMRouter:
    """全局 llm_router 单例（llm_service._report_call_outcome 硬绑定它）。

    健康态/审计隔离由 _isolate_global_state autouse 夹具负责。
    """
    return llm_router


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """隔离全局路由器健康态/自适应统计/审计 ring，防跨测试污染。"""
    from app.core.adaptive_routing import adaptive_routing_engine

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


def _trip(router: LLMRouter, model_key: str) -> None:
    for _ in range(router._model_health[model_key].FAILURE_THRESHOLD if model_key in router._model_health else 5):
        router.report_model_failure(model_key)


def _force_failures(router: LLMRouter, model_key: str, n: int = 5) -> None:
    for _ in range(n):
        router.report_model_failure(model_key)


# ---------------------------------------------------------------------------
# FIX-23 键型对齐（变异锚）
# ---------------------------------------------------------------------------


def test_fix23_report_via_real_call_chain_lands_on_model_key(router):
    """真实调用链（llm_service helper）上报后，健康态必须挂在 model_key 下。

    死键回归（按 model_name 上报）会让 _model_health 出现模型名键、而选型
    按 model_key 查——本断言双向锁死：model_key 有态 & model_name 无态。
    """
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    model_key = selection.model_key
    model_name = selection.config.model_name
    assert model_key != model_name  # 前提：键与名在本池不同（死键的历史形态）

    _report_call_outcome(selection, success=False, latency_ms=12.0)

    assert model_key in router._model_health, "健康态必须挂在选型用的 model_key 下"
    assert model_name not in router._model_health, "禁止按 model_name 制造死键"
    assert router._model_health[model_key].consecutive_failures == 1


def test_fix23_success_report_resets_failures_on_model_key(router):
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    _force_failures(router, selection.model_key, n=2)
    assert router._model_health[selection.model_key].consecutive_failures == 2

    _report_call_outcome(selection, success=True, latency_ms=30.0)

    state = router._model_health[selection.model_key]
    assert state.consecutive_failures == 0
    assert state.phase == "healthy"


def test_fix23_legacy_config_only_path_resolves_model_key(router):
    """legacy 路径只有 config（无 model_key attr）：按配置反查注册 key 上报。

    用 model_name 唯一的注册（mimo_pro / MiMo-V2.5）——deepseek_fast 等与
    default/deepseek_chat 共享 "deepseek-flash"，歧义场景被
    test_fix23_ambiguous_model_name_resolution_is_rejected 单独锁死。
    """
    legacy = type("obj", (object,), {"config": router._available_models["mimo_pro"]})  # 无 model_key
    _report_call_outcome(legacy, success=False)

    assert "mimo_pro" in router._model_health
    assert len(router._model_health) == 1


def test_fix23_unregistered_key_never_creates_dead_state(router):
    """未注册 key 拒收：不造死键（历史行为会创建任意键健康态）。"""
    router.report_model_failure("totally_unregistered_key")
    router.report_model_success("another_unregistered_key")
    assert "totally_unregistered_key" not in router._model_health
    assert "another_unregistered_key" not in router._model_health


def test_fix23_ambiguous_model_name_resolution_is_rejected(router):
    """多个注册共享同一 model_name 时反查必须放弃（宁缺毋滥）。"""
    cfg = router._available_models["deepseek_fast"]
    # 构造同 model_name 的第二个注册
    router._available_models["deepseek_fast_shadow"] = cfg
    try:
        assert router.resolve_model_key(cfg) is None
    finally:
        del router._available_models["deepseek_fast_shadow"]


# ---------------------------------------------------------------------------
# 滞回状态机
# ---------------------------------------------------------------------------


def test_hysteresis_trip_marks_unhealthy_and_skips_selection(router):
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    primary = selection.model_key
    _force_failures(router, primary, n=5)

    state = router._model_health[primary]
    assert state.phase == "unhealthy"
    assert state.is_healthy is False

    next_selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert next_selection.model_key != primary


def test_hysteresis_stale_success_does_not_revive(router):
    """滞回核心：unhealthy 相内在途旧成功不得解除熔断（旧契约=风暴向量）。"""
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    primary = selection.model_key
    _force_failures(router, primary, n=5)
    assert router._model_health[primary].phase == "unhealthy"

    # 切换前发出的在途请求此刻成功返回
    router.report_model_success(primary)

    assert router._model_health[primary].phase == "unhealthy"
    assert router._model_health[primary].is_healthy is False
    # 选型仍跳过
    assert router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST).model_key != primary


def test_hysteresis_cooldown_to_probation_then_probe_success_to_healthy(router):
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    primary = selection.model_key
    _force_failures(router, primary, n=5)
    state = router._model_health[primary]

    # 冷却走完（快进时钟）
    state.last_failure_at = time.monotonic() - state.cooldown_seconds - 1
    state.check_recovery()
    assert state.phase == "probation"
    assert state.is_healthy is True  # 可被选型（回切通道）

    # 探针成功未达标：仍是 probation
    for _ in range(state.PROBE_SUCCESS_THRESHOLD - 1):
        state.record_success()
    assert state.phase == "probation"

    # 达标 → healthy（冷却复位、失败容错恢复）
    state.record_success()
    assert state.phase == "healthy"
    assert state.cooldown_seconds == state.RECOVERY_SECONDS
    assert state.consecutive_failures == 0


def test_hysteresis_probation_failure_trips_back_with_escalating_cooldown(router):
    """probation 相 1 次失败立即回 unhealthy，冷却翻倍；封顶有界。"""
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    primary = selection.model_key
    _force_failures(router, primary, n=5)
    state = router._model_health[primary]
    base_cooldown = state.cooldown_seconds

    state.last_failure_at = time.monotonic() - base_cooldown - 1
    state.check_recovery()
    assert state.phase == "probation"

    state.record_failure()
    assert state.phase == "unhealthy"
    assert state.cooldown_seconds == pytest.approx(base_cooldown * 2)

    # 反复抖动：冷却单调升级且封顶（无风暴的数学上界）
    last = state.cooldown_seconds
    for _ in range(10):
        state.last_failure_at = time.monotonic() - state.cooldown_seconds - 1
        state.check_recovery()
        assert state.phase == "probation"
        state.record_failure()
        assert state.phase == "unhealthy"
        assert state.cooldown_seconds >= last
        assert state.cooldown_seconds <= state.COOLDOWN_MAX_SECONDS
        last = state.cooldown_seconds
    assert state.cooldown_seconds == state.COOLDOWN_MAX_SECONDS  # 封顶不再增长


def test_hysteresis_healthy_trip_keeps_base_cooldown(router):
    """healthy 相直接 trip（首次熔断）不升级冷却——只有 probation 跌落才翻倍。"""
    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    primary = selection.model_key
    state = router._model_health.get(primary)
    assert state is None  # 尚无健康态
    _force_failures(router, primary, n=5)
    state = router._model_health[primary]
    assert state.phase == "unhealthy"
    assert state.cooldown_seconds == state.RECOVERY_SECONDS  # 未翻倍


# ---------------------------------------------------------------------------
# 回退真发生 + 恢复后切回（选型视角，端到端）
# ---------------------------------------------------------------------------


def test_fallback_switch_and_recovery_switch_back(router):
    """注入 provider 故障 → 切走；恢复（冷却+探针）→ 切回原主选。"""
    primary = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST).model_key

    # provider 故障：连续失败触发熔断
    for _ in range(5):
        _report_call_outcome(
            type("S", (object,), {"model_key": primary, "config": router._available_models[primary]}),
            success=False,
            latency_ms=50.0,
        )
    switched = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert switched.model_key != primary, "故障期间必须切换到健康候选"

    # 恢复：冷却走完进入 probation，且 tier 内无其他候选故障 → probation 与健康同权
    # （稳定排序保持策略原序，主选回位=回切通道）
    state = router._model_health[primary]
    state.last_failure_at = time.monotonic() - state.cooldown_seconds - 1
    state.check_recovery()
    assert state.phase == "probation"

    # probation 期继续成功 → 恢复 healthy，主选位稳固
    for _ in range(state.PROBE_SUCCESS_THRESHOLD):
        _report_call_outcome(
            type("S", (object,), {"model_key": primary, "config": router._available_models[primary]}),
            success=True,
            latency_ms=40.0,
        )
    assert state.phase == "healthy"
    back = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert back.model_key == primary, "恢复后必须能切回原主选（自然回切）"


def test_no_storm_flapping_health_bounds_switches(router):
    """健康抖动场景：反复 trip/在途成功不得引起候选反复横跳。

    场景：主选反复「5 连败 trip → 在途成功试图复活 → 冷却 → probation →
    再失败」循环 6 轮。断言：
    - 在途成功从未复活 unhealthy（无横跳窗口）；
    - 冷却单调升级且封顶（切换频率有严格上界）；
    - 每轮 trip 都被审计留痕（切换原因可查）。
    """
    primary = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.FAST).model_key
    fake_sel = type("S", (object,), {"model_key": primary, "config": router._available_models[primary]})

    prev_cooldown = 0.0
    for _round in range(6):
        # trip
        for _ in range(5):
            _report_call_outcome(fake_sel, success=False, latency_ms=50.0)
        state = router._model_health[primary]
        assert state.phase == "unhealthy"
        assert state.cooldown_seconds >= prev_cooldown  # 单调不降（翻倍或封顶）
        assert state.cooldown_seconds <= state.COOLDOWN_MAX_SECONDS
        prev_cooldown = state.cooldown_seconds

        # 抖动：在途成功 ×3（旧契约下这会立即复活 → 风暴）
        for _ in range(3):
            _report_call_outcome(fake_sel, success=True, latency_ms=30.0)
        assert state.phase == "unhealthy", "在途成功不得复活熔断"

        # 冷却 → probation → 探针失败 → 立即回 unhealthy
        state.last_failure_at = time.monotonic() - state.cooldown_seconds - 1
        state.check_recovery()
        assert state.phase == "probation"
        _report_call_outcome(fake_sel, success=False, latency_ms=60.0)
        assert state.phase == "unhealthy"

    # 审计可查：故障相 outcome 记录在案（切换原因可查性）
    outcomes = routing_audit.recent(kind="outcome", limit=200)
    failed = [o for o in outcomes if o.get("model_key") == primary and o.get("success") is False]
    assert len(failed) >= 6 * 6


def test_probation_ranked_after_healthy_in_candidates(router):
    """probation 降权：tier 内有健康候选时，probation 不占首位。"""
    fast_models = list(router._tier_mapping[ModelTier.FAST])
    assert len(fast_models) >= 2
    probe = fast_models[0]
    healthy = fast_models[1]
    # probe 进入 probation
    _force_failures(router, probe, n=5)
    state = router._model_health[probe]
    state.last_failure_at = time.monotonic() - state.cooldown_seconds - 1
    state.check_recovery()
    assert state.phase == "probation"

    ordered = router._order_candidates_by_health(list(fast_models))
    assert ordered.index(healthy) < ordered.index(probe), "健康候选必须排在 probation 之前"
