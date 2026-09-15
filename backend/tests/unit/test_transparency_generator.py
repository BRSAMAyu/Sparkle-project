"""
Unit tests for Transparency Data Generator
透明度数据生成器单元测试
"""
import pytest
import json
from datetime import datetime
from app.orchestration.transparency_data_generator import (
    TransparencyDataGenerator,
    TransparencyStep,
    StepType,
    StepStatus
)


@pytest.fixture
def generator():
    """Create transparency data generator instance"""
    return TransparencyDataGenerator()


class TestTransparencyStep:
    """Test transparency step model"""

    def test_create_step(self, generator: TransparencyDataGenerator):
        """Test creating a transparency step"""
        step = generator.create_step(
            name="Test Step",
            step_type=StepType.TOOL_EXECUTION,
            agent_type="test_agent",
            metadata={"test_key": "test_value"}
        )

        assert isinstance(step, TransparencyStep)
        assert step.name == "Test Step"
        assert step.step_type == StepType.TOOL_EXECUTION
        assert step.agent_type == "test_agent"
        assert step.status == StepStatus.PENDING
        assert step.metadata == {"test_key": "test_value"}
        assert step.step_id is not None

    def test_start_step(self, generator: TransparencyDataGenerator):
        """Test starting a step"""
        step = generator.create_step(
            name="Test Step",
            step_type=StepType.LLM_INFERENCE,
            agent_type="llm_agent"
        )

        generator.start_step(step)

        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None
        assert isinstance(step.started_at, datetime)

    def test_complete_step(self, generator: TransparencyDataGenerator):
        """Test completing a step"""
        step = generator.create_step(
            name="Test Step",
            step_type=StepType.PLANNING,
            agent_type="orchestrator"
        )

        generator.start_step(step)

        result = {"output": "test result"}
        generator.complete_step(step, result)

        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None
        assert step.result == result
        assert step.error is None

    def test_complete_step_with_error(self, generator: TransparencyDataGenerator):
        """Test completing a step with error"""
        step = generator.create_step(
            name="Test Step",
            step_type=StepType.TOOL_EXECUTION,
            agent_type="tool_executor"
        )

        generator.start_step(step)

        error_msg = "Test error"
        generator.complete_step(step, None, error=error_msg)

        assert step.status == StepStatus.FAILED
        assert step.error == error_msg
        assert step.result is None


class TestEventGeneration:
    """Test event generation for WebSocket"""

    def test_get_step_event(self, generator: TransparencyDataGenerator):
        """Test getting step event data"""
        step = generator.create_step(
            name="Execute Tool",
            step_type=StepType.TOOL_EXECUTION,
            agent_type="tool_agent",
            metadata={"tool": "search"}
        )

        generator.start_step(step)

        event = generator.get_step_event(step)

        assert event["step_id"] == step.step_id
        assert event["name"] == "Execute Tool"
        assert event["step_type"] == "tool_execution"
        assert event["status"] == "running"
        assert event["agent_type"] == "tool_agent"
        assert "started_at" in event

    def test_get_complete_event(self, generator: TransparencyDataGenerator):
        """Test getting complete event data"""
        step1 = generator.create_step(
            name="Step 1",
            step_type=StepType.PLANNING,
            agent_type="orchestrator"
        )

        step2 = generator.create_step(
            name="Step 2",
            step_type=StepType.TOOL_EXECUTION,
            agent_type="tool_agent"
        )

        generator.start_step(step1)
        generator.complete_step(step1, {"plan": "created"})

        generator.start_step(step2)
        generator.complete_step(step2, {"result": "success"})

        complete_event = generator.get_complete_event()

        assert "summary" in complete_event
        assert "total_steps" in complete_event
        assert complete_event["total_steps"] == 2
        assert "steps" in complete_event
        assert len(complete_event["steps"]) == 2

    def test_event_serialization(self, generator: TransparencyDataGenerator):
        """Test that events can be serialized to JSON"""
        step = generator.create_step(
            name="Test Event",
            step_type=StepType.LLM_INFERENCE,
            agent_type="llm"
        )

        generator.start_step(step)

        event = generator.get_step_event(step)

        # Should be JSON serializable
        json_str = json.dumps(event)
        assert len(json_str) > 0

        # Should deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["name"] == "Test Event"


class TestConvenienceMethods:
    """Test convenience methods for common patterns"""

    def test_track_planning_step(self, generator: TransparencyDataGenerator):
        """Test tracking a planning step"""
        generator.track_planning_step(
            name="Create Plan",
            metadata={"goal": "test goal"}
        )

        # Should have created and started a step
        steps = generator._active_steps.values()
        assert len(steps) > 0

    def test_track_tool_execution(self, generator: TransparencyDataGenerator):
        """Test tracking tool execution"""
        generator.track_tool_execution(
            tool_name="search",
            metadata={"query": "test query"}
        )

        steps = generator._active_steps.values()
        assert len(steps) > 0

    def test_track_llm_inference(self, generator: TransparencyDataGenerator):
        """Test tracking LLM inference"""
        generator.track_llm_inference(
            model="gpt-4",
            metadata={"prompt_tokens": 100}
        )

        steps = generator._active_steps.values()
        assert len(steps) > 0
