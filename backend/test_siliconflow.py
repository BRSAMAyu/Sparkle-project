#!/usr/bin/env python3
"""
测试脚本：验证硅基流动 SiliconFlow embedding 和 reranking API 的可用性
"""

import os
import asyncio
import sys
import logging
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
import json


async def test_siliconflow_embedding():
    """测试硅基流动 embedding API"""
    print("=" * 60)
    print("🔍 测试 SiliconFlow Embedding API")
    print("=" * 60)

    # 获取 API Key
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("❌ SILICONFLOW_API_KEY 未设置，跳过测试")
        return False

    base_url = "https://api.siliconflow.cn/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    test_cases = [
        {
            "name": "单个文本 embedding (BGE)",
            "model": "BAAI/bge-large-zh-v1.5",
            "input": "什么是人工智能？",
            "dimensions": None,  # BGE 模型不支持 dimensions
        },
        {
            "name": "单个文本 embedding (Qwen)",
            "model": "Qwen/Qwen3-Embedding-4B",
            "input": "什么是人工智能？",
            "dimensions": 1024,
        },
        {
            "name": "批量 embedding",
            "model": "BAAI/bge-large-zh-v1.5",
            "input": ["人工智能是计算机科学的一个分支", "机器学习是实现人工智能的重要方法"],
            "dimensions": None,
        },
        {
            "name": "自定义维度 embedding (Qwen)",
            "model": "Qwen/Qwen3-Embedding-4B",
            "input": ["深度学习是机器学习的一个子领域"],
            "dimensions": 768,
        }
    ]

    for test_case in test_cases:
        print(f"\n📝 {test_case['name']}:")
        try:
            payload = {
                "model": test_case["model"],
                "input": test_case["input"],
                "encoding_format": "float",
            }

            # Qwen 模型支持 dimensions
            if test_case["dimensions"]:
                payload["dimensions"] = test_case["dimensions"]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/embeddings",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功")
                    print(f"   模型: {test_case['model']}")

                    embeddings = data.get("data", [])
                    if isinstance(test_case["input"], list):
                        print(f"   文本数量: {len(test_case['input'])}")
                        print(f"   向量维度: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")
                    else:
                        print(f"   文本: '{test_case['input']}'")
                        print(f"   向量维度: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")

                    # 显示 token 使用情况
                    usage = data.get("usage", {})
                    if usage:
                        print(f"   Token 使用: {usage.get('total_tokens', 'N/A')}")

                else:
                    print(f"❌ 失败 [{response.status_code}]: {response.text}")

        except Exception as e:
            print(f"❌ 异常: {e}")

    return True


async def test_siliconflow_rerank():
    """测试硅基流动 rerank API"""
    print("\n" + "=" * 60)
    print("🔍 测试 SiliconFlow Rerank API")
    print("=" * 60)

    # 获取 API Key
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("❌ SILICONFLOW_API_KEY 未设置，跳过测试")
        return False

    base_url = "https://api.siliconflow.cn"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    test_cases = [
        {
            "name": "基础 rerank (BGE)",
            "model": "BAAI/bge-reranker-v2-m3",
            "query": "什么是人工智能？",
            "documents": [
                "人工智能是计算机科学的一个分支",
                "机器学习是实现人工智能的重要方法",
                "深度学习是机器学习的一个子领域",
                "量子计算是计算科学的前沿领域"
            ],
            "top_n": 3,
            "instruct": None,
        },
        {
            "name": "带 instruct 的 rerank (Qwen)",
            "model": "Qwen/Qwen3-Reranker-4B",
            "query": "如何修改密码？",
            "documents": [
                "忘记密码怎么办？",
                "密码修改教程",
                "账户安全设置",
                "重置密码流程"
            ],
            "top_n": 2,
            "instruct": "Please rerank the documents based on the query.",
        },
        {
            "name": "返回文档内容",
            "model": "BAAI/bge-reranker-v2-m3",
            "query": "Apple",
            "documents": ["apple", "banana", "fruit", "vegetable"],
            "top_n": 4,
            "return_documents": True,
        },
        {
            "name": "分块处理测试",
            "model": "BAAI/bge-reranker-v2-m3",
            "query": "机器学习算法",
            "documents": [
                "机器学习是人工智能的核心技术之一，包括监督学习、无监督学习和强化学习等多种算法。",
                "深度学习是机器学习的一个分支，使用神经网络进行学习。",
                "自然语言处理是人工智能的重要应用领域。"
            ],
            "top_n": 2,
            "max_chunks_per_doc": 3,
            "overlap_tokens": 50,
        }
    ]

    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}:")
        try:
            payload = {
                "model": test_case["model"],
                "query": test_case["query"],
                "documents": test_case["documents"],
                "top_n": test_case["top_n"],
            }

            # 可选参数
            if "instruct" in test_case and test_case["instruct"]:
                payload["instruct"] = test_case["instruct"]

            if "return_documents" in test_case:
                payload["return_documents"] = test_case["return_documents"]

            if "max_chunks_per_doc" in test_case:
                payload["max_chunks_per_doc"] = test_case["max_chunks_per_doc"]

            if "overlap_tokens" in test_case:
                payload["overlap_tokens"] = test_case["overlap_tokens"]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/rerank",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功")
                    print(f"   模型: {test_case['model']}")
                    print(f"   查询: '{test_case['query']}'")
                    print(f"   文档数量: {len(test_case['documents'])}")

                    results = data.get("results", [])
                    print(f"   返回结果数量: {len(results)}")

                    # 显示 token 使用情况
                    meta = data.get("meta", [])
                    if meta:
                        tokens = meta[0].get("tokens", {})
                        print(f"   Token 使用: input={tokens.get('input_tokens', 'N/A')}, output={tokens.get('output_tokens', 'N/A')}")

                    # 显示 rerank 结果
                    for i, item in enumerate(results):
                        doc_text = test_case["documents"][item["index"]]
                        score = item["relevance_score"]
                        print(f"     {i+1}. [Index:{item['index']}] Score: {score:.4f}")
                        if "return_documents" in test_case and test_case["return_documents"]:
                            print(f"        Document: {doc_text[:50]}...")
                        else:
                            print(f"        Document: {doc_text[:50]}...")

                else:
                    print(f"❌ 失败 [{response.status_code}]: {response.text}")

        except Exception as e:
            print(f"❌ 异常: {e}")

    return True


