#!/usr/bin/env python3
"""
直接测试脚本：验证阿里云 DashScope embedding 和 reranking API 的可用性
"""

import os
import asyncio
import sys
import logging
from typing import List
import dashscope
from http import HTTPStatus

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置 API Key
os.environ["DASHSCOPE_API_KEY"] = "sk-cd9af6e3b7da44c9b67de53c69f2fae8"


async def test_dashscope_embedding():
    """直接测试 DashScope embedding API"""
    print("=" * 60)
    print("🔍 直接测试 DashScope Embedding API")
    print("=" * 60)

    # 设置 API Key
    dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

    test_cases = [
        {
            "name": "单个文本 embedding (query)",
            "text": "什么是人工智能？",
            "text_type": "query",
            "dimension": 1024
        },
        {
            "name": "单个文本 embedding (document)",
            "text": "人工智能是计算机科学的一个分支",
            "text_type": "document",
            "dimension": 1024
        },
        {
            "name": "批量 embedding",
            "texts": [
                "人工智能是计算机科学的一个分支",
                "机器学习是实现人工智能的重要方法",
                "深度学习是机器学习的一个子领域"
            ],
            "text_type": "document",
            "dimension": 1024
        }
    ]

    for test_case in test_cases:
        print(f"\n📝 {test_case['name']}:")
        try:
            if "texts" in test_case:
                # 批量测试
                payload = {
                    "model": "text-embedding-v4",
                    "input": test_case["texts"],
                    "dimension": test_case["dimension"],
                    "text_type": test_case["text_type"],
                }
                resp = dashscope.TextEmbedding.call(**payload)
            else:
                # 单个文本测试
                payload = {
                    "model": "text-embedding-v4",
                    "input": [test_case["text"]],
                    "dimension": test_case["dimension"],
                    "text_type": test_case["text_type"],
                }
                resp = dashscope.TextEmbedding.call(**payload)

            if resp.status_code == HTTPStatus.OK:
                print(f"✅ 成功")
                embeddings = resp.output.get("embeddings", [])
                if "texts" in test_case:
                    print(f"   文本数量: {len(test_case['texts'])}")
                    print(f"   每个 embedding 维度: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")
                    print(f"   所有维度一致: {all(len(e['embedding']) == len(embeddings[0]['embedding']) for e in embeddings)}")
                else:
                    print(f"   文本: '{test_case['text']}'")
                    print(f"   维度: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")
                    print(f"   前5个值: {embeddings[0]['embedding'][:5] if embeddings else 'N/A'}")
            else:
                print(f"❌ 失败: {resp.code} - {resp.message}")

        except Exception as e:
            print(f"❌ 异常: {e}")


async def test_dashscope_rerank():
    """直接测试 DashScope rerank API"""
    print("\n" + "=" * 60)
    print("🔍 直接测试 DashScope Rerank API")
    print("=" * 60)

    # 设置 API Key
    dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

    test_cases = [
        {
            "name": "基础 rerank",
            "query": "什么是人工智能？",
            "documents": [
                "人工智能是计算机科学的一个分支",
                "机器学习是实现人工智能的重要方法",
                "深度学习是机器学习的一个子领域",
                "量子计算是计算科学的前沿领域",
                "自然语言处理是人工智能的重要应用"
            ],
            "top_n": 3,
            "instruct": None
        },
        {
            "name": "带 instruct 的 rerank",
            "query": "什么是机器学习？",
            "documents": [
                "机器学习是实现人工智能的重要方法",
                "深度学习是机器学习的一个子领域",
                "监督学习是一种机器学习范式",
                "无监督学习不需要标记数据"
            ],
            "top_n": 2,
            "instruct": "Given a web search query, retrieve relevant passages that answer the query."
        },
        {
            "name": "语义相似度 rerank",
            "query": "如何修改密码？",
            "documents": [
                "忘记密码怎么办？",
                "密码修改教程",
                "账户安全设置",
                "重置密码流程"
            ],
            "top_n": 3,
            "instruct": "Retrieve semantically similar text."
        }
    ]

    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}:")
        try:
            payload = {
                "model": "qwen3-rerank",
                "query": test_case["query"],
                "documents": test_case["documents"],
                "top_n": test_case["top_n"],
            }

            if test_case["instruct"]:
                payload["instruct"] = test_case["instruct"]

            resp = dashscope.TextReRank.call(**payload)

            if resp.status_code == HTTPStatus.OK:
                print(f"✅ 成功")
                print(f"   查询: '{test_case['query']}'")
                print(f"   文档数量: {len(test_case['documents'])}")
                if test_case["instruct"]:
                    print(f"   指令: {test_case['instruct']}")

                results = resp.output.get("results", [])
                print(f"   返回结果数量: {len(results)}")
                print(f"   消耗 Token: {resp.usage.get('total_tokens', 'N/A')}")
                print(f"   Rerank 结果:")
                for i, item in enumerate(results):
                    doc_text = test_case["documents"][item["index"]]
                    print(f"     {i+1}. [Index:{item['index']}] Score: {item['relevance_score']:.4f}")
                    print(f"        文档: {doc_text[:50]}...")
            else:
                print(f"❌ 失败: {resp.code} - {resp.message}")

        except Exception as e:
            print(f"❌ 异常: {e}")


async def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("🔍 测试边界情况")
    print("=" * 60)

    # 设置 API Key
    dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

    test_cases = [
        {
            "name": "空文本",
            "payload": {
                "model": "text-embedding-v4",
                "input": [""],
                "dimension": 1024,
            }
        },
        {
            "name": "超长文本",
            "payload": {
                "model": "text-embedding-v4",
                "input": ["这是一个测试。" * 1000],  # 约2000字
                "dimension": 1024,
            }
        },
        {
            "name": "大量文档 rerank",
            "payload": {
                "model": "qwen3-rerank",
                "query": "测试",
                "documents": ["文档内容"] * 10,  # 10个文档
                "top_n": 5,
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}:")
        try:
            if "embeddings" in test_case["payload"]["model"]:
                resp = dashscope.TextEmbedding.call(**test_case["payload"])
            else:
                resp = dashscope.TextReRank.call(**test_case["payload"])

            if resp.status_code == HTTPStatus.OK:
                print(f"✅ 成功处理边界情况")
                if "embeddings" in test_case["payload"]["model"]:
                    embeddings = resp.output.get("embeddings", [])
                    print(f"   Embedding 维度: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")
                else:
                    results = resp.output.get("results", [])
                    print(f"   返回结果数量: {len(results)}")
            else:
                print(f"⚠️  API 返回: {resp.code} - {resp.message}")

        except Exception as e:
            print(f"❌ 异常: {e}")


async def main():
    """主函数"""
    print("🚀 开始直接测试阿里云 DashScope API")

    # 测试 embedding API
    await test_dashscope_embedding()

    # 测试 rerank API
    await test_dashscope_rerank()

    # 测试边界情况
    await test_edge_cases()

    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print("✅ 直接 API 测试完成")
    print("\n🔧 配置建议:")
    print("   - 确保网络连接正常")
    print("   - API Key 有效且有足够配额")
    print("   - 模型名称正确: text-embedding-v4, qwen3-rerank")
    print("   - 嵌入维度: 1024")


if __name__ == "__main__":
    asyncio.run(main())