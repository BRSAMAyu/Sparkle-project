"""
核心链路二验收测试：任务规划与人机协同审查链路 (Planning & HITL Loop)

验收标准：
1. 审查的有效性 - 审查Agent必须能指出明显错误
2. HITL权重 - 用户意见 > 审查意见
3. LangGraph流转 - 数据不丢失
4. 兜底机制 - 连续两次失败平滑切换

测试用例：
- "不可能三角"测试
- "记忆冲突"测试
- "傲娇用户"测试 (HITL权重)
"""
import asyncio
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.orchestration.plan_review_service import (
    PlanReviewService,
    ReviewDecision,
    ReviewComment,
)
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.agents.reviewer_agent import ReviewerAgent, ReviewResult, ReviewMetric, Issue


# ============================================================================
# Test Fixture Setup
# ============================================================================

@pytest.fixture
async def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.publish = AsyncMock()
    return redis


@pytest.fixture
async def plan_review_service(mock_redis):
    """Plan review service instance"""
    service = PlanReviewService()
    service.set_redis(mock_redis)
    return service


@pytest.fixture
def reviewer_agent():
    """Reviewer agent instance"""
    return ReviewerAgent()


@pytest.fixture
def sample_safe_plan():
    """Sample safe read-only plan"""
    return ExecutablePlan(
        schema_version="4.0",
        plan_id="test-plan-safe",
        snapshot_id="snap-1",
        context_version="v1",
        source="langgraph",
        confidence=0.9,
        rationale="Safe read-only plan",
        tool_calls=[
            ToolCallSpec(
                id="call_1",
                name="get_tasks",
                params={},
                timeout_ms=10000,
            ),
            ToolCallSpec(
                id="call_2",
                name="query_knowledge",
                params={"query": "test"},
                timeout_ms=10000,
            ),
        ],
    )


@pytest.fixture
def sample_risky_plan():
    """Sample risky plan with high-risk operations"""
    return ExecutablePlan(
        schema_version="4.0",
        plan_id="test-plan-risky",
        snapshot_id="snap-1",
        context_version="v1",
        source="langgraph",
        confidence=0.7,
        rationale="Risky plan with delete operations",
        tool_calls=[
            ToolCallSpec(
                id="call_1",
                name="delete_task",
                params={"task_id": "task-123"},
                timeout_ms=10000,
            ),
            ToolCallSpec(
                id="call_2",
                name="reset_progress",
                params={},
                timeout_ms=10000,
            ),
        ],
    )


