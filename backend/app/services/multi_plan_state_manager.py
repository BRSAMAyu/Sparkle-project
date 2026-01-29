"""
Multi-Plan State Manager - 多计划状态管理系统

支持真正的多计划并行：
- 共享会话状态（SharedSessionState）
- 多计划焦点管理（ActivePlansTracker）
- 每计划独立状态（PlanState）
- 自动焦点切换
- 并行数量限制

Design:
┌─────────────────────────────────────────┐
│         MultiPlanStateManager           │
├─────────────────────────────────────────┤
│  SharedSessionState (跨计划共享)        │
│  - user_preferences                     │
│  - cognitive_profile                    │
│  - fatigue_level                        │
├─────────────────────────────────────────┤
│  ActivePlansTracker                     │
│  - focus_plan_id (当前焦点)             │
│  - active_plan_ids (最多3个)            │
│  - switch_history                       │
├─────────────────────────────────────────┤
│  PlanState A │ PlanState B │ PlanState C│
│  (独立状态)  │ (独立状态)  │ (独立状态) │
└─────────────────────────────────────────┘
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.services.plan_state_service import PlanStateService

# Configuration
MAX_ACTIVE_PLANS = 3  # 并行计划数量限制
SHARED_STATE_CACHE_TTL = 3600  # 1 hour
TRACKER_CACHE_TTL = 3600  # 1 hour


@dataclass
class SharedSessionState:
    """会话级共享状态（跨所有计划）"""
    user_id: UUID
    session_id: str

    # 用户偏好（从 UserScope）
    user_preferences: dict[str, Any] = field(default_factory=dict)

    # 认知档案
    cognitive_profile: dict[str, Any] = field(default_factory=dict)

    # 会话级信号
    fatigue_level: float = 0.0
    recent_topics: list[str] = field(default_factory=list)
    last_activity_time: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "user_preferences": self.user_preferences,
            "cognitive_profile": self.cognitive_profile,
            "fatigue_level": self.fatigue_level,
            "recent_topics": self.recent_topics,
            "last_activity_time": self.last_activity_time.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedSessionState:
        """从字典创建"""
        from uuid import UUID

        return cls(
            user_id=UUID(data["user_id"]),
            session_id=data["session_id"],
            user_preferences=data.get("user_preferences", {}),
            cognitive_profile=data.get("cognitive_profile", {}),
            fatigue_level=data.get("fatigue_level", 0.0),
            recent_topics=data.get("recent_topics", []),
            last_activity_time=datetime.fromisoformat(data["last_activity_time"]) if data.get("last_activity_time") else datetime.utcnow()
        )


@dataclass
class ActivePlansTracker:
    """活跃计划追踪器"""
    focus_plan_id: UUID | None = None  # 当前焦点计划
    active_plan_ids: list[UUID] = field(default_factory=list)

    # 切换历史
    switch_history: list[dict[str, Any]] = field(default_factory=list)
    last_switch_time: datetime | None = None

    def add_active_plan(self, plan_id: UUID) -> bool:
        """
        添加计划到活跃集合，强制限制

        Args:
            plan_id: 计划ID

        Returns:
            bool: 是否成功添加
        """
        if plan_id in self.active_plan_ids:
            return True

        # 强制并行限制
        if len(self.active_plan_ids) >= MAX_ACTIVE_PLANS:
            # 移除最老的非焦点计划
            for pid in self.active_plan_ids:
                if pid != self.focus_plan_id:
                    self.active_plan_ids.remove(pid)
                    logger.info(f"Removed plan {pid} to enforce parallel limit")
                    break

        self.active_plan_ids.append(plan_id)
        return True

    def set_focus(self, plan_id: UUID, reason: str = "manual") -> bool:
        """
        设置焦点计划（必须在活跃集合中）

        Args:
            plan_id: 计划ID
            reason: 切换原因

        Returns:
            bool: 是否成功
        """
        # 先添加到活跃集合
        self.add_active_plan(plan_id)

        old_focus = self.focus_plan_id
        self.focus_plan_id = plan_id
        self.last_switch_time = datetime.utcnow()

        # 记录历史
        self.switch_history.append({
            "from": str(old_focus) if old_focus else None,
            "to": str(plan_id),
            "timestamp": self.last_switch_time.isoformat(),
            "reason": reason
        })

        # 限制历史大小
        if len(self.switch_history) > 20:
            self.switch_history = self.switch_history[-20:]

        return True

    def remove_active_plan(self, plan_id: UUID) -> bool:
        """从活跃集合移除计划"""
        if plan_id in self.active_plan_ids:
            self.active_plan_ids.remove(plan_id)

            # 如果移除的是焦点计划，切换到下一个
            if self.focus_plan_id == plan_id:
                self.focus_plan_id = self.active_plan_ids[0] if self.active_plan_ids else None

            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "focus_plan_id": str(self.focus_plan_id) if self.focus_plan_id else None,
            "active_plan_ids": [str(pid) for pid in self.active_plan_ids],
            "switch_history": self.switch_history[-10:],  # 只保留最近10条
            "last_switch_time": self.last_switch_time.isoformat() if self.last_switch_time else None
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivePlansTracker:
        """从字典创建"""
        return cls(
            focus_plan_id=UUID(data["focus_plan_id"]) if data.get("focus_plan_id") else None,
            active_plan_ids=[UUID(pid) for pid in data.get("active_plan_ids", [])],
            switch_history=data.get("switch_history", []),
            last_switch_time=datetime.fromisoformat(data["last_switch_time"]) if data.get("last_switch_time") else None
        )


class MultiPlanStateManager:
    """
    多计划状态管理器

    职责:
    1. 管理共享会话状态
    2. 追踪多个活跃计划
    3. 提供组合上下文（共享+焦点+摘要）
    4. 自动焦点切换
    5. 强制并行限制
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        plan_state_service: PlanStateService | None = None
    ):
        """
        Args:
            db: 数据库会话
            redis: Redis客户端
            plan_state_service: 计划状态服务（可选，自动创建）
        """
        self.db = db
        self.redis = redis
        self.plan_state_service = plan_state_service or PlanStateService(db, redis)

        logger.info("MultiPlanStateManager initialized")

    # ==================== Shared State Management ====================

    async def get_shared_state(
        self,
        user_id: UUID,
        session_id: str
    ) -> SharedSessionState:
        """
        获取共享会话状态

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            SharedSessionState
        """
        if not self.redis:
            return SharedSessionState(user_id=user_id, session_id=session_id)

        cache_key = f"shared_state:{session_id}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return SharedSessionState.from_dict(json.loads(cached))
        except Exception as e:
            logger.warning(f"Failed to get shared state from cache: {e}")

        return SharedSessionState(user_id=user_id, session_id=session_id)

    async def update_shared_state(
        self,
        user_id: UUID,
        session_id: str,
        updates: dict[str, Any]
    ) -> SharedSessionState:
        """
        更新共享会话状态

        Args:
            user_id: 用户ID
            session_id: 会话ID
            updates: 更新内容

        Returns:
            更新后的 SharedSessionState
        """
        state = await self.get_shared_state(user_id, session_id)

        # 应用更新
        if "user_preferences" in updates:
            state.user_preferences.update(updates["user_preferences"])
        if "cognitive_profile" in updates:
            state.cognitive_profile.update(updates["cognitive_profile"])
        if "fatigue_level" in updates:
            state.fatigue_level = updates["fatigue_level"]
        if "recent_topics" in updates:
            state.recent_topics = updates["recent_topics"]

        state.last_activity_time = datetime.utcnow()

        # 缓存
        await self._set_shared_state_cache(session_id, state)

        return state

    # ==================== Active Plans Tracker ====================

    async def get_active_tracker(
        self,
        session_id: str
    ) -> ActivePlansTracker:
        """
        获取活跃计划追踪器

        Args:
            session_id: 会话ID

        Returns:
            ActivePlansTracker
        """
        if not self.redis:
            return ActivePlansTracker()

        cache_key = f"active_tracker:{session_id}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return ActivePlansTracker.from_dict(json.loads(cached))
        except Exception as e:
            logger.warning(f"Failed to get active tracker from cache: {e}")

        return ActivePlansTracker()

    async def update_active_tracker(
        self,
        session_id: str,
        tracker: ActivePlansTracker
    ) -> None:
        """
        更新活跃计划追踪器

        Args:
            session_id: 会话ID
            tracker: 追踪器对象
        """
        if not self.redis:
            return

        cache_key = f"active_tracker:{session_id}"
        try:
            await self.redis.setex(
                cache_key,
                TRACKER_CACHE_TTL,
                json.dumps(tracker.to_dict(), ensure_ascii=False, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache active tracker: {e}")

    # ==================== Core Operations ====================

    async def get_composite_context(
        self,
        user_id: UUID,
        session_id: str,
        focus_plan_id: UUID | None = None
    ) -> dict[str, Any]:
        """
        获取组合上下文（供 LLM 使用）

        包含:
        - 共享会话状态
        - 焦点计划的完整状态
        - 其他活跃计划的摘要

        Args:
            user_id: 用户ID
            session_id: 会话ID
            focus_plan_id: 指定焦点计划（可选）

        Returns:
            Dict: 组合上下文
        """
        # 获取共享状态
        shared = await self.get_shared_state(user_id, session_id)

        # 获取活跃计划追踪器
        tracker = await self.get_active_tracker(session_id)

        # 确定焦点计划
        focus = focus_plan_id or tracker.focus_plan_id
        if not focus and tracker.active_plan_ids:
            focus = tracker.active_plan_ids[0]

        context = {
            "shared_state": shared.to_dict(),
            "focus_plan": None,
            "other_plans_summary": []
        }

        # 获取焦点计划的完整状态
        if focus:
            focus_state = await self.plan_state_service.get_plan_state(user_id, focus)
            if focus_state:
                context["focus_plan"] = {
                    "plan_id": str(focus),
                    "state": focus_state.to_dict(),
                    "task_summaries": (focus_state.task_summaries or [])[:10]  # 限制数量
                }

        # 获取其他活跃计划的摘要
        for plan_id in tracker.active_plan_ids:
            if plan_id != focus:
                state = await self.plan_state_service.get_plan_state(user_id, plan_id)
                if state:
                    task_index = state.task_index or {}
                    context["other_plans_summary"].append({
                        "plan_id": str(plan_id),
                        "task_count": task_index.get("total", 0),
                        "completed_count": task_index.get("completed", 0),
                        "last_milestone": (state.milestones or [])[-1] if state.milestones else None
                    })

        return context

    async def switch_focus_by_task(
        self,
        user_id: UUID,
        session_id: str,
        task_id: UUID
    ) -> UUID | None:
        """
        根据任务自动切换焦点计划

        Args:
            user_id: 用户ID
            session_id: 会话ID
            task_id: 任务ID

        Returns:
            切换后的计划ID，如果未切换则返回当前计划ID
        """
        # 查询任务所属计划
        result = await self.db.execute(
            select(Task.plan_id).where(
                Task.id == task_id,
                Task.user_id == user_id,
                Task.deleted_at.is_(None)
            )
        )
        task_plan_id = result.scalar_one_or_none()

        if not task_plan_id:
            logger.warning(f"Task {task_id} not found or has no plan")
            return None

        # 获取追踪器并切换焦点
        tracker = await self.get_active_tracker(session_id)
        old_focus = tracker.focus_plan_id

        if old_focus != task_plan_id:
            tracker.set_focus(task_plan_id, reason="auto_match")
            await self.update_active_tracker(session_id, tracker)

            logger.info(
                f"Auto-switched focus from {old_focus} to {task_plan_id} "
                f"based on task {task_id}"
            )
            return task_plan_id

        return old_focus

    async def query_task_cards_for_plan(
        self,
        user_id: UUID,
        plan_id: UUID,
        filters: dict[str, Any] | None = None,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        查询特定计划的任务卡（供 LLM 使用）

        Args:
            user_id: 用户ID
            plan_id: 计划ID
            filters: 过滤条件
            limit: 返回数量限制

        Returns:
            List[Dict]: 任务卡列表
        """
        query = select(Task).where(
            Task.user_id == user_id,
            Task.plan_id == plan_id,
            Task.deleted_at.is_(None)
        )

        # 应用过滤
        if filters:
            if "status" in filters:
                query = query.where(Task.status == filters["status"])
            if "type" in filters:
                query = query.where(Task.type == filters["type"])
            if "difficulty_min" in filters:
                query = query.where(Task.difficulty >= filters["difficulty_min"])
            if "difficulty_max" in filters:
                query = query.where(Task.difficulty <= filters["difficulty_max"])

        query = query.order_by(Task.order_index).limit(limit)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status.value,
                "type": t.type.value,
                "estimated_minutes": t.estimated_minutes,
                "difficulty": t.difficulty,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None
            }
            for t in tasks
        ]

    async def set_focus_plan(
        self,
        user_id: UUID,
        session_id: str,
        plan_id: UUID,
        reason: str = "manual"
    ) -> bool:
        """
        手动设置焦点计划

        Args:
            user_id: 用户ID
            session_id: 会话ID
            plan_id: 计划ID
            reason: 切换原因

        Returns:
            bool: 是否成功
        """
        tracker = await self.get_active_tracker(session_id)
        tracker.set_focus(plan_id, reason)
        await self.update_active_tracker(session_id, tracker)

        logger.info(
            f"Set focus plan to {plan_id} for session {session_id}, reason: {reason}"
        )
        return True

    async def get_focus_plan_id(
        self,
        session_id: str
    ) -> UUID | None:
        """
        获取当前焦点计划ID

        Args:
            session_id: 会话ID

        Returns:
            计划ID 或 None
        """
        tracker = await self.get_active_tracker(session_id)
        return tracker.focus_plan_id

    async def add_active_plan(
        self,
        user_id: UUID,
        session_id: str,
        plan_id: UUID
    ) -> bool:
        """
        添加活跃计划（不改变焦点）

        Args:
            user_id: 用户ID
            session_id: 会话ID
            plan_id: 计划ID

        Returns:
            bool: 是否成功
        """
        tracker = await self.get_active_tracker(session_id)
        success = tracker.add_active_plan(plan_id)
        await self.update_active_tracker(session_id, tracker)

        if success:
            logger.info(f"Added active plan {plan_id} for session {session_id}")

        return success

    async def remove_active_plan(
        self,
        user_id: UUID,
        session_id: str,
        plan_id: UUID
    ) -> bool:
        """
        移除活跃计划

        Args:
            user_id: 用户ID
            session_id: 会话ID
            plan_id: 计划ID

        Returns:
            bool: 是否成功
        """
        tracker = await self.get_active_tracker(session_id)
        success = tracker.remove_active_plan(plan_id)
        await self.update_active_tracker(session_id, tracker)

        if success:
            logger.info(f"Removed active plan {plan_id} for session {session_id}")

        return success

    async def get_active_plans(
        self,
        user_id: UUID,
        session_id: str
    ) -> list[UUID]:
        """
        获取所有活跃计划ID列表

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            List[UUID]: 活跃计划ID列表
        """
        tracker = await self.get_active_tracker(session_id)
        return tracker.active_plan_ids.copy()

    # ==================== Cache Helpers ====================

    async def _set_shared_state_cache(
        self,
        session_id: str,
        state: SharedSessionState
    ) -> None:
        """缓存共享状态"""
        if not self.redis:
            return

        cache_key = f"shared_state:{session_id}"
        try:
            await self.redis.setex(
                cache_key,
                SHARED_STATE_CACHE_TTL,
                json.dumps(state.to_dict(), ensure_ascii=False, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache shared state: {e}")
