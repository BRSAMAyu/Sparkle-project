#!/usr/bin/env python3
"""
验证 embedding 和 reranking 配置
"""

import os
import asyncio
from typing import Dict, Any

from app.config import settings
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service


def validate_config():
    """验证配置"""
    print("🔍 验证配置...")

    # 检查环境变量
    env_vars = {
        "EMBEDDING_PROVIDER": os.getenv("EMBEDDING_PROVIDER"),
        "RERANK_PROVIDER": os.getenv("RERANK_PROVIDER"),
        "DASHSCOPE_API_KEY": os.getenv("DASHSCOPE_API_KEY"),
        "SILICONFLOW_API_KEY": os.getenv("SILICONFLOW_API_KEY"),
    }

    print("\n📋 环境变量检查:")
    for key, value in env_vars.items():
        status = "✅" if value else "❌"
        masked = value[:8] + "..." if value and len(value) > 8 else (value if value else "未设置")
        print(f"   {status} {key}: {masked}")

    # 检查配置
    config = {
        "EMBEDDING_PROVIDER": settings.EMBEDDING_PROVIDER,
        "RERANK_PROVIDER": settings.RERANK_PROVIDER,
        "EMBEDDING_MODEL": settings.EMBEDDING_MODEL,
        "RERANK_MODEL": settings.RERANK_MODEL,
        "EMBEDDING_DIM": settings.EMBEDDING_DIM,
        "DASHSCOPE_EMBEDDING_MODEL": settings.DASHSCOPE_EMBEDDING_MODEL,
        "DASHSCOPE_RERANK_MODEL": settings.DASHSCOPE_RERANK_MODEL,
        "SILICONFLOW_EMBEDDING_MODEL": settings.SILICONFLOW_EMBEDDING_MODEL,
        "SILICONFLOW_RERANK_MODEL": settings.SILICONFLOW_RERANK_MODEL,
    }

    print("\n📋 配置检查:")
    for key, value in config.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}: {value}")

    return all(env_vars.values()), config


async def test_aliyun_config():
    """测试阿里云配置"""
    print("\n🔍 测试阿里云配置...")

    try:
        # 设置阿里云 provider
        original_embedding_provider = settings.EMBEDDING_PROVIDER
        original_rerank_provider = settings.RERANK_PROVIDER

        settings.EMBEDDING_PROVIDER = "dashscope"
        settings.RERANK_PROVIDER = "dashscope"

        # 测试 embedding
        embedding = await embedding_service.get_embedding("测试文本", text_type="document")
        print(f"✅ Embedding 测试成功 - 维度: {len(embedding)}")

        # 测试 rerank
        candidates = [{"id": 0, "content": "测试文档"}]
        reranked = await rerank_service.rerank("测试查询", candidates, top_k=1)
        print(f"✅ Rerank 测试成功 - 结果数: {len(reranked)}")

        # 恢复原配置
        settings.EMBEDDING_PROVIDER = original_embedding_provider
        settings.RERANK_PROVIDER = original_rerank_provider

        return True

    except Exception as e:
        print(f"❌ 阿里云测试失败: {e}")
        return False


def generate_env_example():
    """生成环境变量示例"""
    print("\n📝 推荐的环境变量配置:")
    print("=" * 60)
    print("""
# 阿里云 DashScope 配置 (推荐)
EMBEDDING_PROVIDER=dashscope
RERANK_PROVIDER=dashscope
DASHSCOPE_API_KEY=replace_with_provider_api_key

# 模型配置
EMBEDDING_MODEL=text-embedding-v4
RERANK_MODEL=qwen3-rerank
EMBEDDING_DIM=1024

# 硅基流动备用配置 (可选)
# SILICONFLOW_API_KEY=your-siliconflow-api-key
# SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
""")
    print("=" * 60)


async def main():
    """主函数"""
    print("🚀 开始验证 embedding 和 reranking 配置")

    # 验证配置
    env_ok, config = validate_config()

    # 如果环境变量缺失，显示配置建议
    if not env_ok:
        print("\n⚠️  环境变量缺失，请配置以下变量:")
        generate_env_example()
        return False

    # 测试阿里云配置
    aliyun_ok = await test_aliyun_config()

    # 总结
    print("\n" + "=" * 60)
    print("📋 验证总结")
    print("=" * 60)

    if aliyun_ok:
        print("✅ 阿里云 DashScope API 工作正常")
        print("\n🔧 推荐配置:")
        print("   EMBEDDING_PROVIDER=dashscope")
        print("   RERANK_PROVIDER=dashscope")
        print("   EMBEDDING_MODEL=text-embedding-v4")
        print("   RERANK_MODEL=qwen3-rerank")
        print("   EMBEDDING_DIM=1024")
        return True
    else:
        print("❌ 配置验证失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)