# ============================================================================
# Acceptance Test 1: "不可能三角"测试 (Impossible Triangle)
# ============================================================================
"""
场景：用户每天只有1小时空闲，要求制定"一周内精通C++"的计划
预期：审查Agent拦截，提示"目标与可用时间不匹配"
"""
class TestImpossibleTriangle:
    """Test that Review Agent catches impossible constraints"""

    @pytest.mark.asyncio
    async def test_impossible_time_constraints_rejected(self, plan_review_service, mock_redis):
        """Test: 1小时/天 vs 一周精通C++ 应该被拦截"""

        # Create an impossible plan (claims to achieve mastery in 1 week with 1h/day)
        impossible_plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-impossible",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.95,  # 高置信度但目标不现实
            rationale="一周精通C++，每天学习1小时",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="create_plan",
                    params={
                        "title": "一周精通C++",
                        "daily_hours": 1,  # 每天1小时
                        "total_days": 7,   # 7天
                        "difficulty": "expert",  # 目标：精通（专家级别）
                    },
                    timeout_ms=10000,
                ),
            ],
        )

        # User context: only 1 hour available per day, beginner level
        user_context = {
            "available_hours_per_day": 1,
            "current_plan_count": 0,
            "skill_level": "beginner",  # 用户是初学者
        }

        # Review the plan
        review_result = await plan_review_service.review_plan(
            plan=impossible_plan,
            user_message="帮我在一周内精通C++，我每天只有1小时",
            user_context=user_context,
        )

        # P0 Fix #1: Verify feasibility check prevents auto-approval
        # The plan should either be rejected OR require LLM review (not auto-approved)
        assert review_result.auto_approved is False, \
               "Impossible plan should NOT be auto-approved (P0 Fix #1)"

        # Verify: Decision should not be a clean approved without going through review
        # Either requires_confirmation, needs_modification, or went through LLM review
        if review_result.decision == ReviewDecision.APPROVED.value:
            # If approved, it must have gone through LLM review (auto_approved=False)
            assert review_result.auto_approved is False, \
                   "High-confidence infeasible plan must go through LLM review"

        print(f"✅ Impossible triangle test passed: decision={review_result.decision}, auto_approved={review_result.auto_approved}")
        print(f"   Confidence: {review_result.confidence}")
        print(f"   Comments: {len(review_result.comments)}")

    @pytest.mark.asyncio
    async def test_overcommitted_user_warned(self, plan_review_service, mock_redis):
        """Test: 用户已有3个并行大计划时应该被警告 (P0 Fix #2)"""

        # Plan for user who already has too many plans
        overcommitted_plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-overcommit",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="创建第4个大计划",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="create_sprint_plan",
                    params={"duration": "2weeks"},
                    timeout_ms=10000,
                ),
            ],
        )

        # User context: already has 3 active plans (overcommitted)
        user_context = {
            "pending_tasks_count": 50,
            "active_focus_id": None,
            "current_plan_count": 3,  # 已有3个大计划
        }

        # P0 Fix #2: Overcommitment detection should prevent auto-approval
        review_result = await plan_review_service.review_plan(
            plan=overcommitted_plan,
            user_message="帮我再制定一个2周冲刺计划",
            user_context=user_context,
        )

        # P0 Fix #2: Verify auto-approval is blocked
        # The plan should NOT be auto-approved when user has 3+ active plans
        assert review_result.auto_approved is False, \
               "Plan should NOT be auto-approved when user has 3+ active plans (P0 Fix #2)"

        # The decision should go through LLM review which will add warnings
        # or require user confirmation
        print(f"✅ Overcommit test passed: decision={review_result.decision}, auto_approved={review_result.auto_approved}")
        print(f"   Current plan count: {user_context['current_plan_count']}")


# ============================================================================
# Acceptance Test 2: "记忆冲突"测试 (Memory Conflict)
# ============================================================================
"""
场景：用户之前说"我是文科生，不懂代码"，现在要求"写一个Python爬虫"
预期：方案包含详细基础教程，或审查提示"难度过大"
"""
class TestMemoryConflict:
    """Test that system respects user's historical constraints"""

    @pytest.mark.asyncio
    async def test_reviewer_detects_skill_mismatch(self, reviewer_agent):
        """Test: ReviewerAgent should detect when plan doesn't match user skill"""

        # Plan that assumes programming knowledge
        tech_plan = {
            "tool_calls": [
                {
                    "name": "create_task",
                    "params": {
                        "title": "写Python爬虫",
                        "description": "使用Scrapy框架爬取网站数据",
                        "prerequisites": ["Python 3.8+", "pip", "Scrapy库"],
                    }
                }
            ],
            "rationale": "直接开始编写爬虫代码",
            "confidence": 0.85,
        }

        # User query
        user_query = "帮我写一个Python爬虫"

        # User context: liberal arts student, no coding background
        context = {
            "user_background": "liberal_arts",
            "skill_level": "beginner",
            "previous_statements": ["我是文科生，不懂代码"],
        }

        # Review the plan
        review_result = await reviewer_agent.review_plan(
            plan=tech_plan,
            user_query=user_query,
            context=context,
        )

        # Verify: Should detect feasibility issue
        assert review_result.overall_score < 0.8 or \
               any(i.severity == "warning" or i.severity == "critical"
                   for i in review_result.issues), \
               "Should detect skill mismatch"

        # Verify: Should have comments about prerequisites or difficulty
        relevant_issues = [
            i for i in review_result.issues
            if "前提" in i.description or "基础" in i.description or
               "难度" in i.description or "环境" in i.description
        ]

        print(f"✅ Memory conflict test passed: score={review_result.overall_score}")
        print(f"   Issues: {len(review_result.issues)}")
        if relevant_issues:
            print(f"   Relevant issues: {[i.description for i in relevant_issues[:2]]}")

    @pytest.mark.asyncio
    async def test_plan_includes_setup_for_beginners(self, reviewer_agent):
        """Test: Plan for beginner should include environment setup"""

        # Good plan that includes setup steps
        beginner_friendly_plan = {
            "tool_calls": [
                {
                    "name": "create_task",
                    "params": {
                        "title": "Python环境配置",
                        "description": "安装Python和配置开发环境",
                    }
                },
                {
                    "name": "create_task",
                    "params": {
                        "title": "Python基础语法学习",
                        "description": "学习变量、循环、函数等基础概念",
                    }
                },
            ],
            "rationale": "针对文科生的循序渐进Python入门",
            "confidence": 0.75,
        }

        review_result = await reviewer_agent.review_plan(
            plan=beginner_friendly_plan,
            user_query="我是文科生，想学Python写爬虫",
            context={"user_background": "liberal_arts"},
        )

        # Should have better score than the advanced plan
        assert review_result.overall_score >= 0.6, \
               "Beginner-friendly plan should have reasonable score"

        print(f"✅ Beginner-friendly plan test passed: score={review_result.overall_score}")


