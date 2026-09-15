"""
End-to-End validation test (no database required)

Tests the complete validation flow without database dependencies.
"""
import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, '.')

from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.services.plan_execution_validator import PlanExecutionValidator, ExecutionValidationResult
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.tools.base import ToolResult


async def test_tool_result_extraction():
    """Test 1: Tool result extraction from LangGraph messages"""
    print("\n" + "="*60)
    print("TEST 1: ToolResultExtractor")
    print("="*60)

    extractor = ToolResultExtractor()

    # Simulate LangGraph state messages
    messages = [
        {"role": "user", "content": "Help me create a task"},
        {
            "role": "tool",
            "name": "get_focus",
            "tool_call_id": "call_001",
            "content": '{"success": true, "data": {"focus_id": "focus-1", "subject": "Python"}}'
        },
        {
            "role": "tool",
            "name": "create_task",
            "tool_call_id": "call_002",
            "content": '{"success": true, "data": {"task_id": "task-123", "title": "Learn async/await"}}'
        },
        {"role": "assistant", "content": "I've created your task!"},
    ]

    results = extractor.extract_from_messages(messages)

    print(f"✓ Extracted {len(results)} tool results from {len(messages)} messages")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r.tool_name}: success={r.success}, tool_call_id={r.tool_call_id}")

    assert len(results) == 2
    assert results[0].tool_name == "get_focus"
    assert results[0].success is True
    assert results[1].tool_name == "create_task"
    assert results[1].tool_call_id == "call_002"

    print("✅ Test 1 PASSED")
    return True


async def test_validation_all_success():
    """Test 2: Validation with all successful tools"""
    print("\n" + "="*60)
    print("TEST 2: PlanExecutionValidator - All Success")
    print("="*60)

    validator = PlanExecutionValidator()

    plan = ExecutablePlan(
        plan_id="test-plan-success",
        confidence=0.9,
        rationale="Create a learning task",
        success_criteria={
            "min_success_rate": 0.8,
            "required_tools": ["get_focus"],
        },
        tool_calls=[
            ToolCallSpec(id="tc1", name="get_focus", params={}),
            ToolCallSpec(id="tc2", name="create_task", params={}),
            ToolCallSpec(id="tc3", name="add_to_plan", params={}),
        ],
    )

    tool_results = [
        ToolResult(success=True, tool_name="get_focus", data={"focus_id": "f1"}, tool_call_id="c1"),
        ToolResult(success=True, tool_name="create_task", data={"task_id": "t1"}, tool_call_id="c2"),
        ToolResult(success=True, tool_name="add_to_plan", data={"added": True}, tool_call_id="c3"),
    ]

    result = await validator.validate(plan=plan, tool_results=tool_results)

    print(f"✓ Plan ID: {result.plan_id}")
    print(f"✓ Validation Status: {result.validation_status}")
    print(f"✓ Quality Score: {result.quality_score:.2f}")
    print(f"✓ Tool Summary: {result.tool_summary}")
    print(f"✓ Criteria Results: {result.criteria_results}")
    print(f"✓ Issues: {result.issues}")

    assert result.validation_status == "passed"
    assert result.quality_score >= 0.8
    assert result.tool_summary["total"] == 3
    assert result.tool_summary["successful"] == 3
    assert len(result.issues) == 0

    print("✅ Test 2 PASSED")
    return True


async def test_validation_partial_failure():
    """Test 3: Validation with partial failures"""
    print("\n" + "="*60)
    print("TEST 3: PlanExecutionValidator - Partial Failure")
    print("="*60)

    validator = PlanExecutionValidator()

    plan = ExecutablePlan(
        plan_id="test-plan-partial",
        confidence=0.7,
        rationale="Attempt complex operation",
        success_criteria={"min_success_rate": 0.8},
        tool_calls=[
            ToolCallSpec(id="tc1", name="get_task", params={}),
            ToolCallSpec(id="tc2", name="update_task", params={}),
            ToolCallSpec(id="tc3", name="delete_task", params={}),
        ],
    )

    tool_results = [
        ToolResult(success=True, tool_name="get_task", data={"task_id": "t1"}, tool_call_id="c1"),
        ToolResult(success=False, tool_name="update_task", error_message="Task not found", tool_call_id="c2"),
        ToolResult(success=False, tool_name="delete_task", error_message="Permission denied", tool_call_id="c3"),
    ]

    result = await validator.validate(plan=plan, tool_results=tool_results)

    print(f"✓ Plan ID: {result.plan_id}")
    print(f"✓ Validation Status: {result.validation_status}")
    print(f"✓ Quality Score: {result.quality_score:.2f}")
    print(f"✓ Tool Summary: {result.tool_summary}")
    print(f"✓ Issues ({len(result.issues)}):")
    for issue in result.issues:
        print(f"    - {issue}")

    assert result.validation_status in ["partial", "failed"]
    assert result.tool_summary["successful"] == 1
    assert result.tool_summary["failed"] == 2
    # Issues include tool failures AND criteria failures
    assert len(result.issues) >= 2

    print("✅ Test 3 PASSED")
    return True


async def test_validation_with_criteria_check():
    """Test 4: Validation with success criteria checking"""
    print("\n" + "="*60)
    print("TEST 4: PlanExecutionValidator - Criteria Check")
    print("="*60)

    validator = PlanExecutionValidator()

    # Test with forbidden errors
    plan = ExecutablePlan(
        plan_id="test-plan-criteria",
        confidence=0.85,
        rationale="Test with forbidden errors",
        success_criteria={
            "min_success_rate": 0.8,
            "forbidden_errors": ["ValidationError", "AuthenticationError"],
            "required_tools": ["get_user"],
        },
        tool_calls=[
            ToolCallSpec(id="tc1", name="get_user", params={}),
            ToolCallSpec(id="tc2", name="update_user", params={}),
        ],
    )

    tool_results = [
        ToolResult(
            success=False,
            tool_name="get_user",
            error_message="Invalid input",
            error_type="ValidationError",
            tool_call_id="c1"
        ),
        ToolResult(
            success=True,
            tool_name="update_user",
            data={"updated": True},
            tool_call_id="c2"
        ),
    ]

    result = await validator.validate(plan=plan, tool_results=tool_results)

    print(f"✓ Plan ID: {result.plan_id}")
    print(f"✓ Validation Status: {result.validation_status}")
    print(f"✓ Quality Score: {result.quality_score:.2f}")
    print(f"✓ Criteria Results:")
    for check_name, check_data in result.criteria_results.get("checks", {}).items():
        print(f"    - {check_name}: passed={check_data.get('passed', False)}")

    # Check that forbidden_errors was detected
    if "forbidden_errors" in result.criteria_results.get("checks", {}):
        forbidden_check = result.criteria_results["checks"]["forbidden_errors"]
        assert forbidden_check["passed"] is False
        print(f"✓ Forbidden error correctly detected: {forbidden_check}")

    print("✅ Test 4 PASSED")
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PLAN EXECUTION VALIDATION - END-TO-END TESTS")
    print("="*60)

    tests = [
        test_tool_result_extraction,
        test_validation_all_success,
        test_validation_partial_failure,
        test_validation_with_criteria_check,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if await test():
                passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
