"""
Feedback Service
Generates feedback for completed tasks using LLM.
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.models.user import User
from app.core.llm_client import llm_client

class FeedbackService:
    async def generate_feedback(self, task: Task, user: User, db: AsyncSession) -> Dict[str, Any]:
        """
        Generate feedback for a completed task.
        """
        # 1. Prepare context for LLM
        prompt = f"""
        Task: {task.title}
        Type: {task.type}
        Estimated time: {task.estimated_minutes} minutes
        Actual time: {task.actual_minutes} minutes
        User Note: {task.user_note or 'None'}
        Difficulty: {task.difficulty}/5
        
        User Preferences:
        - Depth: {user.depth_preference}
        - Curiosity: {user.curiosity_preference}
        
        Generate brief, constructive feedback (Markdown format).
        Include:
        1. Acknowledgment of effort.
        2. Analysis of time management (if actual vs estimated differs significantly).
        3. A "Next Step" suggestion based on user preferences.
        
        Keep it under 100 words.
        """
        
        # Mock LLM response for MVP
        # response = await llm_client.generate(prompt)
        
        feedback_text = f"Great job on completing **{task.title}**!\n\n"
        
        if task.actual_minutes and task.actual_minutes > task.estimated_minutes * 1.2:
            feedback_text += f"It took a bit longer than expected ({task.actual_minutes}m vs {task.estimated_minutes}m). Consider breaking down similar tasks into smaller chunks next time.\n\n"
        elif task.actual_minutes and task.actual_minutes < task.estimated_minutes * 0.8:
            feedback_text += f"You finished faster than planned! You might be ready for more challenging tasks in this area.\n\n"
        else:
            feedback_text += "Your time estimation was spot on.\n\n"
            
        feedback_text += "**Next Step:** "
        if user.curiosity_preference > 0.6:
            feedback_text += "Why not explore a related advanced topic? Check out the Knowledge Galaxy for connections."
        else:
            feedback_text += "Review your notes and consolidate what you've learned."

        return {
            "content": feedback_text,
            "flame_bonus": 5, # Example bonus
            "galaxy_update": "Knowledge node updated."
        }

feedback_service = FeedbackService()