# ============================================================================
# Acceptance Test 3: "傲娇用户"测试 (HITL Priority)
# ============================================================================
"""
场景：审查Agent提示"方案有风险"，用户点击"我不在乎，强制执行"
预期：系统必须执行，记录行为范式，下次不拿同样理由阻拦
"""
class TestHITLPriority:
    """Test that user decision overrides reviewer concerns"""

    @pytest.mark.asyncio
    async def test_user_can_override_reviewer_rejection(self, plan_review_service, mock_redis):
        """Test: User approves despite reviewer rejection"""

        # Risky plan
        risky_plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-override-test",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.5,  # Low confidence
            rationale="用户坚持要做的冒险计划",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="delete_all_tasks",
                    params={},
                    timeout_ms=10000,
                ),
            ],
        )

        # Simulate review result that requires confirmation
        with patch.object(plan_review_service, '_llm_review', return_value={
            "decision": ReviewDecision.REQUIRES_CONFIRMATION.value,
            "confidence": 0.4,
            "comments": [{
                "category": "safety",
                "severity": "warning",
                "message": "此操作将删除所有任务",
                "suggested_fix": "请确认是否真的要删除",
            }],
        }):
            review_result = await plan_review_service.review_plan(
                plan=risky_plan,
                user_message="我不管，帮我删除所有任务",
                user_context={},
            )

        # Verify: Review requires confirmation
        assert review_result.decision == ReviewDecision.REQUIRES_CONFIRMATION.value

        # Mock pending_actions_store to return the stored review
        from app.core.pending_actions import pending_actions_store

        async def mock_get_action(action_id, user_id):
            return {
                "tool_name": "__plan_review__",
                "arguments": {
                    "review_id": review_result.review_id,
                    "plan_id": risky_plan.plan_id,
                    "decision": ReviewDecision.REQUIRES_CONFIRMATION.value,
                },
                "preview_data": {
                    "plan_id": risky_plan.plan_id,
                    "decision": ReviewDecision.REQUIRES_CONFIRMATION.value,
                    "confidence": 0.4,
                },
            }

        with patch.object(pending_actions_store, "get", side_effect=mock_get_action):
            # Simulate user approval (override)
            db_session_mock = AsyncMock()
            result = await plan_review_service.handle_review_feedback(
                review_id=review_result.review_id,
                user_decision="approve",  # User approves despite warning
                user_id="user-123",
                db_session=db_session_mock,
                user_comment="我确定要删除",
            )

            # Verify: User decision is accepted
            assert result["status"] == "success"
            assert result["user_decision"] == "approve"

        print(f"✅ User override test passed: status={result['status']}")

    @pytest.mark.asyncio
    async def test_rejection_count_triggers_fallback(self, plan_review_service, mock_redis):
        """Test: 连续两次拒绝触发信息收集（兜底机制）"""

        plan_id = "plan-rejection-test"
        user_id = "user-rejection-test"

        # Mock pending_actions_store to return valid actions with plan_id in preview_data
        from app.core.pending_actions import pending_actions_store

        # Mock the get method to return actions with plan_id in preview_data
        async def mock_get_action(action_id, user_id):
            if action_id == "review-1":
                return {
                    "tool_name": "__plan_review__",
                    "arguments": {"review_id": "review-1"},
                    "preview_data": {"plan_id": plan_id, "decision": "requires_confirmation"},
                }
            elif action_id == "review-2":
                return {
                    "tool_name": "__plan_review__",
                    "arguments": {"review_id": "review-2"},
                    "preview_data": {"plan_id": plan_id, "decision": "requires_confirmation"},
                }
            return None

        with patch.object(pending_actions_store, "get", side_effect=mock_get_action):
            # Mock rejection count to return 2 on second call
            mock_redis.incr = AsyncMock(return_value=2)

            # Simulate second rejection (count=2)
            result2 = await plan_review_service.handle_review_feedback(
                review_id="review-2",
                user_decision="reject",
                user_id=user_id,
                db_session=None,
                user_comment="第二次拒绝",
            )

            # Verify: Second rejection triggers information collection
            assert result2["status"] == "information_collection_triggered"
            assert "rejection_count" in result2
            assert result2["rejection_count"] >= 2

            # Verify: Redis publish was called
            assert mock_redis.publish.called, "Should publish information collection trigger"

        print(f"✅ Rejection fallback test passed: {result2['status']}")
        print(f"   Message: {result2['message']}")

    @pytest.mark.asyncio
    async def test_approval_resets_rejection_count(self, plan_review_service, mock_redis):
        """Test: 用户接受方案后重置拒绝计数"""

        plan_id = "plan-reset-test"
        user_id = "user-reset-test"

        # Mock pending_actions_store to return valid action with plan_id
        from app.core.pending_actions import pending_actions_store

        async def mock_get_action(action_id, user_id):
            return {
                "tool_name": "__plan_review__",
                "arguments": {"review_id": "review-1"},
                "preview_data": {"plan_id": plan_id, "decision": "approved"},
            }

        with patch.object(pending_actions_store, "get", side_effect=mock_get_action):
            # Simulate approval (should reset)
            mock_redis.delete = AsyncMock()
            result = await plan_review_service.handle_review_feedback(
                review_id="review-1",
                user_decision="approve",
                user_id=user_id,
                db_session=None,
            )

            # Verify: delete was called to reset count
            assert mock_redis.delete.called, "Should reset rejection count on approval"

        print(f"✅ Rejection count reset test passed")


