from typing import List, Dict, Any, Optional
import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from uuid import UUID

from app.models.task import Task, TaskStatus
from app.models.focus import FocusSession, FocusStatus
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.core.event_bus import event_bus
from app.services.analytics.blindspot_analyzer import BlindspotAnalyzer
# Fixed: Import class from module, not instance
from app.services.nudge_service import NudgeService

class BehaviorPatternService:
    """
    Behavior Pattern Recognition Engine (Cognitive Nexus Phase 3)
    Analyzes user behavior to identify cognitive patterns such as:
    - Planning Optimism (Underestimating task duration)
    - Focus Decay (Declining focus duration)
    - Cognitive Blindspots (Recurring errors in specific areas)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.blindspot_analyzer = BlindspotAnalyzer(db)
        self.nudge_service = NudgeService(db)

    async def analyze_planning_optimism(self, user_id: UUID, task_id: UUID) -> Optional[BehaviorPattern]:
        """
        Analyze if a completed task shows 'Planning Optimism'.
        Condition: Actual time > 1.5 * Estimated time
        """
        task = await self.db.get(Task, task_id)
        # Handle cases where task fields are None
        if not task:
            return None
            
        # Manually extract values to avoid Pylance/SQLAlchemy type confusion
        t_estimated: int = getattr(task, 'estimated_minutes', 0) or 0
        t_actual: int = getattr(task, 'actual_minutes', 0) or 0
        
        if t_estimated <= 0 or t_actual <= 0:
            return None

        # Check for Optimism Bias
        if t_actual > (t_estimated * 1.5):
            # Verify if this is a recurring pattern (last 5 tasks)
            recent_tasks = await self._get_recent_completed_tasks(user_id, limit=5)
            optimism_count = 0
            
            for t in recent_tasks:
                sub_actual: int = getattr(t, 'actual_minutes', 0) or 0
                sub_estimated: int = getattr(t, 'estimated_minutes', 0) or 0
                if sub_estimated > 0 and sub_actual > (sub_estimated * 1.5):
                    optimism_count += 1
            
            confidence = 0.5 + (optimism_count * 0.1) # Base 0.5, increases with frequency
            
            pattern = await self._create_or_update_pattern(
                user_id=user_id,
                pattern_name="Planning Optimism",
                pattern_type="cognitive",
                description=f"You tend to underestimate task duration. Last task took {t_actual}m vs estimated {t_estimated}m.",
                solution_text="Try adding a 20% buffer to your time estimates.",
                evidence_id=str(task_id),
                confidence=min(confidence, 1.0)
            )
            
            # Trigger Nudge
            if confidence > 0.7:
                 await event_bus.publish("nudge.triggered", {
                    "user_id": str(user_id),
                    "type": "planning_optimism",
                    "message": "Looks like tasks are taking longer than planned. Want to adjust your schedule?",
                    "context": {"task_id": str(task_id)}
                })
            
            return pattern
        return None

    async def analyze_focus_decay(self, user_id: UUID) -> Optional[BehaviorPattern]:
        """
        Analyze 'Focus Decay': Average focus session length declining over last 3 days.
        """
        # Get daily averages for last 3 days
        stats = []
        today = datetime.date.today()
        for i in range(3):
            date = today - datetime.timedelta(days=i)
            avg = await self._get_daily_focus_average(user_id, date)
            stats.append(avg) # [Today, Yesterday, 2 Days Ago]

        # Check for decay trend: Day 2 > Day 1 > Today (Strict decay) or significant drop
        if stats[2] > 0 and stats[0] < stats[2] * 0.7: # Today is < 70% of 2 days ago
             pattern = await self._create_or_update_pattern(
                user_id=user_id,
                pattern_name="Focus Decay",
                pattern_type="execution",
                description="Your focus stamina has dropped by over 30% in the last 3 days.",
                solution_text="Consider a rest day or lighter workload to recover mental energy.",
                confidence=0.8,
                evidence_id=f"focus_stats_{today.isoformat()}"
            )
             
             await event_bus.publish("nudge.triggered", {
                "user_id": str(user_id),
                "type": "focus_decay",
                "message": "Your focus is slipping. Time for a recharge?",
                 "context": {"trend": stats}
            })
             return pattern

        return None

    async def analyze_cognitive_blindspots(self, user_id: UUID) -> List[BehaviorPattern]:
        """
        Wrapper around BlindspotAnalyzer to persist results as patterns.
        """
        blindspots = await self.blindspot_analyzer.analyze_blindspots(str(user_id), limit=3)
        
        results = []
        for bs in blindspots:
            pattern = await self._create_or_update_pattern(
                user_id=user_id,
                pattern_name="Cognitive Blindspot",
                pattern_type="cognitive",
                description=f"Persistent gap in '{bs['node_name']}': {bs['reason']}",
                solution_text=f"Review prerequisites for {bs['node_name']} before advancing.",
                evidence_id=str(bs['node_id']),
                confidence=0.9
            )
            results.append(pattern)
            
            # Trigger Nudge for top blindspot
            if bs == blindspots[0]:
                 await event_bus.publish("nudge.triggered", {
                    "user_id": str(user_id),
                    "type": "cognitive_blindspot",
                    "message": f"Struggling with {bs['node_name']}? Let's review the basics first.",
                    "context": {"node_id": str(bs['node_id'])}
                })

        return results

    # --- Helper Methods ---

    async def _get_recent_completed_tasks(self, user_id: UUID, limit: int = 5) -> List[Task]:
        query = select(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED
        ).order_by(desc(Task.completed_at)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all() # type: ignore

    async def _get_daily_focus_average(self, user_id: UUID, date: datetime.date) -> float:
        start = datetime.datetime.combine(date, datetime.time.min)
        end = datetime.datetime.combine(date, datetime.time.max)
        
        query = select(func.avg(FocusSession.duration_minutes)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= start,
            FocusSession.start_time <= end,
            FocusSession.status == FocusStatus.COMPLETED
        )
        result = await self.db.execute(query)
        val = result.scalar()
        return float(val) if val else 0.0

    async def _create_or_update_pattern(self, user_id: UUID, pattern_name: str, pattern_type: str, 
                                      description: str, solution_text: str, evidence_id: str, confidence: float) -> BehaviorPattern:
        # Check if pattern exists (active)
        query = select(BehaviorPattern).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.pattern_name == pattern_name,
            BehaviorPattern.is_archived == False
        )
        result = await self.db.execute(query)
        pattern = result.scalars().first()

        if pattern:
            # Update existing
            # Use setattr to bypass some type checker constraints if needed, but direct assignment is preferred
            pattern.description = description
            pattern.confidence_score = confidence
            current_freq = getattr(pattern, 'frequency', 0) or 0
            pattern.frequency = current_freq + 1
            
            # Add evidence if not present
            current_evidence = getattr(pattern, 'evidence_ids', []) or []
            if evidence_id not in current_evidence:
                 new_evidence = list(current_evidence)
                 new_evidence.append(evidence_id)
                 pattern.evidence_ids = new_evidence # type: ignore
        else:
            # Create new
            pattern = BehaviorPattern(
                user_id=user_id,
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                description=description,
                solution_text=solution_text,
                evidence_ids=[evidence_id],
                confidence_score=confidence,
                frequency=1
            )
            self.db.add(pattern)
        
        await self.db.commit()
        await self.db.refresh(pattern)
        return pattern
