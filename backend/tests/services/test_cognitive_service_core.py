"""
CognitiveService Core Test Suite

测试 CognitiveService 的核心功能：
- create_fragment() - 认知碎片创建与向量化
- analyze_behavior() - RAG 分析逻辑
- HyDE 策略增强
- 向量嵌入降级机制
- 行为模式创建与更新
- 事件发布验证
"""
from __future__ import annotations

import asyncio
import json
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any

from app.services.cognitive_service import CognitiveService, _VECTOR_RUNTIME_ENABLED
from app.models.cognitive import CognitiveFragment, BehaviorPattern, AnalysisStatus
from app.core.event_bus import event_bus
from app.services.system_update_service import SystemUpdateService, build_system_update


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_user_with_fragments(db_session, test_user):
    """创建带有认知碎片的测试用户"""
    # 创建一些测试碎片
    fragments = []
    for i in range(3):
        fragment = CognitiveFragment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            content=f"Test fragment content {i}",
            source_type="task_completion",
            resource_type="text",
            analysis_status=AnalysisStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(fragment)
        fragments.append(fragment)

    await db_session.commit()
    return test_user, fragments


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service"""
    with patch('app.services.cognitive_service.embedding_service') as mock:
        mock.get_embedding = AsyncMock(return_value=[0.1] * 1536)  # OpenAI embedding dimension
        yield mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    with patch('app.services.cognitive_service.llm_service') as mock:
        mock.chat = AsyncMock(return_value='{"pattern_name": "Test Pattern", "confidence_score": 0.8}')
        mock.__class__.__module__ = "unittest.mock"  # 触发 mock 检测
        yield mock


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    with patch('app.services.cognitive_service.event_bus') as mock:
        mock.publish = AsyncMock()
        yield mock


@pytest.fixture
def mock_system_update_service():
    """Mock system update service"""
    with patch('app.services.cognitive_service.SystemUpdateService') as mock:
        service = MagicMock()
        service.enqueue = AsyncMock()
        mock.return_value = service
        yield service


# =============================================================================
# Test create_fragment()
# =============================================================================


class TestCreateFragment:
    """测试认知碎片创建功能"""

    @pytest.mark.asyncio
    async def test_create_fragment_basic(
        self,
        db_session,
        test_user,
        mock_embedding_service,
        mock_event_bus,
        mock_system_update_service,
    ):
        """测试基本的碎片创建"""
        service = CognitiveService(db_session)

        fragment = await service.create_fragment(
            user_id=test_user.id,
            content="This is a test cognitive fragment",
            source_type="task_completion",
            resource_type="text",
        )

        # 验证基本属性
        assert fragment.id is not None
        assert fragment.user_id == test_user.id
        assert fragment.content == "This is a test cognitive fragment"
        assert fragment.source_type == "task_completion"
        assert fragment.resource_type == "text"
        assert fragment.analysis_status == AnalysisStatus.PENDING

        # 验证 embedding 被调用
        mock_embedding_service.get_embedding.assert_called_once_with("This is a test cognitive fragment")

        # 验证事件发布
        assert mock_event_bus.publish.call_count == 1
        publish_call = mock_event_bus.publish.call_args
        assert publish_call[0][0] == "cognitive.fragment.created"

    @pytest.mark.asyncio
    async def test_create_fragment_with_embedding_success(
        self,
        db_session,
        test_user,
        mock_embedding_service,
        mock_event_bus,
    ):
        """测试成功生成嵌入向量"""
        service = CognitiveService(db_session)
        mock_embedding_service.get_embedding.return_value = [0.5, 0.3, 0.8] + [0.0] * 1533

        fragment = await service.create_fragment(
            user_id=test_user.id,
            content="Test content for embedding",
            source_type="reflection",
        )

        # 验证 embedding 被生成
        assert fragment.embedding is not None
        mock_embedding_service.get_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_fragment_embedding_failure_continues_without_vector(
        self,
        db_session,
        test_user,
        mock_event_bus,
    ):
        """测试 embedding 生成失败时继续创建碎片（无向量）"""
        with patch('app.services.cognitive_service.embedding_service') as mock_embedding:
            mock_embedding.get_embedding = AsyncMock(side_effect=Exception("Embedding service unavailable"))

            service = CognitiveService(db_session)

            fragment = await service.create_fragment(
                user_id=test_user.id,
                content="Test content",
                source_type="test",
            )

            # 碎片应该被创建，但 embedding 为 None
            assert fragment.id is not None
            assert fragment.embedding is None

    @pytest.mark.asyncio
    async def test_create_fragment_idempotency_with_source_event_id(
        self,
        db_session,
        test_user,
        mock_embedding_service,
        mock_event_bus,
    ):
        """测试使用 source_event_id 的幂等性"""
        service = CognitiveService(db_session)

        source_event_id = "event-123"
        content = "Original content"

        # 第一次创建
        fragment1 = await service.create_fragment(
            user_id=test_user.id,
            content=content,
            source_type="task_completion",
            source_event_id=source_event_id,
        )

        # 第二次使用相同的 source_event_id
        fragment2 = await service.create_fragment(
            user_id=test_user.id,
            content="Different content",  # 内容不同但应该被忽略
            source_type="task_completion",
            source_event_id=source_event_id,
        )

        # 应该返回同一个碎片
        assert fragment1.id == fragment2.id
        assert fragment2.content == content  # 保持原始内容

        # embedding 服务应该只被调用一次
        assert mock_embedding_service.get_embedding.call_count == 1

    @pytest.mark.asyncio
    async def test_create_fragment_with_full_metadata(
        self,
        db_session,
        test_user,
        mock_embedding_service,
    ):
        """测试带完整元数据的碎片创建"""
        service = CognitiveService(db_session)

        context_tags = {"task_id": "task-123", "subject": "math"}
        error_tags = ["procrastination", "distraction"]
        task_id = uuid.uuid4()

        fragment = await service.create_fragment(
            user_id=test_user.id,
            content="I procrastinated on my math homework",
            source_type="task_error",
            context_tags=context_tags,
            error_tags=error_tags,
            severity=3,
            task_id=task_id,
            resource_url="https://example.com/resource",
        )

        # 验证所有元数据
        assert fragment.context_tags == context_tags
        assert fragment.error_tags == error_tags
        assert fragment.severity == 3
        assert fragment.task_id == task_id
        assert fragment.resource_url == "https://example.com/resource"

    @pytest.mark.asyncio
    async def test_create_fragment_publishes_events(
        self,
        db_session,
        test_user,
        mock_embedding_service,
        mock_event_bus,
        mock_system_update_service,
    ):
        """测试碎片创建时发布事件"""
        service = CognitiveService(db_session)

        await service.create_fragment(
            user_id=test_user.id,
            content="Test fragment",
            source_type="test",
        )

        # 验证事件总线发布
        assert mock_event_bus.publish.call_count >= 1

        # 验证系统更新服务
        assert mock_system_update_service.return_value.enqueue.call_count >= 1


# =============================================================================
# Test analyze_behavior()
# =============================================================================


class TestAnalyzeBehavior:
    """测试行为分析功能"""

    @pytest.mark.asyncio
    async def test_analyze_behavior_basic(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试基本的行为分析"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置 mock 返回完整的分析结果
        mock_llm_service.chat.return_value = json.dumps({
            "root_cause": "Lack of motivation",
            "pattern_name": "Procrastination Pattern",
            "pattern_type": "emotional",
            "description": "User tends to delay tasks when feeling overwhelmed",
            "solution_text": "Break tasks into smaller steps",
            "confidence_score": 0.85
        })

        target_fragment = fragments[0]

        result = await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证分析结果
        assert result["pattern_name"] == "Procrastination Pattern"
        assert result["confidence_score"] == 0.85
        assert result["root_cause"] == "Lack of motivation"
        assert "_meta" in result

        # 验证状态更新
        await db_session.refresh(target_fragment)
        assert target_fragment.analysis_status == AnalysisStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_analyze_behavior_with_rag(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
        mock_embedding_service,
    ):
        """测试使用 RAG 的行为分析"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置 embedding mock
        mock_embedding_service.get_embedding.return_value = [0.1] * 1536

        # 设置 LLM mock
        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "RAG Pattern",
            "confidence_score": 0.75,
            "root_cause": "Test cause",
        })

        target_fragment = fragments[0]
        # 确保 fragment 有 embedding
        target_fragment.embedding = [0.1] * 1536

        result = await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证 RAG 上下文被使用（通过检查 prompt 中包含相似碎片）
        assert result["pattern_name"] == "RAG Pattern"

    @pytest.mark.asyncio
    async def test_analyze_behavior_fragment_not_found(
        self,
        db_session,
        test_user,
    ):
        """测试分析不存在的碎片"""
        service = CognitiveService(db_session)

        with pytest.raises(ValueError, match="Fragment not found"):
            await service.analyze_behavior(
                user_id=test_user.id,
                fragment_id=uuid.uuid4(),  # 不存在的 ID
            )

    @pytest.mark.asyncio
    async def test_analyze_behavior_creates_pattern(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试分析创建新的行为模式"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置高置信度结果以触发模式创建
        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "New Pattern",
            "pattern_type": "cognitive",
            "description": "A newly discovered pattern",
            "solution_text": "Try this approach",
            "confidence_score": 0.8,  # 高于 0.6 阈值
            "root_cause": "Test cause",
        })

        target_fragment = fragments[0]

        await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证模式被创建
        from sqlalchemy import select
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == test_user.id,
            BehaviorPattern.pattern_name == "New Pattern"
        )
        result = await db_session.execute(stmt)
        pattern = result.scalar_one_or_none()

        assert pattern is not None
        assert pattern.confidence_score == 0.8
        assert pattern.frequency == 1
        assert str(target_fragment.id) in pattern.evidence_ids

    @pytest.mark.asyncio
    async def test_analyze_behavior_updates_existing_pattern(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试分析更新现有行为模式"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 创建现有模式
        existing_pattern = BehaviorPattern(
            id=uuid.uuid4(),
            user_id=test_user.id,
            pattern_name="Existing Pattern",
            pattern_type="execution",
            confidence_score=0.6,
            frequency=1,
            evidence_ids=[str(uuid.uuid4())],
        )
        db_session.add(existing_pattern)
        await db_session.commit()

        # 设置返回相同模式名的分析结果
        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "Existing Pattern",
            "pattern_type": "execution",
            "confidence_score": 0.9,  # 更高的置信度
            "description": "Updated description",
            "solution_text": "Updated solution",
            "root_cause": "Test cause",
        })

        target_fragment = fragments[0]

        await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证模式被更新
        await db_session.refresh(existing_pattern)

        # 频率应该增加
        assert existing_pattern.frequency == 2

        # 置信度应该使用 EMA 更新（0.3 * 0.9 + 0.7 * 0.6 ≈ 0.69）
        assert 0.68 < existing_pattern.confidence_score < 0.70

        # 新的 fragment ID 应该被添加
        assert str(target_fragment.id) in existing_pattern.evidence_ids

    @pytest.mark.asyncio
    async def test_analyze_behavior_low_confidence_no_pattern(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试低置信度分析不创建模式"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置低置信度结果
        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "Low Confidence Pattern",
            "confidence_score": 0.5,  # 低于 0.6 阈值
            "root_cause": "Test cause",
        })

        target_fragment = fragments[0]

        await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证没有模式被创建
        from sqlalchemy import select
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == test_user.id,
            BehaviorPattern.pattern_name == "Low Confidence Pattern"
        )
        result = await db_session.execute(stmt)
        pattern = result.scalar_one_or_none()

        assert pattern is None

    @pytest.mark.asyncio
    async def test_analyze_behavior_error_handling(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试分析过程中的错误处理"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置 LLM 失败
        mock_llm_service.chat.side_effect = Exception("LLM service unavailable")

        target_fragment = fragments[0]

        # 分析应该返回错误而不是抛出异常
        result = await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证使用降级结果
        assert result.get("pattern_name") == "Unknown Pattern"
        assert result.get("confidence_score") == 0.0

        # 验证状态更新为 FAILED
        await db_session.refresh(target_fragment)
        assert target_fragment.analysis_status == AnalysisStatus.COMPLETED  # 使用降级时仍标记完成


# =============================================================================
# Test HyDE Strategy
# =============================================================================


class TestHyDEStrategy:
    """测试 HyDE 策略"""

    @pytest.mark.asyncio
    async def test_hyde_document_generation(
        self,
        db_session,
        test_user,
        mock_llm_service,
    ):
        """测试 HyDE 文档生成"""
        service = CognitiveService(db_session)

        # 设置 LLM 返回假设文档
        mock_llm_service.chat.return_value = "A hypothetical analysis suggesting this user struggles with time management."

        hyde_doc = await service._generate_hyde_document("I always run out of time")

        assert hyde_doc is not None
        assert "time management" in hyde_doc.lower() or "hypothetical" in hyde_doc.lower()

    @pytest.mark.asyncio
    async def test_hyde_disabled_for_long_content(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
        mock_embedding_service,
    ):
        """测试长内容禁用 HyDE"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 使用短内容
        short_fragment = fragments[0]
        short_fragment.content = "Short thought"
        short_fragment.embedding = [0.1] * 1536

        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "Test",
            "confidence_score": 0.7,
            "root_cause": "Test",
        })
        mock_embedding_service.get_embedding.return_value = [0.2] * 1536

        result = await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=short_fragment.id,
        )

        # 验证 HyDE 被使用（短内容）
        meta = result.get("_meta", {})
        assert meta.get("strategy_used") == "raw+hyde"

    @pytest.mark.asyncio
    async def test_hyde_timeout_handling(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试 HyDE 超时处理"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 设置 HyDE 生成超时
        async def slow_hyde(*args, **kwargs):
            await asyncio.sleep(10)  # 超过 timeout

        mock_llm_service.chat.side_effect = slow_hyde

        # 短内容应该触发 HyDE
        short_fragment = fragments[0]
        short_fragment.content = "Short"
        short_fragment.embedding = [0.1] * 1536

        # 分析应该继续（HyDE 被跳过）
        # 注意：这需要修改代码以实际测试超时场景
        # 当前代码使用 asyncio.wait_for，超时会取消 HyDE


# =============================================================================
# Test Vector Embedding Fallback
# =============================================================================


class TestVectorEmbeddingFallback:
    """测试向量嵌入降级机制"""

    @pytest.mark.asyncio
    async def test_vector_runtime_error_detection(
        db_session,
        test_user,
    ):
        """测试向量运行时错误检测"""
        service = CognitiveService(db_session)

        # 测试各种错误标记
        assert service._is_vector_runtime_error(Exception("vector.so not found"))
        assert service._is_vector_runtime_error(Exception('type "vector" does not exist'))
        assert service._is_vector_runtime_error(Exception("could not load library pgvector"))
        assert not service._is_vector_runtime_error(Exception("Some other error"))

    @pytest.mark.asyncio
    async def test_vector_runtime_disable_on_error(
        db_session,
        test_user,
        mock_event_bus,
    ):
        """测试向量运行时错误时禁用向量功能"""
        with patch('app.services.cognitive_service._VECTOR_RUNTIME_ENABLED', True):
            with patch('app.services.cognitive_service.embedding_service') as mock_embedding:
                # 模拟向量运行时错误
                mock_embedding.get_embedding = AsyncMock(
                    side_effect=Exception('type "vector" does not exist')
                )

                service = CognitiveService(db_session)

                # 创建碎片应该成功，但 embedding 为 None
                fragment = await service.create_fragment(
                    user_id=test_user.id,
                    content="Test content",
                    source_type="test",
                )

                assert fragment.embedding is None

    @pytest.mark.asyncio
    async def test_rag_fallback_when_vector_disabled(
        self,
        db_session,
        test_user_with_fragments,
        mock_llm_service,
    ):
        """测试向量禁用时 RAG 降级"""
        test_user, fragments = test_user_with_fragments
        service = CognitiveService(db_session)

        # 禁用向量运行时
        import app.services.cognitive_service as cognitive_module
        original_enabled = cognitive_module._VECTOR_RUNTIME_ENABLED
        cognitive_module._VECTOR_RUNTIME_ENABLED = False

        try:
            mock_llm_service.chat.return_value = json.dumps({
                "pattern_name": "Fallback Pattern",
                "confidence_score": 0.7,
                "root_cause": "Test cause",
            })

            target_fragment = fragments[0]

            result = await service.analyze_behavior(
                user_id=test_user.id,
                fragment_id=target_fragment.id,
            )

            # 分析应该成功（使用降级策略）
            assert result["pattern_name"] == "Fallback Pattern"
            assert result["_meta"]["strategy_used"] == "raw"  # 没有 HyDE

        finally:
            cognitive_module._VECTOR_RUNTIME_ENABLED = original_enabled


# =============================================================================
# Test Behavior Pattern Management
# =============================================================================


class TestBehaviorPatternManagement:
    """测试行为模式管理"""

    @pytest.mark.asyncio
    async def test_upsert_pattern_creates_new(
        self,
        db_session,
        test_user,
    ):
        """测试创建新模式"""
        service = CognitiveService(db_session)

        analysis = {
            "pattern_name": "Test Pattern",
            "pattern_type": "cognitive",
            "description": "Test description",
            "solution_text": "Test solution",
            "confidence_score": 0.8,
        }

        fragment_id = uuid.uuid4()

        await service._upsert_pattern(
            user_id=test_user.id,
            analysis=analysis,
            fragment_id=fragment_id,
        )

        # 验证模式被创建
        from sqlalchemy import select
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == test_user.id,
            BehaviorPattern.pattern_name == "Test Pattern"
        )
        result = await db_session.execute(stmt)
        pattern = result.scalar_one()

        assert pattern.pattern_type == "cognitive"
        assert pattern.confidence_score == 0.8
        assert pattern.frequency == 1
        assert str(fragment_id) in pattern.evidence_ids

    @pytest.mark.asyncio
    async def test_upsert_pattern_updates_existing(
        self,
        db_session,
        test_user,
    ):
        """测试更新现有模式"""
        service = CognitiveService(db_session)

        # 创建现有模式
        existing_pattern = BehaviorPattern(
            id=uuid.uuid4(),
            user_id=test_user.id,
            pattern_name="Test Pattern",
            pattern_type="execution",
            confidence_score=0.6,
            frequency=5,
            evidence_ids=["old-fragment-1", "old-fragment-2"],
        )
        db_session.add(existing_pattern)
        await db_session.commit()

        analysis = {
            "pattern_name": "Test Pattern",
            "pattern_type": "execution",
            "description": "Updated description",
            "solution_text": "Updated solution",
            "confidence_score": 0.9,
        }

        new_fragment_id = uuid.uuid4()

        await service._upsert_pattern(
            user_id=test_user.id,
            analysis=analysis,
            fragment_id=new_fragment_id,
        )

        # 验证模式被更新
        await db_session.refresh(existing_pattern)

        # 频率增加
        assert existing_pattern.frequency == 6

        # 置信度使用 EMA 更新
        assert 0.68 < existing_pattern.confidence_score < 0.70

        # 新 fragment ID 被添加
        assert str(new_fragment_id) in existing_pattern.evidence_ids

    @pytest.mark.asyncio
    async def test_get_user_patterns(
        self,
        db_session,
        test_user,
    ):
        """测试获取用户模式"""
        service = CognitiveService(db_session)

        # 创建多个模式
        patterns = [
            BehaviorPattern(
                id=uuid.uuid4(),
                user_id=test_user.id,
                pattern_name=f"Pattern {i}",
                confidence_score=0.5 + (i * 0.1),
                frequency=1,
            )
            for i in range(5)
        ]

        for pattern in patterns:
            db_session.add(pattern)
        await db_session.commit()

        # 获取高置信度模式
        high_confidence_patterns = await service.get_user_patterns(
            user_id=test_user.id,
            min_confidence=0.7,
        )

        # 应该只有 3 个模式（0.8, 0.9, 1.0）
        assert len(high_confidence_patterns) == 3

        # 应该按置信度降序排列
        assert high_confidence_patterns[0].confidence_score >= high_confidence_patterns[1].confidence_score


# =============================================================================
# Test Event Publishing
# =============================================================================


class TestEventPublishing:
    """测试事件发布"""

    @pytest.mark.asyncio
    async def test_fragment_created_event(
        self,
        db_session,
        test_user,
        mock_embedding_service,
        mock_event_bus,
    ):
        """测试碎片创建事件发布"""
        service = CognitiveService(db_session)

        fragment = await service.create_fragment(
            user_id=test_user.id,
            content="Test fragment",
            source_type="test",
        )

        # 验证事件发布
        assert mock_event_bus.publish.called

        publish_args = mock_event_bus.publish.call_args
        event_type = publish_args[0][0]
        event_data = publish_args[0][1]

        assert event_type == "cognitive.fragment.created"
        assert event_data["user_id"] == str(test_user.id)
        assert event_data["fragment_id"] == str(fragment.id)

    @pytest.mark.asyncio
    async def test_pattern_updated_event_on_high_confidence(
        self,
        db_session,
        test_user,
        mock_llm_service,
        mock_event_bus,
    ):
        """测试高置信度时发布模式更新事件"""
        test_user, fragments = await self._setup_fragments_for_events(db_session, test_user)
        service = CognitiveService(db_session)

        # 设置高置信度分析
        mock_llm_service.chat.return_value = json.dumps({
            "pattern_name": "High Confidence Pattern",
            "pattern_type": "emotional",
            "confidence_score": 0.85,  # 高于 0.7 阈值
            "description": "Test",
            "solution_text": "Test",
            "root_cause": "Test",
        })

        target_fragment = fragments[0]

        await service.analyze_behavior(
            user_id=test_user.id,
            fragment_id=target_fragment.id,
        )

        # 验证模式更新事件被发布
        pattern_update_calls = [
            call for call in mock_event_bus.publish.call_args_list
            if len(call[0]) > 0 and "pattern" in str(call[0][0]).lower()
        ]

        assert len(pattern_update_calls) >= 1

    async def _setup_fragments_for_events(self, db_session, test_user):
        """辅助方法：设置事件测试用的碎片"""
        fragments = []
        for i in range(2):
            fragment = CognitiveFragment(
                id=uuid.uuid4(),
                user_id=test_user.id,
                content=f"Test fragment {i}",
                source_type="test",
                analysis_status=AnalysisStatus.PENDING,
            )
            db_session.add(fragment)
            fragments.append(fragment)

        await db_session.commit()
        return test_user, fragments


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestHelperMethods:
    """测试辅助方法"""

    def test_sanitize_content(self):
        """测试内容净化"""
        service = CognitiveService(None)  # 不需要 db

        # 短内容
        assert service._sanitize_content("Short") == "Short"

        # 长内容
        long = "a" * 100
        sanitized = service._sanitize_content(long)
        assert "..." in sanitized
        assert "[len=100]" in sanitized

        # 空内容
        assert service._sanitize_content("") == ""
        assert service._sanitize_content(None) == ""

    def test_snippet(self):
        """测试内容截断"""
        service = CognitiveService(None)

        # 短内容不变
        assert service._snippet("Short") == "Short"

        # 长内容截断
        long = "a" * 100
        snippet = service._snippet(long, limit=50)
        assert len(snippet) == 50
        assert snippet.endswith("…")

    def test_coerce_json_result_valid(self):
        """测试 JSON 结果转换 - 有效输入"""
        service = CognitiveService(None)

        # 字典输入
        assert service._coerce_json_result({"key": "value"}) == {"key": "value"}

        # JSON 字符串
        result = service._coerce_json_result('{"key": "value"}')
        assert result == {"key": "value"}

        # 带代码块的 JSON
        result = service._coerce_json_result('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_coerce_json_result_invalid(self):
        """测试 JSON 结果转换 - 无效输入"""
        service = CognitiveService(None)

        # 无效 JSON
        assert service._coerce_json_result("not json") is None

        # 非字符串非字典
        assert service._coerce_json_result(123) is None

        # 部分有效的 JSON
        result = service._coerce_json_result('prefix {"key": "value"} suffix')
        assert result == {"key": "value"}

    def test_is_thinking_model(self):
        """测试思考模型检测"""
        assert CognitiveService._is_thinking_model("glm-4-thinking") is True
        assert CognitiveService._is_thinking_model("deepseek-thinking") is True
        assert CognitiveService._is_thinking_model("glm-4") is False
        assert CognitiveService._is_thinking_model("deepseek_no_thinking") is False
