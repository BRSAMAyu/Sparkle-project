"""
StepFeedbackCollector — Phase C1

Transforms DAG execution results into structured feedback
for the replanner and planner to learn from.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from app.orchestration.executor import PlanExecutionResult
    from app.orchestration.schemas import ExecutablePlan
    from app.services.plan_execution_validator import ExecutionValidationResult


@dataclass
class StepFeedback:
    """Feedback for a single execution step."""
    step_id: str
    tool_name: str
    success: bool
    duration_ms: int = 0
    exceeded_timeout: bool = False
    missing_output_keys: list[str] = field(default_factory=list)
    error_message: str | None = None
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanExecutionFeedback:
    """Aggregate feedback from a single plan execution cycle.

    Stored in PlanState.feedback_log and consumed by the planner
    and replanner for future planning improvements.
    """
    plan_id: str
    user_id: str
    session_id: str
    validation_status: str  # passed, partial, failed
    quality_score: float
    total_steps: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    aborted: bool = False
    abort_reason: str | None = None
    execution_layers_completed: int = 0
    total_layers: int = 0
    step_feedbacks: list[StepFeedback] = field(default_factory=list)
    # Derived signals for planner consumption
    slow_tools: list[str] = field(default_factory=list)
    failed_tools: list[str] = field(default_factory=list)
    unreliable_dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "plan_execution_feedback",
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "validation_status": self.validation_status,
            "quality_score": self.quality_score,
            "total_steps": self.total_steps,
            "steps_passed": self.steps_passed,
            "steps_failed": self.steps_failed,
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "execution_layers_completed": self.execution_layers_completed,
            "total_layers": self.total_layers,
            "step_feedbacks": [sf.to_dict() for sf in self.step_feedbacks],
            "slow_tools": self.slow_tools,
            "failed_tools": self.failed_tools,
            "unreliable_dependencies": self.unreliable_dependencies,
        }

    @property
    def needs_replanning(self) -> bool:
        """Whether this feedback suggests the plan should be revised."""
        if self.aborted:
            return True
        if self.validation_status == "failed":
            return True
        if self.steps_failed > 0 and any(sf.required for sf in self.step_feedbacks if not sf.success):
            return True
        return False

    @property
    def severity(self) -> str:
        """Severity level for the replanner."""
        if self.aborted or self.validation_status == "failed":
            return "high"
        if self.validation_status == "partial":
            return "medium"
        return "low"


class StepFeedbackCollector:
    """Collects step-level feedback from DAG execution results.

    Usage:
        collector = StepFeedbackCollector()
        feedback = collector.collect(plan, plan_result, validation_result, user_id, session_id)
        # Store feedback in PlanState
        await plan_state_service.upsert_plan_state(
            user_id=..., plan_id=...,
            patch={"feedback_log": feedback.to_dict()},
        )
    """

    def collect(
        self,
        plan: ExecutablePlan,
        plan_result: PlanExecutionResult,
        validation_result: ExecutionValidationResult,
        user_id: str,
        session_id: str,
    ) -> PlanExecutionFeedback:
        """Transform execution artifacts into structured feedback."""
        spec_map = {tc.id: tc for tc in plan.tool_calls}

        step_feedbacks: list[StepFeedback] = []
        slow_tools: list[str] = []
        failed_tools: list[str] = []

        for sr in plan_result.step_results:
            spec = spec_map.get(sr.step_id)
            criteria = spec.success_criteria if spec else None

            exceeded_timeout = False
            if criteria and criteria.max_duration_ms > 0:
                exceeded_timeout = sr.duration_ms > criteria.max_duration_ms

            missing_keys: list[str] = []
            if criteria and criteria.expected_output_keys and sr.tool_result.success:
                actual = set(sr.output_data.keys()) if sr.output_data else set()
                missing_keys = list(set(criteria.expected_output_keys) - actual)

            sf = StepFeedback(
                step_id=sr.step_id,
                tool_name=sr.tool_name,
                success=sr.tool_result.success,
                duration_ms=sr.duration_ms,
                exceeded_timeout=exceeded_timeout,
                missing_output_keys=missing_keys,
                error_message=sr.tool_result.error_message if not sr.tool_result.success else None,
                required=criteria.required if criteria else True,
            )
            step_feedbacks.append(sf)

            if exceeded_timeout:
                slow_tools.append(sr.tool_name)
            if not sr.tool_result.success:
                failed_tools.append(sr.tool_name)

        # Detect unreliable dependencies: steps that failed AND had dependents
        dep_targets = set()
        for tc in plan.tool_calls:
            dep_targets.update(tc.depends_on)
        unreliable = [
            sf.step_id for sf in step_feedbacks
            if not sf.success and sf.step_id in dep_targets
        ]

        steps_passed = sum(1 for sf in step_feedbacks if sf.success)

        feedback = PlanExecutionFeedback(
            plan_id=plan.plan_id,
            user_id=user_id,
            session_id=session_id,
            validation_status=validation_result.validation_status,
            quality_score=validation_result.quality_score,
            total_steps=len(step_feedbacks),
            steps_passed=steps_passed,
            steps_failed=len(step_feedbacks) - steps_passed,
            aborted=plan_result.aborted,
            abort_reason=plan_result.abort_reason,
            execution_layers_completed=plan_result.execution_layers_completed,
            total_layers=plan_result.total_layers,
            step_feedbacks=step_feedbacks,
            slow_tools=list(set(slow_tools)),
            failed_tools=list(set(failed_tools)),
            unreliable_dependencies=unreliable,
        )

        logger.info(
            "Collected execution feedback: plan={}, status={}, "
            "steps={}/{}, slow={}, failed={}, unreliable_deps={}",
            plan.plan_id, feedback.validation_status,
            steps_passed, len(step_feedbacks),
            slow_tools, failed_tools, unreliable,
        )

        return feedback
