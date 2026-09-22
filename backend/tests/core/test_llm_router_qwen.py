"""
2026-09 主力模型切换（GLM → Qwen 通义千问）路由契约单测（全程 mock，零真实请求）。

红绿契约：
- LLMRouter 注册 Qwen 旗舰条目（qwen3_8_max / qwen3_8_max_top），MAX/TOP 层 Qwen 置首
- FAST / FREE_FAST / GLM_BATCH 各层 Qwen 置首；deepseek/xiaomi/GLM 条目全部保留为
  降级候选（GLM「保留待用」，零代码可回切）
- qwen3_7_flash_batch 仅在 DASHSCOPE_API_KEY 配置时注册（MiniMax 同款 key-gate），
  且永不进入主聊天能力层
- 降级链对新模型生效：TOP→MAX→PRO 逐级回落且落点为 Qwen 首位
- O-07 预算矩阵：free run 150k token 限额下，Qwen 各车道最坏成本均受控
  （MAX 层饱和场景 0.51 略超 $0.5 由 max_cost_usd 硬闸兜底，较原 GLM/DeepSeek 首位更优）
"""

from unittest.mock import patch

import pytest

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import ModelProvider, llm_router


def _rebuild_router(dashscope_key: str = "", minimax_key: str = ""):
    """以指定 key 重建路由器（模拟引擎进程启动时的 settings 快照）。"""
    from app.core.llm_router import LLMRouter

    with patch.object(settings, "DASHSCOPE_API_KEY", dashscope_key), patch.object(
        settings, "MINIMAX_API_KEY", minimax_key
    ):
        return LLMRouter()


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """环境无关化：清空 .env 注入的 *_API_KEY 与 LLM_TIER_* override。

    vars(settings) 对 pydantic Settings 枚举不到字段（静默无效——曾让主仓 .env 的
    LLM_TIER_* 钉死穿透进断言），故显式走 model_fields/__fields__。
    """
    field_names = set(getattr(settings, "model_fields", None) or getattr(settings, "__fields__", {}))
    for k in field_names:
        if k.endswith("_API_KEY") or k.startswith("LLM_TIER_"):
            monkeypatch.setattr(settings, k, "")


@pytest.fixture(autouse=True)
def _restore_global_router():
    """恢复全局单例快照，防 key-gated 重建污染同进程后续测试。"""
    saved = dict(llm_router.__dict__)
    yield
    llm_router.__dict__.clear()
    llm_router.__dict__.update(saved)


class TestQwenModelEntries:
    def test_flagship_entries_registered(self):
        router = _rebuild_router()
        max_cfg = router._available_models["qwen3_8_max"]
        top_cfg = router._available_models["qwen3_8_max_top"]
        assert max_cfg.provider == ModelProvider.DASHSCOPE
        assert max_cfg.model_name == settings.DASHSCOPE_MAX_MODEL
        assert max_cfg.tier == ModelTier.MAX
        assert top_cfg.tier == ModelTier.TOP
        # 定价锚点（USD/1k， blended 估算）
        assert max_cfg.cost_per_1k_tokens == pytest.approx(0.0034)

    def test_dashscope_lane_models_are_qwen_2026(self):
        router = _rebuild_router()
        assert router._available_models["dashscope_fast"].model_name == settings.DASHSCOPE_FAST_MODEL
        assert router._available_models["dashscope_standard_thinking"].model_name == settings.DASHSCOPE_STANDARD_MODEL
        assert router._available_models["dashscope_chat"].model_name == settings.DASHSCOPE_CHAT_MODEL
        assert router._available_models["dashscope_reason"].model_name == settings.DASHSCOPE_REASON_MODEL
        # PRO 层思考车道
        assert router._available_models["dashscope_reason"].thinking_mode == "enabled"

    def test_glm_entries_still_registered(self):
        """GLM 条目全部保留待用：不删条目、不逐出降级链。"""
        router = _rebuild_router()
        for key in (
            "glm_4_7_no_thinking",
            "glm_4_7_thinking",
            "glm_4_5_air_batch",
            "glm_4_6_batch",
            "glm_4_7_flash_no_thinking",
            "glm_4_7_flash_thinking",
            "glm_4_5_air_free",
            "glm_5_max",
            "glm_5_1_top",
            "glm_4_7_plus",
            "glm_4_7_pro",
        ):
            assert key in router._available_models, f"GLM 条目被误删: {key}"