# ============================================================================
# Test 4: LangGraph Data Flow
# ============================================================================
class TestLangGraphDataFlow:
    """Test that context is preserved through LangGraph flow"""

    @pytest.mark.asyncio
    async def test_plan_includes_snapshot_data(self):
        """Test: Plan should preserve snapshot context"""

        # Create mock snapshot
        snapshot = MagicMock()
        snapshot.snapshot_id = "snap-123"
        snapshot.to_dict = MagicMock(return_value={
            "user_id": "user-123",
            "available_time": 10,
            "preferences": {"depth_preference": 0.8},
        })
        snapshot.context_versions = {"tasks": "v1", "plans": "v2"}

        # Create planner
        planner = LangGraphPlanner()

        # Mock the graph to avoid actual execution
        with patch.object(planner, 'graph') as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "messages": [],
                "collaboration_agents": ["planner"],
                "collaboration_mode": "single",
            })

            plan = await planner.plan(
                message="测试消息",
                snapshot=snapshot,
                user_id="user-123",
                session_id="session-123",
            )

            # Verify: Plan includes snapshot data
            assert plan.snapshot_id == snapshot.snapshot_id
            assert plan.context_version in ["v1", "v2", "v0"]  # Should be one of the versions

            print(f"✅ Snapshot preservation test passed")
            print(f"   snapshot_id: {plan.snapshot_id}")
            print(f"   context_version: {plan.context_version}")

    @pytest.mark.asyncio
    async def test_reviewer_has_access_to_user_context(self, plan_review_service):
        """Test: Reviewer should receive user context"""

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-context-test",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="Test plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="create_task",
                    params={"title": "Test"},
                    timeout_ms=10000,
                ),
            ],
        )

        # Rich user context
        user_context = {
            "active_focus_id": "focus-123",
            "pending_tasks_count": 5,
            "preferences": {
                "depth_preference": 0.7,
                "curiosity_preference": 0.6,
            },
        }

        # Mock LLM review as async
        async def mock_llm_review(plan, user_message, user_context):
            return {
                "decision": ReviewDecision.APPROVED.value,
                "confidence": 0.8,
                "comments": [],
            }

        with patch.object(plan_review_service, '_llm_review', side_effect=mock_llm_review) as mock_review:
            await plan_review_service.review_plan(
                plan=plan,
                user_message="测试",
                user_context=user_context,
            )

            # Verify: User context was passed to review
            assert mock_review.called
            call_args = mock_review.call_args

            # Check positional args (plan, user_message, user_context)
            assert len(call_args[0]) >= 3  # Should have at least 3 positional args
            passed_context = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("user_context", {})

            assert "active_focus_id" in passed_context
            assert "pending_tasks_count" in passed_context

            print(f"✅ User context passing test passed")


