from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger

from app.config import settings
from app.core.celery_app import celery_app


@dataclass(frozen=True)
class GLMBatchPlan:
    task_type: str
    model_key: str
    mode: str
    queue: str
    reason: str


class GLMBatchService:
    """管理适合进入 GLM batch 的任务与模型模式选择。"""

    def __init__(self) -> None:
        self.queue_name = settings.GLM_BATCH_QUEUE

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

        model_key = "glm_4_7_thinking" if use_thinking else "glm_4_7_no_thinking"
        reason = (
            f"depth={depth_preference:.2f}, curiosity={curiosity_preference:.2f}, "
            f"requested_count={requested_count}, generation_type={generation_type}"
        )
        return GLMBatchPlan(
            task_type="capsule_generation",
            model_key=model_key,
            mode="thinking" if use_thinking else "non_thinking",
            queue=self.queue_name,
            reason=reason,
        )

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
        model_key = "glm_4_7_thinking" if use_thinking else "glm_4_7_no_thinking"
        reason = (
            f"severity={severity}, tag_count={tag_count}, "
            f"complex_context={has_complex_context}"
        )
        return GLMBatchPlan(
            task_type="cognitive_analysis",
            model_key=model_key,
            mode="thinking" if use_thinking else "non_thinking",
            queue=self.queue_name,
            reason=reason,
        )

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
