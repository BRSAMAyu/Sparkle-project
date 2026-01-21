#!/usr/bin/env python3
"""
测试 embedding 和 reranking 服务的实际使用
"""

import os
import asyncio
import sys
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service


async def test_embedding_service_with_dashscope():
    """使用阿里云配置测试 embedding 服务"""
    print("=" * 60)
    print("🔍 测试 Embedding 服务 (阿里云配置)")
    print("=" * 60)

    # 临时设置环境变量
    original_provider = embedding_service.provider
    embedding_service.provider = "dashscope"
    embedding_service.dashscope_api_key = "YOUR_API_KEY_HERE"
    embedding_service.dashscope_model = "text-embedding-v4"
    embedding_service.embedding_dim = 1024

    try:
        # 测试单个文本
        print("\n📝 测试单个文本 embedding:")
        text = "什么是人工智能？"
        embedding = await embedding_service.get_embedding(text, text_type="query")
        print(f"✅ 成功")
        print(f"   文本: '{text}'")
        print(f"   维度: {len(embedding)}")
        print(f"   前10个值: {embedding[:10]}")

        # 测试批量
        print("\n📚 测试批量 embedding:")
        texts = [
            "人工智能是计算机科学的一个分支",
            "机器学习是实现人工智能的重要方法",
            "深度学习是机器学习的一个子领域"
        ]
        embeddings = await embedding_service.batch_embeddings(texts, text_type="document")
        print(f"✅ 成功")
        print(f"   文本数量: {len(texts)}")
        print(f"   维度一致性: {all(len(e) == 1024 for e in embeddings)}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 恢复原配置
        embedding_service.provider = original_provider


async def test_rerank_service_with_dashscope():
    """使用阿里云配置测试 rerank 服务"""
    print("\n" + "=" * 60)
    print("🔍 测试 Rerank 服务 (阿里云配置)")
    print("=" * 60)

    # 临时设置环境变量
    original_provider = rerank_service.provider
    rerank_service.provider = "dashscope"
    rerank_service.dashscope_api_key = "YOUR_API_KEY_HERE"
    rerank_service.dashscope_model = "qwen3-rerank"

    try:
        # 测试基础 rerank
        print("\n📊 测试基础 rerank:")
        query = "什么是人工智能？"
        candidates = [
            {"id": 0, "content": "人工智能是计算机科学的一个分支"},
            {"id": 1, "content": "机器学习是实现人工智能的重要方法"},
            {"id": 2, "content": "深度学习是机器学习的一个子领域"},
            {"id": 3, "content": "量子计算是计算科学的前沿领域"},
            {"id": 4, "content": "自然语言处理是人工智能的重要应用"}
        ]
        reranked = await rerank_service.rerank(query, candidates, top_k=3)
        print(f"✅ 成功")
        print(f"   查询: '{query}'")
        print(f"   结果数量: {len(reranked)}")
        for i, item in enumerate(reranked):
            print(f"     {i+1}. [ID:{item['id']}] {item['content']}")

        # 测试带 instruct
        print("\n🎯 测试带 instruct 的 rerank:")
        instruct = "Given a web search query, retrieve relevant passages that answer the query."
        reranked_instruct = await rerank_service.rerank(
            query,
            candidates,
            top_k=3,
            instruct=instruct
        )
        print(f"✅ 成功")
        print(f"   指令: {instruct}")
        for i, item in enumerate(reranked_instruct):
            print(f"     {i+1}. [ID:{item['id']}] {item['content']}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 恢复原配置
        rerank_service.provider = original_provider


async def test_siliconflow_config():
    """测试硅基流动配置（如果可用）"""
    print("\n" + "=" * 60)
    print("🔍 测试 SiliconFlow 配置")
    print("=" * 60)

    siliconflow_key = os.getenv("SILICONFLOW_API_KEY")
    if not siliconflow_key:
        print("⚠️  SILICONFLOW_API_KEY 未设置，跳过测试")
        return True

    # 临时设置硅基流动配置
    original_provider = embedding_service.provider
    embedding_service.provider = "siliconflow"
    embedding_service.siliconflow_api_key = siliconflow_key
    embedding_service.siliconflow_model = "Qwen/Qwen3-Embedding-4B"
    embedding_service.embedding_dim = 1024

    try:
        # 测试硅基流动 embedding
        print("\n📝 测试 SiliconFlow embedding:")
        text = "什么是人工智能？"
        embedding = await embedding_service.get_embedding(text)
        print(f"✅ SiliconFlow embedding 成功")
        print(f"   维度: {len(embedding)}")

        # 恢复原配置
        embedding_service.provider = original_provider

        # 测试硅基流动 rerank
        original_rerank_provider = rerank_service.provider
        rerank_service.provider = "siliconflow"
        rerank_service.siliconflow_api_key = siliconflow_key
        rerank_service.siliconflow_model = "Qwen/Qwen3-Reranker-4B"

        print("\n📊 测试 SiliconFlow rerank:")
        candidates = [
            {"id": 0, "content": "人工智能是计算机科学的一个分支"},
            {"id": 1, "content": "机器学习是实现人工智能的重要方法"}
        ]
        reranked = await rerank_service.rerank("什么是AI？", candidates, top_k=2)
        print(f"✅ SiliconFlow rerank 成功")
        print(f"   结果数量: {len(reranked)}")

        rerank_service.provider = original_rerank_provider
        return True

    except Exception as e:
        print(f"❌ SiliconFlow 测试失败: {e}")
        embedding_service.provider = original_provider
        return False


async def main():
    """主函数"""
    print("🚀 开始测试 embedding 和 reranking 服务")

    # 测试阿里云配置
    embedding_ok = await test_embedding_service_with_dashscope()
    rerank_ok = await test_rerank_service_with_dashscope()

    # 测试硅基流动配置（如果可用）
    siliconflow_ok = await test_siliconflow_config()

    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)

    if embedding_ok and rerank_ok:
        print("✅ 阿里云 DashScope 服务正常工作")
        print("\n🔧 推荐生产配置:")
        print("   export EMBEDDING_PROVIDER=dashscope")
        print("   export RERANK_PROVIDER=dashscope")
        print("   export DASHSCOPE_API_KEY=sk-your-api-key")
        print("   export EMBEDDING_MODEL=text-embedding-v4")
        print("   export RERANK_MODEL=qwen3-rerank")
        print("   export EMBEDDING_DIM=1024")

        if siliconflow_ok:
            print("\n✅ 硅基流动服务也可作为备用方案")

    else:
        print("❌ 服务测试失败")

    return embedding_ok and rerank_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)