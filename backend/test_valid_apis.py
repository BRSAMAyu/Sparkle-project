"""
快速测试：只测试有效的 API Keys
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


async def test_apis():
    """测试所有有效的 API"""
    from openai import AsyncOpenAI
    from app.config import settings
    from app.services.embedding_service import embedding_service
    from app.services.rerank_service import rerank_service

    results = {}

    # 1. Zhipu GLM
    print("\n🔵 测试 Zhipu GLM...")
    try:
        client = AsyncOpenAI(api_key=settings.ZHIPU_API_KEY, base_url=settings.ZHIPU_BASE_URL)
        response = await client.chat.completions.create(
            model=settings.ZHIPU_CHAT_MODEL,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10
        )
        print(f"✅ Zhipu GLM: {response.choices[0].message.content[:30]}...")
        results["Zhipu GLM"] = True
    except Exception as e:
        print(f"❌ Zhipu GLM: {e}")
        results["Zhipu GLM"] = False

    # 2. GLM-4.7-Flash (非思考模式)
    print("\n🔵 测试 GLM-4.7-Flash...")
    try:
        client = AsyncOpenAI(api_key=settings.ZHIPU_API_KEY, base_url=settings.ZHIPU_BASE_URL)
        response = await client.chat.completions.create(
            model=settings.GLM_4_7_FLASH_MODEL,
            messages=[{"role": "user", "content": "你好"}],
            extra_body={"clear_thinking": True},
            max_tokens=10
        )
        print(f"✅ GLM-4.7-Flash: {response.choices[0].message.content[:30]}...")
        results["GLM-4.7-Flash"] = True
    except Exception as e:
        print(f"❌ GLM-4.7-Flash: {e}")
        results["GLM-4.7-Flash"] = False

    # 3. DashScope
    print("\n🔵 测试 DashScope...")
    try:
        client = AsyncOpenAI(api_key=settings.DASHSCOPE_API_KEY, base_url=settings.DASHSCOPE_BASE_URL_COMPATIBLE)
        response = await client.chat.completions.create(
            model=settings.DASHSCOPE_CHAT_MODEL,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10
        )
        print(f"✅ DashScope: {response.choices[0].message.content[:30]}...")
        results["DashScope"] = True
    except Exception as e:
        print(f"❌ DashScope: {e}")
        results["DashScope"] = False

    # 4. DeepSeek
    print("\n🔵 测试 DeepSeek...")
    try:
        client = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_CHAT_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"✅ DeepSeek: {response.choices[0].message.content[:30]}...")
        results["DeepSeek"] = True
    except Exception as e:
        print(f"❌ DeepSeek: {e}")
        results["DeepSeek"] = False

    # 5. DashScope Embedding
    print("\n🔵 测试 DashScope Embedding...")
    try:
        embedding = await embedding_service.get_embedding("测试文本")
        if len(embedding) == 1024:
            print(f"✅ DashScope Embedding: 维度={len(embedding)}")
            results["DashScope Embedding"] = True
        else:
            raise ValueError(f"向量维度错误: {len(embedding)}")
    except Exception as e:
        print(f"❌ DashScope Embedding: {e}")
        results["DashScope Embedding"] = False

    # 6. DashScope Rerank
    print("\n🔵 测试 DashScope Rerank...")
    try:
        query = "什么是机器学习"
        documents = ["机器学习是AI的一个分支", "深度学习使用神经网络", "天气很好"]
        reranked = await rerank_service.rerank(query, documents, top_k=2)
        print(f"✅ DashScope Rerank: 返回{len(reranked)}个结果")
        results["DashScope Rerank"] = True
    except Exception as e:
        print(f"❌ DashScope Rerank: {e}")
        results["DashScope Rerank"] = False

    # 7. Hunyuan Translation
    print("\n🔵 测试 Hunyuan Translation...")
    try:
        client = AsyncOpenAI(api_key=settings.HUNYUAN_API_KEY, base_url=settings.HUNYUAN_BASE_URL)
        response = await client.chat.completions.create(
            model=settings.HUNYUAN_TRANSLATE_MODEL,
            messages=[{"role": "user", "content": "Translate 'Hello' to Chinese"}],
            max_tokens=20
        )
        print(f"✅ Hunyuan Translation: {response.choices[0].message.content[:30]}...")
        results["Hunyuan Translation"] = True
    except Exception as e:
        print(f"❌ Hunyuan Translation: {e}")
        results["Hunyuan Translation"] = False

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    success = sum(1 for v in results.values() if v)
    total = len(results)
    for name, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")

    print(f"\n成功率: {success}/{total} ({success/total*100:.1f}%)")

    if success == total:
        print("\n🎉 所有 API 测试通过！系统已准备就绪。")
    else:
        print(f"\n⚠️  {total-success} 个 API 测试失败，请检查配置。")


if __name__ == "__main__":
    asyncio.run(test_apis())