class TestQwenPrimaryRouting:
    def test_capability_tiers_qwen_first(self):
        router = _rebuild_router()
        assert router._tier_mapping[ModelTier.FAST][0] == "dashscope_fast"
        assert router._tier_mapping[ModelTier.MAX][0] == "qwen3_8_max"
        assert router._tier_mapping[ModelTier.TOP][0] == "qwen3_8_max_top"
        assert router._tier_mapping[ModelTier.FREE_FAST][0] == "dashscope_fast"

    def test_generation_standard_lands_qwen(self):
        selection = llm_router.select_model(AgentRole.GENERATION, TaskType.STANDARD_RESPONSE)
        assert selection.config.provider == ModelProvider.DASHSCOPE
        assert selection.model_key == "dashscope_standard_thinking"

    def test_deep_reasoning_lands_qwen_pro(self):
        selection = llm_router.select_model(
            AgentRole.DEEP_ANALYST, TaskType.DEEP_REASONING, reasoning_mode="deep"
        )
        assert selection.config.provider == ModelProvider.DASHSCOPE
        assert selection.model_key in {"dashscope_reason", "dashscope_chat"}

    def test_forced_max_lands_flagship(self):
        selection = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
        assert selection.model_key == "qwen3_8_max"
        assert selection.config.provider == ModelProvider.DASHSCOPE

    def test_forced_top_lands_flagship_top(self):
        selection = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.TOP)
        assert selection.model_key == "qwen3_8_max_top"

    def test_legacy_glm_still_selectable(self):
        """保留待用 ≠ 不可用：GLM 条目仍可显式选中（回切演练面）。"""
        selection = llm_router.select_specific_model("glm_5_1_top", agent_role=AgentRole.GENERATION)
        assert selection.model_key == "glm_5_1_top"
        assert selection.config.provider == ModelProvider.ZHIPU


class TestQwenFallbackChain:
    def test_top_falls_back_to_max_flagship(self):
        failed = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.TOP)
        fallback = llm_router.get_fallback_model(failed)
        assert fallback.model_key == "qwen3_8_max"
        assert fallback.is_fallback is True

    def test_max_falls_back_to_pro_qwen_first(self):
        failed = llm_router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
        fallback = llm_router.get_fallback_model(failed)
        assert fallback.tier_used == ModelTier.PRO.value
        assert fallback.model_key in {"dashscope_reason", "glm_4_7_pro"}
        assert fallback.model_key == "dashscope_reason"  # Qwen 置首

    def test_max_chain_keeps_legacy_candidates(self):
        """MAX 层降级链保留 deepseek/glm 候选（Qwen 不健康时可回落）。"""
        chain = llm_router._tier_mapping[ModelTier.MAX]
        assert chain == ["qwen3_8_max", "deepseek_reason", "glm_5_max"]

    def test_unhealthy_flagship_falls_back_within_tier(self):
        router = _rebuild_router()
        for _ in range(10):
            router.report_model_failure("qwen3_8_max")
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)
        assert selection.model_key in {"deepseek_reason", "glm_5_max"}


class TestQwenBatchLane:
    def test_batch_entry_registered_when_key_present(self):
        router = _rebuild_router(dashscope_key="test-key")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert glm_batch_chain == ["qwen3_7_flash_batch"]
        # 新链（minimax/qwen batch）任一注册即不启用 GLM —— MM-M3 语义：
        # 批任务不静默回落付费 GLM，失败走 celery 重试
        assert "glm_4_7_no_thinking" not in glm_batch_chain
        selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.GLM_BATCH)
        assert selection.model_key == "qwen3_7_flash_batch"
        assert selection.config.model_name == settings.DASHSCOPE_BATCH_MODEL

    def test_batch_entry_absent_without_key(self):
        router = _rebuild_router(dashscope_key="")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert "qwen3_7_flash_batch" not in glm_batch_chain
        assert glm_batch_chain[0] == "glm_4_7_no_thinking"  # 原路由不变

    def test_batch_entry_never_enters_capability_tiers(self):
        router = _rebuild_router(dashscope_key="test-key")
        for tier in (
            ModelTier.FAST,
            ModelTier.STANDARD,
            ModelTier.PLUS,
            ModelTier.PRO,
            ModelTier.MAX,
            ModelTier.TOP,
            ModelTier.FREE_FAST,
        ):
            assert "qwen3_7_flash_batch" not in router._tier_mapping[tier]

    def test_minimax_ahead_of_qwen_when_both_keys_present(self):
        """用户指令（2026-09 batch 车道）：MiniMax M3（免费测试用）优先 → Qwen batch
        次位；任一注册即无 GLM（与 MM-M3「不静默回落 GLM」语义一致）。"""
        router = _rebuild_router(dashscope_key="test-key", minimax_key="test-key")
        glm_batch_chain = router._tier_mapping[ModelTier.GLM_BATCH]
        assert glm_batch_chain == ["minimax_m3_batch", "qwen3_7_flash_batch"]

    def test_capsule_explicit_plan_accepts_qwen_batch_key(self):
        """capsule 显式计划接受 qwen 车道键：失败回落 MiniMax 免费档（非 GLM）。"""
        from app.services.capsule_generation_service import ModelSelectionStrategy

        primary, fallbacks, thinking = ModelSelectionStrategy._normalize_explicit_model("qwen3_7_flash_batch")
        assert primary == "qwen3_7_flash_batch"
        assert fallbacks == ["minimax_m3_batch"]
        assert thinking is False


