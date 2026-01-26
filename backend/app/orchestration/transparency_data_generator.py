"""
Transparency Data Generator
透明度数据生成器

Tracks and formats transparency data for the frontend transparency panel.
This module captures execution steps, agent switching, tool calls, and resource usage.
"""
import time
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from loguru import logger
from dataclasses import dataclass, field


class StepType(str, Enum):
    """Transparency step types matching frontend"""
    THINKING = "thinking"
    GENERATING = "generating"
    EXECUTING_TOOL = "executing_tool"
    PLANNING = "planning"
    VALIDATING = "validating"


class StepStatus(str, Enum):
    """Step status matching frontend"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TransparencyStep:
    """A single transparency step"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    step_type: StepType = StepType.THINKING
    status: StepStatus = StepStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: int = 0
    agent_type: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        duration_ms = 0
        if self.end_time:
            duration_ms = int((self.end_time - self.start_time) * 1000)
        elif self.status == StepStatus.IN_PROGRESS:
            duration_ms = int((time.time() - self.start_time) * 1000)

        return {
            "stepId": self.step_id,
            "name": self.name,
            "type": self.step_type.value,
            "status": self.status.value,
            "durationMs": duration_ms,
            "agentType": self.agent_type,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    def mark_started(self):
        """Mark step as started"""
        self.status = StepStatus.IN_PROGRESS
        self.start_time = time.time()

    def mark_completed(self, result: Optional[str] = None):
        """Mark step as completed"""
        self.status = StepStatus.COMPLETED
        self.end_time = time.time()
        if result:
            self.result = result

    def mark_failed(self, error: str):
        """Mark step as failed"""
        self.status = StepStatus.FAILED
        self.end_time = time.time()
        self.error = error


class TransparencyDataGenerator:
    """
    Generates transparency data for frontend display.

    This class tracks the AI workflow execution and produces
    transparency_step and transparency_complete events.
    """

    def __init__(self, request_id: str, enabled: bool = True):
        """
        Initialize transparency data generator.

        Args:
            request_id: Unique request identifier
            enabled: Whether transparency mode is enabled
        """
        self.request_id = request_id
        self.enabled = enabled
        self.steps: List[TransparencyStep] = []
        self.current_step_index = 0
        self.total_tokens = 0
        self.start_time = time.time()

    def create_step(
        self,
        name: str,
        step_type: StepType,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TransparencyStep:
        """
        Create a new transparency step.

        Args:
            name: Step name
            step_type: Step type
            agent_type: Agent type (e.g., "KNOWLEDGE", "MATH")
            metadata: Additional metadata

        Returns:
            TransparencyStep: Created step
        """
        if not self.enabled:
            # Return a dummy step that won't be tracked
            return TransparencyStep(name=name, step_type=step_type)

        step = TransparencyStep(
            name=name,
            step_type=step_type,
            agent_type=agent_type,
            metadata=metadata or {},
        )
        self.steps.append(step)
        return step

    def start_step(self, step: TransparencyStep):
        """Mark a step as started"""
        if not self.enabled:
            return

        step.mark_started()
        logger.debug(f"[Transparency] Step started: {step.name}")

    def complete_step(
        self,
        step: TransparencyStep,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Mark a step as completed"""
        if not self.enabled:
            return

        step.mark_completed(result)
        if metadata:
            step.metadata.update(metadata)

        logger.debug(f"[Transparency] Step completed: {step.name} ({step.duration_ms}ms)")

    def fail_step(
        self,
        step: TransparencyStep,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Mark a step as failed"""
        if not self.enabled:
            return

        step.mark_failed(error)
        if metadata:
            step.metadata.update(metadata)

        logger.debug(f"[Transparency] Step failed: {step.name} - {error}")

    def get_step_event(self) -> Optional[Dict[str, Any]]:
        """
        Get the next step event to send to frontend.

        Returns:
            Dict with transparency_step event data, or None if no steps
        """
        if not self.enabled or self.current_step_index >= len(self.steps):
            return None

        step = self.steps[self.current_step_index]
        self.current_step_index += 1

        return {
            "type": "transparency_step",
            "data": {
                "currentStep": self.current_step_index,
                "totalSteps": len(self.steps),
                "step": step.to_dict(),
            },
        }

    def get_complete_event(self) -> Optional[Dict[str, Any]]:
        """
        Get the transparency_complete event with all steps.

        Returns:
            Dict with transparency_complete event data, or None if disabled
        """
        if not self.enabled:
            return None

        total_duration_ms = int((time.time() - self.start_time) * 1000)

        return {
            "type": "transparency_complete",
            "data": {
                "requestId": self.request_id,
                "steps": [step.to_dict() for step in self.steps],
                "totalDurationMs": total_duration_ms,
                "totalTokens": self.total_tokens,
            },
        }

    def add_tokens(self, token_count: int):
        """Add to total token count"""
        self.total_tokens += token_count


# Convenience functions for common workflow patterns

def track_planning_phase(
    generator: TransparencyDataGenerator,
    plan_name: str,
) -> TransparencyStep:
    """
    Track the planning phase.

    Args:
        generator: Transparency data generator
        plan_name: Name of the plan being created

    Returns:
        TransparencyStep: The planning step
    """
    step = generator.create_step(
        name=f"制定计划: {plan_name}",
        step_type=StepType.PLANNING,
        agent_type="ORCHESTRATOR",
        metadata={"phase": "planning"},
    )
    generator.start_step(step)
    return step


def track_tool_execution(
    generator: TransparencyDataGenerator,
    tool_name: str,
    agent_type: Optional[str] = None,
) -> TransparencyStep:
    """
    Track a tool execution.

    Args:
        generator: Transparency data generator
        tool_name: Name of the tool being executed
        agent_type: Agent type executing the tool

    Returns:
        TransparencyStep: The tool execution step
    """
    # Map tool name to agent type if not provided
    if agent_type is None:
        from app.orchestration.orchestrator import get_agent_type_for_tool
        from app.gen.agent.v1 import agent_service_pb2
        agent_int = get_agent_type_for_tool(tool_name)
        agent_type = agent_service_pb2.AgentType.Name(agent_int)

    step = generator.create_step(
        name=f"执行工具: {tool_name}",
        step_type=StepType.EXECUTING_TOOL,
        agent_type=agent_type,
        metadata={"tool": tool_name},
    )
    generator.start_step(step)
    return step


def track_agent_thinking(
    generator: TransparencyDataGenerator,
    agent_type: str,
    context: Optional[str] = None,
) -> TransparencyStep:
    """
    Track agent thinking/reasoning.

    Args:
        generator: Transparency data generator
        agent_type: Type of agent (e.g., "KNOWLEDGE", "MATH")
        context: Context of the thinking

    Returns:
        TransparencyStep: The thinking step
    """
    step = generator.create_step(
        name=f"{agent_type} 思考中",
        step_type=StepType.THINKING,
        agent_type=agent_type,
        metadata={"context": context} if context else {},
    )
    generator.start_step(step)
    return step


def track_response_generation(
    generator: TransparencyDataGenerator,
) -> TransparencyStep:
    """
    Track the response generation phase.

    Args:
        generator: Transparency data generator

    Returns:
        TransparencyStep: The generation step
    """
    step = generator.create_step(
        name="生成回复",
        step_type=StepType.GENERATING,
        agent_type="ORCHESTRATOR",
        metadata={"phase": "generation"},
    )
    generator.start_step(step)
    return step


def track_validation(
    generator: TransparencyDataGenerator,
    validation_type: str,
) -> TransparencyStep:
    """
    Track a validation phase.

    Args:
        generator: Transparency data generator
        validation_type: Type of validation (e.g., "grounding", "sufficiency")

    Returns:
        TransparencyStep: The validation step
    """
    step = generator.create_step(
        name=f"验证: {validation_type}",
        step_type=StepType.VALIDATING,
        agent_type="ORCHESTRATOR",
        metadata={"validation_type": validation_type},
    )
    generator.start_step(step)
    return step
