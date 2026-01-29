"""
测试所有 API Key 配置

验证所有服务的 API key 是否正确配置
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings


def test_api_keys():
    """测试所有 API Key 配置"""
    print("\n" + "=" * 60)
    print("API Key 配置验证")
    print("=" * 60)

    # XiaoMi MIMO
    print(f"\n✓ XiaoMi MIMO:")
    print(f"  - API Key: {'已配置' if settings.XIAOMI_MIMO_API_KEY and settings.XIAOMI_MIMO_API_KEY != 'your_xiaomi_mimo_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.XIAOMI_MIMO_BASE_URL}")
    print(f"  - Chat Model: {settings.XIAOMI_CHAT_MODEL}")
    print(f"  - Temperature: {settings.XIAOMI_TEMPERATURE}")

    # Zhipu GLM
    print(f"\n✓ Zhipu GLM:")
    print(f"  - API Key: {'已配置' if settings.ZHIPU_API_KEY and settings.ZHIPU_API_KEY != 'your_zhipu_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.ZHIPU_BASE_URL}")
    print(f"  - Chat Model: {settings.ZHIPU_CHAT_MODEL}")
    print(f"  - Flash Model: {settings.ZHIPU_FLASH_MODEL}")
    print(f"  - GLM-4.7-Flash: {settings.GLM_4_7_FLASH_MODEL}")

    # DashScope
    print(f"\n✓ DashScope (阿里云):")
    print(f"  - API Key: {'已配置' if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != 'your_dashscope_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.DASHSCOPE_BASE_URL_COMPATIBLE}")
    print(f"  - Chat Model: {settings.DASHSCOPE_CHAT_MODEL}")
    print(f"  - Embedding Model: {settings.DASHSCOPE_EMBEDDING_MODEL}")
    print(f"  - Rerank Model: {settings.DASHSCOPE_RERANK_MODEL}")

    # DeepSeek
    print(f"\n✓ DeepSeek:")
    print(f"  - API Key: {'已配置' if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != 'your_deepseek_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.DEEPSEEK_BASE_URL}")
    print(f"  - Chat Model: {settings.DEEPSEEK_CHAT_MODEL}")
    print(f"  - Reason Model: {settings.DEEPSEEK_REASON_MODEL}")

    # SiliconFlow
    print(f"\n✓ SiliconFlow:")
    print(f"  - API Key: {'已配置' if settings.SILICONFLOW_API_KEY and settings.SILICONFLOW_API_KEY != 'your_siliconflow_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.SILICONFLOW_BASE_URL}")
    print(f"  - OCR Model: {settings.SILICONFLOW_OCR_MODEL}")
    print(f"  - Embedding Model: {settings.SILICONFLOW_EMBEDDING_MODEL}")
    print(f"  - Rerank Model: {settings.SILICONFLOW_RERANK_MODEL}")

    # Hunyuan Translation
    print(f"\n✓ Hunyuan Translation:")
    print(f"  - API Key: {'已配置' if settings.HUNYUAN_API_KEY and settings.HUNYUAN_API_KEY != 'your_hunyuan_api_key' else '未配置'}")
    print(f"  - Base URL: {settings.HUNYUAN_BASE_URL}")
    print(f"  - Translate Model: {settings.HUNYUAN_TRANSLATE_MODEL}")

    # XunFei STT
    print(f"\n✓ XunFei STT (科大讯飞):")
    print(f"  - API Key: {'已配置' if settings.XUNFEI_API_KEY and settings.XUNFEI_API_KEY != 'your_xunfei_api_key_here' else '未配置'}")
    print(f"  - API Secret: {'已配置' if settings.XUNFEI_API_SECRET and settings.XUNFEI_API_SECRET != 'your_xunfei_api_secret_here' else '未配置'}")
    print(f"  - Domain: {settings.XUNFEI_STT_DOMAIN}")
    print(f"  - Language: {settings.XUNFEI_STT_LANGUAGE}")

    # Embedding & Rerank
    print(f"\n✓ Embedding & Rerank:")
    print(f"  - Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    print(f"  - Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"  - Rerank Provider: {settings.RERANK_PROVIDER}")
    print(f"  - Rerank Model: {settings.RERANK_MODEL}")
    print(f"  - Reranker Enabled: {settings.RERANKER_ENABLED}")

    # Demo Mode
    print(f"\n✓ Demo Mode:")
    print(f"  - 状态: {'启用' if settings.DEMO_MODE else '禁用'}")
    if settings.DEMO_MODE:
        print(f"  ⚠️  警告: Demo Mode 已启用，将返回模拟响应")


def verify_api_keys_format():
    """验证 API Key 格式"""
    print(f"\n" + "=" * 60)
    print("API Key 格式验证")
    print("=" * 60)

    issues = []

    # XiaoMi MIMO
    if not settings.XIAOMI_MIMO_API_KEY.startswith("sk-"):
        issues.append("XIAOMI_MIMO_API_KEY 格式不正确，应以 'sk-' 开头")

    # Zhipu GLM
    if "." not in settings.ZHIPU_API_KEY:
        issues.append("ZHIPU_API_KEY 格式不正确，应包含 '.' 分隔符")

    # DashScope
    if not settings.DASHSCOPE_API_KEY.startswith("sk-"):
        issues.append("DASHSCOPE_API_KEY 格式不正确，应以 'sk-' 开头")

    # DeepSeek
    if not settings.DEEPSEEK_API_KEY.startswith("sk-"):
        issues.append("DEEPSEEK_API_KEY 格式不正确，应以 'sk-' 开头")

    # SiliconFlow
    if not settings.SILICONFLOW_API_KEY.startswith("sk-"):
        issues.append("SILICONFLOW_API_KEY 格式不正确，应以 'sk-' 开头")

    # XunFei
    if len(settings.XUNFEI_API_SECRET) < 10:
        issues.append("XUNFEI_API_SECRET 长度不足")

    if issues:
        print(f"\n❌ 发现问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ 所有 API Key 格式正确")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("API 配置完整验证")
    print("=" * 60)

    try:
        test_api_keys()
        verify_api_keys_format()

        print("\n" + "=" * 60)
        print("✅ 配置验证完成")
        print("=" * 60)

        # 统计
        total_keys = 7
        configured_keys = sum([
            1 if settings.XIAOMI_MIMO_API_KEY and settings.XIAOMI_MIMO_API_KEY != 'your_xiaomi_mimo_api_key' else 0,
            1 if settings.ZHIPU_API_KEY and settings.ZHIPU_API_KEY != 'your_zhipu_api_key' else 0,
            1 if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != 'your_dashscope_api_key' else 0,
            1 if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != 'your_deepseek_api_key' else 0,
            1 if settings.SILICONFLOW_API_KEY and settings.SILICONFLOW_API_KEY != 'your_siliconflow_api_key' else 0,
            1 if settings.HUNYUAN_API_KEY and settings.HUNYUAN_API_KEY != 'your_hunyuan_api_key' else 0,
            1 if settings.XUNFEI_API_KEY and settings.XUNFEI_API_KEY != 'your_xunfei_api_key_here' else 0,
        ])

        print(f"\n📊 配置统计:")
        print(f"  - 已配置: {configured_keys}/{total_keys}")
        print(f"  - 配置率: {configured_keys/total_keys*100:.1f}%")

        if configured_keys == total_keys and not settings.DEMO_MODE:
            print(f"\n🎉 所有 API Key 已正确配置，Demo Mode 已禁用")
        elif configured_keys == total_keys and settings.DEMO_MODE:
            print(f"\n⚠️  所有 API Key 已配置，但 Demo Mode 仍启用")
        else:
            print(f"\n⚠️  部分 API Key 未配置，请检查 .env 文件")

        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
