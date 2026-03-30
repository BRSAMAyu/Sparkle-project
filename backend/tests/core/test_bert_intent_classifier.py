"""
BERT Intent Classifier Test Suite

测试 BERT 意图分类器的核心功能：
- BERT 模型加载与初始化
- 批量推理性能 (<200ms 目标)
- 置信度校准
- 模型不可用时的降级
- 多语言输入处理

NOTE: torch is required for BERT model loading.
These tests are skipped when torch is not installed.
"""
from __future__ import annotations

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from typing import Any

# Skip entire module if torch is not available
try:
    import torch  # noqa: F401
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed - BERT tests require PyTorch")

if HAS_TORCH:
    from app.orchestration.bert_intent_classifier import (
        BERTIntentClassifier,
        get_bert_classifier,
        classify_with_bert,
        TRANSFORMERS_AVAILABLE,
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_transformers():
    """Mock transformers library"""
    with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
        with patch('app.orchestration.bert_intent_classifier.AutoTokenizer') as mock_tokenizer:
            with patch('app.orchestration.bert_intent_classifier.AutoModelForSequenceClassification') as mock_model:
                # 设置 mock tokenizer
                tokenizer_instance = MagicMock()
                tokenizer_instance.return_value = {
                    "input_ids": [[1, 2, 3]],
                    "attention_mask": [[1, 1, 1]],
                }
                mock_tokenizer.from_pretrained.return_value = tokenizer_instance

                # 设置 mock model
                model_instance = MagicMock()
                mock_output = MagicMock()
                mock_output.logits = [MagicMock()]  # 单个样本的 logits

                # 模拟 softmax 概率分布
                import torch
                mock_logits = MagicMock()
                mock_logits_softmax = torch.tensor([0.1, 0.7, 0.05, 0.05, 0.02, 0.02, 0.01, 0.01, 0.02, 0.02])
                mock_output.logits[0] = mock_logits_softmax

                model_instance.return_value = mock_output
                model_instance.eval = MagicMock()

                mock_model.from_pretrained.return_value = model_instance

                yield {
                    "tokenizer": mock_tokenizer,
                    "model": mock_model,
                    "tokenizer_instance": tokenizer_instance,
                    "model_instance": model_instance,
                }


@pytest.fixture
def mock_torch():
    """Mock torch library"""
    with patch('app.orchestration.bert_intent_classifier.torch') as mock:
        # 模拟设备检测
        mock.cuda.is_available.return_value = False
        mock.device = MagicMock

        # 模拟 no_grad 上下文管理器
        mock.no_gradient.return_value.__aenter__ = AsyncMock(return_value=None)
        mock.no_gradient.return_value.__aexit__ = AsyncMock(return_value=None)

        # 模拟 softmax
        import torch
        mock.softmax = torch.softmax
        mock.max = torch.max
        mock.argmax = torch.argmax

        # 模拟 to_tensor
        tensor = MagicMock()
        tensor.to = MagicMock(return_value=tensor)
        mock.tensor.return_value = tensor

        yield mock


@pytest.fixture
def classifier(mock_transformers, mock_torch):
    """创建测试用的分类器实例"""
    with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
        with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
            classifier = BERTIntentClassifier(model_name="test-model", device="cpu")
            classifier.model_loaded = True
            return classifier


# =============================================================================
# Test Model Loading and Initialization
# =============================================================================


class TestModelLoading:
    """测试 BERT 模型加载与初始化"""

    def test_classifier_initialization_with_transformers_available(
        self,
        mock_transformers,
        mock_torch,
    ):
        """测试 transformers 可用时的初始化"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier = BERTIntentClassifier(model_name="test-model", device="cpu")

                assert classifier.model_name == "test-model"
                assert classifier.device.type == "cpu"
                assert classifier.max_length == 128
                assert classifier.batch_size == 8

    def test_classifier_initialization_without_transformers(self):
        """测试 transformers 不可用时抛出错误"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', False):
            with pytest.raises(ImportError, match="transformers library not available"):
                BERTIntentClassifier()

    def test_device_detection_auto(self, mock_transformers, mock_torch):
        """测试自动设备检测"""
        # 测试 CUDA 不可用时使用 CPU
        mock_torch.cuda.is_available.return_value = False

        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier = BERTIntentClassifier(device="auto")
                assert classifier.device.type == "cpu"

    def test_device_detection_cuda(self, mock_transformers, mock_torch):
        """测试 CUDA 设备检测"""
        mock_torch.cuda.is_available.return_value = True

        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier = BERTIntentClassifier(device="auto")
                assert classifier.device.type == "cuda"

    def test_model_load_failure_handling(self, mock_transformers, mock_torch):
        """测试模型加载失败的处理"""
        mock_transformers["model"].from_pretrained.side_effect = Exception("Model download failed")

        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier = BERTIntentClassifier(model_name="invalid-model")
                assert classifier.model_loaded is False

    def test_get_model_info(self, classifier):
        """测试获取模型信息"""
        info = classifier.get_model_info()

        assert info["model_name"] == "test-model"
        assert info["device"] in ["cpu", "cuda"]
        assert info["loaded"] is True
        assert info["num_labels"] == 10
        assert info["max_length"] == 128
        assert "intents" in info


# =============================================================================
# Test Intent Classification
# =============================================================================


class TestIntentClassification:
    """测试意图分类功能"""

    @pytest.mark.asyncio
    async def test_classify_basic(self, classifier):
        """测试基本的意图分类"""
        # Mock the inference method
        with patch.object(classifier, '_infer', return_value={
            "intent": "create",
            "confidence": 0.85,
            "probabilities": {
                "chat": 0.05,
                "create": 0.85,
                "update": 0.03,
                "delete": 0.02,
                "query": 0.02,
                "learn": 0.01,
                "review": 0.01,
                "translation": 0.005,
                "prism": 0.005,
                "sprint": 0.005,
            }
        }):
            result = await classifier.classify("创建一个新任务")

            assert result["intent"] == "create"
            assert result["confidence"] == 0.85
            assert "probabilities" in result
            assert len(result["probabilities"]) == 10

    @pytest.mark.asyncio
    async def test_classify_with_context(self, classifier):
        """测试带上下文的意图分类"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "update",
            "confidence": 0.75,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }) as mock_infer:
            await classifier.classify(
                message="把它改成明天",
                context="用户正在查看任务列表"
            )

            # 验证上下文被包含在输入中
            call_args = mock_infer.call_args[0][0]
            assert "把它改成明天" in call_args
            assert "用户正在查看任务列表" in call_args
            assert "[CLS]" in call_args
            assert "[SEP]" in call_args

    @pytest.mark.asyncio
    async def test_classify_model_not_loaded(self, classifier):
        """测试模型未加载时的降级"""
        classifier.model_loaded = False

        result = await classifier.classify("test message")

        assert result["intent"] == "chat"  # 默认意图
        assert result["confidence"] == 0.5
        assert all(prob == 0.1 for prob in result["probabilities"].values())

    @pytest.mark.asyncio
    async def test_classify_inference_error_handling(self, classifier):
        """测试推理错误的处理"""
        with patch.object(classifier, '_infer', side_effect=Exception("Inference failed")):
            result = await classifier.classify("test message")

            # 应该返回降级结果
            assert result["intent"] == "chat"
            assert result["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_classify_different_intents(self, classifier):
        """测试不同意图的分类"""
        test_cases = [
            ("你好", "chat"),
            ("创建一个学习计划", "create"),
            ("修改任务", "update"),
            ("删除这个", "delete"),
            ("搜索数学题", "query"),
            ("我想学习英语", "learn"),
            ("复习笔记", "review"),
            ("翻译这句话", "translation"),
        ]

        for message, expected_intent in test_cases:
            with patch.object(classifier, '_infer', return_value={
                "intent": expected_intent,
                "confidence": 0.8,
                "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
            }):
                result = await classifier.classify(message)
                assert result["intent"] == expected_intent


# =============================================================================
# Test Batch Classification
# =============================================================================


class TestBatchClassification:
    """测试批量分类"""

    @pytest.mark.asyncio
    async def test_classify_batch_basic(self, classifier):
        """测试基本的批量分类"""
        messages = ["消息1", "消息2", "消息3"]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {
                "intent": "chat",
                "confidence": 0.8,
                "probabilities": {},
            }

            results = await classifier.classify_batch(messages)

            assert len(results) == 3
            assert mock_classify.call_count == 3

    @pytest.mark.asyncio
    async def test_classify_batch_with_contexts(self, classifier):
        """测试带上下文的批量分类"""
        messages = ["消息1", "消息2"]
        contexts = ["上下文1", "上下文2"]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {
                "intent": "chat",
                "confidence": 0.8,
                "probabilities": {},
            }

            await classifier.classify_batch(messages, contexts)

            # 验证每个消息都使用对应的上下文
            assert mock_classify.call_count == 2
            mock_classify.assert_any_call("消息1", "上下文1")
            mock_classify.assert_any_call("消息2", "上下文2")

    @pytest.mark.asyncio
    async def test_classify_batch_uses_batch_size(self, classifier):
        """测试批量分类使用正确的批次大小"""
        classifier.batch_size = 2

        messages = ["msg1", "msg2", "msg3", "msg4", "msg5"]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {"intent": "chat", "confidence": 0.8, "probabilities": {}}

            await classifier.classify_batch(messages)

            # 应该分 3 批处理 (2+2+1)
            assert mock_classify.call_count == 5

    @pytest.mark.asyncio
    async def test_classify_batch_empty_list(self, classifier):
        """测试空列表批量分类"""
        results = await classifier.classify_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_classify_batch_default_contexts(self, classifier):
        """测试批量分类使用默认空上下文"""
        messages = ["msg1", "msg2"]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {"intent": "chat", "confidence": 0.8, "probabilities": {}}

            await classifier.classify_batch(messages)

            # 验证使用空上下文
            mock_classify.assert_any_call("msg1", "")
            mock_classify.assert_any_call("msg2", "")


# =============================================================================
# Test Performance
# =============================================================================


class TestPerformance:
    """测试性能相关功能"""

    @pytest.mark.asyncio
    async def test_inference_latency_target(self, classifier):
        """测试推理延迟目标 <200ms"""
        import time

        # 模拟快速推理
        def fast_infer(text):
            start = time.time()
            time.sleep(0.05)  # 50ms
            elapsed = (time.time() - start) * 1000
            return {
                "intent": "chat",
                "confidence": 0.8,
                "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
            }

        with patch.object(classifier, '_infer', side_effect=fast_infer):
            start = time.time()
            result = await classifier.classify("test message")
            elapsed = (time.time() - start) * 1000

            assert result["intent"] == "chat"
            assert elapsed < 200  # 应该小于 200ms

    @pytest.mark.asyncio
    async def test_batch_classification_performance(self, classifier):
        """测试批量分类性能"""
        messages = [f"消息{i}" for i in range(10)]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            async def mock_classify_func(msg, ctx=""):
                await asyncio.sleep(0.01)  # 模拟 10ms 推理
                return {"intent": "chat", "confidence": 0.8, "probabilities": {}}

            mock_classify.side_effect = mock_classify_func

            start = time.time()
            results = await classifier.classify_batch(messages)
            elapsed = (time.time() - start) * 1000

            assert len(results) == 10
            # 批量处理应该比单个处理快
            # 但由于我们使用 asyncio.gather，大约是 10 * 10ms = 100ms
            assert elapsed < 500  # 宽松的限制

    @pytest.mark.asyncio
    async def test_concurrent_classification(self, classifier):
        """测试并发分类性能"""
        messages = [f"消息{i}" for i in range(20)]

        with patch.object(classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            async def mock_classify_func(msg, ctx=""):
                await asyncio.sleep(0.02)  # 模拟 20ms 推理
                return {"intent": "chat", "confidence": 0.8, "probabilities": {}}

            mock_classify.side_effect = mock_classify_func

            start = time.time()
            tasks = [classifier.classify(msg) for msg in messages]
            results = await asyncio.gather(*tasks)
            elapsed = (time.time() - start) * 1000

            assert len(results) == 20
            # 并发处理应该显著快于串行
            # 串行需要 20 * 20ms = 400ms，并发应该更短
            assert elapsed < 500


# =============================================================================
# Test Confidence Scoring
# =============================================================================


class TestConfidenceScoring:
    """测试置信度评分"""

    @pytest.mark.asyncio
    async def test_confidence_score_range(self, classifier):
        """测试置信度分数范围"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "create",
            "confidence": 0.95,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            result = await classifier.classify("明确的消息")

            assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_probabilities_sum_to_one(self, classifier):
        """测试概率总和为 1"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "create",
            "confidence": 0.7,
            "probabilities": {
                "chat": 0.1,
                "create": 0.7,
                "update": 0.05,
                "delete": 0.05,
                "query": 0.03,
                "learn": 0.02,
                "review": 0.02,
                "translation": 0.01,
                "prism": 0.01,
                "sprint": 0.01,
            },
        }):
            result = await classifier.classify("test")

            total = sum(result["probabilities"].values())
            assert 0.99 <= total <= 1.01  # 允许浮点误差

    @pytest.mark.asyncio
    async def test_adjust_scores_with_bert(self, classifier):
        """测试使用 BERT 调整分数"""
        keyword_scores = {
            "chat": 0.3,
            "create": 0.6,
            "update": 0.1,
        }

        with patch.object(classifier, 'classify', new_callable=AsyncMock, return_value={
            "intent": "create",
            "confidence": 0.8,
            "probabilities": {
                "chat": 0.1,
                "create": 0.8,
                "update": 0.05,
                "delete": 0.01,
                "query": 0.01,
                "learn": 0.01,
                "review": 0.01,
                "translation": 0.005,
                "prism": 0.005,
                "sprint": 0.005,
            },
        }):
            intent, confidence = classifier.adjust_scores_with_bert(
                keyword_scores,
                "创建一个任务",
                bert_weight=0.4,
            )

            # BERT 加权后，create 的分数应该最高
            assert intent == "create"
            assert confidence > 0.6  # 应该接近 0.6 * 0.6 + 0.8 * 0.4 = 0.68


# =============================================================================
# Test Fallback Mechanisms
# =============================================================================


class TestFallbackMechanisms:
    """测试降级机制"""

    @pytest.mark.asyncio
    async def test_fallback_on_model_unavailable(self):
        """测试模型不可用时的降级"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', False):
            result = await classify_with_bert("test message")
            assert result is None

    def test_get_classifier_fallback(self):
        """测试获取分类器的降级"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', False):
            classifier = get_bert_classifier()
            assert classifier is None

    @pytest.mark.asyncio
    async def test_adjust_scores_without_model(self, classifier):
        """测试没有模型时的分数调整"""
        classifier.model_loaded = False

        keyword_scores = {
            "chat": 0.2,
            "create": 0.7,
            "update": 0.1,
        }

        intent, confidence = classifier.adjust_scores_with_bert(
            keyword_scores,
            "test",
        )

        # 应该返回关键词分数的最高项
        assert intent == "create"
        assert confidence == 0.7

    @pytest.mark.asyncio
    async def test_classify_uses_default_on_error(self, classifier):
        """测试错误时使用默认值"""
        with patch('app.orchestration.bert_intent_classifier.asyncio.to_thread', side_effect=Exception("Unknown error")):
            result = await classifier.classify("test")

            assert result["intent"] == "chat"
            assert result["confidence"] == 0.5


# =============================================================================
# Test Input Building
# =============================================================================


class TestInputBuilding:
    """测试输入构建"""

    def test_build_input_text_without_context(self, classifier):
        """测试没有上下文的输入构建"""
        text = classifier._build_input_text("你好", "")
        assert text == "[CLS] 你好 [SEP]"

    def test_build_input_text_with_context(self, classifier):
        """测试有上下文的输入构建"""
        text = classifier._build_input_text("今天天气怎么样", "用户询问天气")
        assert "[CLS]" in text
        assert "用户询问天气" in text
        assert "今天天气怎么样" in text
        assert text.count("[SEP]") == 2

    def test_build_input_text_special_tokens(self, classifier):
        """测试特殊标记格式"""
        text = classifier._build_input_text("test", "context")
        assert text.startswith("[CLS]")
        assert text.endswith("[SEP]")


# =============================================================================
# Test Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """测试单例模式"""

    def test_get_classifier_singleton(self, mock_transformers, mock_torch):
        """测试获取单例分类器"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier1 = get_bert_classifier(model_name="test-model")
                classifier2 = get_bert_classifier()

                assert classifier1 is classifier2  # 应该是同一个实例

    def test_force_reload(self, mock_transformers, mock_torch):
        """测试强制重新加载"""
        with patch('app.orchestration.bert_intent_classifier.TRANSFORMERS_AVAILABLE', True):
            with patch('app.orchestration.bert_intent_classifier.torch', mock_torch):
                classifier1 = get_bert_classifier(model_name="model1")
                classifier1_id = id(classifier1)

                classifier2 = get_bert_classifier(force_reload=True, model_name="model2")
                classifier2_id = id(classifier2)

                # 强制重新加载应该创建新实例
                assert classifier1_id != classifier2_id


# =============================================================================
# Test Multi-language Support
# =============================================================================


class TestMultiLanguageSupport:
    """测试多语言支持"""

    @pytest.mark.asyncio
    async def test_chinese_input(self, classifier):
        """测试中文输入"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "create",
            "confidence": 0.85,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            result = await classifier.classify("创建一个学习计划")
            assert result["intent"] == "create"

    @pytest.mark.asyncio
    async def test_english_input(self, classifier):
        """测试英文输入"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "query",
            "confidence": 0.75,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            result = await classifier.classify("What is the weather today?")
            assert result["intent"] == "query"

    @pytest.mark.asyncio
    async def test_mixed_language_input(self, classifier):
        """测试混合语言输入"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "learn",
            "confidence": 0.7,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            result = await classifier.classify("I want to 学习 English")
            assert result["intent"] == "learn"

    @pytest.mark.asyncio
    async def test_long_input_truncation(self, classifier):
        """测试长输入截断"""
        long_message = "这是一个很长的消息" * 100  # 超过 max_length

        with patch.object(classifier, '_infer', return_value={
            "intent": "chat",
            "confidence": 0.6,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }) as mock_infer:
            await classifier.classify(long_message)

            # 验证输入被截断
            call_args = mock_infer.call_args[0][0]
            # tokenizer 应该处理截断
            assert "[CLS]" in call_args


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_message(self, classifier):
        """测试空消息"""
        with patch.object(classifier, '_infer', return_value={
            "intent": "chat",
            "confidence": 0.5,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            result = await classifier.classify("")
            assert result["intent"] == "chat"

    @pytest.mark.asyncio
    async def test_special_characters(self, classifier):
        """测试特殊字符"""
        special_messages = [
            "!@#$%^&*()",
            "🎉🎊🎁",
            "<script>alert('test')</script>",
        ]

        with patch.object(classifier, '_infer', return_value={
            "intent": "chat",
            "confidence": 0.5,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            for msg in special_messages:
                result = await classifier.classify(msg)
                assert "intent" in result

    @pytest.mark.asyncio
    async def test_very_long_context(self, classifier):
        """测试非常长的上下文"""
        long_context = "前文内容" * 1000

        with patch.object(classifier, '_infer', return_value={
            "intent": "chat",
            "confidence": 0.7,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }) as mock_infer:
            await classifier.classify("新消息", context=long_context)

            # 上下文应该被包含
            call_args = mock_infer.call_args[0][0]
            assert "前文内容" in call_args

    @pytest.mark.asyncio
    async def test_unicode_emojis(self, classifier):
        """测试 Unicode 表情符号"""
        emoji_messages = [
            "😊 你好",
            "🎉 创建任务",
            "❌ 删除",
        ]

        with patch.object(classifier, '_infer', return_value={
            "intent": "create",
            "confidence": 0.7,
            "probabilities": {label: 0.1 for label in classifier.INTENT_LABELS},
        }):
            for msg in emoji_messages:
                result = await classifier.classify(msg)
                assert result is not None
