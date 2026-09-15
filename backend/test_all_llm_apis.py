#!/usr/bin/env python3
"""
大模型 API 服务全面验证测试
====================================

验证所有引入真实 API 的服务领域：
1. LLM 对话服务 (Chat/Reason)
2. Embedding 向量服务
3. Rerank 重排序服务
4. 文档清洗 OCR 服务
5. 翻译服务 (Hunyuan)
6. ASR 语音转文字服务

运行方式:
    cd backend && python test_all_llm_apis.py
"""
import asyncio
import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service
from loguru import logger


class APIValidator:
    """API 服务验证器"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def print_section(self, title: str):
        """打印小节标题"""
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}")

    async def test_api(
        self,
        name: str,
        api_func,
        category: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        执行单个 API 测试

        Args:
            name: 测试名称
            api_func: 异步测试函数
            category: 分类
            description: 描述
        """
        self.total_tests += 1
        result = {
            "name": name,
            "category": category,
            "description": description,
            "status": "pending",
            "duration": 0,
            "error": None,
            "details": None,
        }

        print(f"\n  [{self.total_tests}] 测试: {name}")
        print(f"      描述: {description}")

        try:
            start_time = time.time()
            details = await api_func()
            duration = time.time() - start_time

            result["status"] = "passed"
            result["duration"] = duration
            result["details"] = details

            self.passed_tests += 1
            print(f"      状态: ✅ PASSED ({duration:.2f}s)")

            if details:
                print(f"      详情: {json.dumps(details, ensure_ascii=False, indent=10)[:200]}...")

        except Exception as e:
            result["status"] = "failed"
            result["duration"] = time.time() - start_time
            result["error"] = str(e)

            self.failed_tests += 1
            print(f"      状态: ❌ FAILED")
            print(f"      错误: {e}")

        self.results.append(result)
        return result

    def skip_test(self, name: str, category: str, reason: str):
        """跳过测试"""
        self.total_tests += 1
        self.skipped_tests += 1

        result = {
            "name": name,
            "category": category,
            "status": "skipped",
            "reason": reason,
        }

        self.results.append(result)
        print(f"\n  [{self.total_tests}] 跳过: {name}")
        print(f"      原因: {reason}")

    async def validate_llm_service(self):
        """验证 LLM 对话服务"""
        self.print_section("1. LLM 对话服务验证")

        # 检查配置
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "placeholder":
            self.skip_test("LLM Chat 基础对话", "LLM", "未配置 DASHSCOPE_API_KEY")
            return

        # 测试 1: 基础对话
        async def test_chat():
            messages = [
                {"role": "system", "content": "你是一个AI助手。"},
                {"role": "user", "content": "用一句话介绍Python编程语言。"}
            ]
            response = await llm_service.chat(messages, temperature=0.7)
            if not response:
                raise ValueError("响应为空")
            return {"response_length": len(response), "preview": response[:50]}

        await self.test_api(
            "LLM Chat 基础对话",
            test_chat,
            "LLM",
            "测试与阿里云通义千问的对话能力"
        )

        # 测试 2: 流式对话
        async def test_stream_chat():
            messages = [
                {"role": "user", "content": "数数1到5"}
            ]
            full_response = ""
            async for chunk in llm_service.stream_chat(messages, temperature=0.3):
                full_response += chunk
            if not full_response:
                raise ValueError("流式响应为空")
            return {"stream_length": len(full_response), "preview": full_response[:50]}

        await self.test_api(
            "LLM Stream 流式对话",
            test_stream_chat,
            "LLM",
            "测试流式输出功能"
        )

        # 测试 3: JSON 输出
        async def test_json_output():
            messages = [
                {"role": "user", "content": "返回JSON格式的测试数据: {\"status\": \"ok\", \"value\": 42}"}
            ]
            response = await llm_service.chat_json(messages, temperature=0.1)
            if not isinstance(response, dict):
                raise ValueError(f"响应不是字典: {type(response)}")
            return {"parsed_keys": list(response.keys())}

        await self.test_api(
            "LLM JSON 结构化输出",
            test_json_output,
            "LLM",
            "测试JSON格式输出解析"
        )

    async def validate_embedding_service(self):
        """验证 Embedding 向量服务"""
        self.print_section("2. Embedding 向量服务验证")

        # 检查配置
        provider = settings.EMBEDDING_PROVIDER
        if provider == "dashscope" and (
            not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "placeholder"
        ):
            self.skip_test("Embedding 单文本向量化", "Embedding", "未配置 DASHSCOPE_API_KEY")
            return
        if provider == "siliconflow" and not settings.SILICONFLOW_API_KEY:
            self.skip_test("Embedding 单文本向量化", "Embedding", "未配置 SILICONFLOW_API_KEY")
            return

        # 测试 1: 单文本向量化
        async def test_single_embedding():
            text = "测试文本的向量化表示"
            embedding = await embedding_service.get_embedding(text, text_type="document")
            if not embedding or len(embedding) == 0:
                raise ValueError("向量为空")
            expected_dim = settings.EMBEDDING_DIM
            if len(embedding) != expected_dim:
                raise ValueError(f"向量维度错误: 期望 {expected_dim}, 实际 {len(embedding)}")
            return {
                "dimension": len(embedding),
                "provider": provider,
                "sample_values": embedding[:3]
            }

        await self.test_api(
            f"Embedding 单文本向量化 ({provider})",
            test_single_embedding,
            "Embedding",
            f"使用 {provider} 将文本转换为向量"
        )

        # 测试 2: 批量向量化
        async def test_batch_embedding():
            texts = ["第一段测试文本", "第二段测试文本", "第三段测试文本"]
            embeddings = await embedding_service.batch_embeddings(texts, text_type="document")
            if not embeddings or len(embeddings) != len(texts):
                raise ValueError(f"批量返回数量错误: 期望 {len(texts)}, 实际 {len(embeddings)}")
            return {
                "count": len(embeddings),
                "dimension": len(embeddings[0]) if embeddings else 0
            }

        await self.test_api(
            f"Embedding 批量向量化 ({provider})",
            test_batch_embedding,
            "Embedding",
            "批量处理多个文本的向量化"
        )

    async def validate_rerank_service(self):
        """验证 Rerank 重排序服务"""
        self.print_section("3. Rerank 重排序服务验证")

        # 检查配置
        provider = settings.RERANK_PROVIDER
        if provider == "dashscope" and (
            not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "placeholder"
        ):
            self.skip_test("Rerank 文档重排序", "Rerank", "未配置 DASHSCOPE_API_KEY")
            return
        if provider == "siliconflow" and not settings.SILICONFLOW_API_KEY:
            self.skip_test("Rerank 文档重排序", "Rerank", "未配置 SILICONFLOW_API_KEY")
            return

        # 测试重排序
        async def test_rerank():
            query = "什么是机器学习"
            candidates = [
                {"id": "1", "content": "机器学习是人工智能的一个分支，通过算法让计算机从数据中学习。"},
                {"id": "2", "content": "深度学习是机器学习的一个子领域，使用神经网络模型。"},
                {"id": "3", "content": "今天天气很好，适合户外运动。"},
                {"id": "4", "content": "Python是一种流行的编程语言，广泛用于机器学习开发。"},
            ]
            reranked = await rerank_service.rerank(query, candidates, top_k=3)
            if not reranked or len(reranked) == 0:
                raise ValueError("重排序结果为空")
            if len(reranked) > 3:
                raise ValueError(f"返回结果超过 top_k=3: {len(reranked)}")
            return {
                "reranked_count": len(reranked),
                "top_ids": [c.get("id") for c in reranked[:3]],
                "provider": provider
            }

        await self.test_api(
            f"Rerank 文档重排序 ({provider})",
            test_rerank,
            "Rerank",
            f"使用 {provider} 对查询结果进行重排序"
        )

        # 测试 RRF 算法（不需要 API）
        async def test_rrf():
            results1 = [
                {"id": "1", "content": "结果1"},
                {"id": "2", "content": "结果2"},
            ]
            results2 = [
                {"id": "2", "content": "结果2"},
                {"id": "3", "content": "结果3"},
            ]
            fused = rerank_service.reciprocal_rank_fusion([results1, results2], k=60)
            return {
                "fused_count": len(fused),
                "top_ids": [item.get("id") for item, score in fused]
            }

        await self.test_api(
            "Rerank RRF 融合算法",
            test_rrf,
            "Rerank",
            "测试倒数排名融合算法（本地算法，无需API）"
        )

    async def validate_ocr_service(self):
        """验证文档清洗 OCR 服务"""
        self.print_section("4. 文档清洗 OCR 服务验证")

        # 检查配置
        if not settings.ZHIPU_API_KEY:
            self.skip_test("GLM OCR 文档清洗", "OCR", "未配置 ZHIPU_API_KEY")
            return

        # 测试 GLM OCR（生成一张简单图片进行真实识别）
        async def test_ocr_via_api():
            import base64
            import io

            from PIL import Image, ImageDraw

            from app.services.ocr_service import ocr_service

            image = Image.new("RGB", (960, 240), color="white")
            draw = ImageDraw.Draw(image)
            draw.text((40, 90), "GLM OCR connectivity test 123", fill="black")

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            text = await ocr_service.ocr_from_base64(image_b64)
            if not text.strip():
                raise ValueError("GLM OCR 返回空结果")

            return {
                "ocr_model": settings.ZHIPU_OCR_MODEL,
                "base_url": settings.ZHIPU_OCR_BASE_URL,
                "preview": text[:100],
            }

        await self.test_api(
            "GLM OCR 实际识别",
            test_ocr_via_api,
            "OCR",
            "验证智谱 GLM OCR 真实可调用"
        )

        # 测试本地文本清洗
        async def test_text_cleaning():
            from app.core.ingestion.ingestion_service import ingestion_service

            dirty_text = "exam-\nple\n\n\n123\nDo Not Distribute\x00"
            clean_text = ingestion_service._clean_text(dirty_text)
            return {
                "original_length": len(dirty_text),
                "cleaned_length": len(clean_text),
                "preview": clean_text[:50]
            }

        await self.test_api(
            "文档文本清洗",
            test_text_cleaning,
            "OCR",
            "测试本地文本预处理和清洗功能"
        )

    async def validate_translation_service(self):
        """验证翻译服务"""
        self.print_section("5. 翻译服务验证 (Hunyuan)")

        # 检查配置
        if not settings.HUNYUAN_API_KEY:
            self.skip_test("Hunyuan 翻译服务", "Translation", "未配置 HUNYUAN_API_KEY")
            return

        # 测试翻译
        async def test_translation():
            # 直接调用 API 验证连通性与模型可用性
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.HUNYUAN_API_KEY,
                base_url=settings.HUNYUAN_BASE_URL
            )

            prompt = "请将以下文本翻译成中文。只输出翻译结果，不要添加任何解释或额外内容。\n\nHello, how are you?"

            response = await client.chat.completions.create(
                model=settings.HUNYUAN_TRANSLATE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            translation = response.choices[0].message.content.strip()

            if not translation:
                raise ValueError("翻译结果为空")

            return {
                "original": "Hello, how are you?",
                "translation": translation,
                "model": settings.HUNYUAN_TRANSLATE_MODEL
            }

        await self.test_api(
            "Hunyuan 中英翻译",
            test_translation,
            "Translation",
            "使用腾讯混元模型进行中英互译"
        )

    async def validate_asr_service(self):
        """验证 ASR 语音转文字服务"""
        self.print_section("6. ASR 语音转文字服务验证 (Zhipu)")

        # 检查配置
        if not settings.ZHIPU_API_KEY:
            self.skip_test("智谱 ASR 服务", "ASR", "未配置 ZHIPU_API_KEY")
            return

        # 测试智谱 ASR 配置
        async def test_zhipu_asr_config():
            from app.services.stt.providers.zhipu_provider import ZhipuProvider

            try:
                provider = ZhipuProvider()

                # 验证配置
                if not settings.ZHIPU_API_KEY:
                    raise ValueError("ZHIPU_API_KEY 未配置")

                return {
                    "endpoint": provider.endpoint,
                    "model": settings.ZHIPU_ASR_MODEL,
                    "sample_rate": settings.ZHIPU_ASR_SAMPLE_RATE,
                    "max_audio_seconds": settings.ZHIPU_ASR_MAX_AUDIO_SECONDS,
                    "status": "配置验证通过",
                    "note": "完整STT测试需要实际音频文件"
                }

            except Exception as e:
                raise ValueError(f"智谱 ASR 初始化失败: {e}")

        await self.test_api(
            "智谱 ASR 配置验证",
            test_zhipu_asr_config,
            "ASR",
            "验证智谱语音识别配置"
        )

        # 测试 STT 文本增强功能
        async def test_stt_enhancement():
            from app.services.stt_service import stt_service

            # 模拟ASR原始文本（缺少标点、有错误）
            raw_text = "今天天气很好我要去学习"

            # 注意：这需要LLM服务可用，如果LLM不可用会失败
            enhanced = await stt_service.enhance_transcript(raw_text)

            return {
                "original": raw_text,
                "enhanced": enhanced[:100],
                "status": "文本增强功能可用"
            }

        await self.test_api(
            "STT 文本后处理增强",
            test_stt_enhancement,
            "ASR",
            "使用LLM增强ASR转写结果（标点、纠错）"
        )

    async def validate_llm_router(self):
        """验证 LLM 路由器"""
        self.print_section("7. LLM 路由器验证")

        async def test_llm_router():
            from app.core.llm_router import llm_router
            from app.core.agent_profiles import AgentRole, TaskType

            # 测试不同角色的模型选择
            selections = {}
            for role in [AgentRole.GENERATION, AgentRole.MATH_AGENT, AgentRole.CODE_AGENT]:
                selection = llm_router.select_model(role)
                selections[role.value] = {
                    "model": selection.config.model_name,
                    "provider": selection.config.provider.value,
                    "tier": selection.config.tier.value,
                    "reason": selection.reason
                }

            # 测试任务类型切换
            task_selection = llm_router.select_model(
                AgentRole.GENERATION,
                task_type=TaskType.DEEP_REASONING
            )
            selections["deep_reasoning_task"] = {
                "model": task_selection.config.model_name,
                "provider": task_selection.config.provider.value,
                "tier": task_selection.config.tier.value,
                "reason": task_selection.reason
            }

            return selections

        await self.test_api(
            "LLM 路由器模型选择",
            test_llm_router,
            "LLM Router",
            "验证基于角色和任务类型的动态模型选择"
        )

    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试结果摘要")

        print(f"\n  总测试数: {self.total_tests}")
        print(f"  通过:     {self.passed_tests} ✅")
        print(f"  失败:     {self.failed_tests} ❌")
        print(f"  跳过:     {self.skipped_tests} ⏭️")

        if self.total_tests > 0:
            pass_rate = (self.passed_tests / self.total_tests) * 100
            print(f"\n  通过率:   {pass_rate:.1f}%")

        # 按分类统计
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
            categories[cat]["total"] += 1
            if r["status"] == "passed":
                categories[cat]["passed"] += 1
            elif r["status"] == "failed":
                categories[cat]["failed"] += 1
            else:
                categories[cat]["skipped"] += 1

        print(f"\n  按分类统计:")
        for cat, stats in categories.items():
            print(f"    {cat:15} - 通过: {stats['passed']}/{stats['total']}")

        # 失败详情
        if self.failed_tests > 0:
            print(f"\n  失败详情:")
            for r in self.results:
                if r["status"] == "failed":
                    print(f"    ❌ {r['name']}: {r['error']}")

        # API 配置状态
        self.print_section("API 配置状态")

        config_checks = [
            ("Zhipu (Chat/OCR/ASR)", bool(settings.ZHIPU_API_KEY)),
            ("DashScope (LLM/Embedding/Rerank)", settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != "placeholder"),
            ("SiliconFlow (Embedding/Rerank)", bool(settings.SILICONFLOW_API_KEY)),
            ("Hunyuan (Translation)", bool(settings.HUNYUAN_API_KEY)),
            ("XunFei (ASR/STT)", bool(settings.XUNFEI_API_KEY) and bool(settings.XUNFEI_API_SECRET)),
        ]

        for name, configured in config_checks:
            status = "✅ 已配置" if configured else "❌ 未配置"
            print(f"    {name:40} {status}")

        # 最终结论
        self.print_header("验证结论")

        all_critical_passed = self.failed_tests == 0

        if all_critical_passed:
            print("\n  ✅ 所有API服务验证通过！")
            print("  系统已配置完整的大模型API服务能力。")
        else:
            print(f"\n  ⚠️ 发现 {self.failed_tests} 个测试失败")
            print("  请检查API密钥配置和网络连接。")

        print("\n" + "=" * 60 + "\n")

        return all_critical_passed

    async def run_all_tests(self):
        """运行所有测试"""
        self.print_header("🚀 Sparkle 大模型 API 服务全面验证")
        print(f"\n  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  环境: {settings.ENVIRONMENT}")
        print(f"  LLM Provider: {settings.LLM_PROVIDER}")

        # 运行各服务验证
        await self.validate_llm_service()
        await self.validate_embedding_service()
        await self.validate_rerank_service()
        await self.validate_ocr_service()
        await self.validate_translation_service()
        await self.validate_asr_service()
        await self.validate_llm_router()

        # 打印摘要
        return self.print_summary()


async def main():
    """主函数"""
    validator = APIValidator()
    success = await validator.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
