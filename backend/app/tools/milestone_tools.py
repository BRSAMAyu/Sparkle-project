"""
Milestone interaction tools for LLM.

Allows the LLM to confirm or dismiss milestone task proposals.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool


class ConfirmMilestoneProposalTool(BaseTool):
    """Confirm a milestone task proposal and create the tasks."""
    name = "confirm_milestone_proposal"
    description = "确认里程碑提案，创建推荐的任务。当用户表示同意、确认或接受里程碑推荐的任务时使用。"
    category = "plan"

    async def execute(
        self,
        db: AsyncSession,
        user_id: str,
        proposal_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Confirm a milestone proposal and create the recommended tasks.

        Args:
            db: Database session
            user_id: User ID
            proposal_id: The proposal ID to confirm

        Returns:
            Result with created task information
        """
        from app.services.milestone_handler import MilestoneHandler

        handler = MilestoneHandler(db)
        result = await handler.confirm_proposal(proposal_id, user_id)

        return self.format_result(
            success=result.get("success", False),
            tool_name=self.name,
            data=result,
            message=f"已创建 {result.get('tasks_created', 0)} 个任务" if result.get("success") else result.get("error", "确认失败"),
        )


class DismissMilestoneProposalTool(BaseTool):
    """Dismiss a milestone task proposal."""
    name = "dismiss_milestone_proposal"
    description = "忽略里程碑提案。当用户表示拒绝、不需要或忽略里程碑推荐的任务时使用。"
    category = "plan"

    async def execute(
        self,
        db: AsyncSession,
        user_id: str,
        proposal_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Dismiss a milestone proposal without creating tasks.

        Args:
            db: Database session
            user_id: User ID
            proposal_id: The proposal ID to dismiss

        Returns:
            Result indicating the proposal was dismissed
        """
        from app.core.pending_actions import pending_actions_store

        success = await pending_actions_store.delete(proposal_id, user_id)

        return self.format_result(
            success=success,
            tool_name=self.name,
            data={"action": "dismissed", "proposal_id": proposal_id},
            message="提案已忽略" if success else "提案不存在或已过期",
        )
