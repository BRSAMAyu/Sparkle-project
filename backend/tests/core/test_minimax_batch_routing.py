"""
MiniMax M3 接入 glm_batch 异步分析池的路由单测（全程 mock，零真实请求）。

背景：MiniMax M3（token plan 免费档，并发硬上限 8）定位为"高性价比异步分析车道"。
用户决策（2026-09 MM-M3 batch）：配置 MINIMAX_API_KEY 后 glm_batch 车道默认档 =
MiniMax M3 **唯一候选**（GLM batch 条目【保留待用】默认不启用，仅作无 key 环境
原链兜底）；MiniMax 不健康时也不静默偷切 GLM —— 批任务失败 → celery 重试接管，
不静默假成功。显式回切 GLM 走 LLM_TIER_GLM_BATCH env 覆盖。
"""

from unittest.mock import patch

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier

_GLM_BATCH_KEYS = ["glm_4_7_no_thinking", "glm_4_7_thinking", "glm_4_5_air_batch", "glm_4_6_batch"]


def _rebuild_router(minimax_key: str, tier_override: str = ""):
    """以指定 MINIMAX_API_KEY 重建路由器（模拟引擎进程启动时的 settings 快照）。"""
    from app.core.llm_router import LLMRouter

    with patch.object(settings, "MINIMAX_API_KEY", minimax_key), patch.object(
        settings, "LLM_TIER_GLM_BATCH", tier_override
    ):
        return LLMRouter()


class TestRouterPoolEntry:
    def test_minimax_batch_pool_entry_registered_when_key_present(self):
        router = _rebuild_router("test-key")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        # 默认档 = MiniMax M3 唯一候选；GLM 条目从默认档移除
        assert glm_batch_chain == ["minimax_m3_batch"]

        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "minimax_m3_batch"
        assert selection.config.provider.value == "minimax"
        assert selection.config.model_name == settings.MINIMAX_CHAT_MODEL
        assert selection.config.base_url == settings.MINIMAX_BASE_URL

    def test_glm_batch_entries_kept_registered_but_not_in_default_tier(self):
        """GLM 条目【保留待用】：配置仍注册（可 env 覆盖/运行时回切），默认档不含。"""
        router = _rebuild_router("test-key")
        for key in _GLM_BATCH_KEYS:
            assert key in router._available_models, f"{key} 应保留注册（保留待用）"
            assert router._available_models[key].tier == ModelTier.GLM_BATCH
            assert key not in router._tier_mapping[ModelTier.GLM_BATCH]

    def test_glm_batch_restorable_via_env_override(self):
        """LLM_TIER_GLM_BATCH env 覆盖可把 GLM 加回默认档（回切通道）。"""
        router = _rebuild_router("test-key", tier_override="glm_4_6_batch,minimax_m3_batch")
        assert router._tier_mapping[ModelTier.GLM_BATCH] == ["glm_4_6_batch", "minimax_m3_batch"]

    def test_minimax_pool_entry_absent_without_key(self):
        router = _rebuild_router("")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert "minimax_m3_batch" not in glm_batch_chain
        assert glm_batch_chain == _GLM_BATCH_KEYS  # 无 key 环境 GLM 原链不变

        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "glm_4_7_no_thinking"

    def test_minimax_entry_never_enters_capability_tiers(self):
        """主聊天能力层（fast/standard/plus/pro/max/top）不得出现 minimax 池条目。"""
        router = _rebuild_router("test-key")
        capability_chains = [
            router._tier_mapping[t]
            for t in (
                ModelTier.FAST,
                ModelTier.STANDARD,
                ModelTier.PLUS,
                ModelTier.PRO,
                ModelTier.MAX,
                ModelTier.TOP,
                ModelTier.FREE_FAST,
                ModelTier.SPECIALIST,
            )
        ]
        for chain in capability_chains:
            assert "minimax_m3_batch" not in chain


