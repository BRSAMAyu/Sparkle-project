"""Unit tests for PlanReviewService enhancements."""

from unittest.mock import patch

import pytest

from app.orchestration.plan_review_service import (
    PlanReviewService,
    ReviewDecision,
)
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec


class TestLLMReviewRetry:
    """Test LLM review retry mechanism."""

    @pytest.mark.asyncio
    async def test_llm_review_retry_on_failure(self):
        """Test that LLM review retries on transient failures."""
        service = PlanReviewService()

        # Create a simple plan
        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="test-plan-1",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.9,
            rationale="Test plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="get_tasks",
                    params={},
                    timeout_ms=10000,
                )
            ],
        )

        # Mock llm_service to fail first attempt, succeed second
        call_count = 0

        async def mock_reason_json(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            # Second attempt succeeds
            return {
                "decision": "approved",
                "confidence": 0.9,
                "comments": [],
            }

        with patch("app.orchestration.plan_review_service.llm_service") as mock_llm:
            mock_llm.reason_json = mock_reason_json

            result = await service._llm_review(
                plan=plan,
                user_message="test message",
                user_context={},
            )

            assert result["decision"] == "approved"
            assert call_count == 2  # Should have retried once

    @pytest.mark.asyncio
    async def test_llm_review_fallback_after_max_retries(self):
        """Test that fallback is used after max retries exhausted."""
        service = PlanReviewService()

        # Create a safe plan (should auto-approve in fallback)
        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="test-plan-2",
            snapshot_id="snap-2",
            context_version="v1",
            source="langgraph",
            confidence=0.9,
            rationale="Test plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="get_tasks",
                    params={},
                    timeout_ms=10000,
                )
            ],
        )

        # Mock llm_service to always fail
        async def mock_reason_json_fail(*args, **kwargs):
            raise Exception("LLM unavailable")

        with patch("app.orchestration.plan_review_service.llm_service") as mock_llm:
            mock_llm.reason_json = mock_reason_json_fail

            result = await service._llm_review(
                plan=plan,
                user_message="test message",
                user_context={},
            )

            # Should use fallback
            assert result["fallback_used"] is True
            assert result["fallback_reason"] == "llm_review_unavailable"
            # Safe plan should be auto-approved
            assert result["decision"] == "approved"


class TestLLMReviewFallback:
    """Test intelligent fallback strategy."""

    @pytest.mark.asyncio
    async def test_fallback_auto_approves_safe_plan(self):
        """Test that fallback auto-approves safe read-only plans."""
        service = PlanReviewService()

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="test-plan-safe",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="Safe plan",
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

        result = await service._llm_review_fallback(
            plan=plan,
            user_message="test",
            user_context={},
        )

        assert result["decision"] == "approved"
        assert result["confidence"] >= 0.8
        assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_fallback_requires_confirmation_for_high_risk(self):
        """Test that fallback requires confirmation for high-risk plans."""
        service = PlanReviewService()

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="test-plan-risky",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="Risky plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="delete_task",
                    params={"task_id": "task-1"},
                    timeout_ms=10000,
                ),
            ],
        )

        result = await service._llm_review_fallback(
            plan=plan,
            user_message="test",
            user_context={},
        )

        assert result["decision"] == "requires_confirmation"
        assert result["confidence"] == 0.3
        assert any("delete_task" in c.get("affected_tool_calls", [])
                for c in result["comments"])

    @pytest.mark.asyncio
    async def test_fallback_handles_empty_plan(self):
        """Test that fallback handles empty plans gracefully."""
        service = PlanReviewService()

        plan = ExecutablePlan(
            schema_version="4.0",
            plan_id="test-plan-empty",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.5,
            rationale="Empty plan",
            tool_calls=[],
        )

        result = await service._llm_review_fallback(
            plan=plan,
            user_message="test",
            user_context={},
        )

        assert result["decision"] == "approved"
        assert result["confidence"] == 1.0


class TestPlanningFeasibilityGuard:
    """Test deterministic planning feasibility checks."""

    @pytest.mark.asyncio
    async def test_review_plan_blocks_mastery_promise_with_insufficient_capacity(self):
        service = PlanReviewService()
        plan = ExecutablePlan(
            schema_version="5.0",
            plan_id="test-plan-impossible-schedule",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.98,
            rationale="Seven day mastery plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="create_plan",
                    params={
                        "title": "一周精通 C++",
                        "total_days": 7,
                        "daily_hours": 1,
                        "difficulty": "expert",
                    },
                    timeout_ms=10000,
                )
            ],
        )

        result = await service.review_plan(
            plan=plan,
            user_message="我每天只有1小时，帮我一周精通 C++",
            user_context={"available_hours_per_day": 1, "current_plan_count": 0},
        )

        assert result.decision == ReviewDecision.NEEDS_MODIFICATION.value
        assert result.auto_approved is False
        assert any("总可用时间" in comment.message for comment in result.comments)

    def test_feasibility_guard_requires_review_cadence_for_short_plan(self):
        service = PlanReviewService()
        plan = ExecutablePlan(
            schema_version="5.0",
            plan_id="test-plan-tight-no-review",
            snapshot_id="snap-1",
            context_version="v1",
            source="langgraph",
            confidence=0.8,
            rationale="Tight sprint plan",
            tool_calls=[
                ToolCallSpec(
                    id="call_1",
                    name="create_plan",
                    params={
                        "title": "7 天考试冲刺",
                        "total_days": 7,
                        "daily_hours": 2,
                        "planned_daily_minutes": 90,
                    },
                    timeout_ms=10000,
                )
            ],
        )

        comments = service._collect_feasibility_comments(plan=plan, user_context={})

        assert any(comment.category == "completeness" and "复盘节奏" in comment.message for comment in comments)
        assert not any(comment.severity == "critical" for comment in comments)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
