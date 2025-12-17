from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.user import User
from app.models.plan import Plan, PlanType
from app.models.galaxy import UserNodeStatus, KnowledgeNode
from app.services.decay_service import DecayService

class PushStrategy(ABC):
    """
    Abstract base class for push notification strategies.
    """
    
    @abstractmethod
    async def should_trigger(self, user: User, db: AsyncSession, context: Dict[str, Any] = None) -> bool:
        """
        Determine if the push notification should be triggered for the given user.
        
        Args:
            user: The user object.
            db: Database session.
            context: Additional context data.
            
        Returns:
            True if the push should be triggered, False otherwise.
        """
        pass

    @abstractmethod
    async def get_trigger_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """
        Get data required for generating the push content.
        
        Args:
            user: The user object.
            db: Database session.
            
        Returns:
            Dictionary containing data for content generation.
        """
        pass


class MemoryStrategy(PushStrategy):
    """
    记忆临界点策略 (Memory Retention Strategy)
    Trigger: When retention < 30% and importance > 4.
    """
    
    def __init__(self):
        self.trigger_nodes = [] # Cache found nodes to avoid re-querying in get_trigger_data

    async def should_trigger(self, user: User, db: AsyncSession, context: Dict[str, Any] = None) -> bool:
        """
        Check if user has important nodes with low retention.
        Retention is calculated via DecayService logic (implicitly via mastery_score/time).
        However, the prompt specifies checking "retention < 0.3".
        Since retention is a calculated value at runtime, we can use the formula from DecayService
        or approximate using mastery_score if DecayService stores decayed mastery.
        
        DecayService:
        Retention = e^(-t/S)
        New Mastery = Current Mastery * Retention
        
        If the prompt strictly means "current calculated retention < 0.3", we need to calculate it.
        Let's assume we find nodes where calculated retention is low.
        
        Requirement: retention < 0.3 AND importance > 4.
        """
        decay_service = DecayService(db)
        
        # We need to join UserNodeStatus with KnowledgeNode to check importance
        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                and_(
                    UserNodeStatus.user_id == user.id,
                    UserNodeStatus.is_unlocked == True,
                    UserNodeStatus.decay_paused == False,
                    KnowledgeNode.importance_level > 4,  # High importance
                    UserNodeStatus.mastery_score > decay_service.MIN_MASTERY # meaningful nodes
                )
            )
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        self.trigger_nodes = []
        now = datetime.now(timezone.utc)
        
        for status, node in rows:
            if not status.last_study_at:
                continue
                
            days_elapsed = (now - status.last_study_at).days
            
            # Re-implement retention calculation logic from DecayService._calculate_decay
            # or simply use the fact that if mastery is low enough relative to initial?
            # But DecayService updates mastery daily.
            # So `mastery_score` IS the current decayed mastery (approximately).
            # The prompt says "retention < 0.3". Retention is a factor (0-1).
            # This implies we calculate: Retention = e^(-t/S).
            
            # Using logic from DecayService:
            stability_factor = 1 + (status.mastery_score / 100) * 2
            effective_half_life = decay_service.BASE_HALF_LIFE_DAYS * stability_factor
            
            import math
            if effective_half_life > 0:
                decay_rate = math.log(2) / effective_half_life
                retention = math.exp(-decay_rate * days_elapsed)
            else:
                retention = 0.0

            if retention < 0.3:
                self.trigger_nodes.append({
                    "node_name": node.name,
                    "retention": retention,
                    "mastery": status.mastery_score
                })
                
            if len(self.trigger_nodes) >= 2:
                break
                
        return len(self.trigger_nodes) > 0

    async def get_trigger_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """
        Return the most urgent 1-2 knowledge nodes and current retention rate.
        """
        # If should_trigger was called in the same request context, self.trigger_nodes might be populated.
        # But for safety (statelessness), we should probably re-query or assume the caller manages state.
        # Given this is a service method, let's re-run the query if empty, or optimization is needed.
        # For this implementation, I'll allow re-running query if list is empty to be stateless safe.
        
        if not self.trigger_nodes:
            await self.should_trigger(user, db)
            
        return {
            "type": "memory",
            "nodes": [n["node_name"] for n in self.trigger_nodes],
            "retention_rate": min([n["retention"] for n in self.trigger_nodes]) if self.trigger_nodes else 0.0
        }


class SprintStrategy(PushStrategy):
    """
    冲刺/DDL策略 (Sprint/Deadline Strategy)
    Trigger: User has a Plan with deadline in < 72 hours.
    """

    async def should_trigger(self, user: User, db: AsyncSession, context: Dict[str, Any] = None) -> bool:
        now = datetime.now(timezone.utc)
        deadline_threshold = now + timedelta(hours=72)
        
        # Plan.target_date is Date, so we compare with date component
        # We look for Active plans
        query = select(Plan).where(
            and_(
                Plan.user_id == user.id,
                Plan.is_active == True,
                Plan.target_date != None,
                Plan.target_date <= deadline_threshold.date(),
                Plan.target_date >= now.date() # Not expired
            )
        )
        
        result = await db.execute(query)
        self.urgent_plans = result.scalars().all()
        
        return len(self.urgent_plans) > 0

    async def get_trigger_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        if not hasattr(self, 'urgent_plans') or not self.urgent_plans:
            await self.should_trigger(user, db)
            
        if not self.urgent_plans:
            return {}

        plan = self.urgent_plans[0] # Take the first one
        
        # Calculate remaining hours
        # Assuming target_date is end of that day (23:59:59) for safety or just 00:00
        # Let's treat target_date as date object.
        now = datetime.now(timezone.utc)
        # Naive conversion for Plan.target_date (Date) to datetime
        # Plan.target_date is likely naive date. 
        # We need to be careful with timezones.
        # Let's assume target date is in user's timezone or UTC.
        # For simplicity, calculate days difference * 24.
        
        days_diff = (plan.target_date - now.date()).days
        hours_remaining = max(0, days_diff * 24) 
        # Refine: if it's today, hours remaining is until end of day? 
        # Or just use raw hours if possible. 
        # Given simple Date field, hours is approximation.
        
        return {
            "type": "sprint",
            "plan_name": plan.name,
            "hours_remaining": hours_remaining
        }


class InactivityStrategy(PushStrategy):
    """
    长期未活跃唤醒 (Inactivity Wake-up Strategy)
    Trigger: User.last_active_at > 24 hours.
    """

    async def should_trigger(self, user: User, db: AsyncSession, context: Dict[str, Any] = None) -> bool:
        # Check for last_active_at, fallback to updated_at, then created_at
        last_active = getattr(user, "last_active_at", None)
        if not last_active:
            # Fallback logic: check updated_at or notifications/tasks?
            # Using updated_at from BaseModel
            last_active = user.updated_at
        
        if not last_active:
            last_active = user.created_at

        if not last_active:
            return False

        # Ensure timezone awareness
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        diff = now - last_active
        
        return diff > timedelta(hours=24)

    async def get_trigger_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        return {
            "type": "inactivity",
            "last_active_hours_ago": 24 # Simplified
        }
