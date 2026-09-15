"""
测试 Embedding 和 Rerank 配置

验证默认提供商是否切换到 DashScope
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service


def test_config():
    """测试配置"""
    print("\n" + "=" * 60)
    print("Embedding 和 Rerank 配置测试")
    print("=" * 60)

    print(f"\n✓ Embedding 配置:")
    print(f"  - Provider: {settings.EMBEDDING_PROVIDER}")
    print(f"  - Model: {settings.EMBEDDING_MODEL}")
    print(f"  - Dimension: {settings.EMBEDDING_DIM}")
    print(f"  - DashScope API Key: {'已设置' if settings.DASHSCOPE_API_KEY else '未设置'}")
    print(f"  - SiliconFlow API Key: {'已设置' if settings.SILICONFLOW_API_KEY else '未设置'}")

    print(f"\n✓ Rerank 配置:")
    print(f"  - Provider: {settings.RERANK_PROVIDER}")
    print(f"  - Model: {settings.RERANK_MODEL}")
    print(f"  - Reranker Enabled: {settings.RERANKER_ENABLED}")

    print(f"\n✓ Embedding Service 实例:")
    print(f"  - Provider: {embedding_service.provider}")
    print(f"  - DashScope Model: {embedding_service.dashscope_model}")
    print(f"  - SiliconFlow Model: {embedding_service.siliconflow_model}")

    print(f"\n✓ Rerank Service 实例:")
    print(f"  - Provider: {rerank_service.provider}")
    print(f"  - DashScope Model: {rerank_service.dashscope_model}")
    print(f"  - SiliconFlow Model: {rerank_service.siliconflow_model}")

    # 验证默认配置
    print(f"\n✓ 验证默认配置:")
    if settings.EMBEDDING_PROVIDER == "dashscope":
        print("  ✅ Embedding Provider 正确设置为 dashscope")
    else:
        print(f"  ❌ Embedding Provider 为 {settings.EMBEDDING_PROVIDER}，应为 dashscope")

    if settings.RERANK_PROVIDER == "dashscope":
        print("  ✅ Rerank Provider 正确设置为 dashscope")
    else:
        print(f"  ❌ Rerank Provider 为 {settings.RERANK_PROVIDER}，应为 dashscope")

    if settings.EMBEDDING_MODEL == "text-embedding-v4":
        print("  ✅ Embedding Model 正确设置为 text-embedding-v4")
    else:
        print(f"  ❌ Embedding Model 为 {settings.EMBEDDING_MODEL}，应为 text-embedding-v4")

    if settings.RERANK_MODEL == "qwen3-rerank":
        print("  ✅ Rerank Model 正确设置为 qwen3-rerank")
    else:
        print(f"  ❌ Rerank Model 为 {settings.RERANK_MODEL}，应为 qwen3-rerank")


def test_service_initialization():
    """测试服务初始化"""
    print(f"\n✓ 服务初始化测试:")

    # Embedding Service
    print(f"\n  Embedding Service:")
    print(f"    - Provider: {embedding_service.provider}")
    if embedding_service.provider == "dashscope":
        print(f"    - 将使用: DashScope API ({embedding_service.dashscope_model})")
        print(f"    - API Key: {'已设置' if embedding_service.dashscope_api_key else '未设置'}")
    else:
        print(f"    - 将使用: SiliconFlow API ({embedding_service.siliconflow_model})")
        print(f"    - API Key: {'已设置' if embedding_service.siliconflow_api_key else '未设置'}")

    # Rerank Service
    print(f"\n  Rerank Service:")
    print(f"    - Provider: {rerank_service.provider}")
    if rerank_service.provider == "dashscope":
        print(f"    - 将使用: DashScope API ({rerank_service.dashscope_model})")
        print(f"    - API Key: {'已设置' if rerank_service.dashscope_api_key else '未设置'}")
    else:
        print(f"    - 将使用: SiliconFlow API ({rerank_service.siliconflow_model})")
        print(f"    - API Key: {'已设置' if rerank_service.siliconflow_api_key else '未设置'}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Embedding & Rerank 配置验证")
    print("=" * 60)

    try:
        test_config()
        test_service_initialization()

        print("\n" + "=" * 60)
        print("✅ 配置验证完成")
        print("=" * 60)
        print("\n📋 当前配置:")
        print(f"  - Embedding: {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL})")
        print(f"  - Rerank: {settings.RERANK_PROVIDER} ({settings.RERANK_MODEL})")
        print("\n💡 如果需要切换到 SiliconFlow:")
        print("  EMBEDDING_PROVIDER=siliconflow")
        print("  RERANK_PROVIDER=siliconflow")
        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
