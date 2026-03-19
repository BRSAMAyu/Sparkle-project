from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.celery_app import celery_app
from app.core.llm_router import llm_router
from app.services.llm.concurrency import llm_concurrency


@dataclass(frozen=True)
class GLMBatchPlan:
    task_type: str
    model_key: str
    mode: str
    queue: str
    reason: str


@dataclass(frozen=True)
class GLMBatchDispatchDecision:
    task_type: str
    should_enqueue: bool
    batch_model_key: str
    spillover_model_key: str | None
    execution_mode: str
    queue: str
    reason: str


class GLMBatchService:
    """管理适合进入 GLM batch 的任务与模型模式选择。"""

    def __init__(self) -> None:
        self.queue_name = settings.GLM_BATCH_QUEUE

    def get_runtime_status(self) -> dict[str, Any]:
        runtime = llm_concurrency.get_provider_runtime_state("zhipu_coding")
        runtime["queue"] = self.queue_name
        return runtime

    def get_runtime_limit(self) -> int:
        return llm_concurrency.get_runtime_limit("zhipu_coding")

    def _select_spillover_model(self, *, task_type: str, use_thinking: bool) -> str:
        if task_type == "capsule_generation":
            if use_thinking:
                selection = llm_router.select_model(AgentRole.DEEP_ANALYST, TaskType.DEEP_REASONING)
            else:
                selection = llm_router.select_model(AgentRole.GENERATION, TaskType.STANDARD_RESPONSE)
        else:
            if use_thinking:
                selection = llm_router.select_model(AgentRole.ERROR_ANALYST, TaskType.ERROR_DIAGNOSIS)
            else:
                selection = llm_router.select_model(AgentRole.PROBLEM_SOLVER, TaskType.STANDARD_RESPONSE)
        return selection.model_key

    def evaluate_dispatch(
        self,
        *,
        plan: GLMBatchPlan,
        celery_status: dict[str, Any] | None,
    ) -> GLMBatchDispatchDecision:
        runtime = self.get_runtime_status()
        status = celery_status or {}
        queue_active = int(status.get("queue_active_tasks") or 0)
        queue_reserved = int(status.get("queue_reserved_tasks") or 0)
        queue_workers = int(status.get("queue_worker_count") or 0)
        queue_healthy = status.get("status") == "healthy"
        runtime_limit = max(1, int(runtime.get("current_limit") or self.get_runtime_limit() or 1))
        backlog_threshold = max(1, runtime_limit * int(settings.GLM_BATCH_SPILLOVER_BACKLOG_FACTOR or 2))
        queue_saturated = queue_active >= runtime_limit
        backlog_heavy = queue_reserved >= backlog_threshold
        cooldown_active = bool(runtime.get("cooldown_active"))
        use_thinking = plan.mode == "thinking"

        should_enqueue = (
            settings.GLM_BATCH_ENABLED
            and queue_healthy
            and queue_workers > 0
            and not queue_saturated
            and not backlog_heavy
            and not cooldown_active
        )
        if not settings.GLM_BATCH_SPILLOVER_ENABLED and not should_enqueue:
            spillover_model_key = None
        else:
            spillover_model_key = None if should_enqueue else self._select_spillover_model(
                task_type=plan.task_type,
                use_thinking=use_thinking,
            )

        reasons: list[str] = [plan.reason]
        if not queue_healthy:
            reasons.append("queue_unhealthy")
        if queue_workers <= 0:
            reasons.append("no_glm_batch_worker")
        if queue_saturated:
            reasons.append(f"queue_active={queue_active}>=runtime_limit={runtime_limit}")
        if backlog_heavy:
            reasons.append(f"queue_reserved={queue_reserved}>=backlog_threshold={backlog_threshold}")
        if cooldown_active:
            reasons.append("runtime_cooldown_active")

        return GLMBatchDispatchDecision(
            task_type=plan.task_type,
            should_enqueue=should_enqueue,
            batch_model_key=plan.model_key,
            spillover_model_key=spillover_model_key,
            execution_mode="glm_batch" if should_enqueue else "standard_spillover",
            queue=plan.queue,
            reason="; ".join(reasons),
        )

    def plan_capsule_generation(
        self,
        depth_preference: float,
        curiosity_preference: float,
        requested_count: int,
        generation_type: str,
    ) -> GLMBatchPlan:
        use_thinking = (
            depth_preference >= settings.GLM_BATCH_THINKING_DEPTH_THRESHOLD
            and requested_count <= 2
        ) or (
            depth_preference >= 0.6
            and curiosity_preference >= 0.8
            and generation_type in {"manual", "weekly", "push_triggered"}
        )

        # 通过路由器选模型（支持健康感知和 env 覆盖）
        _task = TaskType.DEEP_REASONING if use_thinking else TaskType.STANDARD_RESPONSE
        _role = AgentRole.DEEP_ANALYST if use_thinking else AgentRole.GENERATION
        _selection = llm_router.select_model(_role, _task, force_tier=ModelTier.GLM_BATCH)
        model_key = _selection.model_key
        reason = (
            f"depth={depth_preference:.2f}, curiosity={curiosity_preference:.2f}, "
            f"requested_count={requested_count}, generation_type={generation_type}, "
            f"router={_selection.reason}"
        )
        return GLMBatchPlan(
            task_type="capsule_generation",
            model_key=model_key,
            mode="thinking" if use_thinking else "non_thinking",
            queue=self.queue_name,
            reason=reason,
        )

    def decide_capsule_dispatch(
        self,
        *,
        depth_preference: float,
        curiosity_preference: float,
        requested_count: int,
        generation_type: str,
        celery_status: dict[str, Any] | None,
    ) -> GLMBatchDispatchDecision:
        plan = self.plan_capsule_generation(
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            requested_count=requested_count,
            generation_type=generation_type,
        )
        return self.evaluate_dispatch(plan=plan, celery_status=celery_status)

    def plan_cognitive_analysis(
        self,
        severity: int,
        context_tags: dict[str, Any] | None = None,
        error_tags: list[str] | None = None,
    ) -> GLMBatchPlan:
        tag_count = len(error_tags or [])
        has_complex_context = bool(context_tags and len(context_tags) >= 3)
        use_thinking = (
            severity >= settings.GLM_BATCH_THINKING_SEVERITY_THRESHOLD
            or tag_count >= 3
            or has_complex_context
        )
        # 通过路由器选模型（支持健康感知和 env 覆盖）
        _task = TaskType.ERROR_DIAGNOSIS if use_thinking else TaskType.STANDARD_RESPONSE
        _role = AgentRole.ERROR_ANALYST if use_thinking else AgentRole.PROBLEM_SOLVER
        _selection = llm_router.select_model(_role, _task, force_tier=ModelTier.GLM_BATCH)
        model_key = _selection.model_key
        reason = (
            f"severity={severity}, tag_count={tag_count}, "
            f"complex_context={has_complex_context}, "
            f"router={_selection.reason}"
        )
        return GLMBatchPlan(
            task_type="cognitive_analysis",
            model_key=model_key,
            mode="thinking" if use_thinking else "non_thinking",
            queue=self.queue_name,
            reason=reason,
        )

    def decide_cognitive_dispatch(
        self,
        *,
        severity: int,
        context_tags: dict[str, Any] | None = None,
        error_tags: list[str] | None = None,
        celery_status: dict[str, Any] | None,
    ) -> GLMBatchDispatchDecision:
        plan = self.plan_cognitive_analysis(
            severity=severity,
            context_tags=context_tags,
            error_tags=error_tags,
        )
        return self.evaluate_dispatch(plan=plan, celery_status=celery_status)

    def enqueue_capsule_generation(
        self,
        user_id: UUID,
        depth_preference: float,
        curiosity_preference: float,
        generation_type: str,
        requested_count: int,
        job_id: UUID | None = None,
    ):
        plan = self.plan_capsule_generation(
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            requested_count=requested_count,
            generation_type=generation_type,
        )
        logger.info(f"[GLMBatch] enqueue capsule_generation user={user_id} model={plan.model_key} mode={plan.mode} {plan.reason}")
        return celery_app.send_task(
            "generate_capsules_batch",
            args=(
                str(user_id),
                depth_preference,
                curiosity_preference,
                generation_type,
                requested_count,
                plan.model_key,
                "glm_batch",
                str(job_id) if job_id else None,
            ),
            queue=plan.queue,
        )

    def enqueue_cognitive_analysis(
        self,
        user_id: UUID,
        fragment_id: UUID,
        severity: int,
        context_tags: dict[str, Any] | None = None,
        error_tags: list[str] | None = None,
    ):
        plan = self.plan_cognitive_analysis(
            severity=severity,
            context_tags=context_tags,
            error_tags=error_tags,
        )
        logger.info(f"[GLMBatch] enqueue cognitive_analysis fragment={fragment_id} model={plan.model_key} mode={plan.mode} {plan.reason}")
        return celery_app.send_task(
            "analyze_cognitive_fragment_batch",
            args=(str(user_id), str(fragment_id), plan.model_key),
            queue=plan.queue,
        )


glm_batch_service = GLMBatchService()