class TestGLMBatchServiceSelection:
    def test_batch_model_key_minimax_only_when_registered(self):
        from app.services.glm_batch_service import GLMBatchService

        router = _rebuild_router("test-key")
        service = GLMBatchService()
        with patch("app.services.glm_batch_service.llm_router", router):
            assert service._select_batch_model_key(use_thinking=False, task_type="capsule_generation") == "minimax_m3_batch"
            assert service._select_batch_model_key(use_thinking=False, task_type="cognitive_analysis") == "minimax_m3_batch"
            assert service._select_batch_model_key(use_thinking=True, task_type="cognitive_analysis") == "minimax_m3_batch"

    def test_batch_model_key_falls_back_to_glm_without_key(self):
        from app.services.glm_batch_service import GLMBatchService

        router = _rebuild_router("")
        service = GLMBatchService()
        with patch("app.services.glm_batch_service.llm_router", router):
            assert service._select_batch_model_key(use_thinking=False, task_type="capsule_generation") == "glm_4_5_air_batch"
            assert service._select_batch_model_key(use_thinking=False, task_type="cognitive_analysis") == "glm_4_6_batch"
            assert service._select_batch_model_key(use_thinking=True, task_type="cognitive_analysis") == "glm_4_7_thinking"

    def test_batch_model_key_stays_minimax_when_unhealthy(self):
        """MiniMax 不健康不偷切 GLM（用户决策：批任务失败可重试，不静默假成功）。"""
        from app.services.glm_batch_service import GLMBatchService

        router = _rebuild_router("test-key")
        for _ in range(10):
            router.report_model_failure("minimax_m3_batch")
        service = GLMBatchService()
        with patch("app.services.glm_batch_service.llm_router", router):
            assert service._select_batch_model_key(use_thinking=False, task_type="capsule_generation") == "minimax_m3_batch"


class TestGLMBatchConcurrencyPool:
    def test_dispatch_pool_switches_to_minimax_when_registered(self):
        """车道默认档切 MiniMax 后，dispatch 拥塞信号读 minimax 池（而非 zhipu_coding）。"""
        from app.services.glm_batch_service import GLMBatchService
        from app.services.llm.concurrency import llm_concurrency

        service = GLMBatchService()
        with patch("app.services.glm_batch_service.llm_router", _rebuild_router("test-key")):
            assert GLMBatchService._active_concurrency_pool() == "minimax"
            assert service.get_runtime_limit() == llm_concurrency.get_runtime_limit("minimax")
            status = service.get_runtime_status()
            assert status["provider"] == "minimax"

        with patch("app.services.glm_batch_service.llm_router", _rebuild_router("")):
            assert GLMBatchService._active_concurrency_pool() == "zhipu_coding"
            assert service.get_runtime_limit() == llm_concurrency.get_runtime_limit("zhipu_coding")


class TestCapsuleExplicitModelPlan:
    def test_minimax_explicit_model_has_no_glm_fallbacks(self):
        from app.services.capsule_generation_service import ModelSelectionStrategy

        primary, fallbacks, thinking = ModelSelectionStrategy._normalize_explicit_model("minimax_m3_batch")
        assert primary == "minimax_m3_batch"
        assert fallbacks == []  # GLM 默认不启用：失败不偷切，celery 重试接管
        assert thinking is False

    def test_execution_plan_accepts_minimax_model_key(self):
        from app.services.capsule_generation_service import ModelSelectionStrategy

        plan = ModelSelectionStrategy.build_execution_plan(
            depth_preference=0.5,
            curiosity_preference=0.5,
            generation_type="daily",
            execution_mode="glm_batch",
            requested_count=1,
            model_key="minimax_m3_batch",
        )
        assert plan.primary_model == "minimax_m3_batch"
        assert plan.fallback_models == []
        assert plan.execution_mode == "glm_batch"

    def test_execution_plan_glm_batch_defaults_to_minimax_when_registered(self):
        """model_key 缺省（手动 send_task / dispatch 未带 key）时 glm_batch 默认档也是 MiniMax。"""
        from app.services.capsule_generation_service import ModelSelectionStrategy

        with patch.object(ModelSelectionStrategy, "_minimax_lane_registered", return_value=True):
            for depth in (0.1, 0.5, 0.9):
                plan = ModelSelectionStrategy.build_execution_plan(
                    depth_preference=depth,
                    curiosity_preference=0.5,
                    generation_type="daily",
                    execution_mode="glm_batch",
                    requested_count=1,
                )
                assert plan.primary_model == "minimax_m3_batch"
                assert plan.fallback_models == []

    def test_execution_plan_glm_batch_keeps_glm_chain_without_key(self):
        from app.services.capsule_generation_service import ModelSelectionStrategy

        with patch.object(ModelSelectionStrategy, "_minimax_lane_registered", return_value=False):
            shallow = ModelSelectionStrategy.build_execution_plan(
                depth_preference=0.1, curiosity_preference=0.5,
                generation_type="daily", execution_mode="glm_batch", requested_count=1,
            )
            assert shallow.primary_model == "glm_4_5_air_batch"  # 原链不变
            deep = ModelSelectionStrategy.build_execution_plan(
                depth_preference=0.9, curiosity_preference=0.5,
                generation_type="daily", execution_mode="glm_batch", requested_count=1,
            )
            assert deep.primary_model == "glm_4_7_thinking"


