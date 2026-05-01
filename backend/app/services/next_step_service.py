from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent_profiles import AgentRole
from app.models.galaxy import UserNodeStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import NextActionSuggestion, NextActionType
from app.services.llm_service import get_llm_service


class NextStepService:
    """
    Service to suggest next actions after a task is completed.
    Uses LLM with a rule-based fallback to ensure low latency.
    """

    async def suggest_next_actions(
        self,
        completed_task: Task,
        user: User,
        db: AsyncSession
    ) -> list[NextActionSuggestion]:
        """
        Suggest next actions based on the completed task.
        """
        # 1. Calculate fatigue ratio
        estimated = completed_task.estimated_minutes or 15
        actual = completed_task.actual_minutes or estimated
        fatigue_ratio = actual / estimated if estimated > 0 else 1.0

        # 2. Get user action preferences (if available)
        action_preferences = await self._get_user_action_preferences(user.id, db)

        # 3. Gather context (Plan & Galaxy)
        plan_context = None

        if completed_task.plan_id:
            # Simple check if there are more pending tasks in the plan
            # We can't easily import PlanService due to circular imports potential,
            # so we do a quick DB check or rely on passed info if we refactor.
            # For now, let's just note the plan ID.
            plan_context = {"plan_id": str(completed_task.plan_id)}

        if completed_task.knowledge_node_id:
            # We would ideally get the node name.
            # Assuming we might need to fetch it if not eager loaded.
            # For speed, if we don't have it, we skip name specific prompts or fetch it.
            # Let's try to fetch node name if possible, but keep it light.
            pass

        # 4. Try LLM Generation with Timeout
        try:
            # Set a strict timeout for the LLM call to ensure UI responsiveness
            return await asyncio.wait_for(
                self._generate_with_llm(completed_task, fatigue_ratio, plan_context, action_preferences),
                timeout=3.0
            )
        except (TimeoutError, Exception) as e:
            logger.warning(f"Next step generation failed or timed out: {e}. Using fallback.")
            return await self._rule_based_fallback(completed_task, fatigue_ratio, db, action_preferences)

    async def _generate_with_llm(
        self,
        task: Task,
        fatigue_ratio: float,
        plan_context: dict | None,
        action_preferences: dict[str, float] | None = None
    ) -> list[NextActionSuggestion]:

        llm = get_llm_service(AgentRole.TIME_TUTOR)

        prompt = f"""
        User just completed a task: "{task.title}" (Type: {task.type}).
        Stats: Estimated {task.estimated_minutes}m, Actual {task.actual_minutes}m. (Fatigue Ratio: {fatigue_ratio:.2f}).
        Difficulty: {task.difficulty}/5.

        Based on this, suggest 2-3 next actions.

        Principles:
        1. If Fatigue Ratio > 1.5 or Actual > 40m -> Suggest 'rest_break' first.
        2. If part of a plan -> Suggest 'continue_plan'.
        3. Otherwise -> 'quick_review' (quiz) or 'light_expand' (related knowledge).
        4. ALL suggestions must be <= 15 mins.

        Return JSON list of objects matching this schema:
        {{
            "type": "str", // quick_review, light_expand, practice_apply, rest_break, continue_plan
            "title": "str",
            "description": "str",
            "estimated_minutes": int, // <= 15
            "energy_cost": int, // <= 2
            "difficulty": int, // <= task.difficulty
            "reason": "str", // Encouraging tone
            "quick_create_params": {{ // Optional, for one-click creation
                "title": "str",
                "type": "str", // learning, training, etc.
                "estimated_minutes": int
            }}
        }}
        """

        response = await llm.chat_json(
            messages=[
                {"role": "system", "content": "You are an empathetic study coach. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        suggestions = []
        if isinstance(response, list):
            items = response
        elif isinstance(response, dict) and "actions" in response:
            items = response["actions"]
        else:
            items = []

        for item in items:
            try:
                # Ensure validation
                sug = NextActionSuggestion(**item)
                suggestions.append(sug)
            except Exception as e:
                logger.warning(f"Skipping invalid suggestion: {e}")

        if not suggestions:
            raise ValueError("No valid suggestions generated")

        return suggestions[:settings.NEXT_STEP_MAX_RECOMMENDATIONS]

    async def _get_plan_next_task(
        self,
        task: Task,
        db: AsyncSession
    ) -> NextActionSuggestion | None:
        """获取计划内下一个待办任务"""
        # 查询同一计划下的 PENDING 任务
        query = select(Task).where(
            and_(
                Task.plan_id == task.plan_id,
                Task.user_id == task.user_id,
                Task.status == TaskStatus.PENDING
            )
        ).order_by(desc(Task.priority), desc(Task.created_at)).limit(1)

        result = await db.execute(query)
        next_task = result.scalar_one_or_none()

        if not next_task:
            return None

        # 计算计划进度
        total_count_result = await db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.plan_id == task.plan_id,
                    Task.user_id == task.user_id
                )
            )
        )
        total_count = total_count_result.scalar() or 1

        # 已完成数量 = 总数 - 当前待办数
        pending_count_result = await db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.plan_id == task.plan_id,
                    Task.user_id == task.user_id,
                    Task.status == TaskStatus.PENDING
                )
            )
        )
        pending_count = pending_count_result.scalar() or 0
        completed_count = total_count - pending_count

        return NextActionSuggestion(
            type=NextActionType.CONTINUE_PLAN,
            title=f"继续：{next_task.title}",
            description=f"这是你计划的下一步（进度 {completed_count}/{total_count}）",
            estimated_minutes=min(next_task.estimated_minutes, 15),
            energy_cost=min(next_task.energy_cost, 2),
            difficulty=min(next_task.difficulty, task.difficulty),
            reason=f"按计划推进，已完成 {completed_count} 个任务",
            existing_task_id=next_task.id,
            quick_create_params=None,
            can_quick_create=False  # 任务已存在，不是创建而是"开始"
        )

    async def _get_node_mastery(
        self,
        db: AsyncSession,
        user_id: UUID,
        node_id: UUID
    ) -> float:
        """获取用户对节点的掌握度"""
        result = await db.execute(
            select(UserNodeStatus.mastery_score).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        score = result.scalar_one_or_none()
        return score if score is not None else 0.0

    async def _suggest_knowledge_expands(
        self,
        task: Task,
        db: AsyncSession,
        max_results: int = 2
    ) -> list[NextActionSuggestion]:
        """基于知识图谱邻居节点推荐拓展任务"""
        if not task.knowledge_node_id:
            return []

        from app.services.galaxy_service import GalaxyService

        galaxy = GalaxyService(db)

        # 获取邻居节点
        neighbors = await galaxy.get_node_neighbors(
            node_id=task.knowledge_node_id,
            limit=10
        )

        # 过滤：只保留相关/应用/进化关系，排除已掌握节点
        valid_neighbors = []
        for node in neighbors:
            # 检查掌握度
            mastery = await self._get_node_mastery(db, task.user_id, node.id)
            if mastery < 80:  # 未完全掌握
                valid_neighbors.append((node, mastery))

        # 按 mastery 升序（推荐掌握度较低的）
        valid_neighbors.sort(key=lambda x: x[1])

        suggestions = []
        for node, mastery in valid_neighbors[:max_results]:
            suggestions.append(NextActionSuggestion(
                type=NextActionType.LIGHT_EXPAND,
                title=f"拓展：{node.name}",
                description=f"了解「{node.name}」与刚才内容的联系",
                estimated_minutes=min(5 + int((100 - mastery) / 20), 15),
                energy_cost=1,
                difficulty=min(3, task.difficulty),
                reason="基于你刚学的知识推荐相关延伸",
                quick_create_params={
                    "title": f"学习：{node.name}",
                    "type": "learning",
                    "estimated_minutes": 10,
                    "knowledge_node_id": str(node.id),
                    "tags": [task.title[:20]]  # 继承原任务标签
                },
                existing_task_id=None,
                can_quick_create=True
            ))

        return suggestions

    def _create_rest_suggestion(self, task: Task) -> NextActionSuggestion:
        """创建休息建议"""
        return NextActionSuggestion(
            type=NextActionType.REST_BREAK,
            title="休息一下",
            description="刚才的任务比较消耗精力，建议休息5分钟恢复状态。",
            estimated_minutes=5,
            energy_cost=0,
            difficulty=1,
            reason="劳逸结合才能走得更远",
            quick_create_params=None,
            existing_task_id=None,
            can_quick_create=False
        )

    def _create_light_action_suggestion(self, task: Task) -> NextActionSuggestion:
        """创建轻量行动建议（用于疲劳时）"""
        return NextActionSuggestion(
            type=NextActionType.QUICK_REVIEW,
            title="快速回顾",
            description=f"花几分钟回顾一下 {task.title} 的核心要点。",
            estimated_minutes=5,
            energy_cost=1,
            difficulty=1,
            reason="及时回顾能有效对抗遗忘",
            quick_create_params={
                "title": f"回顾: {task.title}",
                "type": "review",
                "estimated_minutes": 5
            },
            existing_task_id=None,
            can_quick_create=True
        )

    def _create_review_suggestion(self, task: Task) -> NextActionSuggestion:
        """创建回顾建议（默认）"""
        return NextActionSuggestion(
            type=NextActionType.QUICK_REVIEW,
            title="快速回顾",
            description=f"花几分钟回顾一下 {task.title} 的核心要点。",
            estimated_minutes=5,
            energy_cost=1,
            difficulty=1,
            reason="及时回顾能有效对抗遗忘",
            quick_create_params={
                "title": f"回顾: {task.title}",
                "type": "review",
                "estimated_minutes": 5
            },
            existing_task_id=None,
            can_quick_create=True
        )

    async def _rule_based_fallback(
        self,
        task: Task,
        fatigue_ratio: float,
        db: AsyncSession,
        action_preferences: dict[str, float] | None = None
    ) -> list[NextActionSuggestion]:
        """使用配置的规则引擎生成建议"""
        suggestions = []

        # 1. 疲劳处理（使用配置阈值）
        if fatigue_ratio >= settings.NEXT_STEP_FATIGUE_EXTREME_THRESHOLD:
            # 极度疲劳：只推荐休息
            return [self._create_rest_suggestion(task)]

        if fatigue_ratio >= settings.NEXT_STEP_FATIGUE_HIGH_THRESHOLD:
            # 高疲劳：休息 + 一个轻量选项
            suggestions.append(self._create_rest_suggestion(task))
            # 根据任务类型添加轻量选项
            suggestions.append(self._create_light_action_suggestion(task))
            return suggestions[:settings.NEXT_STEP_MAX_RECOMMENDATIONS]

        # 2. 计划内任务
        if task.plan_id:
            plan_task = await self._get_plan_next_task(task, db)
            if plan_task:
                suggestions.append(plan_task)

        # 3. 知识拓展（如果有知识节点且疲劳度较低）
        if task.knowledge_node_id and fatigue_ratio < 1.2:
            expand_suggestions = await self._suggest_knowledge_expands(task, db)
            suggestions.extend(expand_suggestions)

        # 4. 默认回顾（如果没有其他建议）
        if not suggestions:
            suggestions.append(self._create_review_suggestion(task))

        # 5. 根据用户偏好排序
        if action_preferences:
            suggestions = self._sort_by_preferences(suggestions, action_preferences)

        return suggestions[:settings.NEXT_STEP_MAX_RECOMMENDATIONS]

    def _sort_by_preferences(
        self,
        suggestions: list[NextActionSuggestion],
        preferences: dict[str, float]
    ) -> list[NextActionSuggestion]:
        """
        根据用户偏好排序建议

        Args:
            suggestions: 原始建议列表
            preferences: 用户偏好 {action_type: selection_rate}

        Returns:
            排序后的建议列表
        """
        def get_score(suggestion: NextActionSuggestion) -> float:
            # 获取该类型的偏好分数
            action_type_str = suggestion.type.value if hasattr(suggestion.type, 'value') else str(suggestion.type)
            return preferences.get(action_type_str, 0.0)

        # 按偏好分数降序排序
        return sorted(suggestions, key=get_score, reverse=True)

    async def _get_user_action_preferences(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> dict[str, float] | None:
        """
        获取用户对各类型action的选择偏好

        Args:
            user_id: 用户ID
            db: 数据库会话

        Returns:
            {action_type: selection_rate} 字典，如果没有数据则返回None
        """
        try:
            from app.services.next_action_selection_service import NextActionSelectionService

            service = NextActionSelectionService(db)
            preferences = await service.get_user_action_preferences(user_id, days=30)

            # 只有有数据时才返回
            return preferences if preferences else None
        except Exception as e:
            logger.warning(f"Failed to get user action preferences: {e}")
            return None

next_step_service = NextStepService()
