"""
Test suite for Plan Execution Validation feature

Tests:
1. ToolResultExtractor - extracting tool results from LangGraph messages
2. PlanExecutionValidator - validating execution results
3. PlanExecutionRecordService - persisting validation results
4. Integration - end-to-end validation flow
"""
import pytest
import sys
from datetime import datetime
from uuid import UUID, uuid4

sys.path.insert(0, '.')

from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.services.plan_execution_validator import PlanExecutionValidator, ExecutionValidationResult
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.tools.base import ToolResult


# ============================================================================
# Test 1: ToolResultExtractor
# ============================================================================

class TestToolResultExtractor:
    """Test extracting tool results from LangGraph state messages"""

    @pytest.fixture
    def extractor(self):
        return ToolResultExtractor()

    @pytest.fixture
    def sample_messages(self):
        """Sample LangGraph state messages"""
        return [
            {"role": "user", "content": "Hello"},
            {
                "role": "tool",
                "name": "get_task",
                "tool_call_id": "call_123",
                "content": '{"success": true, "data": {"task_id": "task-1"}}'
            },
            {
                "role": "tool",
                "name": "create_task",
                "tool_call_id": "call_456",
                "content": '{"success": false, "error": "Invalid input"}'
            },
            {
                "role": "assistant",
                "content": "I've processed your request."
            },
            # Malformed tool message
            {
                "role": "tool",
                "name": "search",
                "content": "not json"
            },
            # Tool message with error field
            {
                "role": "tool",
                "name": "delete_task",
                "tool_call_id": "call_789",
                "content": '{"success": false, "error": "Task not found", "error_type": "NotFoundError"}'
            },
        ]

    def test_extract_from_messages(self, extractor, sample_messages):
        """Test extracting tool results from messages"""
        results = extractor.extract_from_messages(sample_messages)

        # Should extract 4 tool messages (skip non-tool messages)
        assert len(results) == 4, f"Expected 4 results, got {len(results)}"

        # Check first successful result
        assert results[0].success is True
        assert results[0].tool_name == "get_task"
        assert results[0].tool_call_id == "call_123"
        assert results[0].data is not None

        # Check failed result
        assert results[1].success is False
        assert results[1].tool_name == "create_task"
        assert results[1].error_message == "Invalid input"

        # Check malformed handling
        assert results[2].tool_name == "search"

        # Check error_type extraction
        assert results[3].success is False
        assert results[3].error_type == "NotFoundError"

    def test_extract_empty_messages(self, extractor):
        """Test with empty message list"""
        results = extractor.extract_from_messages([])
        assert len(results) == 0

    def test_extract_no_tool_messages(self, extractor):
        """Test with no tool messages"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        results = extractor.extract_from_messages(messages)
        assert len(results) == 0


# ============================================================================
# Test 2: PlanExecutionValidator
# ============================================================================

class TestPlanExecutionValidator:
    """Test plan execution validation logic"""

    @pytest.fixture
    def validator(self):
        return PlanExecutionValidator()

    @pytest.fixture
    def sample_plan(self):
        """Create a sample ExecutablePlan"""
        return ExecutablePlan(
            plan_id="test-plan-123",
            confidence=0.9,
            rationale="Test plan",
            success_criteria={
                "min_success_rate": 0.8,
                "required_tools": ["get_task"],
                "forbidden_errors": ["ValidationError"],
            },
            tool_calls=[
                ToolCallSpec(id="tc1", name="get_task", params={}),
                ToolCallSpec(id="tc2", name="create_task", params={}),
            ],
        )

    @pytest.fixture
    def successful_tool_results(self):
        """All tools executed successfully"""
        return [
            ToolResult(success=True, tool_name="get_task", data={"task_id": "t1"}, tool_call_id="c1"),
            ToolResult(success=True, tool_name="create_task", data={"task_id": "t2"}, tool_call_id="c2"),
        ]

    @pytest.fixture
    def partial_failed_results(self):
        """Some tools failed"""
        return [
            ToolResult(success=True, tool_name="get_task", data={"task_id": "t1"}, tool_call_id="c1"),
            ToolResult(success=False, tool_name="create_task", error_message="Invalid input", tool_call_id="c2"),
        ]

    @pytest.fixture
    def all_failed_results(self):
        """All tools failed"""
        return [
            ToolResult(success=False, tool_name="get_task", error_message="Not found", tool_call_id="c1"),
            ToolResult(success=False, tool_name="create_task", error_message="Invalid input", tool_call_id="c2"),
        ]

    @pytest.mark.asyncio
    async def test_validate_all_success(self, validator, sample_plan, successful_tool_results):
        """Test validation with all successful tool results"""
        result = await validator.validate(
            plan=sample_plan,
            tool_results=successful_tool_results,
        )

        assert result.validation_status == "passed"
        assert result.quality_score >= 0.8
        assert result.tool_summary["total"] == 2
        assert result.tool_summary["successful"] == 2
        assert result.tool_summary["failed"] == 0
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_validate_partial_failure(self, validator, sample_plan, partial_failed_results):
        """Test validation with partial failures"""
        result = await validator.validate(
            plan=sample_plan,
            tool_results=partial_failed_results,
        )

        assert result.validation_status in ["partial", "failed"]
        assert result.tool_summary["total"] == 2
        assert result.tool_summary["successful"] == 1
        assert result.tool_summary["failed"] == 1
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_validate_all_failure(self, validator, sample_plan, all_failed_results):
        """Test validation with all failures"""
        result = await validator.validate(
            plan=sample_plan,
            tool_results=all_failed_results,
        )

        assert result.validation_status == "failed"
        assert result.quality_score < 0.5
        assert result.tool_summary["successful"] == 0
        assert result.tool_summary["failed"] == 2

    @pytest.mark.asyncio
    async def test_validate_with_success_criteria(self, validator, sample_plan, partial_failed_results):
        """Test validation against success criteria"""
        result = await validator.validate(
            plan=sample_plan,
            tool_results=partial_failed_results,
        )

        # Check criteria results
        assert "criteria_results" in result.__dict__
        assert result.criteria_results is not None
        assert "checks" in result.criteria_results

        # min_success_rate check
        if "min_success_rate" in result.criteria_results["checks"]:
            rate_check = result.criteria_results["checks"]["min_success_rate"]
            assert "actual" in rate_check
            assert "passed" in rate_check

    @pytest.mark.asyncio
    async def test_validate_empty_tool_results(self, validator, sample_plan):
        """Test validation with no tool results"""
        result = await validator.validate(
            plan=sample_plan,
            tool_results=[],
        )

        # Empty results should still return a valid result
        assert result.validation_status in ["passed", "failed"]
        assert result.tool_summary["total"] == 0


# ============================================================================
# Test 3: PlanExecutionRecordService
# ============================================================================

class TestPlanExecutionRecordService:
    """Test persistence of validation results"""

    @pytest.fixture
    def record_service(self, db_session):
        return PlanExecutionRecordService(db_session)

    @pytest.mark.asyncio
    async def test_create_record(self, record_service):
        """Test creating an execution record"""
        plan_id = uuid4()
        user_id = uuid4()

        record = await record_service.create_record(
            plan_id=plan_id,
            user_id=user_id,
            validation_status="passed",
            quality_score=0.85,
            criteria_results={"all_passed": True},
            tool_summary={"total": 3, "successful": 3, "failed": 0},
            issues=[],
        )

        assert record is not None
        assert str(record.plan_id) == str(plan_id)
        assert str(record.user_id) == str(user_id)
        assert record.validation_status == "passed"
        assert record.quality_score == 0.85
        assert record.total_tools == 3
        assert record.successful_tools == 3
        assert record.failed_tools == 0

    @pytest.mark.asyncio
    async def test_get_records_by_plan(self, record_service):
        """Test retrieving records by plan"""
        plan_id = uuid4()
        user_id = uuid4()

        # Create multiple records
        await record_service.create_record(
            plan_id=plan_id,
            user_id=user_id,
            validation_status="passed",
            quality_score=0.9,
            criteria_results={},
            tool_summary={},
            issues=[],
        )

        records = await record_service.get_records_by_plan(plan_id)
        assert len(records) >= 1
        assert str(records[0].plan_id) == str(plan_id)

    @pytest.mark.asyncio
    async def test_get_user_execution_stats(self, record_service):
        """Test getting user execution statistics"""
        user_id = uuid4()

        # Create some records
        for i in range(5):
            await record_service.create_record(
                plan_id=uuid4(),
                user_id=user_id,
                validation_status="passed" if i < 4 else "failed",
                quality_score=0.8 if i < 4 else 0.3,
                criteria_results={},
                tool_summary={},
                issues=[],
            )

        stats = await record_service.get_user_execution_stats(user_id, days=30)
        assert stats["total"] >= 5
        assert 0 <= stats["avg_score"] <= 1


# ============================================================================
# Test 4: Integration Tests
# ============================================================================

class TestExecutionValidationIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_validation_flow(self, db_session):
        """Test complete validation and persistence flow"""
        from app.services.plan_execution_record_service import PlanExecutionRecordService

        # Setup
        user_id = uuid4()
        plan = ExecutablePlan(
            plan_id=str(uuid4()),
            confidence=0.85,
            rationale="Integration test plan",
            success_criteria={"min_success_rate": 0.7},
            tool_calls=[
                ToolCallSpec(id="tc1", name="tool1", params={}),
                ToolCallSpec(id="tc2", name="tool2", params={}),
            ],
        )

        tool_results = [
            ToolResult(success=True, tool_name="tool1", data={"result": "ok"}, tool_call_id="c1"),
            ToolResult(success=False, tool_name="tool2", error_message="Failed", tool_call_id="c2"),
        ]

        # Create validator with record service
        record_service = PlanExecutionRecordService(db_session)
        validator = PlanExecutionValidator(record_service=record_service)

        # Execute validation with persistence
        result = await validator.validate_and_record(
            plan=plan,
            tool_results=tool_results,
            user_id=user_id,
        )

        # Verify validation result
        assert result is not None
        assert result.plan_id == plan.plan_id
        assert result.validation_status in ["passed", "partial", "failed"]
        assert 0 <= result.quality_score <= 1
        assert result.tool_summary["total"] == 2

        # Verify record was persisted
        records = await record_service.get_records_by_plan(UUID(plan.plan_id))
        assert len(records) >= 1
        assert records[0].validation_status == result.validation_status
        assert records[0].quality_score == result.quality_score


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
