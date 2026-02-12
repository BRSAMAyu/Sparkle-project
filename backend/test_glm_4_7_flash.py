"""
测试 GLM-4.7-Flash 模型配置

测试场景：
1. 非思考模式 - 快速响应
2. 思考模式 - 深度推理
"""
import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.core.llm_router import llm_router, ModelTier
from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import LLMService
from loguru import logger


async def test_model_selection():
    """测试模型选择逻辑"""
    print("\n" + "=" * 60)
    print("测试 1: 模型选择逻辑")
    print("=" * 60)

    # 测试 FAST tier (非思考模式)
    selection_fast = llm_router.select_specific_model(
        "glm_4_7_flash_no_thinking",
        agent_role=AgentRole.GENERATION
    )
    print(f"\n✓ FAST Tier 模型选择:")
    print(f"  - 模型: {selection_fast.config.model_name}")
    print(f"  - Provider: {selection_fast.config.provider.value}")
    print(f"  - Tier: {selection_fast.config.tier.value}")
    print(f"  - Clear Thinking: {selection_fast.config.clear_thinking}")
    print(f"  - 原因: {selection_fast.reason}")

    # 测试 REASONING tier (思考模式)
    selection_reasoning = llm_router.select_specific_model(
        "glm_4_7_flash_thinking",
        agent_role=AgentRole.GENERATION
    )
    print(f"\n✓ REASONING Tier 模型选择:")
    print(f"  - 模型: {selection_reasoning.config.model_name}")
    print(f"  - Provider: {selection_reasoning.config.provider.value}")
    print(f"  - Tier: {selection_reasoning.config.tier.value}")
    print(f"  - Clear Thinking: {selection_reasoning.config.clear_thinking}")
    print(f"  - 原因: {selection_reasoning.reason}")

    # 测试通过 AgentRole 自动选择
    selection_auto = llm_router.select_model(
        agent_role=AgentRole.CODE_AGENT,
        task_type=TaskType.DEEP_REASONING
    )
    print(f"\n✓ 自动选择 (Code Agent + Deep Reasoning):")
    print(f"  - 模型: {selection_auto.config.model_name}")
    print(f"  - Tier: {selection_auto.config.tier.value}")
    print(f"  - Clear Thinking: {selection_auto.config.clear_thinking}")


async def test_llm_service_integration():
    """测试 LLMService 集成"""
    print("\n" + "=" * 60)
    print("测试 2: LLMService 集成")
    print("=" * 60)

    # 创建非思考模式服务
    llm_service_fast = LLMService(
        agent_role=AgentRole.GENERATION,
        enable_dynamic_routing=True
    )

    # 强制使用非思考模式
    selection_fast = llm_router.select_specific_model("glm_4_7_flash_no_thinking")
    kwargs = llm_router.get_openai_client_kwargs(selection_fast)

    print(f"\n✓ 非思考模式配置:")
    print(f"  - Model: {kwargs['model']}")
    print(f"  - Base URL: {kwargs['base_url']}")
    print(f"  - Extra Body: {kwargs.get('extra_body', {})}")

    # 创建思考模式服务
    selection_reasoning = llm_router.select_specific_model("glm_4_7_flash_thinking")
    kwargs_reasoning = llm_router.get_openai_client_kwargs(selection_reasoning)

    print(f"\n✓ 思考模式配置:")
    print(f"  - Model: {kwargs_reasoning['model']}")
    print(f"  - Base URL: {kwargs_reasoning['base_url']}")
    print(f"  - Extra Body: {kwargs_reasoning.get('extra_body', {})}")


async def test_env_configuration():
    """测试环境变量配置"""
    print("\n" + "=" * 60)
    print("测试 3: 环境变量配置")
    print("=" * 60)

    from app.config import settings

    print(f"\n✓ GLM 配置:")
    print(f"  - ZHIPU_API_KEY: {'已设置' if settings.ZHIPU_API_KEY else '未设置'}")
    print(f"  - ZHIPU_BASE_URL: {settings.ZHIPU_BASE_URL}")
    print(f"  - ZHIPU_CHAT_MODEL: {settings.ZHIPU_CHAT_MODEL}")
    print(f"  - ZHIPU_FLASH_MODEL: {settings.ZHIPU_FLASH_MODEL}")
    print(f"  - GLM_4_7_FLASH_MODEL: {settings.GLM_4_7_FLASH_MODEL}")
    print(f"  - ZHIPU_TEMPERATURE: {settings.ZHIPU_TEMPERATURE}")


async def test_tier_mapping():
    """测试层级映射"""
    print("\n" + "=" * 60)
    print("测试 4: 层级映射")
    print("=" * 60)

    from app.core.agent_profiles import ModelTier

    print(f"\n✓ FREE_FAST Tier (免费快速) 模型列表:")
    free_fast_models = llm_router._tier_mapping.get(ModelTier.FREE_FAST, [])
    if free_fast_models:
        for i, model_key in enumerate(free_fast_models, 1):
            config = llm_router._available_models.get(model_key)
            if config:
                print(f"  {i}. {model_key}: {config.model_name} (clear_thinking={config.clear_thinking})")
    else:
        print("  (无模型)")

    print(f"\n✓ FREE_REASONING Tier (免费推理) 模型列表:")
    free_reasoning_models = llm_router._tier_mapping.get(ModelTier.FREE_REASONING, [])
    if free_reasoning_models:
        for i, model_key in enumerate(free_reasoning_models, 1):
            config = llm_router._available_models.get(model_key)
            if config:
                print(f"  {i}. {model_key}: {config.model_name} (clear_thinking={config.clear_thinking})")
    else:
        print("  (无模型)")

    print(f"\n✓ FAST Tier (付费快速) 模型列表:")
    fast_models = llm_router._tier_mapping.get(ModelTier.FAST, [])
    if fast_models:
        for i, model_key in enumerate(fast_models, 1):
            config = llm_router._available_models.get(model_key)
            if config:
                print(f"  {i}. {model_key}: {config.model_name} (clear_thinking={config.clear_thinking})")
    else:
        print("  (无模型)")

    print(f"\n✓ REASONING Tier (付费推理) 模型列表:")
    reasoning_models = llm_router._tier_mapping.get(ModelTier.REASONING, [])
    if reasoning_models:
        for i, model_key in enumerate(reasoning_models, 1):
            config = llm_router._available_models.get(model_key)
            if config:
                print(f"  {i}. {model_key}: {config.model_name} (clear_thinking={config.clear_thinking})")
    else:
        print("  (无模型)")

    # 显示所有可用的 tier
    print(f"\n✓ 所有可用的 ModelTier:")
    for tier in ModelTier:
        models = llm_router._tier_mapping.get(tier, [])
        print(f"  - {tier.value}: {len(models)} 个模型")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GLM-4.7-Flash 模型配置测试")
    print("=" * 60)

    try:
        await test_model_selection()
        await test_llm_service_integration()
        await test_env_configuration()
        await test_tier_mapping()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        print("\n📋 配置总结:")
        print("  - glm_4_7_flash_no_thinking: 非思考模式 (FAST tier)")
        print("  - glm_4_7_flash_thinking: 思考模式 (REASONING tier)")
        print("\n💡 使用方法:")
        print("  1. 在 .env 中设置 ZHIPU_API_KEY")
        print("  2. 使用 llm_router.select_specific_model() 选择模型")
        print("  3. 或通过 AgentRole 和 TaskType 自动选择")
        print()

    except Exception as e:
        logger.exception("测试失败")
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
