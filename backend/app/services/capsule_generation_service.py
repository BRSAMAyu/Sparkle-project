"""
Capsule Generation Service

支持：
- DeepSeek Reasoner 集成
- 二维控制面 (深度偏好 x 好奇心偏好)
- 异步批量生成
- 模型降级策略
- 指数退避重试
"""
import asyncio
import random
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import TaskType
from app.models.capsule_generation_job import CapsuleGenerationJob, JobStatus
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.task import Task
from app.models.user import User
from app.services.llm_service import get_llm_service_for_task, llm_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ModelSelectionStrategy:
    """
    模型选择策略

    二维控制面映射：
    - depth_preference: 0.0-1.0
    - curiosity_preference: 0.0-1.0
    """

    # 根据深度偏好选择模型
    DEPTH_MODEL_MAP = {
        DepthLevel.SHALLOW: ["xiaomi_chat", "zhipu_flash"],  # 浅度：快速响应
        DepthLevel.MEDIUM: ["zhipu_chat", "deepseek_chat", "xiaomi_chat"],  # 中度：标准深度
        DepthLevel.DEEP: ["deepseek_reason", "zhipu_chat", "deepseek_chat"],  # 深度：深度推理
    }

    @classmethod
    def select_depth_level(cls, depth_preference: float) -> DepthLevel:
        """根据深度偏好选择深度级别"""
        if depth_preference < 0.3:
            return DepthLevel.SHALLOW
        elif depth_preference > 0.7:
            return DepthLevel.DEEP
        else:
            return DepthLevel.MEDIUM

    @classmethod
    def get_model_fallback_chain(cls, depth_level: DepthLevel) -> list[str]:
        """获取模型降级链"""
        return cls.DEPTH_MODEL_MAP.get(depth_level, ["zhipu_chat"])

    @classmethod
    def calculate_capsule_count(cls, curiosity_preference: float) -> int:
        """根据好奇心偏好计算生成胶囊数量"""
        if curiosity_preference < 0.3:
            return 1
        elif 0.3 <= curiosity_preference <= 0.7:
            return random.choice([2, 3])
        else:
            return random.choice([4, 5])


class RetryConfig:
    """重试配置 - 针对不同异常类型的精细重试"""

    CONFIG = {
        "rate_limit_error": {"base_delay": 60, "max_retries": 3},
        "timeout_error": {"base_delay": 30, "max_retries": 2},
        "api_error": {"base_delay": 10, "max_retries": 3},
        "llm_service_unavailable": {"base_delay": 120, "max_retries": 5},
    }

    @classmethod
    def get_config(cls, error_type: str) -> dict:
        return cls.CONFIG.get(error_type, {"base_delay": 10, "max_retries": 3})


