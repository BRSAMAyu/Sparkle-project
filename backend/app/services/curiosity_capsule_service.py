"""
Curiosity Capsule Service
"""
import random
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User
from app.models.task import Task
from app.core.llm_client import llm_client

class CuriosityCapsuleService:
    async def generate_daily_capsule(self, user_id: UUID, db: AsyncSession) -> Optional[CuriosityCapsule]:
        """
        Generate a daily curiosity capsule for the user based on recent activity.
        """
        # 1. Get user preferences
        user = await db.get(User, user_id)
        if not user:
            return None
            
        if not user.curiosity_preference or user.curiosity_preference < 0.3:
            # Low curiosity preference users might receive fewer or no capsules automatically
            # For now, we generate anyway but maybe content is different.
            pass

        # 2. Get recent completed tasks to find a topic
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(desc(Task.completed_at))
            .limit(5)
        )
        recent_tasks = result.scalars().all()
        
        topic = "General Knowledge"
        related_task = None
        
        if recent_tasks:
            # Pick a random task to elaborate on
            related_task = random.choice(recent_tasks)
            topic = related_task.title
        
        # 3. Generate content using LLM
        prompt = f"""
        Generate a short, interesting 'Curiosity Capsule' (100-150 words) related to: "{topic}".
        Target audience: A college student.
        Tone: Engaging, inspiring, slightly surprising.
        Format: Markdown.
        Title: A catchy title.
        Content: The body text.
        """
        
        # Mock LLM call for now to avoid actual API cost/latency in this loop, 
        # or use real one if configured. 
        # We will use a real call structure but assume it returns something valid.
        
        # response = await llm_client.generate(prompt) # Hypothetical
        # For prototype speed, we'll use static generation or simple logic
        
        title = f"Did you know about {topic}?"
        content = f"Here is a fascinating fact about **{topic}**...\n\nDid you know that exploring {topic} can lead to unexpected discoveries in other fields? Keep your curiosity alive!"
        
        # 4. Save to DB
        capsule = CuriosityCapsule(
            user_id=user_id,
            title=title,
            content=content,
            related_subject=topic,
            related_task_id=related_task.id if related_task else None,
            is_read=False
        )
        
        db.add(capsule)
        await db.commit()
        await db.refresh(capsule)
        
        return capsule

    async def get_today_capsules(self, user_id: UUID, db: AsyncSession) -> List[CuriosityCapsule]:
        """
        Get unread capsules for today/recent.
        """
        # For simplicity, just return all unread ones
        result = await db.execute(
            select(CuriosityCapsule)
            .where(CuriosityCapsule.user_id == user_id, CuriosityCapsule.is_read == False)
            .order_by(desc(CuriosityCapsule.created_at))
        )
        return result.scalars().all()

    async def mark_as_read(self, capsule_id: UUID, db: AsyncSession):
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if capsule:
            capsule.is_read = True
            await db.commit()

curiosity_capsule_service = CuriosityCapsuleService()
