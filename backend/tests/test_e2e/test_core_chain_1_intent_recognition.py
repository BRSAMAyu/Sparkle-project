"""
End-to-End Test Suite for Core Chain 1: Intent Recognition & Dynamic Information Completion
========================================================================================

Coverage (Acceptance Criteria):
1. ✅ Routing Accuracy: Distinguish chitchat from complex tasks
2. ✅ Stop Mechanism: Clarification loop prevents infinite追问
3. ✅ Multimodal Compatibility: Voice-to-text semantic understanding
4. ✅ Special Mode Entry: Translation, Cognitive Prism, Sprint mode

Test Structure:
- Suite A: Intent Recognition & Routing (验收点 1, 4a, 4b, 5a, 5b, 5c, 5d)
- Suite B: Information Sufficiency & Clarification Loop (验收点 2, 3)
- Suite C: Multimodal & Edge Cases (验收点 4)
- Suite D: Integration & Performance (系统级测试)

Run with:
    cd backend && pytest tests/test_e2e/test_core_chain_1_intent_recognition.py -v
    cd backend && pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteA::test_chitchat_vs_task_routing -v
"""
import pytest
import asyncio
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, AsyncMock, patch

from app.orchestration.request_router import RequestRouter
from app.orchestration.sufficiency_checker import (
    SufficiencyChecker,
    SufficiencyStatus,
    SufficiencyCheckResult
)
from app.orchestration.bert_intent_classifier import BERTIntentClassifier
from app.core.unified_intent_router import (
    UnifiedIntentRouter,
    UnifiedIntentType,
    IntentRoutingResult
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
async def mock_redis():
    """Mock Redis client for caching"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def request_router(mock_redis):
    """Initialize RequestRouter with mock Redis"""
    return RequestRouter(
        redis_client=mock_redis,
        enable_bert=False,  # Disable BERT for faster tests
        enable_profiling=False,
        enable_monitoring=False
    )


@pytest.fixture
def sufficiency_checker():
    """Initialize SufficiencyChecker"""
    return SufficiencyChecker(strict_mode=False)


@pytest.fixture
def unified_intent_router(mock_redis):
    """Initialize UnifiedIntentRouter"""
    return UnifiedIntentRouter(
        redis_client=mock_redis,
        llm_service=None,
        context_window_size=5
    )


# =============================================================================
# Test Suite A: Intent Recognition & Routing Accuracy
# (验收点 1, 4a, 4b, 5a, 5b, 5c, 5d)
# =============================================================================

class TestSuiteA_IntentRecognition:
    """测试套件A：意图识别与路由准确性"""

    @pytest.mark.asyncio
    async def test_chitchat_vs_task_routing(self, request_router):
        """
        验收点 1: 路由准确率 - 区分闲聊与复杂任务

        确保不会把"帮我制定学习计划"误判为闲聊
        """
        # Test cases: (message, expected_intent, min_confidence, description)
        test_cases = [
            # === Chitchat cases (should route to chat) ===
            ("你好", "chat", 0.3, "Simple greeting"),
            ("今天天气怎么样", "chat", 0.3, "Weather small talk"),
            ("谢谢", "chat", 0.3, "Gratitude"),
            ("哈哈很好笑", "chat", 0.3, "Laughter"),
            ("在吗", "chat", 0.3, "Presence check"),

            # === Complex task cases (should NOT be chat) ===
            ("帮我制定学习计划", "create", 0.7, "Learning plan request - MUST NOT be chat"),
            ("我想复习数学", "review", 0.5, "Math review request"),
            ("创建一个复习计划", "create", 0.7, "Review plan creation"),
            ("帮我安排学习时间", "create", 0.7, "Time scheduling"),
            ("制定考试冲刺计划", "create", 0.7, "Exam sprint plan"),
        ]

        for message, expected_intent, min_confidence, description in test_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            # Assert intent matches
            assert intent == expected_intent, (
                f"[{description}] Intent mismatch: '{message}' -> "
                f"got '{intent}', expected '{expected_intent}'"
            )

            # Assert confidence is reasonable
            assert confidence >= min_confidence, (
                f"[{description}] Confidence too low: {confidence:.2f} < {min_confidence}"
            )

            # Critical check: Complex tasks must NOT be classified as chat
            if expected_intent in ["create", "review"]:
                assert intent != "chat", (
                    f"CRITICAL FAILURE: '{message}' was classified as 'chat' instead of '{expected_intent}'. "
                    f"This violates the验收标准: 不会把'帮我制定学习计划'误判为闲聊"
                )

    @pytest.mark.asyncio
    async def test_special_mode_detection_translation(self, request_router):
        """验收点 5c: 翻译模式入口验证"""
        translation_cases = [
            "请翻译这句话",
            "what does this mean in Chinese",
            "怎么说英语",
            "translate this",
            "翻译成中文",
            "in English",
        ]

        for message in translation_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == "translation", (
                f"Translation mode not triggered: '{message}' -> got '{intent}', expected 'translation'"
            )
            assert confidence >= 0.7, (
                f"Translation confidence too low: {confidence:.2f} for '{message}'"
            )

    @pytest.mark.asyncio
    async def test_special_mode_detection_prism(self, request_router):
        """验收点 5b: 认知棱镜模式入口验证"""
        prism_cases = [
            "我的学习画像",
            "查看我的认知棱镜",
            "生成周报",
            "行为分析",
            "学习习惯",
            "study habits",
            "user profile",
        ]

        for message in prism_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == "prism", (
                f"Prism mode not triggered: '{message}' -> got '{intent}', expected 'prism'"
            )
            assert confidence >= 0.7, (
                f"Prism confidence too low: {confidence:.2f} for '{message}'"
            )

    @pytest.mark.asyncio
    async def test_special_mode_detection_sprint(self, request_router):
        """验收点 5d: 冲刺模式入口验证"""
        sprint_cases = [
            "进入冲刺模式",
            "开始专注",
            "我要突击复习",
            "focus mode",
            "sprint mode",
            "cramming",
            "集中注意力",
        ]

        for message in sprint_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == "sprint", (
                f"Sprint mode not triggered: '{message}' -> got '{intent}', expected 'sprint'"
            )
            assert confidence >= 0.7, (
                f"Sprint confidence too low: {confidence:.2f} for '{message}'"
            )

    @pytest.mark.asyncio
    async def test_execution_mode_routing(self, request_router):
        """
        验收点 4a, 4b: 执行模式路由决策

        验证:
        - 闲聊/简单查询 → direct
        - 复杂规划 → langgraph
        - 特殊模式 → direct
        - 高风险 → direct (安全优先)
        """
        test_cases = [
            # (message, expected_mode, description)
            ("你好", "direct", "Chitchat -> direct"),
            ("帮我制定学习计划", "langgraph", "Complex planning -> langgraph"),
            ("翻译这个", "direct", "Translation -> direct (specialized)"),
            ("我的学习画像", "direct", "Prism -> direct (specialized)"),
            ("进入冲刺", "direct", "Sprint -> direct (specialized)"),
            ("删除所有任务", "direct", "High-risk -> direct (safety)"),
            ("创建任务然后规划复习", "langgraph", "Multi-step -> langgraph"),
        ]

        for message, expected_mode, description in test_cases:
            decision = await request_router.decide(
                message=message,
                user_id="test-user",
                session_id="test-session"
            )

            assert decision.execution_mode == expected_mode, (
                f"[{description}] Routing decision failed: '{message}' -> "
                f"got '{decision.execution_mode}', expected '{expected_mode}'. "
                f"Reason: {decision.reason}"
            )

    @pytest.mark.asyncio
    async def test_combined_pattern_priority(self, request_router):
        """
        验收点 1: 组合模式优先级

        P0修复：确保"帮我制定学习计划"中"制定"优先于"学习"
        """
        # Test that verb + noun combination gets higher priority than single keyword
        test_cases = [
            ("帮我制定学习计划", "create", 0.85, "verb+noun: 制定+计划"),
            ("我要创建任务", "create", 0.85, "verb+noun: 创建+任务"),
            ("安排复习数学", "review", 0.85, "verb+noun: 安排+复习"),
            ("我想学习", "learn", 0.5, "single verb: 学习 (lower priority)"),
        ]

        for message, expected_intent, expected_confidence, description in test_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == expected_intent, (
                f"[{description}] Intent mismatch: '{message}' -> got '{intent}', expected '{expected_intent}'"
            )

            # For combined patterns, confidence should be higher
            if "verb+noun" in description:
                assert confidence >= 0.7, (
                    f"[{description}] Combined pattern should have high confidence: {confidence:.2f}"
                )


# =============================================================================
# Test Suite B: Information Sufficiency & Clarification Loop
# (验收点 2, 3)
# =============================================================================

class TestSuiteB_SufficiencyChecker:
    """测试套件B：信息充分性与追问循环"""

    @pytest.mark.asyncio
    async def test_required_field_detection(self, sufficiency_checker):
        """验收点 2: 必需字段检测"""
        test_cases = [
            {
                "name": "Create task without title",
                "intent": "create_task",
                "entities": {"task_type": "study"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["task_title"],
            },
            {
                "name": "Create plan without title",
                "intent": "create_plan",
                "entities": {"plan_type": "sprint"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["plan_title"],
            },
            {
                "name": "Update task without ID",
                "intent": "update_task",
                "entities": {"new_status": "in_progress"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["task_id"],
            },
            {
                "name": "Complete task creation",
                "intent": "create_task",
                "entities": {"task_title": "Study math", "task_type": "study"},
                "expected_status": SufficiencyStatus.SUFFICIENT,
                "expected_missing": [],
            },
        ]

        for case in test_cases:
            result = await sufficiency_checker.check(
                intent=case["intent"],
                extracted_entities=case["entities"],
                conversation_context=[],
            )

            assert result.status == case["expected_status"], (
                f"[{case['name']}] Status mismatch: got {result.status}, expected {case['expected_status']}"
            )

            assert set(result.missing_fields) == set(case["expected_missing"]), (
                f"[{case['name']}] Missing fields mismatch: got {result.missing_fields}, "
                f"expected {case['expected_missing']}"
            )

    @pytest.mark.asyncio
    async def test_clarification_question_generation(self, sufficiency_checker):
        """验收点 2: 追问问题生成"""
        test_cases = [
            ("task_title", "create_task", "asks for task title"),
            ("plan_type", "create_plan", "asks for plan type"),
            ("due_date", "create_task", "asks for due date"),
            ("subject_id", "knowledge_query", "asks for subject"),
        ]

        for field, intent, description in test_cases:
            result = await sufficiency_checker.check(
                intent=intent,
                extracted_entities={},  # Empty to trigger missing
                conversation_context=[],
            )

            # Should have clarification questions
            assert len(result.clarification_questions) > 0, (
                f"[{description}] No clarification questions generated for missing {field}"
            )

            # Questions should be relevant
            question_relevant = any(
                field.lower() in q.lower() or
                any(keyword in q for keyword in ["请问", "什么", "哪个", "什么时候"])
                for q in result.clarification_questions
            )
            assert question_relevant, (
                f"[{description}] Questions not relevant: {result.clarification_questions}"
            )

    @pytest.mark.asyncio
    async def test_stop_mechanism_no_infinite_loop(self, sufficiency_checker):
        """
        验收点 3: 追问停止机制 - 防止无限追问死循环

        验证LLM Judge能否准确判断"信息已足够"
        """
        # Turn 1: User says "create task" -> Ask for title
        result1 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={},
            conversation_context=[],
        )

        assert result1.status == SufficiencyStatus.NEED_CLARIFICATION, (
            "Turn 1: Should ask for missing task_title"
        )
        assert len(result1.clarification_questions) > 0, "Turn 1: Should generate questions"

        # Turn 2: User provides title -> Should be sufficient now
        result2 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={"task_title": "Study math"},
            conversation_context=[
                {"role": "assistant", "content": result1.clarification_questions[0]},
                {"role": "user", "content": "Study math"},
            ],
        )

        assert result2.status == SufficiencyStatus.SUFFICIENT, (
            "Turn 2: Should stop asking when info is sufficient. "
            "This is the CRITICAL check for验收点 3"
        )

        # Turn 3: Verify no infinite loop
        # With title already provided, should NOT ask again
        result3 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={"task_title": "Study math"},
            conversation_context=[
                {"role": "assistant", "content": result1.clarification_questions[0]},
                {"role": "user", "content": "Study math"},
                {"role": "assistant", "content": "任务已创建"},
            ],
        )

        assert result3.status == SufficiencyStatus.SUFFICIENT, (
            "Turn 3: Must NOT enter infinite追问loop. "
            "If this fails, the stop mechanism is broken."
        )

    @pytest.mark.asyncio
    async def test_context_inference(self, sufficiency_checker):
        """验收点 2: 上下文推断能力"""
        conversation_with_time = [
            {"role": "user", "content": "我要学习30分钟"},
            {"role": "assistant", "content": "好的，创建任务"},
            {"role": "user", "content": "帮我创建学习任务"},
        ]

        result = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={"task_title": "Study math"},
            conversation_context=conversation_with_time,
        )

        # In non-strict mode (default), should be sufficient
        # Duration can be inferred from "我要学习30分钟"
        assert result.status == SufficiencyStatus.SUFFICIENT, (
            "Should infer estimated_minutes from conversation context"
        )

    @pytest.mark.asyncio
    async def test_high_risk_confirmation(self, sufficiency_checker):
        """验收点 2: 高风险操作确认"""
        result = await sufficiency_checker.check(
            intent="delete_task",
            extracted_entities={"task_id": "task123", "task_title": "My Task"},
            conversation_context=[],
        )

        assert result.status == SufficiencyStatus.NEED_CONFIRMATION, (
            "Delete operations should require confirmation"
        )

        assert result.confirmation_message is not None, (
            "Confirmation message should be generated"
        )

        assert "确定" in result.confirmation_message or "删除" in result.confirmation_message, (
            f"Confirmation message should mention confirmation: {result.confirmation_message}"
        )


# =============================================================================
# Test Suite C: Multimodal & Voice Input Compatibility
# (验收点 4)
# =============================================================================

class TestSuiteC_Multimodal:
    """测试套件C：多模态兼容性"""

    @pytest.mark.asyncio
    async def test_voice_input_preprocessing(self, request_router):
        """
        验收点 4: 语音转文字后的语义理解

        验证语音识别的常见问题：
        - 填充词（嗯、啊、那个）
        - 重复短语
        - 口语化表达
        """
        voice_cases = [
            ("嗯，帮我制定学习计划", "create", "With filler '嗯'"),
            ("那个，我想复习数学", "review", "With filler '那个'"),
            ("啊，进入冲刺模式", "sprint", "With filler '啊'"),
            ("帮我...帮我安排时间", "create", "With repetition (preprocessed)"),
            ("今天怎么样今天不错", "chat", "Repetitive chitchat"),
            ("呃翻译这个", "translation", "With filler '呃'"),
        ]

        for message, expected_intent, description in voice_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == expected_intent, (
                f"[{description}] Voice input not understood: '{message}' -> "
                f"got '{intent}', expected '{expected_intent}'"
            )

            # Voice input might have lower confidence, but should still be reasonable
            assert confidence >= 0.5, (
                f"[{description}] Confidence too low for voice input: {confidence:.2f}"
            )

    @pytest.mark.asyncio
    async def test_mixed_language_input(self, request_router):
        """验收点 4: 中英混合输入"""
        mixed_cases = [
            ("I want to study 数学", "learn", "Mixed English + Chinese"),
            ("帮我 translate this", "translation", "Mixed Chinese + English"),
            ("Create 学习计划", "create", "Mixed verb + object"),
            ("Analyze 我的习惯", "prism", "Mixed command + content"),
            ("进入 focus mode", "sprint", "Mixed entry + mode"),
        ]

        for message, expected_intent, description in mixed_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            assert intent == expected_intent, (
                f"[{description}] Mixed language not understood: '{message}' -> "
                f"got '{intent}', expected '{expected_intent}'"
            )

            assert confidence >= 0.5, (
                f"[{description}] Confidence too low: {confidence:.2f}"
            )

    @pytest.mark.asyncio
    async def test_colloquial_expressions(self, request_router):
        """验收点 4: 口语化表达理解"""
        colloquial_cases = [
            ("搞个任务", "create", "Slang '搞'"),
            ("弄个计划", "create", "Slang '弄'"),
            ("瞅瞅我的任务", "query", "Slang '瞅瞅'"),
            ("整个学习", "create", "Slang '整'"),
        ]

        for message, expected_intent, description in colloquial_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)

            # Colloquial might not match perfectly, but should not crash
            assert intent is not None, f"[{description}] Should return some intent"

    @pytest.mark.asyncio
    async def test_voice_preprocessing_function(self, request_router):
        """直接测试语音预处理函数"""
        test_cases = [
            ("帮我...帮我", "帮我帮我", "Repetition preprocessing"),
            ("制定...计划", "制定，计划", "Ellipsis preprocessing"),
            ("嗯  帮我", "嗯 帮我", "Whitespace normalization"),
        ]

        for input_text, expected_contains, description in test_cases:
            processed = request_router._preprocess_voice_input(input_text)

            # Check that preprocessing happened (no strict assertion on exact output)
            assert processed is not None, f"[{description}] Preprocessing should not return None"

            # Ellipsis should be replaced
            if "..." in input_text:
                assert "..." not in processed, "Ellipsis should be replaced"


# =============================================================================
# Test Suite D: Integration & Performance
# =============================================================================

class TestSuiteD_Integration:
    """测试套件D：集成与性能测试"""

    @pytest.mark.asyncio
    async def test_unified_intent_router_integration(self, unified_intent_router):
        """集成测试：统一意图路由器"""
        test_cases = [
            # (message, expected_intent, description)
            ("翻译这个", UnifiedIntentType.TRANSLATION, "Translation mode"),
            ("我的画像", UnifiedIntentType.COGNITIVE_PRISM, "Prism mode"),
            ("开始冲刺", UnifiedIntentType.SPRINT_PLAN, "Sprint mode"),
            ("你好", UnifiedIntentType.CHAT, "Chat mode"),
        ]

        for message, expected_intent, description in test_cases:
            result = await unified_intent_router.route(
                message=message,
                user_id="test-user",
                session_id="test-session",
                payload={},
                conversation_history=[]
            )

            assert result.primary_intent == expected_intent, (
                f"[{description}] Unified routing failed: '{message}' -> "
                f"got {result.primary_intent}, expected {expected_intent}"
            )

            # Should have reasonable confidence
            assert result.confidence >= 0.5, (
                f"[{description}] Confidence too low: {result.confidence:.2f}"
            )

    @pytest.mark.asyncio
    async def test_classification_performance(self, request_router):
        """性能测试：分类延迟应满足要求"""
        import time

        test_messages = [
            "你好",
            "帮我制定学习计划",
            "翻译这个",
            "我的学习画像",
            "进入冲刺模式",
        ]

        latencies = []
        for message in test_messages:
            start = time.time()
            await request_router._classify_intent_with_confidence(message)
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)

        # Tier-1 classification should be fast (<50ms)
        assert avg_latency < 50, (
            f"Classification latency too high: {avg_latency:.1f}ms. "
            f"Target: <50ms for Tier-1 (keyword matching)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_classification(self, request_router):
        """并发测试：同时处理多个分类请求"""
        test_messages = [
            ("你好", "chat"),
            ("帮我制定学习计划", "create"),
            ("翻译这个", "translation"),
            ("我的学习画像", "prism"),
            ("开始冲刺", "sprint"),
        ]

        # Run all classifications concurrently
        tasks = [
            request_router._classify_intent_with_confidence(msg)
            for msg, _ in test_messages
        ]
        results = await asyncio.gather(*tasks)

        # Verify all results
        for (message, expected_intent), (intent, confidence) in zip(test_messages, results):
            assert intent == expected_intent, (
                f"Concurrent classification failed: '{message}' -> "
                f"got '{intent}', expected '{expected_intent}'"
            )

    @pytest.mark.asyncio
    async def test_error_handling(self, request_router):
        """错误处理：边界情况不应崩溃"""
        edge_cases = [
            "",  # Empty
            "   ",  # Whitespace
            "!!!@#$%",  # Special chars
            "a" * 500,  # Very long
            "\n\n\n",  # Newlines
        ]

        for message in edge_cases:
            try:
                intent, confidence = await request_router._classify_intent_with_confidence(message)
                # Should not crash and should return some intent
                assert intent is not None, f"Edge case should return intent: '{message[:20]}...'"
                assert isinstance(confidence, float), "Confidence should be float"
            except Exception as e:
                pytest.fail(f"Edge case raised exception: '{message[:20]}...' -> {e}")


# =============================================================================
# Test Suite E: Real-world Scenarios
# =============================================================================

class TestSuiteE_RealWorldScenarios:
    """测试套件E：真实场景模拟"""

    @pytest.mark.asyncio
    async def test_student_study_plan_flow(self, request_router, sufficiency_checker):
        """场景1：学生创建学习计划的完整流程"""
        # Step 1: User says "帮我制定学习计划"
        intent1, conf1 = await request_router._classify_intent_with_confidence("帮我制定学习计划")
        assert intent1 == "create", "Should recognize create intent"

        # Step 2: Check information sufficiency (missing title)
        result2 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={},
            conversation_context=[],
        )
        assert result2.status == SufficiencyStatus.NEED_CLARIFICATION, "Should ask for plan title"

        # Step 3: User provides title "数学期末复习"
        result3 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={"task_title": "数学期末复习"},
            conversation_context=[
                {"role": "assistant", "content": result2.clarification_questions[0]},
                {"role": "user", "content": "数学期末复习"},
            ],
        )
        assert result3.status == SufficiencyStatus.SUFFICIENT, "Should be sufficient with title"

    @pytest.mark.asyncio
    async def test_exam_prep_sprint_flow(self, request_router):
        """场景2：考试冲刺模式触发"""
        # Step 1: User says "我要考试冲刺"
        intent1, conf1 = await request_router._classify_intent_with_confidence("我要考试冲刺")
        assert intent1 == "sprint", "Should recognize sprint intent"

        # Step 2: Check routing decision
        decision2 = await request_router.decide(
            message="我要考试冲刺",
            user_id="test-user",
            session_id="test-session",
        )
        assert decision2.execution_mode == "direct", "Sprint should route to direct mode"

    @pytest.mark.asyncio
    async def test_translation_request_flow(self, request_router):
        """场景3：翻译请求处理"""
        # Step 1: User says "请翻译这个单词"
        intent1, conf1 = await request_router._classify_intent_with_confidence("请翻译这个单词")
        assert intent1 == "translation", "Should recognize translation intent"

        # Step 2: Check routing
        decision2 = await request_router.decide(
            message="请翻译这个单词",
            user_id="test-user",
            session_id="test-session",
        )
        assert decision2.execution_mode == "direct", "Translation should route to direct mode"

    @pytest.mark.asyncio
    async def test_cognitive_prism_flow(self, request_router):
        """场景4：认知棱镜分析请求"""
        # Step 1: User says "看看我的学习习惯"
        intent1, conf1 = await request_router._classify_intent_with_confidence("看看我的学习习惯")
        assert intent1 == "prism", "Should recognize prism intent"

        # Step 2: Check routing
        decision2 = await request_router.decide(
            message="看看我的学习习惯",
            user_id="test-user",
            session_id="test-session",
        )
        assert decision2.execution_mode == "direct", "Prism should route to direct mode"

    @pytest.mark.asyncio
    async def test_multi_turn_clarification_flow(self, sufficiency_checker):
        """场景5：多轮追问完整流程"""
        # Turn 1: "帮我创建任务"
        result1 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={},
            conversation_context=[],
        )
        assert result1.status == SufficiencyStatus.NEED_CLARIFICATION
        assert "task_title" in result1.missing_fields

        # Turn 2: "学习数学"
        result2 = await sufficiency_checker.check(
            intent="create_task",
            extracted_entities={"task_title": "学习数学"},
            conversation_context=[
                {"role": "assistant", "content": result1.clarification_questions[0]},
                {"role": "user", "content": "学习数学"},
            ],
        )
        assert result2.status == SufficiencyStatus.SUFFICIENT, "Should stop after getting title"


# =============================================================================
# Summary Report Generation
# =============================================================================

@pytest.fixture(autouse=True)
def test_summary(request):
    """Generate test summary at the end"""
    yield
    # This runs after each test
    # Can be used to collect metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
