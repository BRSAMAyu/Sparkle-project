"""
Capsule Generation Service

支持：
- 二维偏好控制（深度 x 好奇心）
- GLM batch / 在线模式统一执行
- 显式模型主备链
- 思考 / 非思考模式分流
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capsule_generation_job import CapsuleGenerationJob, JobStatus
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.llm_service import get_llm_service_for_specific_model


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class CapsuleExecutionPlan:
    primary_model: str
    fallback_models: list[str]
    depth_level: DepthLevel
    thinking_mode: bool
    execution_mode: str


class ModelSelectionStrategy:
    """根据用户偏好和执行模式为胶囊生成选择模型计划。"""

    _BATCH_NON_THINKING_MODELS = [
        "glm_4_5_air_batch",
        "glm_4_6_batch",
        "glm_4_7_no_thinking",
    ]
    _BATCH_THINKING_MODELS = [
        "glm_4_7_thinking",
        "glm_4_7_no_thinking",
        "glm_4_6_batch",
    ]

    @staticmethod
    def select_depth_level(depth_preference: float) -> DepthLevel:
        if depth_preference < 0.3:
            return DepthLevel.SHALLOW
        if depth_preference > 0.7:
            return DepthLevel.DEEP
        return DepthLevel.MEDIUM

    @staticmethod
    def calculate_capsule_count(curiosity_preference: float) -> int:
        if curiosity_preference < 0.3:
            return 1
        if curiosity_preference <= 0.7:
            return random.choice([2, 3])
        return random.choice([4, 5])

    @classmethod
    def build_execution_plan(
        cls,
        depth_preference: float,
        curiosity_preference: float,
        generation_type: str,
        execution_mode: str,
        requested_count: int,
        model_key: str | None = None,
    ) -> CapsuleExecutionPlan:
        depth_level = cls.select_depth_level(depth_preference)
        explicit_mode = cls._normalize_explicit_model(model_key)
        if explicit_mode is not None:
            return CapsuleExecutionPlan(
                primary_model=model_key or explicit_mode[0],
                fallback_models=explicit_mode[1],
                depth_level=depth_level,
                thinking_mode=explicit_mode[2],
                execution_mode=execution_mode,
            )

        use_thinking = depth_level == DepthLevel.DEEP and requested_count <= 2
        if not use_thinking:
            use_thinking = (
                depth_preference >= 0.65
                and curiosity_preference >= 0.8
                and generation_type in {"manual", "weekly", "push_triggered"}
            )

        if use_thinking:
            if execution_mode == "glm_batch":
                return CapsuleExecutionPlan(
                    primary_model="glm_4_7_thinking",
                    fallback_models=["glm_4_7_no_thinking", "glm_4_6_batch"],
                    depth_level=depth_level,
                    thinking_mode=True,
                    execution_mode=execution_mode,
                )
            return CapsuleExecutionPlan(
                primary_model="glm_4_7_thinking",
                fallback_models=["glm_4_7_flash_thinking", "deepseek_reason"],
                depth_level=depth_level,
                thinking_mode=True,
                execution_mode=execution_mode,
            )

        if execution_mode == "glm_batch":
            if depth_level == DepthLevel.SHALLOW:
                primary = "glm_4_5_air_batch"
                fallbacks = ["glm_4_6_batch", "glm_4_7_no_thinking"]
            elif depth_level == DepthLevel.MEDIUM:
                primary = "glm_4_6_batch"
                fallbacks = ["glm_4_5_air_batch", "glm_4_7_no_thinking"]
            else:
                primary = "glm_4_7_no_thinking"
                fallbacks = ["glm_4_6_batch", "glm_4_5_air_batch"]
            return CapsuleExecutionPlan(
                primary_model=primary,
                fallback_models=fallbacks,
                depth_level=depth_level,
                thinking_mode=False,
                execution_mode=execution_mode,
            )

        if depth_level == DepthLevel.SHALLOW:
            primary = "glm_4_7_flash_no_thinking"
            fallbacks = ["glm_4_7_no_thinking", "deepseek_chat"]
        else:
            primary = "glm_4_7_no_thinking"
            fallbacks = ["glm_4_7_flash_no_thinking", "deepseek_chat"]

        return CapsuleExecutionPlan(
            primary_model=primary,
            fallback_models=fallbacks,
            depth_level=depth_level,
            thinking_mode=False,
            execution_mode=execution_mode,
        )

    @staticmethod
    def _normalize_explicit_model(model_key: str | None) -> tuple[str, list[str], bool] | None:
        if not model_key:
            return None
        if model_key == "glm_4_5_air_batch":
            return model_key, ["glm_4_6_batch", "glm_4_7_no_thinking"], False
        if model_key == "glm_4_6_batch":
            return model_key, ["glm_4_5_air_batch", "glm_4_7_no_thinking"], False
        if model_key == "glm_4_7_thinking":
            return model_key, ["glm_4_7_no_thinking", "glm_4_6_batch"], True
        if model_key == "glm_4_7_flash_thinking":
            return model_key, ["glm_4_7_thinking", "deepseek_reason"], True
        if model_key == "glm_4_7_no_thinking":
            return model_key, ["glm_4_6_batch", "glm_4_5_air_batch"], False
        if model_key == "glm_4_7_flash_no_thinking":
            return model_key, ["glm_4_7_no_thinking", "deepseek_chat"], False
        if model_key == "deepseek_reason":
            return model_key, ["glm_4_7_thinking", "glm_4_7_flash_thinking"], True
        if model_key == "deepseek_chat":
            return model_key, ["glm_4_7_no_thinking", "glm_4_7_flash_no_thinking"], False
        return model_key, [], model_key.endswith("_thinking") and "no_thinking" not in model_key


class CapsuleGenerationService:
    """生成好奇心胶囊，并记录完整执行计划和回退结果。"""

    def __init__(self) -> None:
        self.model_strategy = ModelSelectionStrategy()

    async def generate_capsules_batch(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
        generation_type: str = "daily",
        requested_count: int | None = None,
        model_key: str | None = None,
        execution_mode: str = "online",
        existing_job_id: UUID | None = None,
    ) -> CapsuleGenerationJob:
        requested_total = requested_count or self.model_strategy.calculate_capsule_count(curiosity_preference)
        execution_plan = self.model_strategy.build_execution_plan(
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            generation_type=generation_type,
            execution_mode=execution_mode,
            requested_count=requested_total,
            model_key=model_key,
        )

        if existing_job_id is not None:
            job = await db.get(CapsuleGenerationJob, existing_job_id)
            if job is None:
                raise ValueError(f"Capsule generation job {existing_job_id} not found")
            if job.user_id != user_id:
                raise ValueError("Capsule generation job does not belong to requested user")
            job.status = JobStatus.PENDING.value
            job.generation_type = generation_type
            job.depth_preference = depth_preference
            job.curiosity_preference = curiosity_preference
            job.requested_count = requested_total
            job.actual_count = None
            job.capsule_ids = None
            job.progress = 0.0
            job.error_message = None
            job.duration_ms = None
            job.model_used = execution_plan.primary_model
            job.started_at = None
            job.completed_at = None
            db.add(job)
            await db.flush()
        else:
            job = CapsuleGenerationJob(
                user_id=user_id,
                status=JobStatus.PENDING.value,
                generation_type=generation_type,
                depth_preference=depth_preference,
                curiosity_preference=curiosity_preference,
                requested_count=requested_total,
                model_used=execution_plan.primary_model,
            )
            db.add(job)
            await db.flush()

        try:
            job.mark_started()
            await db.flush()

            user_context = await self._gather_user_context(
                user_id=user_id,
                db=db,
                depth_preference=depth_preference,
                curiosity_preference=curiosity_preference,
                generation_type=generation_type,
                execution_mode=execution_mode,
            )

            capsule_ids: list[UUID] = []
            for index in range(job.requested_count):
                progress = 0.1 + (0.8 * (index + 1) / job.requested_count)
                job.update_progress(progress)
                await db.flush()

                capsule = await self._generate_single_capsule(
                    user_id=user_id,
                    db=db,
                    execution_plan=execution_plan,
                    user_context=user_context,
                    index=index,
                )
                if capsule is not None:
                    capsule_ids.append(capsule.id)

            job.mark_completed(capsule_ids)
            await db.commit()
            await db.refresh(job)
            logger.info(
                "[CapsuleGen] Job {} completed: {}/{} capsules, mode={}, model={}",
                job.id,
                len(capsule_ids),
                job.requested_count,
                execution_plan.execution_mode,
                execution_plan.primary_model,
            )
            return job
        except Exception as exc:
            logger.error("[CapsuleGen] Job {} failed: {}", job.id, exc)
            job.mark_failed(str(exc))
            await db.commit()
            await db.refresh(job)
            return job

    async def create_generation_job(
        self,
        *,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float,
        curiosity_preference: float,
        generation_type: str,
        requested_count: int,
        model_used: str | None = None,
    ) -> CapsuleGenerationJob:
        job = CapsuleGenerationJob(
            user_id=user_id,
            status=JobStatus.PENDING.value,
            generation_type=generation_type,
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            requested_count=requested_count,
            model_used=model_used,
            progress=0.0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def expire_stale_jobs(
        self,
        *,
        user_id: UUID,
        db: AsyncSession,
        older_than_seconds: int = 300,
    ) -> int:
        cutoff = _utcnow() - timedelta(seconds=older_than_seconds)
        result = await db.execute(
            select(CapsuleGenerationJob).where(
                CapsuleGenerationJob.user_id == user_id,
                CapsuleGenerationJob.status.in_([JobStatus.PENDING.value, JobStatus.GENERATING.value]),
                CapsuleGenerationJob.created_at < cutoff,
            )
        )
        jobs = list(result.scalars().all())
        if not jobs:
            return 0

        for job in jobs:
            job.mark_failed("胶囊生成队列处理超时，已自动切换到即时生成。")
            if job.started_at is None:
                job.progress = 0.0
            db.add(job)
        await db.commit()
        return len(jobs)

    async def _generate_single_capsule(
        self,
        user_id: UUID,
        db: AsyncSession,
        execution_plan: CapsuleExecutionPlan,
        user_context: dict[str, Any],
        index: int = 0,
    ) -> CuriosityCapsule | None:
        model_chain = [execution_plan.primary_model, *execution_plan.fallback_models]
        last_error: Exception | None = None

        for model_name in model_chain:
            try:
                content_data = await self._generate_content(
                    model_name=model_name,
                    depth_level=execution_plan.depth_level,
                    thinking_mode=self._is_thinking_model(model_name),
                    user_context=user_context,
                    index=index,
                )

                personalization_context = self._build_personalization_context(user_context)
                capsule = CuriosityCapsule(
                    user_id=user_id,
                    title=content_data["title"],
                    content=content_data["content"],
                    related_subject=content_data.get("subject"),
                    related_task_id=content_data.get("task_id"),
                    is_read=False,
                    depth_level=execution_plan.depth_level,
                    generation_method=model_name,
                    source_context={
                        "depth_level": execution_plan.depth_level.value,
                        "execution_mode": execution_plan.execution_mode,
                        "thinking_mode": self._is_thinking_model(model_name),
                        "primary_model": execution_plan.primary_model,
                        "model_chain": model_chain,
                        "selected_model": model_name,
                        "subjects_studied": [s.get("title") for s in user_context.get("recent_tasks", [])],
                        "generated_at": _utcnow().isoformat(),
                        "dominant_pattern": user_context.get("dominant_pattern"),
                        "behavior_patterns": [
                            p.get("name") for p in user_context.get("behavior_patterns", []) if p.get("name")
                        ],
                        "profile_preferences": {
                            "depth_preference": user_context.get("depth_preference"),
                            "curiosity_preference": user_context.get("curiosity_preference"),
                        },
                    },
                    personalization_context=personalization_context,
                    quality_score=content_data.get("quality_score", 0.5),
                )
                db.add(capsule)
                await db.flush()
                await db.refresh(capsule)
                logger.info("[CapsuleGen] Generated capsule {} using {}", capsule.id, model_name)
                return capsule
            except Exception as exc:
                last_error = exc
                logger.warning("[CapsuleGen] Model {} failed for user {}: {}", model_name, user_id, exc)

        logger.error("[CapsuleGen] All models failed for user {}: {}", user_id, last_error)
        return None

    def _build_personalization_context(self, user_context: dict[str, Any]) -> dict[str, Any] | None:
        patterns = user_context.get("behavior_patterns") or []
        if not patterns:
            return {
                "depth_preference": user_context.get("depth_preference"),
                "curiosity_preference": user_context.get("curiosity_preference"),
            }

        return {
            "depth_preference": user_context.get("depth_preference"),
            "curiosity_preference": user_context.get("curiosity_preference"),
            "based_on_patterns": [p.get("name") for p in patterns if p.get("name")],
            "dominant_pattern": user_context.get("dominant_pattern"),
            "confidence_scores": {
                p.get("name"): p.get("confidence")
                for p in patterns
                if p.get("name") and p.get("confidence") is not None
            },
        }

    def _build_personalized_prompt(
        self,
        user_context: dict[str, Any],
        depth_level: DepthLevel,
        thinking_mode: bool,
    ) -> str:
        depth_instruction = {
            DepthLevel.SHALLOW: "简洁明了，用很短篇幅点出最值得继续探索的一个角度。",
            DepthLevel.MEDIUM: "适度展开，讲清背景、关键点与下一步探索方向。",
            DepthLevel.DEEP: "深度解析，解释原理、迁移意义，以及可以继续思考的问题。",
        }
        curiosity_value = float(user_context.get("curiosity_preference") or 0.5)
        if curiosity_value < 0.35:
            exploration_instruction = "保持聚焦，只围绕当前学习主题做一步延伸。"
        elif curiosity_value > 0.75:
            exploration_instruction = "鼓励跨主题联想，加入一个意想不到但合理的连接点。"
        else:
            exploration_instruction = "在当前主题附近做中等幅度拓展。"

        mode_instruction = (
            "先充分思考结构与洞见，再输出最终 JSON。不要输出思考过程。"
            if thinking_mode
            else "直接输出高质量结果，不展开冗长推理。"
        )

        base_prompt = f"""你是 Sparkle AI 的好奇心胶囊生成器。

