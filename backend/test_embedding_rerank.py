#!/usr/bin/env python3
"""
测试脚本：验证阿里云 DashScope embedding 和 reranking API 的可用性
"""

import os
import asyncio
import sys
from typing import List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service


async def test_embedding_service():
    """测试 embedding 服务"""
    print("=" * 60)
    print("🔍 测试 Embedding 服务")
    print("=" * 60)

    test_texts = [
        "人工智能是计算机科学的一个分支",
        "机器学习是实现人工智能的重要方法",
        "深度学习是机器学习的一个子领域"
    ]

    try:
        # 测试单个文本 embedding
        print("\n📝 测试单个文本 embedding:")
        text = "什么是人工智能？"
        embedding = await embedding_service.get_embedding(text, text_type="query")
        print(f"✅ 成功获取 embedding")
        print(f"   文本: '{text}'")
        print(f"   维度: {len(embedding)}")
        print(f"   前10个值: {embedding[:10]}")

        # 测试批量 embedding
        print("\n📚 测试批量 embedding:")
        embeddings = await embedding_service.batch_embeddings(test_texts, text_type="document")
        print(f"✅ 成功获取批量 embeddings")
        print(f"   文本数量: {len(test_texts)}")
        print(f"   每个 embedding 维度: {len(embeddings[0])}")
        print(f"   所有 embedding 维度一致: {all(len(e) == len(embeddings[0]) for e in embeddings)}")

        # 测试 text_type 区分
        print("\n🔄 测试 text_type 区分:")
        query_embedding = await embedding_service.get_embedding("什么是机器学习？", text_type="query")
        doc_embedding = await embedding_service.get_embedding("机器学习是实现人工智能的重要方法", text_type="document")
        print(f"✅ 成功获取不同 text_type 的 embeddings")
        print(f"   Query embedding 维度: {len(query_embedding)}")
        print(f"   Document embedding 维度: {len(doc_embedding)}")

    except Exception as e:
        print(f"❌ Embedding 测试失败: {e}")
        return False

    return True


async def test_rerank_service():
    """测试 rerank 服务"""
    print("\n" + "=" * 60)
    print("🔍 测试 Rerank 服务")
    print("=" * 60)

    test_query = "什么是人工智能？"
    test_documents = [
        "人工智能是计算机科学的一个分支",
        "机器学习是实现人工智能的重要方法",
        "深度学习是机器学习的一个子领域",
        "量子计算是计算科学的前沿领域",
        "自然语言处理是人工智能的重要应用"
    ]

    # 创建测试候选对象（字典格式）
    candidates = [{"id": i, "content": doc} for i, doc in enumerate(test_documents)]

    try:
        # 测试基础 rerank
        print("\n📊 测试基础 rerank:")
        reranked = await rerank_service.rerank(test_query, candidates, top_k=3)
        print(f"✅ 成功完成 rerank")
        print(f"   原始文档数量: {len(candidates)}")
        print(f"   返回结果数量: {len(reranked)}")
        print(f"   rerank 后的文档:")
        for i, item in enumerate(reranked):
            print(f"     {i+1}. [ID:{item['id']}] {item['content']}")

        # 测试带 instruct 的 rerank
        print("\n🎯 测试带 instruct 的 rerank:")
        instruct = "Given a web search query, retrieve relevant passages that answer the query."
        reranked_with_instruct = await rerank_service.rerank(
            test_query,
            candidates,
            top_k=3,
            instruct=instruct
        )
        print(f"✅ 成功完成带 instruct 的 rerank")
        print(f"   使用指令: {instruct}")
        print(f"   rerank 结果:")
        for i, item in enumerate(reranked_with_instruct):
            print(f"     {i+1}. [ID:{item['id']}] {item['content']}")

        # 测试 RRF 算法
        print("\n🔄 测试 RRF (Reciprocal Rank Fusion) 算法:")
        # 模拟多个搜索结果
        mock_results_list = [
            [{"id": 0}, {"id": 2}, {"id": 1}],  # 结果集1
            [{"id": 1}, {"id": 0}, {"id": 4}],  # 结果集2
            [{"id": 2}, {"id": 3}, {"id": 0}],  # 结果集3
        ]
        fused_results = rerank_service.reciprocal_rank_fusion(mock_results_list, k=60)
        print(f"✅ 成功完成 RRF")
        print(f"   融合后的结果 (前5个):")
        for i, (item, score) in enumerate(fused_results[:5]):
            print(f"     {i+1}. [ID:{item['id']}] Score: {score:.4f}")

    except Exception as e:
        print(f"❌ Rerank 测试失败: {e}")
        return False

    return True


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("🔍 测试错误处理")
    print("=" * 60)

    try:
        # 测试空输入
        print("\n📝 测试空输入处理:")
        empty_embedding = await embedding_service.get_embedding("")
        print(f"✅ 空输入处理成功: {empty_embedding[:3] if empty_embedding else 'None'}")

        # 测试超长文本
        print("\n📝 测试超长文本:")
        long_text = "这是一个测试。" * 1000  # 约2000字
        long_embedding = await embedding_service.get_embedding(long_text)
        print(f"✅ 超长文本处理成功，维度: {len(long_embedding)}")

        # 测试 rerank 空输入
        print("\n📊 测试 rerank 空输入:")
        empty_rerank = await rerank_service.rerank("test", [])
        print(f"✅ 空候选列表处理成功: {len(empty_rerank)}")

        # 测试 rerank 单个候选
        print("\n📊 测试 rerank 单个候选:")
        single_candidate = [{"id": 0, "content": "测试文档"}]
        single_rerank = await rerank_service.rerank("test", single_candidate)
        print(f"✅ 单个候选处理成功: {len(single_rerank)}")

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False

    return True


async def main():
    """主函数"""
    print("🚀 开始测试阿里云 DashScope Embedding 和 Rerank API")

    # API 密钥从环境变量或 .env 文件读取
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("❌ 错误: DASHSCOPE_API_KEY 环境变量未设置")
        print("   请在 .env 文件中配置 DASHSCOPE_API_KEY")
        return False

    # 设置使用阿里云 provider
    from app.config import settings
    settings.EMBEDDING_PROVIDER = "dashscope"
    settings.RERANK_PROVIDER = "dashscope"
    settings.EMBEDDING_MODEL = "text-embedding-v4"
    settings.RERANK_MODEL = "qwen3-rerank"
    settings.EMBEDDING_DIM = 1024

    # 测试结果
    results = []

    # 测试 embedding 服务
    results.append(await test_embedding_service())

    # 测试 rerank 服务
    results.append(await test_rerank_service())

    # 测试错误处理
    results.append(await test_error_handling())

    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)

    if all(results):
        print("✅ 所有测试通过！阿里云 DashScope API 正常工作。")
        print("\n🔧 配置建议:")
        print("   - EMBEDDING_PROVIDER: dashscope")
        print("   - RERANK_PROVIDER: dashscope")
        print("   - EMBEDDING_MODEL: text-embedding-v4")
        print("   - RERANK_MODEL: qwen3-rerank")
        print("   - EMBEDDING_DIM: 1024")
        return True
    else:
        print("❌ 部分测试失败，请检查配置和网络连接。")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)