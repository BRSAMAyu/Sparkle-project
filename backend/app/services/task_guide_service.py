"""
Task Guide Service
Generates AI guides for tasks based on user preferences and task details.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.models.user import User

class TaskGuideService:
    async def generate_guide(self, task: Task, user: User, db: AsyncSession) -> str:
        """
        Generate a step-by-step guide for the task.
        TODO: Integrate with LLM service.
        """
        # Placeholder implementation for now
        return f"""
# Guide for: {task.title}

## Overview
This is an AI-generated guide to help you complete this task efficiently.

## Steps
1. **Preparation**: Gather necessary materials.
2. **Execution**: Focus on the core objective.
3. **Review**: Check your work against the requirements.

## Tips
- Break it down into smaller chunks if needed.
- Stay focused!
"""

task_guide_service = TaskGuideService()