任务：基于用户最近的学习轨迹，生成一个短小但有价值的知识胶囊。

风格要求：
- {depth_instruction[depth_level]}
- {exploration_instruction}
- {mode_instruction}
- 内容必须自然，不能像解释自己在帮用户生成内容
- 使用 Markdown

输出格式（JSON）：
{{
  "title": "吸引人的标题",
  "content": "胶囊正文（Markdown）",
  "quality_score": 0.0
}}"""

        patterns = user_context.get("behavior_patterns") or []
        if patterns:
            hints: list[str] = []
            for pattern in patterns:
                name = pattern.get("name")
                solution_hint = pattern.get("solution_hint")
                if name == "Planning Optimism":
                    hints.append("用户容易低估时间，适合加入可执行的拆解或节奏提示。")
                elif name == "Focus Decay":
                    hints.append("用户近期专注力波动，适合给出轻量、能快速启动的切入点。")
                elif name == "Procrastination":
                    hints.append("用户有拖延倾向，内容应降低启动阻力。")
                elif name and solution_hint:
                    hints.append(f"结合模式「{name}」：{solution_hint}")
                elif name:
                    hints.append(f"结合模式「{name}」做个性化调整。")
            if hints:
                base_prompt += "\n\n个性化约束：\n" + "\n".join(f"- {hint}" for hint in hints)

        return base_prompt

    async def _generate_content(
        self,
        model_name: str,
        depth_level: DepthLevel,
        thinking_mode: bool,
        user_context: dict[str, Any],
        index: int = 0,
    ) -> dict[str, Any]:
        recent_tasks = user_context.get("recent_tasks", [])
        selected_task = None
        topic = "有趣的知识点"
        if recent_tasks:
            selected_task = recent_tasks[index % len(recent_tasks)]
            topic = selected_task.get("title", "学习内容")

        system_prompt = self._build_personalized_prompt(
            user_context=user_context,
            depth_level=depth_level,
            thinking_mode=thinking_mode,
        )
        user_prompt = f"""用户最近学习了：{topic}

