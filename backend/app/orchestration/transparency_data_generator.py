"""
Transparency Data Generator
透明度数据生成器

Tracks and formats transparency data for the frontend transparency panel.
This module captures execution steps, agent switching, tool calls, and resource usage.
"""
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class StepType(str, Enum):
    """Transparency step types matching frontend"""
    THINKING = "thinking"
    GENERATING = "generating"
    EXECUTING_TOOL = "executing_tool"
    PLANNING = "planning"
    VALIDATING = "validating"
    # Backward-compatible aliases used in legacy tests/callers.
    TOOL_EXECUTION = "executing_tool"
    LLM_INFERENCE = "generating"


class StepStatus(str, Enum):
    """Step status matching frontend"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    # Backward-compatible alias.
    RUNNING = "in_progress"


@dataclass
class TransparencyStep:
    """A single transparency step"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    step_type: StepType = StepType.THINKING
    status: StepStatus = StepStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: int = 0
    agent_type: str | None = None
    result: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def started_at(self):
        if self.start_time is None:
            return None
        return None if self.status == StepStatus.PENDING else datetime.fromtimestamp(self.start_time)

    @property
    def completed_at(self):
        if self.end_time is None:
            return None
        return datetime.fromtimestamp(self.end_time)

    def to_dict(self) -> dict[str, Any]:
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

    def mark_completed(self, result: str | None = None):
        """Mark step as completed"""
        self.status = StepStatus.COMPLETED
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        if result:
            self.result = result

    def mark_failed(self, error: str):
        """Mark step as failed"""
        self.status = StepStatus.FAILED
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        self.error = error


class TransparencyDataGenerator:
    """
    Generates transparency data for frontend display.

    This class tracks the AI workflow execution and produces
    transparency_step and transparency_complete events.
    """

    def __init__(self, request_id: str | None = None, enabled: bool = True):
        """
        Initialize transparency data generator.

        Args:
            request_id: Unique request identifier
            enabled: Whether transparency mode is enabled
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.enabled = enabled
        self.steps: list[TransparencyStep] = []
        self._active_steps: dict[str, TransparencyStep] = {}
        self.current_step_index = 0
        self.total_tokens = 0
        self.start_time = time.time()

    def create_step(
        self,
        name: str,
        step_type: StepType,
        agent_type: str | None = None,
        metadata: dict[str, Any] | None = None,
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
        self._active_steps[step.step_id] = step
        logger.debug(f"[Transparency] Step started: {step.name}")

    def complete_step(
        self,
        step: TransparencyStep,
        result: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Mark a step as completed"""
        if not self.enabled:
            return

        if error:
            step.mark_failed(error)
        else:
            step.mark_completed(result)
        if metadata:
            step.metadata.update(metadata)
        self._active_steps.pop(step.step_id, None)

        logger.debug(f"[Transparency] Step completed: {step.name} ({step.duration_ms}ms)")

    def fail_step(
        self,
        step: TransparencyStep,
        error: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Mark a step as failed"""
        if not self.enabled:
            return

        step.mark_failed(error)
        if metadata:
            step.metadata.update(metadata)
        self._active_steps.pop(step.step_id, None)

        logger.debug(f"[Transparency] Step failed: {step.name} - {error}")

    def get_step_event(self, step: TransparencyStep | None = None) -> dict[str, Any] | None:
        """
        Get the next step event to send to frontend.

        Returns:
            Dict with transparency_step event data, or None if no steps
        """
        if step is not None:
            # Legacy flat payload used by older tests/callers.
            legacy_step_type = (
                "tool_execution" if step.step_type == StepType.EXECUTING_TOOL else step.step_type.value
            )
            legacy_status = "running" if step.status == StepStatus.IN_PROGRESS else step.status.value
            return {
                "step_id": step.step_id,
                "name": step.name,
                "step_type": legacy_step_type,
                "status": legacy_status,
                "agent_type": step.agent_type,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "result": step.result,
                "error": step.error,
                "metadata": step.metadata,
            }

        if not self.enabled or self.current_step_index >= len(self.steps):
            return None

        current_step = self.steps[self.current_step_index]
        self.current_step_index += 1

        return {
            "type": "transparency_step",
            "data": {
                "currentStep": self.current_step_index,
                "totalSteps": len(self.steps),
                "step": current_step.to_dict(),
            },
        }

    def get_complete_event(self) -> dict[str, Any] | None:
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
            # Legacy compatibility fields.
            "summary": {
                "completed_steps": sum(1 for step in self.steps if step.status == StepStatus.COMPLETED),
                "failed_steps": sum(1 for step in self.steps if step.status == StepStatus.FAILED),
            },
            "total_steps": len(self.steps),
            "steps": [step.to_dict() for step in self.steps],
        }

    def add_tokens(self, token_count: int):
        """Add to total token count"""
        self.total_tokens += token_count

    def track_planning_step(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransparencyStep:
        step = self.create_step(name=name, step_type=StepType.PLANNING, metadata=metadata)
        self.start_step(step)
        return step

    def track_tool_execution(
        self,
        tool_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransparencyStep:
        step = self.create_step(
            name=f"Execute Tool: {tool_name}",
            step_type=StepType.EXECUTING_TOOL,
            metadata={"tool": tool_name, **(metadata or {})},
        )
        self.start_step(step)
        return step

    def track_llm_inference(
        self,
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransparencyStep:
        step = self.create_step(
            name=f"LLM Inference: {model}",
            step_type=StepType.LLM_INFERENCE,
            metadata={"model": model, **(metadata or {})},
        )
        self.start_step(step)
        return step


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
    agent_type: str | None = None,
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
        from app.gen.agent.v1 import agent_service_pb2
        from app.orchestration.orchestrator import get_agent_type_for_tool
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
    context: str | None = None,
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