async def test_siliconflow_service_layer():
    """测试硅基流动服务层"""
    print("\n" + "=" * 60)
    print("🔍 测试硅基流动服务层集成")
    print("=" * 60)

    from app.services.embedding_service import embedding_service
    from app.services.rerank_service import rerank_service

    # 设置硅基流动配置
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("❌ SILICONFLOW_API_KEY 未设置，跳过测试")
        return False

    original_embedding_provider = embedding_service.provider
    original_rerank_provider = rerank_service.provider

    try:
        # 设置硅基流动
        embedding_service.provider = "siliconflow"
        embedding_service.siliconflow_api_key = api_key
        embedding_service.siliconflow_model = "Qwen/Qwen3-Embedding-4B"
        embedding_service.embedding_dim = 1024

        rerank_service.provider = "siliconflow"
        rerank_service.siliconflow_api_key = api_key
        rerank_service.siliconflow_model = "Qwen/Qwen3-Reranker-4B"

        # 测试 embedding 服务
        print("\n📝 测试 Embedding 服务层:")
        embedding = await embedding_service.get_embedding("测试文本")
        print(f"✅ Service layer embedding 成功 - 维度: {len(embedding)}")

        # 测试 rerank 服务
        print("\n📊 测试 Rerank 服务层:")
        candidates = [
            {"id": 0, "content": "测试文档1"},
            {"id": 1, "content": "测试文档2"}
        ]
        reranked = await rerank_service.rerank("测试查询", candidates, top_k=1)
        print(f"✅ Service layer rerank 成功 - 结果数: {len(reranked)}")

        return True

    except Exception as e:
        print(f"❌ 服务层测试失败: {e}")
        return False
    finally:
        # 恢复原配置
        embedding_service.provider = original_embedding_provider
        rerank_service.provider = original_rerank_provider


async def main():
    """主函数"""
    print("🚀 开始测试硅基流动 SiliconFlow API")

    # 检查 API Key
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("⚠️  SILICONFLOW_API_KEY 未设置，请设置后重新运行")
        print("\n设置环境变量:")
        print("export SILICONFLOW_API_KEY=your-siliconflow-api-key")
        return False

    # 测试 API
    await test_siliconflow_embedding()
    await test_siliconflow_rerank()
    await test_siliconflow_service_layer()

    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print("✅ 硅基流动 API 测试完成")
    print("\n🔧 配置建议:")
    print("   export EMBEDDING_PROVIDER=siliconflow")
    print("   export RERANK_PROVIDER=siliconflow")
    print("   export SILICONFLOW_API_KEY=your-api-key")
    print("   export EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B")
    print("   export RERANK_MODEL=Qwen/Qwen3-Reranker-4B")
    print("   export EMBEDDING_DIM=1024")


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)