"""
BATCH_LLM_PROVIDER 开关（B 线模型切换 2026-09-22）路由契约单测（全程 mock，零真实请求、零真实 key）。

语义（测试替换 = 开关可回滚）：
- "glm"（默认，回滚位）：batch 类调用走 GLM 原链；minimax_m3_batch /
  qwen3_7_flash_batch 不注册（key 即便配置也「保留配置不启用」）——GLM 路径
  与 MM-M3 决策合入前逐位一致。
- "minimax"：MM-M3+QWEN-PLAN 已验证车道（MiniMax M3 置首、Qwen batch 次位，
  均 key-gated；全无 key 环境 GLM 原链兜底）。
- 直连车道（error_book → minimax_provider）同受开关裁决，回滚不留半切换态。
- glm_batch 队列路由（celery task_routes 表 + 显式 queue= 覆盖双处）与本开关
  正交：本卡两处均不改，测试锁定其一致性。
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import ModelProvider, batch_llm_provider, llm_router

_GLM_BATCH_KEYS = ["glm_4_7_no_thinking", "glm_4_7_thinking", "glm_4_5_air_batch", "glm_4_6_batch"]
_CAPABILITY_TIERS = (
    ModelTier.FAST,
    ModelTier.STANDARD,
    ModelTier.PLUS,
    ModelTier.PRO,
    ModelTier.MAX,
    ModelTier.TOP,
)


def _rebuild_router(
    *,
    minimax_key: str = "",
    dashscope_key: str = "",
    batch_provider: str = "glm",
    tier_override: str = "",
):
    """以指定 settings 快照重建路由器（模拟引擎进程启动；fleet 惯例）。

    全部 key 为测试假值，任何路径都不发起真实请求。
    """
    from app.core.llm_router import LLMRouter

    with (
        patch.object(settings, "MINIMAX_API_KEY", minimax_key),
        patch.object(settings, "DASHSCOPE_API_KEY", dashscope_key),
        patch.object(settings, "BATCH_LLM_PROVIDER", batch_provider),
        patch.object(settings, "LLM_TIER_GLM_BATCH", tier_override),
    ):
        return LLMRouter()


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """环境无关化：*_API_KEY / LLM_TIER_* 清空，BATCH_LLM_PROVIDER 钉回代码默认。

    vars(settings) 对 pydantic Settings 枚举不到字段（静默无效），故显式走
    model_fields/__fields__（test_llm_router_qwen.py 同款惯例）。
    """
    field_names = set(getattr(settings, "model_fields", None) or getattr(settings, "__fields__", {}))
    for k in field_names:
        if k.endswith("_API_KEY") or k.startswith("LLM_TIER_"):
            monkeypatch.setattr(settings, k, "")
        elif k == "BATCH_LLM_PROVIDER":
            monkeypatch.setattr(settings, k, "glm")


@pytest.fixture(autouse=True)
def _restore_global_router():
    """恢复全局单例快照，防 key-gated 重建污染同进程后续测试。"""
    saved = dict(llm_router.__dict__)
    yield
    llm_router.__dict__.clear()
    llm_router.__dict__.update(saved)


# =============================================================================
# 1) 开关默认位（glm）：零变化契约
# =============================================================================


class TestSwitchDefaultGlm:
    def test_default_value_is_glm(self):
        """settings 默认值必须是 glm（回滚位；切换默认不在本卡内）。"""
        assert settings.BATCH_LLM_PROVIDER == "glm"

    def test_keys_present_but_switch_glm_entries_not_registered(self):
        """开关=glm + 双 key 配置：batch 专用条目不注册（保留配置不启用）。"""
        router = _rebuild_router(minimax_key="test-key", dashscope_key="test-key")
        assert "minimax_m3_batch" not in router._available_models
        assert "qwen3_7_flash_batch" not in router._available_models

    def test_switch_glm_batch_tier_is_legacy_glm_chain(self):
        """开关=glm：GLM_BATCH 链与 MM-M3 决策合入前原链逐位一致（零变化）。"""
        router = _rebuild_router(minimax_key="test-key", dashscope_key="test-key")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == _GLM_BATCH_KEYS
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "glm_4_7_no_thinking"
        assert selection.config.provider == ModelProvider.ZHIPU
        assert selection.config.tier == ModelTier.GLM_BATCH

    def test_switch_glm_glm_entries_kept_registered(self):
        """开关=glm：GLM 池条目仍全部注册（保留配置不删，供回滚/env 覆盖）。"""
        router = _rebuild_router(minimax_key="test-key")
        for key in _GLM_BATCH_KEYS:
            assert key in router._available_models, f"{key} 应保留注册（保留待用）"
            assert router._available_models[key].tier == ModelTier.GLM_BATCH

    def test_switch_glm_batch_entries_never_enter_capability_tiers(self):
        """主聊天能力层在任何开关位下都不得出现 batch 池条目。"""
        for provider_value in ("glm", "minimax"):
            router = _rebuild_router(minimax_key="test-key", dashscope_key="test-key", batch_provider=provider_value)
            for tier in _CAPABILITY_TIERS:
                chain = router._tier_mapping[tier]
                assert "minimax_m3_batch" not in chain
                assert "qwen3_7_flash_batch" not in chain

    def test_invalid_switch_value_falls_back_to_glm(self):
        """非法开关值安全回退 glm（与默认位同语义），绝不抛错。"""
        assert batch_llm_provider() == "glm"  # fixture 钉回默认
        with patch.object(settings, "BATCH_LLM_PROVIDER", "openai"):
            assert batch_llm_provider() == "glm"
        router = _rebuild_router(minimax_key="test-key", batch_provider="openai")
        assert "minimax_m3_batch" not in router._available_models
        assert router._tier_mapping[ModelTier.GLM_BATCH] == _GLM_BATCH_KEYS

    def test_switch_reader_tolerates_case_and_whitespace(self):
        """读取口归一：大小写/首尾空白容忍；空值回退 glm。"""
        with patch.object(settings, "BATCH_LLM_PROVIDER", " MiniMax "):
            assert batch_llm_provider() == "minimax"
        with patch.object(settings, "BATCH_LLM_PROVIDER", "GLM"):
            assert batch_llm_provider() == "glm"
        with patch.object(settings, "BATCH_LLM_PROVIDER", ""):
            assert batch_llm_provider() == "glm"

    def test_no_key_environment_switch_positions_identical(self):
        """无 key 环境：两个开关位解析结果完全一致（本仓测试环境基线）。"""
        glm_router = _rebuild_router(batch_provider="glm")
        minimax_router = _rebuild_router(batch_provider="minimax")
        assert (
            glm_router._tier_mapping[ModelTier.GLM_BATCH]
            == minimax_router._tier_mapping[ModelTier.GLM_BATCH]
            == _GLM_BATCH_KEYS
        )


# =============================================================================
# 2) 开关 minimax 位：MM-M3+QWEN-PLAN 已验证语义
# =============================================================================


class TestSwitchMinimax:
    def test_minimax_position_resolves_minimax_provider_and_model(self):
        """开关 glm→minimax：batch tier 解析到 MiniMax provider + MiniMax-M3。"""
        router = _rebuild_router(minimax_key="test-key", batch_provider="minimax")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == ["minimax_m3_batch"]
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "minimax_m3_batch"
        assert selection.config.provider == ModelProvider.MINIMAX
        assert selection.config.model_name == settings.MINIMAX_CHAT_MODEL
        assert selection.config.base_url == settings.MINIMAX_BASE_URL

    def test_minimax_position_qwen_second_when_minimax_keyless(self):
        """开关=minimax + 仅 DASHSCOPE key：Qwen batch 承接（MM-M3 前基线行为）。"""
        router = _rebuild_router(dashscope_key="test-key", batch_provider="minimax")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == ["qwen3_7_flash_batch"]
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.config.provider == ModelProvider.DASHSCOPE

    def test_minimax_position_both_keys_ordering(self):
        """开关=minimax + 双 key：MiniMax 置首、Qwen batch 次位。"""
        router = _rebuild_router(minimax_key="test-key", dashscope_key="test-key", batch_provider="minimax")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == [
            "minimax_m3_batch",
            "qwen3_7_flash_batch",
        ]

    def test_minimax_position_without_any_key_falls_back_to_glm_chain(self):
        """开关=minimax + 全无 key：GLM 原链兜底，车道保持可用（不空转）。"""
        router = _rebuild_router(batch_provider="minimax")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == _GLM_BATCH_KEYS
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "glm_4_7_no_thinking"

    def test_minimax_position_glm_entries_still_registered_not_in_tier(self):
        """开关=minimax：GLM 条目保留注册（保留待用）但不在默认档。"""
        router = _rebuild_router(minimax_key="test-key", batch_provider="minimax")
        for key in _GLM_BATCH_KEYS:
            assert key in router._available_models
            assert key not in router._tier_mapping[ModelTier.GLM_BATCH]

    def test_tier_override_still_wins_over_switch(self):
        """LLM_TIER_GLM_BATCH env 覆盖在开关之上仍生效（运维逃生通道不变）。"""
        router = _rebuild_router(
            minimax_key="test-key",
            batch_provider="minimax",
            tier_override="glm_4_6_batch,minimax_m3_batch",
        )
        assert router._tier_mapping[ModelTier.GLM_BATCH] == ["glm_4_6_batch", "minimax_m3_batch"]


# =============================================================================
# 3) 执行面一致性：glm_batch 执行器与直连车道同受开关裁决
# =============================================================================


class TestExecutorCoherence:
    def test_glm_batch_service_lane_registration_follows_switch(self):
        """glm_batch_service 的注册判定/并发池随开关切换（router 注册为唯一真源）。"""
        from app.services import glm_batch_service as mod

        router_glm = _rebuild_router(minimax_key="test-key", batch_provider="glm")
        with patch.object(mod, "llm_router", router_glm):
            assert mod.GLMBatchService._minimax_lane_registered() is False
            assert mod.GLMBatchService._active_concurrency_pool() == "zhipu_coding"

        router_minimax = _rebuild_router(minimax_key="test-key", batch_provider="minimax")
        with patch.object(mod, "llm_router", router_minimax):
            assert mod.GLMBatchService._minimax_lane_registered() is True
            assert mod.GLMBatchService._active_concurrency_pool() == "minimax"

    def test_capsule_strategy_lane_registration_follows_switch(self):
        """胶囊执行计划侧注册判定随开关切换（读全局 router 注册表）。"""
        from app.services.capsule_generation_service import ModelSelectionStrategy

        router_glm = _rebuild_router(minimax_key="test-key", batch_provider="glm")
        with patch.object(llm_router, "_available_models", router_glm._available_models):
            assert ModelSelectionStrategy._minimax_lane_registered() is False

        router_minimax = _rebuild_router(minimax_key="test-key", batch_provider="minimax")
        with patch.object(llm_router, "_available_models", router_minimax._available_models):
            assert ModelSelectionStrategy._minimax_lane_registered() is True

    def test_batch_worklane_resolution_follows_switch(self):
        """E-06 车道解析（router 真源）：glm 档落 GLM 原链、minimax 档落 M3。"""
        from app.services.batch_worklane import BatchWorkloadKind, batch_worklane

        kind = next(iter(BatchWorkloadKind))
        router_glm = _rebuild_router(minimax_key="test-key", batch_provider="glm")
        with patch("app.services.batch_worklane.llm_router", router_glm):
            selection = batch_worklane.resolve_selection(kind)
            assert selection.model_key == "glm_4_7_no_thinking"
            assert selection.config.provider == ModelProvider.ZHIPU

        router_minimax = _rebuild_router(minimax_key="test-key", batch_provider="minimax")
        with patch("app.services.batch_worklane.llm_router", router_minimax):
            selection = batch_worklane.resolve_selection(kind)
            assert selection.model_key == "minimax_m3_batch"
            assert selection.config.provider == ModelProvider.MINIMAX


class TestErrorBookDirectLaneGating:
    """error_book 直连 MiniMax 车道与开关联动（回滚必须全链生效）。"""

    @staticmethod
    def _make_service():
        from app.services.error_book_service import ErrorBookService

        return object.__new__(ErrorBookService)  # db 未触碰：_run_llm_analysis 不用 self.db

    def test_switch_glm_skips_minimax_lane(self):
        import app.services.error_book_service as mod

        svc = self._make_service()
        payload = '{"error_type": "concept_confusion", "error_type_label": "概念混淆"}'
        with (
            patch.object(settings, "BATCH_LLM_PROVIDER", "glm"),
            patch.object(mod, "minimax_provider") as mock_lane,
            patch.object(
                mod.llm_client, "chat_completion", new_callable=AsyncMock, return_value=payload
            ) as mock_primary,
        ):
            result = asyncio.run(svc._run_llm_analysis("math", "1+1=?", "3", "2", []))
        mock_lane.analyze.assert_not_called()
        mock_primary.assert_awaited_once()
        assert result["error_type"] == "concept_confusion"

    def test_switch_minimax_uses_minimax_lane(self):
        import app.services.error_book_service as mod

        svc = self._make_service()
        payload = '{"error_type": "calculation_error", "error_type_label": "计算错误"}'
        with (
            patch.object(settings, "BATCH_LLM_PROVIDER", "minimax"),
            patch.object(mod.minimax_provider, "analyze", new_callable=AsyncMock, return_value=payload) as mock_lane,
            patch.object(mod.llm_client, "chat_completion", new_callable=AsyncMock) as mock_primary,
        ):
            result = asyncio.run(svc._run_llm_analysis("math", "1+1=?", "3", "2", []))
        mock_lane.assert_awaited_once()
        mock_primary.assert_not_awaited()
        assert result["error_type"] == "calculation_error"

    def test_switch_minimax_lane_failure_still_falls_back_to_primary(self):
        """minimax 档下车道 busy/失败仍降级主 LLM 通道（既有降级语义保持）。"""
        import app.services.error_book_service as mod

        svc = self._make_service()
        payload = '{"error_type": "knowledge_gap", "error_type_label": "知识空缺"}'
        with (
            patch.object(settings, "BATCH_LLM_PROVIDER", "minimax"),
            patch.object(mod.minimax_provider, "analyze", new_callable=AsyncMock, side_effect=RuntimeError("busy")),
            patch.object(
                mod.llm_client, "chat_completion", new_callable=AsyncMock, return_value=payload
            ) as mock_primary,
        ):
            result = asyncio.run(svc._run_llm_analysis("math", "1+1=?", "3", "2", []))
        mock_primary.assert_awaited_once()
        assert result["error_type"] == "knowledge_gap"


# =============================================================================
# 4) glm_batch 队列路由双处一致性（本卡审计结论：两处均不改，锁定现状）
# =============================================================================

# 显式 queue= 覆盖位（与 celery task_routes 表并行的第二处路由定义）。
# 已审计（B-MODEL-SWITCH 2026-09-22）：generate_capsules_batch 三处在表内有同队列
# 条目（显式覆盖与表一致，属冗余而非分叉）；generate_long_horizon_prediction 不在
# 表内，显式覆盖是其唯一路由——两处定义互补，均不得漂移。
_EXPLICIT_QUEUE_SITES = [
    ("app/core/celery_app.py", "generate_capsules_batch"),
    ("app/api/v1/capsules.py", "generate_capsules_batch"),
    ("app/services/predictive_service.py", "generate_long_horizon_prediction"),
    ("app/services/push_strategies/empty_capsule.py", "generate_capsules_batch"),
]
_TASK_ROUTES_GLM_BATCH = {
    "batch_error_analysis",
    "analyze_error_batch",
    "generate_capsules_batch",
    "analyze_cognitive_fragment_batch",
    "classify_node_sector_batch",
}
_EXPLICIT_ONLY_TASKS = {"generate_long_horizon_prediction"}


class TestBatchQueueRoutingConsistency:
    def test_task_routes_table_routes_batch_tasks_to_glm_batch(self):
        """路由表处：五个 batch 任务 → glm_batch，且与 settings.GLM_BATCH_QUEUE 同源。"""
        from app.core.celery_app import celery_app

        routes = celery_app.conf.task_routes or {}
        for task_name in sorted(_TASK_ROUTES_GLM_BATCH):
            assert (
                routes.get(task_name, {}).get("queue") == settings.GLM_BATCH_QUEUE
            ), f"task_routes[{task_name}] 必须落 {settings.GLM_BATCH_QUEUE}（队列身份不得漂移）"
        assert settings.GLM_BATCH_QUEUE == "glm_batch"

    def test_explicit_queue_overrides_consistent_with_table(self):
        """显式覆盖处：已知四个调用位存在且任务名与表一致/在白名单内。"""
        backend_root = Path(__file__).resolve().parents[2]
        for rel_path, task_name in _EXPLICIT_QUEUE_SITES:
            text = (backend_root / rel_path).read_text(encoding="utf-8")
            assert 'queue="glm_batch"' in text, f"{rel_path} 的显式 queue= 覆盖位丢失"
            assert f'"{task_name}"' in text, f"{rel_path} 应投递 {task_name}"
            assert (
                task_name in _TASK_ROUTES_GLM_BATCH | _EXPLICIT_ONLY_TASKS
            ), f"{task_name} 未登记：新显式覆盖位必须登记本测试（表内或白名单）"

    def test_no_undocumented_explicit_glm_batch_queue_sites(self):
        """全仓唯一性：queue="glm_batch" 字面量只出现在已审计的四个文件。"""
        backend_root = Path(__file__).resolve().parents[2]
        hit_files = set()
        for py in sorted((backend_root / "app").rglob("*.py")):
            if 'queue="glm_batch"' in py.read_text(encoding="utf-8"):
                hit_files.add(py.relative_to(backend_root).as_posix())
        expected = {rel for rel, _ in _EXPLICIT_QUEUE_SITES}
        assert hit_files == expected, f"显式 glm_batch 覆盖位漂移：{sorted(hit_files ^ expected)}"

    def test_variable_queue_site_sources_from_settings(self):
        """变量覆盖位（glm_batch_service 统一投递面）队列名源自 settings.GLM_BATCH_QUEUE。"""
        from app.services.glm_batch_service import GLMBatchService

        assert GLMBatchService().queue_name == settings.GLM_BATCH_QUEUE
