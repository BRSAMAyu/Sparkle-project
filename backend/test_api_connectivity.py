"""
测试所有 API Keys 的连通性

验证每个 API key 是否可以正常调用
"""
import asyncio
import sys
import os
from typing import Dict, Any
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings


class APIConnectivityTest:
    """API 连通性测试"""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}

    async def test_xiaomi_mimo(self) -> Dict[str, Any]:
        """测试 XiaoMi MIMO API"""
        print("\n" + "=" * 60)
        print("测试 XiaoMi MIMO API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.XIAOMI_MIMO_API_KEY,
                base_url=settings.XIAOMI_MIMO_BASE_URL
            )

            response = await client.chat.completions.create(
                model=settings.XIAOMI_CHAT_MODEL,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )

            content = response.choices[0].message.content
            print(f"✅ XiaoMi MIMO API 测试成功")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.XIAOMI_CHAT_MODEL
            }
        except Exception as e:
            print(f"❌ XiaoMi MIMO API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_zhipu_glm(self) -> Dict[str, Any]:
        """测试 Zhipu GLM API"""
        print("\n" + "=" * 60)
        print("测试 Zhipu GLM API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.ZHIPU_API_KEY,
                base_url=settings.ZHIPU_BASE_URL
            )

            response = await client.chat.completions.create(
                model=settings.ZHIPU_CHAT_MODEL,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )

            content = response.choices[0].message.content
            print(f"✅ Zhipu GLM API 测试成功")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.ZHIPU_CHAT_MODEL
            }
        except Exception as e:
            print(f"❌ Zhipu GLM API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_dashscope(self) -> Dict[str, Any]:
        """测试 DashScope API"""
        print("\n" + "=" * 60)
        print("测试 DashScope API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL_COMPATIBLE
            )

            response = await client.chat.completions.create(
                model=settings.DASHSCOPE_CHAT_MODEL,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )

            content = response.choices[0].message.content
            print(f"✅ DashScope API 测试成功")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.DASHSCOPE_CHAT_MODEL
            }
        except Exception as e:
            print(f"❌ DashScope API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_deepseek(self) -> Dict[str, Any]:
        """测试 DeepSeek API"""
        print("\n" + "=" * 60)
        print("测试 DeepSeek API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )

            response = await client.chat.completions.create(
                model=settings.DEEPSEEK_CHAT_MODEL,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )

            content = response.choices[0].message.content
            print(f"✅ DeepSeek API 测试成功")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.DEEPSEEK_CHAT_MODEL
            }
        except Exception as e:
            print(f"❌ DeepSeek API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_dashscope_embedding(self) -> Dict[str, Any]:
        """测试 DashScope Embedding API"""
        print("\n" + "=" * 60)
        print("测试 DashScope Embedding API")
        print("=" * 60)

        try:
            from app.services.embedding_service import embedding_service

            # 测试 embedding
            embedding = await embedding_service.get_embedding("测试文本")

            if embedding and len(embedding) == settings.EMBEDDING_DIM:
                print(f"✅ DashScope Embedding API 测试成功")
                print(f"   向量维度: {len(embedding)}")
                print(f"   前5个值: {embedding[:5]}")

                return {
                    "status": "success",
                    "dimension": len(embedding),
                    "model": settings.DASHSCOPE_EMBEDDING_MODEL
                }
            else:
                raise ValueError(f"向量维度不匹配: 期望 {settings.EMBEDDING_DIM}, 实际 {len(embedding) if embedding else 0}")

        except Exception as e:
            print(f"❌ DashScope Embedding API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_dashscope_rerank(self) -> Dict[str, Any]:
        """测试 DashScope Rerank API"""
        print("\n" + "=" * 60)
        print("测试 DashScope Rerank API")
        print("=" * 60)

        try:
            from app.services.rerank_service import rerank_service

            # 测试 rerank
            query = "什么是机器学习"
            documents = [
                "机器学习是人工智能的一个分支",
                "深度学习使用神经网络",
                "今天天气很好"
            ]

            results = await rerank_service.rerank(query, documents, top_k=2)

            if results and len(results) > 0:
                print(f"✅ DashScope Rerank API 测试成功")
                print(f"   返回结果数: {len(results)}")
                print(f"   最相关: {results[0][:30]}...")

                return {
                    "status": "success",
                    "results_count": len(results),
                    "model": settings.DASHSCOPE_RERANK_MODEL
                }
            else:
                raise ValueError("Rerank 返回空结果")

        except Exception as e:
            print(f"❌ DashScope Rerank API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_siliconflow_ocr(self) -> Dict[str, Any]:
        """测试 SiliconFlow OCR API (仅验证配置，不实际调用)"""
        print("\n" + "=" * 60)
        print("测试 SiliconFlow OCR API 配置")
        print("=" * 60)

        try:
            # OCR 需要图片，这里只验证配置
            if settings.SILICONFLOW_API_KEY and settings.SILICONFLOW_API_KEY != 'your_siliconflow_api_key':
                print(f"✅ SiliconFlow OCR API 配置验证成功")
                print(f"   API Key: {settings.SILICONFLOW_API_KEY[:20]}...")
                print(f"   Base URL: {settings.SILICONFLOW_BASE_URL}")
                print(f"   Model: {settings.SILICONFLOW_OCR_MODEL}")
                print(f"   ⚠️  注意: OCR 需要图片数据，未进行实际调用")

                return {
                    "status": "success",
                    "model": settings.SILICONFLOW_OCR_MODEL
                }
            else:
                raise ValueError("API Key 未配置")

        except Exception as e:
            print(f"❌ SiliconFlow OCR API 配置验证失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_hunyuan_translation(self) -> Dict[str, Any]:
        """测试 Hunyuan 翻译 API"""
        print("\n" + "=" * 60)
        print("测试 Hunyuan Translation API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.HUNYUAN_API_KEY,
                base_url=settings.HUNYUAN_BASE_URL
            )

            response = await client.chat.completions.create(
                model=settings.HUNYUAN_TRANSLATE_MODEL,
                messages=[
                    {"role": "user", "content": "Translate 'Hello' to Chinese"}
                ],
                max_tokens=20,
                temperature=0.3
            )

            content = response.choices[0].message.content
            print(f"✅ Hunyuan Translation API 测试成功")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.HUNYUAN_TRANSLATE_MODEL
            }
        except Exception as e:
            print(f"❌ Hunyuan Translation API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_xunfei_stt(self) -> Dict[str, Any]:
        """测试 XunFei STT API (仅验证配置)"""
        print("\n" + "=" * 60)
        print("测试 XunFei STT API 配置")
        print("=" * 60)

        try:
            # STT 需要音频数据，这里只验证配置
            if settings.XUNFEI_API_KEY and settings.XUNFEI_API_SECRET:
                print(f"✅ XunFei STT API 配置验证成功")
                print(f"   API Key: {settings.XUNFEI_API_KEY[:20]}...")
                print(f"   Domain: {settings.XUNFEI_STT_DOMAIN}")
                print(f"   Language: {settings.XUNFEI_STT_LANGUAGE}")
                print(f"   ⚠️  注意: STT 需要音频数据，未进行实际调用")

                return {
                    "status": "success",
                    "domain": settings.XUNFEI_STT_DOMAIN
                }
            else:
                raise ValueError("API Key 或 Secret 未配置")

        except Exception as e:
            print(f"❌ XunFei STT API 配置验证失败: {e}")
            return {"status": "error", "error": str(e)}

    async def test_glm_4_7_flash(self) -> Dict[str, Any]:
        """测试 GLM-4.7-Flash API"""
        print("\n" + "=" * 60)
        print("测试 GLM-4.7-Flash API")
        print("=" * 60)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.ZHIPU_API_KEY,
                base_url=settings.ZHIPU_BASE_URL
            )

            # 测试非思考模式
            response = await client.chat.completions.create(
                model=settings.GLM_4_7_FLASH_MODEL,
                messages=[{"role": "user", "content": "你好"}],
                extra_body={"clear_thinking": True},
                max_tokens=10
            )

            content = response.choices[0].message.content
            print(f"✅ GLM-4.7-Flash API 测试成功 (非思考模式)")
            print(f"   响应: {content[:50]}...")

            return {
                "status": "success",
                "response": content,
                "model": settings.GLM_4_7_FLASH_MODEL
            }
        except Exception as e:
            print(f"❌ GLM-4.7-Flash API 测试失败: {e}")
            return {"status": "error", "error": str(e)}

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("🚀 开始测试所有 API Keys")
        print("=" * 60)

        # 运行所有测试
        tests = [
            ("XiaoMi MIMO", self.test_xiaomi_mimo()),
            ("Zhipu GLM", self.test_zhipu_glm()),
            ("GLM-4.7-Flash", self.test_glm_4_7_flash()),
            ("DashScope", self.test_dashscope()),
            ("DeepSeek", self.test_deepseek()),
            ("DashScope Embedding", self.test_dashscope_embedding()),
            ("DashScope Rerank", self.test_dashscope_rerank()),
            ("Hunyuan Translation", self.test_hunyuan_translation()),
            ("SiliconFlow OCR", self.test_siliconflow_ocr()),
            ("XunFei STT", self.test_xunfei_stt()),
        ]

        for name, test_coro in tests:
            try:
                result = await test_coro
                self.results[name] = result
            except Exception as e:
                logger.exception(f"{name} 测试异常")
                self.results[name] = {"status": "error", "error": str(e)}

        # 打印总结
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)

        success_count = 0
        error_count = 0
        config_only_count = 0

        for name, result in self.results.items():
            status = result.get("status", "unknown")
            if status == "success":
                success_count += 1
                print(f"✅ {name}: 成功")
            elif status == "error":
                if "配置验证" in str(result.get("error", "")) or "注意:" in str(result.get("error", "")):
                    config_only_count += 1
                    print(f"⚠️  {name}: 仅配置验证 (需要实际数据)")
                else:
                    error_count += 1
                    print(f"❌ {name}: 失败 - {result.get('error', 'Unknown error')}")
            else:
                print(f"❓ {name}: 未知状态")

        print(f"\n统计:")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ⚠️  仅配置验证: {config_only_count}")
        print(f"  ❌ 失败: {error_count}")
        print(f"  📊 总计: {len(self.results)}")

        if error_count == 0:
            print(f"\n🎉 所有 API 测试通过！")
        else:
            print(f"\n⚠️  部分 API 测试失败，请检查配置")


async def main():
    """主函数"""
    tester = APIConnectivityTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
