import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.task import Task
from app.services.llm_service import llm_service

from app.models.user import User

class FocusService:
    @staticmethod
    async def log_session(
        db: AsyncSession,
        user_id: UUID,
        task_id: Optional[UUID],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        duration_minutes: int,
        focus_type: FocusType = FocusType.POMODORO,
        status: FocusStatus = FocusStatus.COMPLETED
    ) -> Dict[str, Any]:
        """Log a completed focus session and award flame points"""
        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            focus_type=focus_type,
            status=status
        )
        db.add(session)
        
        # Calculate Rewards
        flame_earned = 0
        leveled_up = False
        new_level = 0
        
        if status == FocusStatus.COMPLETED:
            # Base logic: 1 minute = 1 point. 
            # 100 points = 1.0 brightness = 1 level up.
            points = duration_minutes
            flame_earned = points
            
            user = await db.get(User, user_id)
            if user:
                # Add brightness (0.01 per minute)
                increment = points / 100.0
                user.flame_brightness += increment
                
                # Check Level Up
                if user.flame_brightness >= 1.0:
                    levels_gained = int(user.flame_brightness)
                    user.flame_level += levels_gained
                    user.flame_brightness -= levels_gained
                    leveled_up = True
                
                new_level = user.flame_level
                
            # Update Task Stats
            if task_id:
                task = await db.get(Task, task_id)
                if task:
                    task.actual_minutes = (task.actual_minutes or 0) + duration_minutes
                    if task.status == "pending":
                        task.status = "in_progress"
                        task.started_at = start_time
        
        return {
            "session": session,
            "rewards": {
                "flame_earned": flame_earned,
                "leveled_up": leveled_up,
                "new_level": new_level
            }
        }

    @staticmethod
    async def get_today_stats(
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get focus stats for today"""
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total duration
        stmt_duration = select(func.sum(FocusSession.duration_minutes)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= today_start,
            FocusSession.status == FocusStatus.COMPLETED
        )
        result_duration = await db.execute(stmt_duration)
        total_minutes = result_duration.scalar() or 0
        
        # Count sessions
        stmt_count = select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= today_start,
            FocusSession.status == FocusStatus.COMPLETED
        )
        result_count = await db.execute(stmt_count)
        pomodoro_count = result_count.scalar() or 0
        
        return {
            "total_minutes": total_minutes,
            "pomodoro_count": pomodoro_count,
            "today_date": today_start.isoformat()
        }

    @staticmethod
    async def get_methodological_guidance(
        task_context: str,
        user_input: str
    ) -> str:
        """
        Get methodological guidance from LLM (Hint/Direction, NOT Solution).
        """
        system_prompt = """
        You are a Socratic tutor and coach.
        The user is working on a task and feels stuck or needs direction.
        
        Goal: Provide "Methodological Guidance" - do NOT give the direct answer.
        1. Analyze the user's input and task.
        2. Suggest a framework, a mental model, or a step-by-step approach to solve it.
        3. Ask a guiding question to prompt the user's thinking.
        4. Keep it concise (under 150 words).
        5. Tone: Encouraging, Insightful, Professional.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task_context}\n\nUser Question/Context: {user_input}"}
        ]
        
        return await llm_service.chat(messages, temperature=0.7)

    @staticmethod
    async def breakdown_task_via_llm(
        task_title: str,
        task_description: str
    ) -> List[Dict[str, Any]]:
        """
        Break down a task into subtasks using LLM.
        Returns JSON list of subtasks.
        """
        system_prompt = """
        You are an expert Project Manager.
        Task: Break down the given task into 3-5 concrete, actionable subtasks.
        
        Output Format: JSON Array ONLY.
        Example: [{"title": "Step 1", "minutes": 25}, {"title": "Step 2", "minutes": 15}]
        
        Constraints:
        1. Subtasks should be small enough (15-45 mins).
        2. Titles should be action-oriented.
        """
        
        prompt = f"Task: {task_title}\nDescription: {task_description}"
        
        return await llm_service.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

focus_service = FocusService()