class TestBudgetMatrixQwen:
    """O-07 run 预算 × Qwen 定价的最坏成本面（free 150k token 限额）。"""

    def test_free_run_limits_unchanged(self):
        from app.core.budget_matrix import derive_default_run_budget

        limits = derive_default_run_budget("free")["limits"]
        assert limits["max_total_tokens"] == 150000
        assert limits["max_cost_usd"] == 0.5
        assert limits["max_tool_calls"] == 50
        assert limits["max_duration_seconds"] == 1800

    def _worst_case_cost(self, router, model_key: str, total_tokens: int = 150000) -> float:
        cfg = router._available_models[model_key]
        return cfg.cost_per_1k_tokens * total_tokens / 1000

    def test_qwen_main_lanes_fit_free_budget(self):
        router = _rebuild_router(dashscope_key="test-key")
        for key in ("dashscope_fast", "dashscope_standard_thinking", "dashscope_chat", "dashscope_reason"):
            worst = self._worst_case_cost(router, key)
            assert worst < 0.5, f"{key} 饱和成本 ${worst:.4f} 超 free run $0.5 闸"

    def test_flagship_saturation_marginally_over_but_improved(self):
        """MAX 层 150k 全饱和 = $0.51 略超 $0.5 硬闸（由 max_cost_usd 闸门截断，
        属预期语义）；较原首位 deepseek_reason($1.20)/glm_5_max($0.60) 显著改善。"""
        router = _rebuild_router(dashscope_key="test-key")
        worst_max = self._worst_case_cost(router, "qwen3_8_max")
        assert worst_max == pytest.approx(0.51)
        assert worst_max < self._worst_case_cost(router, "deepseek_reason")
        assert worst_max < self._worst_case_cost(router, "glm_5_max")


class TestQwenProfiles:
    def test_free_fast_profiles_prefer_qwen_first(self):
        from app.core.agent_profiles import agent_profile_registry

        for role in (AgentRole.ROUTER, AgentRole.RETRIEVAL, AgentRole.SEARCH_AGENT, AgentRole.STUDY_BUDDY):
            profile = agent_profile_registry.get_profile(role)
            assert profile.model_policy.preferred_models[0] == "dashscope_fast"
            assert "glm_4_7_flash_no_thinking" in profile.model_policy.preferred_models  # 保留待用

    def test_free_fast_tier_chain_qwen_first_glm_retained(self):
        chain = llm_router._tier_mapping[ModelTier.FREE_FAST]
        assert chain[0] == "dashscope_fast"
        assert chain[-2:] == ["glm_4_7_flash_thinking", "glm_4_5_air_free"]


class TestQwenClientKwargs:
    def test_qwen_selection_has_no_zhipu_extra_body(self):
        selection = llm_router.select_specific_model("qwen3_8_max", agent_role=AgentRole.GENERATION)
        kwargs = llm_router.get_openai_client_kwargs(selection)
        assert kwargs["base_url"].startswith("https://dashscope.aliyuncs.com/compatible-mode")
        assert "extra_body" not in kwargs  # clear_thinking/thinking 是 ZHIPU 车道专属

    def test_glm_lane_kwargs_unchanged(self):
        """GLM 保留车道的 wire 语义不受切换影响（coding 端点 thinking disabled）。"""
        selection = llm_router.select_specific_model("glm_4_7_no_thinking", agent_role=AgentRole.GENERATION)
        kwargs = llm_router.get_openai_client_kwargs(selection)
        assert kwargs["extra_body"]["clear_thinking"] is True
        assert kwargs["extra_body"]["thinking"] == {"type": "disabled"}