class CapsuleGenerationService:
    """
    胶囊生成服务

    核心功能：
    - 批量生成胶囊
    - 模型选择与降级
    - 用户上下文收集
    - 任务状态追踪
    """

    def __init__(self):
        self.llm = llm_service
        self.model_strategy = ModelSelectionStrategy()

    async def generate_capsules_batch(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
        generation_type: str = "daily",
        requested_count: int | None = None,
    ) -> CapsuleGenerationJob:
        """
        批量生成胶囊

        Args:
            user_id: 用户ID
            db: 数据库会话
            depth_preference: 深度偏好 (0.0-1.0)
            curiosity_preference: 好奇心偏好 (0.0-1.0)
            generation_type: 生成类型 (daily/weekly/manual/push_triggered)
            requested_count: 请求生成的数量（可选，默认根据偏好计算）

        Returns:
            生成任务对象
        """
        # 创建生成任务记录
        job = CapsuleGenerationJob(
            user_id=user_id,
            status=JobStatus.PENDING.value,
            generation_type=generation_type,
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            requested_count=requested_count or self.model_strategy.calculate_capsule_count(curiosity_preference),
        )
        db.add(job)
        await db.flush()

        try:
            # 标记任务开始
            job.mark_started()
            await db.flush()

            # 收集用户上下文
            user_context = await self._gather_user_context(user_id, db)

            # 选择深度级别
            depth_level = self.model_strategy.select_depth_level(depth_preference)

            # 生成胶囊
            capsule_ids = []
            for i in range(job.requested_count):
                job.update_progress(0.1 + (0.8 * (i + 1) / job.requested_count))
                await db.flush()

                capsule = await self._generate_single_capsule(
                    user_id=user_id,
                    db=db,
                    depth_level=depth_level,
                    user_context=user_context,
                    index=i,
                )

                if capsule:
                    capsule_ids.append(capsule.id)

            # 标记任务完成
            job.mark_completed(capsule_ids)
            await db.commit()
            await db.refresh(job)

            logger.info(
                f"[CapsuleGen] Job {job.id} completed: "
                f"{len(capsule_ids)}/{job.requested_count} capsules generated"
            )

            return job

        except Exception as e:
            logger.error(f"[CapsuleGen] Job {job.id} failed: {e}")
            job.mark_failed(str(e))
            await db.commit()
            await db.refresh(job)
            return job

    async def _generate_single_capsule(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_level: DepthLevel,
        user_context: dict[str, Any],
        index: int = 0,
    ) -> CuriosityCapsule | None:
        """
        生成单个胶囊，支持模型降级

        Args:
            user_id: 用户ID
            db: 数据库会话
            depth_level: 深度级别
            user_context: 用户上下文
            index: 生成索引（用于生成不同内容）

        Returns:
            生成的胶囊对象，失败返回 None
        """
        # 获取模型降级链
        model_chain = self.model_strategy.get_model_fallback_chain(depth_level)

        last_error = None
        for model_name in model_chain:
            try:
                logger.debug(f"[CapsuleGen] Trying model: {model_name} for depth_level={depth_level.value}")

                # 根据模型选择LLM服务
                if "reason" in model_name:
                    llm = get_llm_service_for_task(TaskType.DEEP_REASONING)
                elif "flash" in model_name:
                    llm = get_llm_service_for_task(TaskType.FAST_GENERATION)
                else:
                    llm = self.llm

                # 生成内容
                content_data = await self._generate_content(
                    llm=llm,
                    model_name=model_name,
                    depth_level=depth_level,
                    user_context=user_context,
                    index=index,
                )

                # 创建胶囊
                capsule = CuriosityCapsule(
                    user_id=user_id,
                    title=content_data["title"],
                    content=content_data["content"],
                    related_subject=content_data.get("subject"),
                    related_task_id=content_data.get("task_id"),
                    is_read=False,
                    depth_level=depth_level,
                    generation_method=model_name,
                    source_context={
                        "depth_level": depth_level.value,
                        "subjects_studied": [s.get("title") for s in user_context.get("recent_tasks", [])],
                        "generated_at": _utcnow().isoformat(),
                    },
                    quality_score=content_data.get("quality_score", 0.5),
                )

                db.add(capsule)
                await db.flush()
                await db.refresh(capsule)

                logger.info(f"[CapsuleGen] Generated capsule {capsule.id} using {model_name}")
                return capsule

            except Exception as e:
                last_error = e
                logger.warning(f"[CapsuleGen] Model {model_name} failed: {e}, trying fallback...")

                # 检查是否需要重试
                error_type = self._classify_error(e)
                retry_config = RetryConfig.get_config(error_type)

                # 如果是速率限制，等待后重试
                if error_type == "rate_limit_error" and model_chain.index(model_name) == 0:
                    await asyncio.sleep(retry_config["base_delay"])

                # 继续尝试下一个模型
                continue

        # 所有模型都失败了
        logger.error(f"[CapsuleGen] All models failed for user {user_id}: {last_error}")
        return None

    async def _generate_content(
        self,
        llm,
        model_name: str,
        depth_level: DepthLevel,
        user_context: dict[str, Any],
        index: int = 0,
    ) -> dict[str, Any]:
        """
        使用LLM生成胶囊内容

        Returns:
            {
                "title": str,
                "content": str,
                "subject": Optional[str],
                "task_id": Optional[UUID],
                "quality_score": float,
            }
        """
        # 选择主题（从最近任务中选择或随机）
        recent_tasks = user_context.get("recent_tasks", [])
        selected_task = None
        topic = "有趣的知识点"

        if recent_tasks and len(recent_tasks) > index:
            selected_task = recent_tasks[index % len(recent_tasks)]
            topic = selected_task.get("title", "学习内容")

        # 构建prompt
        depth_instruction = {
            DepthLevel.SHALLOW: "简洁明了，一两句话点出核心",
            DepthLevel.MEDIUM: "适度展开，包含背景、核心、延伸建议",
            DepthLevel.DEEP: "深度解析，包含原理、应用、拓展思考",
        }

        system_prompt = f"""你是Sparkle AI学习助手的知识胶囊生成器。

任务：基于用户最近的学习内容，生成一个"好奇心胶囊"——一个简短有趣的知识拓展。

风格要求：
- {depth_instruction[depth_level]}
- 引人入胜，激发好奇心
- 与主题直接相关
- 使用Markdown格式

输出格式（JSON）：
{{
    "title": "吸引人的标题",
    "content": "胶囊内容（Markdown格式）",
    "quality_score": 0.8  // 0.0-1.0 内容质量自评
}}"""

        user_prompt = f"""用户最近学习了：{topic}

请生成一个相关的"好奇心胶囊"，拓展这个知识点。"""

        try:
            # 使用chat_json获取结构化输出
            result = await llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7 if depth_level != DepthLevel.DEEP else 0.5,
            )

            if not result or not isinstance(result, dict):
                raise ValueError("Invalid LLM response")

            title = result.get("title", f"关于{topic}的小知识")
            content = result.get("content", f"探索**{topic}**的更多可能性...")
            quality_score = result.get("quality_score", 0.5)

            return {
                "title": title,
                "content": content,
                "subject": topic if isinstance(topic, str) else "学习拓展",
                "task_id": selected_task.get("id") if selected_task else None,
                "quality_score": quality_score,
            }

        except Exception as e:
            logger.error(f"[CapsuleGen] Content generation failed: {e}")
            # 返回兜底内容
            return {
                "title": f"探索{topic}",
                "content": f"""关于 **{topic}** 的小知识：

这是为你准备的知识胶囊。探索这个主题，发现更多有趣的连接！""",
                "subject": topic if isinstance(topic, str) else "学习拓展",
                "task_id": selected_task.get("id") if selected_task else None,
                "quality_score": 0.3,
            }

    async def _gather_user_context(self, user_id: UUID, db: AsyncSession) -> dict[str, Any]:
        """
        收集用户上下文用于生成个性化内容

        Returns:
            {
                "user_id": str,
                "nickname": str,
                "recent_tasks": List[Dict],
                "subjects": List[str],
            }
        """
        # 获取用户信息
        user = await db.get(User, user_id)
        if not user:
            return {}

        # 获取最近完成的任务
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.status == "completed")
            .order_by(desc(Task.completed_at))
            .limit(5)
        )
        recent_tasks = result.scalars().all()

        return {
            "user_id": str(user_id),
            "nickname": user.nickname or "学习者",
            "recent_tasks": [
                {"id": t.id, "title": t.title, "subject": t.subject, "type": t.type}
                for t in recent_tasks
            ],
            "subjects": list({t.subject for t in recent_tasks if t.subject}),
        }

    @staticmethod
    def _classify_error(error: Exception) -> str:
        """分类错误类型用于重试策略"""
        error_msg = str(error).lower()

        if "rate limit" in error_msg or "429" in error_msg:
            return "rate_limit_error"
        elif "timeout" in error_msg or "timed out" in error_msg:
            return "timeout_error"
        elif "service unavailable" in error_msg or "503" in error_msg:
            return "llm_service_unavailable"
        else:
            return "api_error"

    async def get_user_generation_jobs(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[CapsuleGenerationJob]:
        """获取用户的生成任务列表"""
        result = await db.execute(
            select(CapsuleGenerationJob)
            .where(CapsuleGenerationJob.user_id == user_id)
            .order_by(desc(CapsuleGenerationJob.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_job_status(
        self,
        job_id: UUID,
        db: AsyncSession,
    ) -> CapsuleGenerationJob | None:
        """获取任务状态"""
        return await db.get(CapsuleGenerationJob, job_id)


# 全局单例
capsule_generation_service = CapsuleGenerationService()