class TestPredictiveLongHorizonChain:
    """长时程预测链：MiniMax 注册时收敛为唯一候选（GLM 链保留待用）。"""

    @staticmethod
    def _chain(router):
        from app.services.predictive_service import PredictiveService

        service = PredictiveService(db=None)
        # 高复杂信号：complexity = 2+2+1+1+1 = 7 ≥ 6 → 走高复杂分支（原首选 glm_4_7_thinking）
        signals = {
            "pending_task_count": 6,
            "overdue_count": 1,
            "top_task_priority": 2,
            "focus_minutes_last_24h": 60,
            "study_records_last_7d": 8,
        }
        with patch("app.services.predictive_service.llm_router", router):
            return service._select_long_horizon_model_chain(signals)

    def test_chain_converges_to_minimax_when_registered(self):
        ordered, reason = self._chain(_rebuild_router("test-key"))
        assert ordered == ["minimax_m3_batch"]
        assert "MiniMax M3" in reason

    def test_chain_keeps_glm_preference_without_key(self):
        ordered, reason = self._chain(_rebuild_router(""))
        assert ordered[0] == "glm_4_7_thinking"  # 高复杂分支原首选
        assert "MiniMax" not in reason


class TestJSONParseThinkHardening:
    def test_parse_json_payload_strips_think_prefix_with_braces_inside(self):
        """<think> 思维链内含花括号时，旧解析器会锚定到思维链内的 '{' 而解析失败。"""
        from app.services.llm_service import LLMService

        raw = '<think>用户想分类 {TCP} 协议，先给个草稿 {"COSMOS": 0}</think>\n{"sector_weights": {"TECH": 100}}'
        parsed = LLMService._parse_json_payload(raw, response_kind="chat")
        assert parsed == {"sector_weights": {"TECH": 100}}

    def test_parse_json_payload_still_handles_bare_json(self):
        from app.services.llm_service import LLMService

        assert LLMService._parse_json_payload('{"a": 1}', response_kind="chat") == {"a": 1}
        assert LLMService._parse_json_payload('```json\n{"a": 1}\n```', response_kind="chat") == {"a": 1}


class TestProviderNameAndConcurrencyPool:
    def test_provider_name_resolves_minimax(self):
        from app.services.llm.providers import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(api_key="k", base_url="https://api.minimaxi.com/v1")
        assert provider._get_provider_name() == "minimax"

    def test_minimax_concurrency_pool_uses_lane_cap(self):
        from app.services.llm.concurrency import PROVIDER_CONFIGS, ProviderType, LLMConcurrencyManager

        assert ProviderType.MINIMAX in PROVIDER_CONFIGS
        assert PROVIDER_CONFIGS[ProviderType.MINIMAX].max_concurrent == settings.MINIMAX_MAX_CONCURRENCY
        manager = LLMConcurrencyManager()
        assert manager._get_provider_type("minimax") == ProviderType.MINIMAX


class TestSwitchSpecificModelDemoMode:
    def test_switch_to_keyed_model_clears_demo_mode(self):
        """显式切换到有 key 的模型必须重估 demo 模式（wt9 全链踩中：初始无 key 的
        selection 激活 demo_mode 后，glm_batch 切换 minimax_m3_batch 仍被 demo 短路）。"""
        import asyncio

        from app.core.llm_router import ModelConfig, ModelProvider, LLMSelection
        from app.services.llm_service import LLMService

        service = LLMService(agent_role="generation")
        service.demo_mode = True  # 模拟初始 selection 无 key 激活的 demo 模式

        keyed_selection = LLMSelection(
            model_key="minimax_m3_batch",
            config=ModelConfig(
                provider=ModelProvider.MINIMAX,
                model_name="MiniMax-M3",
                base_url="https://api.minimaxi.com/v1",
                api_key="test-key",
                tier=ModelTier.GLM_BATCH,
            ),
            agent_role=service.agent_role,
            task_type=None,
            reason="probe",
        )
        router_stub = type("RouterStub", (), {})()
        router_stub.select_specific_model = lambda *a, **kw: keyed_selection
        router_stub.get_openai_client_kwargs = lambda selection: {
            "api_key": selection.config.api_key,
            "base_url": selection.config.base_url,
            "model": selection.config.model_name,
            "temperature": selection.config.temperature,
            "max_tokens": selection.config.max_tokens,
        }

        with patch("app.services.llm_service.llm_router", router_stub):
            asyncio.get_event_loop_policy()
            asyncio.run(service.switch_to_specific_model("minimax_m3_batch"))

        assert service.demo_mode is False
        assert service.chat_model == "MiniMax-M3"
        assert service._current_selection.model_key == "minimax_m3_batch"
