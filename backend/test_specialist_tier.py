"""
测试 SPECIALIST 层级配置

验证专家模型（OCR、翻译）是否正确配置
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.llm_router import llm_router, ModelTier
from app.core.agent_profiles import AgentRole
from loguru import logger


async def test_specialist_tier():
    """测试 SPECIALIST tier 配置"""
    print("\n" + "=" * 60)
    print("SPECIALIST Tier 配置测试")
    print("=" * 60)

    # 检查 ModelTier 是否包含 SPECIALIST
    from app.core.agent_profiles import ModelTier
    tiers = [t.value for t in ModelTier]
    print(f"\n✓ 可用的 ModelTier:")
    for tier in ModelTier:
        print(f"  - {tier.value}")

    if "specialist" not in tiers:
        print("\n❌ SPECIALIST tier 未定义")
        return False

    # 检查 SPECIALIST tier 的模型配置
    specialist_models = llm_router._tier_mapping.get(ModelTier.SPECIALIST, [])
    print(f"\n✓ SPECIALIST Tier 模型列表 ({len(specialist_models)} 个):")
    if not specialist_models:
        print("  (无模型)")
        return False

    for i, model_key in enumerate(specialist_models, 1):
        config = llm_router._available_models.get(model_key)
        if config:
            print(f"  {i}. {model_key}:")
            print(f"     - Model: {config.model_name}")
            print(f"     - Provider: {config.provider.value}")
            print(f"     - Base URL: {config.base_url}")
            print(f"     - API Key: {'已设置' if config.api_key else '未设置'}")
            print(f"     - Temperature: {config.temperature}")
            print(f"     - Tier: {config.tier.value}")
        else:
            print(f"  {i}. {model_key}: (配置未找到)")

    return True


async def test_model_selection():
    """测试模型选择逻辑"""
    print("\n" + "=" * 60)
    print("模型选择测试")
    print("=" * 60)

    # 测试 OCR 模型选择
    ocr_selection = llm_router.select_specific_model(
        "siliconflow_ocr",
        agent_role=AgentRole.GENERATION
    )
    print(f"\n✓ OCR 模型选择（兼容 key: siliconflow_ocr）:")
    print(f"  - Model: {ocr_selection.config.model_name}")
    print(f"  - Tier: {ocr_selection.config.tier.value}")
    print(f"  - Provider: {ocr_selection.config.provider.value}")
    print(f"  - Reason: {ocr_selection.reason}")

    # 测试翻译模型选择
    translate_selection = llm_router.select_specific_model(
        "siliconflow_translate",
        agent_role=AgentRole.GENERATION
    )
    print(f"\n✓ 翻译模型选择:")
    print(f"  - Model: {translate_selection.config.model_name}")
    print(f"  - Tier: {translate_selection.config.tier.value}")
    print(f"  - Provider: {translate_selection.config.provider.value}")
    print(f"  - Reason: {translate_selection.reason}")


async def test_env_config():
    """测试环境变量配置"""
    print("\n" + "=" * 60)
    print("环境变量配置检查")
    print("=" * 60)

    from app.config import settings

    print(f"\n✓ Zhipu OCR 配置:")
    print(f"  - ZHIPU_API_KEY: {'已设置' if settings.ZHIPU_API_KEY else '未设置'}")
    print(f"  - ZHIPU_OCR_BASE_URL: {settings.ZHIPU_OCR_BASE_URL}")
    print(f"  - ZHIPU_OCR_MODEL: {settings.ZHIPU_OCR_MODEL}")

    print(f"\n✓ Hunyuan 翻译配置:")
    print(f"  - HUNYUAN_API_KEY: {'已设置' if settings.HUNYUAN_API_KEY else '未设置'}")
    print(f"  - HUNYUAN_BASE_URL: {settings.HUNYUAN_BASE_URL}")
    print(f"  - HUNYUAN_TRANSLATE_MODEL: {settings.HUNYUAN_TRANSLATE_MODEL}")


async def test_all_tiers():
    """显示所有 tier 的模型分布"""
    print("\n" + "=" * 60)
    print("所有 Tier 模型分布")
    print("=" * 60)

    from app.core.agent_profiles import ModelTier

    for tier in ModelTier:
        models = llm_router._tier_mapping.get(tier, [])
        print(f"\n{tier.value.upper()} ({len(models)} 个模型):")
        if models:
            for model_key in models:
                config = llm_router._available_models.get(model_key)
                if config:
                    print(f"  - {model_key}: {config.model_name}")
        else:
            print("  (无模型)")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("SPECIALIST Tier 配置验证")
    print("=" * 60)

    try:
        # 测试 tier 配置
        if not await test_specialist_tier():
            print("\n❌ SPECIALIST tier 配置失败")
            sys.exit(1)

        # 测试模型选择
        await test_model_selection()

        # 测试环境变量
        await test_env_config()

        # 显示所有 tier
        await test_all_tiers()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        print("\n📋 SPECIALIST Tier 总结:")
        print("  - siliconflow_ocr: GLM OCR (兼容旧 key，文档识别)")
        print("  - siliconflow_translate: Hunyuan MT (机器翻译)")
        print("\n💡 使用方法:")
        print("  selection = llm_router.select_specific_model('siliconflow_ocr')")
        print("  selection = llm_router.select_specific_model('siliconflow_translate')")
        print()

    except Exception as e:
        logger.exception("测试失败")
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