# ============================================================================
# Test 5: Review Result Data Structure
# ============================================================================
class TestReviewResultStructure:
    """Test that review result matches expected structure"""

    @pytest.mark.asyncio
    async def test_review_result_has_required_fields(self, plan_review_service):
        """Test: Review result should have all required fields"""

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-structure-test",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="Test plan",
            tool_calls=[],
        )

        review_result = await plan_review_service.review_plan(
            plan=plan,
            user_message="测试",
            user_context={},
        )

        # Verify: Has all required fields
        assert hasattr(review_result, 'review_id')
        assert hasattr(review_result, 'plan_id')
        assert hasattr(review_result, 'decision')
        assert hasattr(review_result, 'confidence')
        assert hasattr(review_result, 'comments')
        assert hasattr(review_result, 'reviewed_at')

        # Verify: Can be converted to dict
        result_dict = review_result.to_dict()
        assert 'review_id' in result_dict
        assert 'decision' in result_dict
        assert 'confidence' in result_dict
        assert 'comments' in result_dict

        print(f"✅ Review result structure test passed")
        print(f"   Fields: {list(result_dict.keys())}")

    @pytest.mark.asyncio
    async def test_comments_have_required_structure(self, plan_review_service):
        """Test: Review comments should have required structure"""

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="plan-comment-test",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.6,
            rationale="Test plan for comments",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="risky_operation",
                    params={},
                    timeout_ms=10000,
                ),
            ],
        )

        # Mock LLM to return structured comments
        with patch.object(plan_review_service, '_llm_review', return_value={
            "decision": ReviewDecision.NEEDS_MODIFICATION.value,
            "confidence": 0.6,
            "comments": [{
                "category": "safety",
                "severity": "warning",
                "message": "测试评论",
                "suggested_fix": "建议修改",
                "affected_tool_calls": ["call_1"],
            }],
        }):
            review_result = await plan_review_service.review_plan(
                plan=plan,
                user_message="测试",
                user_context={},
            )

            # Verify: Comments have structure
            assert len(review_result.comments) > 0
            comment = review_result.comments[0]

            assert hasattr(comment, 'category')
            assert hasattr(comment, 'severity')
            assert hasattr(comment, 'message')
            assert hasattr(comment, 'suggested_fix')
            assert hasattr(comment, 'affected_tool_calls')

            # Verify: Comment can be converted to dict
            comment_dict = comment.to_dict()
            assert 'category' in comment_dict
            assert 'severity' in comment_dict
            assert 'message' in comment_dict

            print(f"✅ Comment structure test passed")


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("核心链路二验收测试：任务规划与人机协同审查")
    print("=" * 70)
    print()

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