请围绕这个主题生成一个相关的好奇心胶囊。"""

        llm = await get_llm_service_for_specific_model(model_name, agent_role="generation")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        temperature = 0.45 if thinking_mode or depth_level == DepthLevel.DEEP else 0.7

        try:
            if thinking_mode:
                result = await asyncio.wait_for(
                    llm.reason_json(messages=messages, temperature=temperature),
                    timeout=25.0,
                )
            else:
                result = await asyncio.wait_for(
                    llm.chat_json(messages=messages, temperature=temperature),
                    timeout=25.0,
                )
            if not result or not isinstance(result, dict):
                raise ValueError("Invalid LLM response")
            return {
                "title": result.get("title", f"关于 {topic} 的延伸思考"),
                "content": result.get("content", f"从 **{topic}** 再往前走一步，会看到更多联系。"),
                "subject": topic if isinstance(topic, str) else "学习拓展",
                "task_id": selected_task.get("id") if selected_task else None,
                "quality_score": float(result.get("quality_score", 0.5)),
            }
        except Exception as exc:
            logger.error("[CapsuleGen] Content generation failed with {}: {}", model_name, exc)
            return {
                "title": f"探索 {topic}",
                "content": f"""关于 **{topic}** 的一个延伸视角：

这个主题不仅关乎当前内容，也可能和你接下来要学的知识建立联系。""",
                "subject": topic if isinstance(topic, str) else "学习拓展",
                "task_id": selected_task.get("id") if selected_task else None,
                "quality_score": 0.3,
            }

    async def _gather_user_context(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
        generation_type: str = "daily",
        execution_mode: str = "online",
    ) -> dict[str, Any]:
        user = await db.get(User, user_id)
        if not user:
            return {}

        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.status == TaskStatus.COMPLETED)
            .order_by(desc(Task.completed_at))
            .limit(5)
        )
        recent_tasks = result.scalars().all()

        def _task_subject(task: Task) -> str | None:
            tags = task.tags if isinstance(task.tags, list) else []
            for tag in tags:
                if isinstance(tag, str) and tag.strip():
                    return tag.strip()
            return None

        from app.services.cognitive_service import CognitiveService

        cognitive_service = CognitiveService(db)
        patterns = await cognitive_service.get_user_patterns(user_id, min_confidence=0.6)

        return {
            "user_id": str(user_id),
            "nickname": user.nickname or "学习者",
            "depth_preference": depth_preference,
            "curiosity_preference": curiosity_preference,
            "generation_type": generation_type,
            "execution_mode": execution_mode,
            "recent_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "subject": _task_subject(t),
                    "type": t.type.value if hasattr(t.type, "value") else str(t.type),
                }
                for t in recent_tasks
            ],
            "subjects": list({subject for t in recent_tasks for subject in [_task_subject(t)] if subject}),
            "behavior_patterns": [
                {
                    "name": pattern.pattern_name,
                    "type": pattern.pattern_type,
                    "confidence": pattern.confidence_score,
                    "solution_hint": pattern.solution_text,
                }
                for pattern in patterns[:3]
            ],
            "dominant_pattern": patterns[0].pattern_name if patterns else None,
        }

    @staticmethod
    def _is_thinking_model(model_key: str) -> bool:
        return model_key.endswith("_thinking") and "no_thinking" not in model_key

    async def get_user_generation_jobs(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[CapsuleGenerationJob]:
        result = await db.execute(
            select(CapsuleGenerationJob)
            .where(CapsuleGenerationJob.user_id == user_id)
            .order_by(desc(CapsuleGenerationJob.created_at))
            .limit(limit)
        )
        return result.scalars().all()


capsule_generation_service = CapsuleGenerationService()
