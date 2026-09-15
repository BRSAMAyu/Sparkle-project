"""
Task Feedback Service

处理任务反馈，更新用户推断偏好
"""
from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.event_bus import event_bus
from app.event_publishers.srl_events import publish_srl_event
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService
from app.services.routing_profile_service import RoutingProfileService
from app.services.task_reflection_service import TaskReflectionService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TaskFeedbackService:
    """
    任务反馈服务

    核心功能：
    - 提交反馈
    - 验证任务状态（必须是COMPLETED）
    - 更新用户推断偏好
    """

    REMEDIAL_TRIGGER_CATEGORIES = {"unclear", "too_difficult"}
    TIME_PRESSURE_TRIGGER_CATEGORIES = {"too_long"}
    REMEDIAL_TEXT_MARKERS = (
        "不懂",
        "不理解",
        "搞不懂",
        "看不懂",
        "不会",
        "没思路",
        "太难",
        "confus",
        "don't understand",
        "do not understand",
    )
    TIME_PRESSURE_TEXT_MARKERS = ("没时间", "来不及", "时间不够", "太长", "做不完", "排不开")
    MAX_CONSECUTIVE_REMEDIAL_TASKS = 2

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)

    async def submit_feedback(
        self,
        user_id: UUID,
        task_id: UUID,
        completion_quality: int | None = None,
        feedback_text: str | None = None,
        category: str | None = None,
        stuck_point: str | None = None,
        effective_method: str | None = None,
        adjustment_intention: str | None = None,
    ) -> tuple[TaskFeedback, dict[str, Any] | None]:
        """
        提交任务反馈

        Args:
            user_id: 用户ID
            task_id: 任务ID
            completion_quality: 完成质量评分 (1-5)
            feedback_text: 用户文字反馈
            category: 反馈分类

        Returns:
            反馈对象
        """
        # 验证任务并获取任务状态快照
        task = await self._get_and_validate_task(task_id, user_id)
        task_snapshot = {
            "id": task.id,
            "user_id": task.user_id,
            "plan_id": task.plan_id,
            "title": task.title,
            "actual_minutes": task.actual_minutes,
        }

        # 检查是否已有反馈
        existing_feedback = await self._get_existing_feedback(user_id, task_id)

        if existing_feedback:
            # 更新现有反馈
            feedback = await self._update_feedback(
                existing_feedback,
                completion_quality,
                feedback_text,
                category,
            )
            logger.info(f"[TaskFeedback] Updated feedback for task {task_id}")
        else:
            # 创建新反馈
            feedback = await self._create_feedback(
                user_id,
                task_id,
                completion_quality,
                feedback_text,
                category,
                task,
            )
            logger.info(f"[TaskFeedback] Created new feedback for task {task_id}")

        await self.db.flush()
        feedback_snapshot = {
            "id": feedback.id,
            "category": feedback.category,
            "feedback_text": feedback.feedback_text,
        }

        # 计算偏好变化
        depth_delta, difficulty_delta = feedback.calculate_preference_deltas()
        feedback.inferred_depth_delta = depth_delta
        feedback.inferred_difficulty_delta = difficulty_delta

        # 更新用户推断偏好
        await self._update_inferred_preferences(user_id, depth_delta, difficulty_delta)

        # Adaptive replanning based on feedback signals
        if task_snapshot["plan_id"]:
            try:
                adaptive_replanner = AdaptiveReplanner(self.db, self.redis)
                await adaptive_replanner.on_task_feedback(
                    user_id=user_id,
                    plan_id=task_snapshot["plan_id"],
                    task_id=task_id,
                    category=feedback_snapshot["category"],
                    difficulty_delta=difficulty_delta,
                    feedback_text=feedback_snapshot["feedback_text"],
                )
            except Exception as e:
                logger.warning(f"[TaskFeedback] Adaptive replanning failed: {e}")

        try:
            await self._maybe_update_routing_profile_after_feedback(
                user_id=user_id,
                category=feedback_snapshot["category"],
                feedback_text=feedback_snapshot["feedback_text"],
            )
        except Exception as e:
            logger.warning(f"[TaskFeedback] Routing profile update skipped: {e}")

        reflection_prompt = None
        has_structured_reflection = any(
            str(value or "").strip()
            for value in (stuck_point, effective_method, adjustment_intention)
        )
        try:
            reflection_service = TaskReflectionService(self.db, self.redis)
            if has_structured_reflection:
                reflection_payload = await reflection_service.submit_reflection_answer(
                    user_id=user_id,
                    feedback_id=feedback.id,
                    selected_option=category,
                    free_text=feedback_text,
                    stuck_point=stuck_point,
                    effective_method=effective_method,
                    adjustment_intention=adjustment_intention,
                )
                prompt_value = reflection_payload.get("prompt")
                reflection_prompt = prompt_value if isinstance(prompt_value, dict) else None
            else:
                reflection_prompt = await reflection_service.maybe_enqueue_reflection_prompt(
                    user_id=user_id,
                    task=task,
                    feedback=feedback,
                    category=feedback_snapshot["category"],
                    time_spent_minutes=task_snapshot["actual_minutes"],
                )
        except Exception as e:
            logger.warning(f"[TaskFeedback] Reflection prompt generation failed: {e}")

        fail_safe_signal = self._classify_fail_safe_signal(
            feedback_snapshot["category"],
            feedback_snapshot["feedback_text"],
        )
        if task_snapshot["plan_id"] and fail_safe_signal:
            try:
                if fail_safe_signal == "knowledge_gap":
                    knowledge_gap = await self._record_knowledge_gap(
                        user_id=user_id,
                        task_snapshot=task_snapshot,
                        feedback_snapshot=feedback_snapshot,
                    )
                else:
                    knowledge_gap = self._build_fail_safe_gap(
                        task_snapshot=task_snapshot,
                        feedback_snapshot=feedback_snapshot,
                        signal_type=fail_safe_signal,
                    )
                await self._insert_remedial_task(
                    user_id=user_id,
                    plan_id=task_snapshot["plan_id"],
                    task_id=task_snapshot["id"],
                    knowledge_gap=knowledge_gap,
                    signal_type=fail_safe_signal,
                )
            except Exception as e:
                logger.warning(f"[TaskFeedback] Remedial task insertion skipped: {e}")

        await self.db.commit()
        await self.db.refresh(
            feedback,
            attribute_names=[
                "id",
                "user_id",
                "task_id",
                "completion_quality",
                "feedback_text",
                "category",
                "inferred_depth_delta",
                "inferred_difficulty_delta",
                "task_difficulty_snapshot",
                "task_type_snapshot",
                "actual_minutes_snapshot",
                "reflection_payload",
                "created_at",
                "updated_at",
            ],
        )

        await event_bus.publish(
            "task.feedback_submitted",
            {
                "event_type": "task.feedback_submitted",
                "user_id": str(user_id),
                "feedback_id": str(feedback.id),
                "task_id": str(task_id),
                "plan_id": str(task_snapshot["plan_id"]) if task_snapshot["plan_id"] else "",
                "category": feedback.category or "",
                "feedback_text": feedback.feedback_text or "",
            },
        )
        await publish_srl_event(
            user_id=user_id,
            trigger_event_type="task.feedback_submitted",
            evidence_id=str(feedback.id),
            metadata={"plan_id": str(task_snapshot["plan_id"]) if task_snapshot["plan_id"] else None},
        )

        return feedback, reflection_prompt

    def _is_knowledge_gap_signal(self, category: str | None, feedback_text: str | None) -> bool:
        normalized_category = str(category or "").strip().lower()
        if normalized_category in self.REMEDIAL_TRIGGER_CATEGORIES:
            return True
        haystack = str(feedback_text or "").strip().lower()
        return bool(haystack) and any(marker in haystack for marker in self.REMEDIAL_TEXT_MARKERS)

    def _classify_fail_safe_signal(self, category: str | None, feedback_text: str | None) -> str | None:
        if self._is_knowledge_gap_signal(category, feedback_text):
            return "knowledge_gap"
        normalized_category = str(category or "").strip().lower()
        if normalized_category in self.TIME_PRESSURE_TRIGGER_CATEGORIES:
            return "time_pressure"
        haystack = str(feedback_text or "").strip().lower()
        if bool(haystack) and any(marker in haystack for marker in self.TIME_PRESSURE_TEXT_MARKERS):
            return "time_pressure"
        return None

    def _build_fail_safe_gap(
        self,
        *,
        task_snapshot: dict[str, Any],
        feedback_snapshot: dict[str, Any],
        signal_type: str,
    ) -> dict[str, Any]:
        description = self._build_fail_safe_description(
            task_title=str(task_snapshot.get("title") or "当前任务"),
            feedback_text=str(feedback_snapshot.get("feedback_text") or "").strip(),
            signal_type=signal_type,
        )
        return {
            "id": f"fallback:{task_snapshot['id']}:{feedback_snapshot['id']}",
            "task_id": str(task_snapshot["id"]),
            "plan_id": str(task_snapshot["plan_id"]) if task_snapshot.get("plan_id") else None,
            "task_title": task_snapshot.get("title"),
            "description": description,
            "feedback_text": str(feedback_snapshot.get("feedback_text") or "").strip(),
            "category": feedback_snapshot.get("category"),
            "source": "task_feedback",
            "signal_type": signal_type,
            "created_at": _utcnow().isoformat(),
        }

    def _build_fail_safe_description(self, task_title: str, feedback_text: str, signal_type: str) -> str:
        if signal_type == "time_pressure":
            if feedback_text:
                return f"{task_title}: 时间不够，先压缩成最小保底版（{feedback_text[:60]}）"
            return f"{task_title}: 时间不够，先压缩成最小保底版"
        return self._build_knowledge_gap_description(task_title, feedback_text)

    async def _record_knowledge_gap(
        self,
        *,
        user_id: UUID,
        task_snapshot: dict[str, Any],
        feedback_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        explicit = dict(getattr(prefs, "explicit", {}) or {})
        existing = explicit.get("knowledge_gaps")
        gaps = list(existing) if isinstance(existing, list) else []
        feedback_text = str(feedback_snapshot.get("feedback_text") or "").strip()
        description = self._build_knowledge_gap_description(
            str(task_snapshot.get("title") or "当前任务"),
            feedback_text,
        )
        gap = {
            "id": f"kgap:{task_snapshot['id']}:{feedback_snapshot['id']}",
            "task_id": str(task_snapshot["id"]),
            "plan_id": str(task_snapshot["plan_id"]) if task_snapshot.get("plan_id") else None,
            "task_title": task_snapshot.get("title"),
            "description": description,
            "feedback_text": feedback_text,
            "category": feedback_snapshot.get("category"),
            "source": "task_feedback",
            "created_at": _utcnow().isoformat(),
        }
        deduped = [
            item
            for item in gaps
            if not (isinstance(item, dict) and item.get("task_id") == str(task_snapshot["id"]))
        ]
        deduped.append(gap)
        await ProfileWriteService(self.db, self.redis).set_explicit_preference(
            user_id=user_id,
            pref_key="knowledge_gaps",
            pref_value=deduped[-20:],
            evidence_refs=[{"type": "task_feedback", "id": str(feedback_snapshot["id"])}],
            confidence=0.8,
            source_type="task_feedback",
            source="task_feedback_service",
        )
        return gap

    def _build_knowledge_gap_description(self, task_title: str, feedback_text: str) -> str:
        if feedback_text:
            trimmed = feedback_text[:80]
            return f"{task_title}: {trimmed}"
        return f"{task_title}: 用户反馈该任务过难或不清楚"

    async def _insert_remedial_task(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        knowledge_gap: dict[str, Any],
        signal_type: str = "knowledge_gap",
    ) -> Task | None:
        task = await self._get_and_validate_task(task_id, user_id)
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.plan_id == plan_id)
            .order_by(Task.order_index.asc(), Task.created_at.asc())
        )
        plan_tasks = list(result.scalars().all())
        current_index = next((index for index, item in enumerate(plan_tasks) if item.id == task.id), -1)
        if current_index < 0:
            return None
        consecutive = 0
        for item in plan_tasks[current_index + 1 :]:
            if self._is_remedial_task(item):
                consecutive += 1
                continue
            break
        if consecutive >= self.MAX_CONSECUTIVE_REMEDIAL_TASKS:
            return None

        insert_order = int(task.order_index or 0) + 1
        await self.db.execute(
            update(Task)
            .where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.order_index >= insert_order,
            )
            .values(order_index=Task.order_index + 1)
        )
        guide_json = self._build_remedial_guide_json(
            task,
            knowledge_gap,
            signal_type=signal_type,
            consecutive_failures=consecutive,
        )
        extra_tags = []
        if signal_type == "time_pressure":
            extra_tags.extend(["time_boxed", "compressed_recovery"])
        if consecutive > 0:
            extra_tags.append("streak_fail_safe")
        remedial_task = Task(
            user_id=task.user_id,
            plan_id=task.plan_id,
            title=f"[补强] {knowledge_gap['description'][:80]}",
            type=TaskType.LEARNING,
            tags=[
                "remedial",
                "knowledge_gap",
                "scaffolded",
                "reduced_density",
                "sprint_fail_safe",
                *extra_tags,
                f"source_task:{task.id}",
            ],
            estimated_minutes=int(guide_json["time_estimate_minutes"]),
            difficulty=int(guide_json.get("difficulty", max(1, int(task.difficulty or 2) - 1))),
            energy_cost=1,
            guide_content=guide_json["objective"],
            guide_json=guide_json,
            ai_prompt=self._build_remedial_ai_prompt(task, knowledge_gap, guide_json),
            source_planning_session_id=task.source_planning_session_id,
            phase_index=task.phase_index,
            success_criteria=guide_json["success_criteria"],
            status=TaskStatus.PENDING,
            priority=max(int(task.priority or 0), 0) + 1,
            order_index=insert_order,
            due_date=task.due_date,
        )
        self.db.add(remedial_task)
        await self.db.flush()
        return remedial_task

    def _is_remedial_task(self, task: Task) -> bool:
        tags = [str(tag) for tag in (task.tags or [])]
        return task.title.startswith("[补强]") or "remedial" in tags

    def _build_remedial_guide_json(
        self,
        task: Task,
        knowledge_gap: dict[str, Any],
        *,
        signal_type: str = "knowledge_gap",
        consecutive_failures: int = 0,
    ) -> dict[str, Any]:
        description = str(knowledge_gap.get("description") or task.title)
        if signal_type == "time_pressure":
            minutes = 20 if consecutive_failures > 0 else min(25, max(15, int((task.estimated_minutes or 30) * 0.45)))
            return {
                "objective": f"把刚才没做完的内容压缩成今天能交付的最小保底版：{description}",
                "method_steps": [
                    "先把原任务缩成 1 个最小可见产出，例如 3 个保底点、1 道代表题或 1 张错因卡。",
                    "只回收最影响下一步的 1 个知识点或题型，不追完整章。",
                    "最后写一句下次从哪里继续，避免重新启动成本。",
                ],
                "time_estimate_minutes": minutes,
                "difficulty": 1,
                "success_criteria": "留下 1 个最小可检查产出，并明确下次从哪里继续。",
                "output_action": "完成 1 个最小保底产出，例如 3 个保底点、1 道代表题或 1 张错因卡。",
                "key_points": [description, "先保可继续推进的最小结果"],
                "common_mistakes": ["想一次补回全部进度，结果又把任务做得过重。"],
                "sprint_fail_safe": True,
                "density_adjustment": "minimum_viable",
                "scaffolding_mode": "time_boxed_minimum_viable",
                "micro_contract": "如果开始，就只保 1 个最小产出；没做完前，不允许再加第二个模块。",
                "fail_safe_rule": "今天不补整章，只回收下一步最需要的最小结果。",
            }

        minutes = min(30, max(15, int((task.estimated_minutes or 30) * 0.5)))
        if consecutive_failures > 0:
            minutes = min(minutes, 20)
        return {
            "objective": f"把刚才卡住的点补到能说清：{description}",
            "method_steps": [
                "用 5 分钟回看原任务里最卡的句子或题目，圈出一个具体问题。",
                "用自己的话写出这个知识点的定义、适用条件和一个反例。",
                "只做 1 道最小练习题或口头复述一次，确认不是只看懂答案；今天不额外加新难点。",
            ],
            "time_estimate_minutes": minutes,
            "difficulty": 1 if consecutive_failures > 0 else max(1, int(task.difficulty or 2) - 1),
            "success_criteria": "能不用资料解释这个卡点，并完成 1 个最小检查题。",
            "output_action": "补清 1 个卡点，并完成 1 个最小检查题。",
            "key_points": [description, "先补前置理解，再回到原任务"],
            "common_mistakes": ["直接重做原任务，但没有先定位到底是哪一个概念卡住。"],
            "sprint_fail_safe": True,
            "density_adjustment": "minimum_viable" if consecutive_failures > 0 else "reduced",
            "scaffolding_mode": "single_gap_minimal_check",
            "micro_contract": "如果开始，就只处理 1 个卡点；没讲清前，不切到第二个漏洞。",
            "fail_safe_rule": "今天不继续加新难点，只修当前最关键的一处理解断点。",
        }

    def _build_remedial_ai_prompt(
        self,
        task: Task,
        knowledge_gap: dict[str, Any],
        guide_json: dict[str, Any],
    ) -> str:
        return (
            f"【背景】我刚做任务「{task.title}」时卡住了。\n\n"
            f"【具体卡点】{knowledge_gap.get('description')}\n\n"
            f"【补强目标】{guide_json['objective']}\n"
            f"【输出动作】{guide_json.get('output_action')}\n"
            f"【完成标准】{guide_json['success_criteria']}\n\n"
            "【请帮我】\n"
            "1. 先判断我现在更需要概念补强还是时间压缩版保底任务\n"
            "2. 用最短路径给我一个更轻、更具体的补强动作\n"
            "3. 给我 1 道最小检查题，不要先给答案\n"
            "4. 不要继续加更难的新内容\n\n"
            "【风格要求】直接、具体、不要泛泛鼓励。"
        )

    async def _get_and_validate_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        获取并验证任务状态

        任务必须存在、属于用户、且状态为COMPLETED
        """
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == user_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != TaskStatus.COMPLETED:
            raise ValueError(f"Task {task_id} is not completed (status: {task.status.value})")

        return task

    async def _get_existing_feedback(self, user_id: UUID, task_id: UUID) -> TaskFeedback | None:
        """查询现有反馈"""
        result = await self.db.execute(
            select(TaskFeedback)
            .options(
                load_only(
                    TaskFeedback.id,
                    TaskFeedback.user_id,
                    TaskFeedback.task_id,
                    TaskFeedback.completion_quality,
                    TaskFeedback.feedback_text,
                    TaskFeedback.category,
                    TaskFeedback.inferred_depth_delta,
                    TaskFeedback.inferred_difficulty_delta,
                    TaskFeedback.task_difficulty_snapshot,
                    TaskFeedback.task_type_snapshot,
                    TaskFeedback.actual_minutes_snapshot,
                    TaskFeedback.created_at,
                    TaskFeedback.updated_at,
                )
            )
            .where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_feedback(
        self,
        user_id: UUID,
        task_id: UUID,
        completion_quality: int | None,
        feedback_text: str | None,
        category: str | None,
        task: Task,
    ) -> TaskFeedback:
        """创建新反馈"""
        feedback = TaskFeedback(
            user_id=user_id,
            task_id=task_id,
            completion_quality=completion_quality,
            feedback_text=feedback_text,
            category=category,
            # 保存任务状态快照
            task_difficulty_snapshot=task.difficulty,
            task_type_snapshot=task.type.value if task.type else None,
            actual_minutes_snapshot=task.actual_minutes,
        )
        self.db.add(feedback)
        return feedback

    async def _update_feedback(
        self,
        feedback: TaskFeedback,
        completion_quality: int | None,
        feedback_text: str | None,
        category: str | None,
    ) -> TaskFeedback:
        """更新现有反馈"""
        if completion_quality is not None:
            feedback.completion_quality = completion_quality
        if feedback_text is not None:
            feedback.feedback_text = feedback_text
        if category is not None:
            feedback.category = category
        return feedback

    async def _update_inferred_preferences(
        self,
        user_id: UUID,
        depth_delta: float | None,
        difficulty_delta: float | None,
    ):
        """
        更新用户推断偏好

        基于反馈计算出的偏好变化，更新用户的推断偏好设置
        """
        if depth_delta is None and difficulty_delta is None:
            return

        updates = {}
        if depth_delta is not None:
            # 平滑更新，避免剧烈波动
            updates["depth_preference"] = depth_delta * 0.1
        if difficulty_delta is not None:
            updates["task_difficulty_preference"] = difficulty_delta * 0.1

        await self.preference_service.update_inferred(user_id, updates)
        logger.debug(f"[TaskFeedback] Updated inferred preferences for user {user_id}: {updates}")

    async def _maybe_update_routing_profile_after_feedback(
        self,
        *,
        user_id: UUID,
        category: str | None,
        feedback_text: str | None,
    ) -> None:
        if not AdaptiveReplanner.is_strong_cognitive_struggle_feedback(
            category=category,
            feedback_text=feedback_text,
        ):
            return

        snapshot = await self._get_recent_dual_core_snapshot(user_id)
        if not snapshot:
            return

        route_mode = str(snapshot.get("mode") or "").strip().lower()
        if route_mode != "execution_first":
            return

        await RoutingProfileService(self.db, self.redis).record_session_outcome(
            user_id,
            route_mode=route_mode,
            execution_suggestion_ignored=True,
        )

    async def _get_recent_dual_core_snapshot(self, user_id: UUID) -> dict[str, Any] | None:
        if not self.redis:
            return None

        cache_key = f"user:routing:last_dual_core:{user_id}"
        raw = self.redis.get(cache_key)
        if inspect.isawaitable(raw):
            raw = await raw
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        try:
            snapshot = json.loads(raw)
        except (TypeError, ValueError):
            return None

        if not isinstance(snapshot, dict):
            return None

        timestamp = str(snapshot.get("timestamp") or "").strip()
        if not timestamp:
            return None

        try:
            observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None

        if observed_at.tzinfo is not None:
            observed_at = observed_at.astimezone(UTC).replace(tzinfo=None)

        if observed_at < _utcnow() - timedelta(hours=12):
            return None

        return snapshot

    async def get_task_feedbacks(
        self,
        task_id: UUID,
    ) -> list[TaskFeedback]:
        """获取任务的所有反馈"""
        result = await self.db.execute(
            select(TaskFeedback).where(TaskFeedback.task_id == task_id)
        )
        return list(result.scalars().all())

    async def get_user_task_feedback_stats(
        self,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        获取用户任务反馈统计

        Returns:
            {
                "total_feedbacks": int,
                "avg_completion_quality": float,
                "category_distribution": dict,
                "recent_feedbacks": list,
            }
        """
        result = await self.db.execute(
            select(TaskFeedback).where(TaskFeedback.user_id == user_id)
        )
        feedbacks = result.scalars().all()

        total = len(feedbacks)
        qualities = [f.completion_quality for f in feedbacks if f.completion_quality is not None]
        avg_quality = sum(qualities) / len(qualities) if qualities else None

        category_dist = {}
        for f in feedbacks:
            if f.category:
                category_dist[f.category] = category_dist.get(f.category, 0) + 1

        # 获取最近的反馈（最多10条）
        recent_result = await self.db.execute(
            select(TaskFeedback)
            .where(TaskFeedback.user_id == user_id)
            .order_by(TaskFeedback.created_at.desc())
            .limit(10)
        )
        recent_feedbacks = list(recent_result.scalars().all())

        return {
            "total_feedbacks": total,
            "avg_completion_quality": avg_quality,
            "category_distribution": category_dist,
            "recent_feedbacks": recent_feedbacks,
        }
