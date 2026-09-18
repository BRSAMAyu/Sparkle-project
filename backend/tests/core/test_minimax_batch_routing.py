"""
MiniMax M3 接入 glm_batch 异步分析池的路由单测（全程 mock，零真实请求）。

背景：MiniMax M3（token plan 免费档，并发硬上限 8）定位为"高性价比异步分析车道"。
glm_batch 队列任务（generate_capsules_batch / analyze_cognitive_fragment_batch /
classify_node_sector_batch / batch_error_analysis）此前全部落在 glm_* 池条目上，
本组测试锁定：配置了 MINIMAX_API_KEY 时 glm_batch tier 解析到 minimax 池条目，
未配置时保持 glm 原路由（无 key 环境零行为变化）。
"""

from unittest.mock import patch

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier


def _rebuild_router(minimax_key: str):
    """以指定 MINIMAX_API_KEY 重建路由器（模拟引擎进程启动时的 settings 快照）。"""
    from app.core.llm_router import LLMRouter

    with patch.object(settings, "MINIMAX_API_KEY", minimax_key):
        return LLMRouter()


class TestRouterPoolEntry:
    def test_minimax_batch_pool_entry_registered_when_key_present(self):
        router = _rebuild_router("test-key")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert glm_batch_chain[0] == "minimax_m3_batch"
        assert "glm_4_7_no_thinking" in glm_batch_chain  # glm 降级链保留

        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "minimax_m3_batch"
        assert selection.config.provider.value == "minimax"
        assert selection.config.model_name == settings.MINIMAX_CHAT_MODEL
        assert selection.config.base_url == settings.MINIMAX_BASE_URL

    def test_minimax_pool_entry_absent_without_key(self):
        router = _rebuild_router("")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert "minimax_m3_batch" not in glm_batch_chain
        assert glm_batch_chain[0] == "glm_4_7_no_thinking"  # 原路由不变

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
    def test_batch_model_key_prefers_minimax_when_registered(self):
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

    def test_batch_model_key_falls_back_to_glm_when_minimax_unhealthy(self):
        from app.services.glm_batch_service import GLMBatchService

        router = _rebuild_router("test-key")
        router.report_model_failure("minimax_m3_batch")
        for _ in range(10):
            router.report_model_failure("minimax_m3_batch")
        service = GLMBatchService()
        with patch("app.services.glm_batch_service.llm_router", router):
            assert service._select_batch_model_key(use_thinking=False, task_type="capsule_generation") == "glm_4_5_air_batch"


class TestCapsuleExplicitModelPlan:
    def test_minimax_explicit_model_maps_to_glm_fallbacks(self):
        from app.services.capsule_generation_service import ModelSelectionStrategy

        primary, fallbacks, thinking = ModelSelectionStrategy._normalize_explicit_model("minimax_m3_batch")
        assert primary == "minimax_m3_batch"
        assert fallbacks == ["glm_4_5_air_batch", "glm_4_6_batch"]
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
        assert plan.fallback_models == ["glm_4_5_air_batch", "glm_4_6_batch"]
        assert plan.execution_mode == "glm_batch"


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
