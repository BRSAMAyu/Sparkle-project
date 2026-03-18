"""
Milestone interaction tools for LLM.

Allows the LLM to confirm or dismiss milestone task proposals.
"""
from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolCategory, ToolResult

# ============ Parameter Schemas ============

class ConfirmMilestoneProposalParams(BaseModel):
    """确认里程碑提案的参数"""
    proposal_id: str = Field(..., description="提案ID")


class DismissMilestoneProposalParams(BaseModel):
    """忽略里程碑提案的参数"""
    proposal_id: str = Field(..., description="提案ID")


# ============ Tool Implementations ============

class ConfirmMilestoneProposalTool(BaseTool):
    """Confirm a milestone task proposal and create the tasks."""
    name = "confirm_milestone_proposal"
    description = "确认里程碑提案，创建推荐的任务。当用户表示同意、确认或接受里程碑推荐的任务时使用。"
    category = ToolCategory.PLAN
    parameters_schema = ConfirmMilestoneProposalParams
    requires_confirmation = False

    async def execute(
        self,
        params: ConfirmMilestoneProposalParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        """
        Confirm a milestone proposal and create the recommended tasks.

        Args:
            params: Tool parameters containing proposal_id
            user_id: User ID
            db_session: Database session
            tool_call_id: Tool call ID for tracking

        Returns:
            ToolResult with created task information
        """
        try:
            from app.services.milestone_handler import MilestoneHandler

            handler = MilestoneHandler(db_session)
            result = await handler.confirm_proposal(params.proposal_id, user_id)

            if result.get("success"):
                tasks_created = result.get("tasks_created", 0)
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={
                        "proposal_id": params.proposal_id,
                        "tasks_created": tasks_created,
                        "task_ids": result.get("task_ids", [])
                    },
                    widget_type="task_list",
                    widget_data={
                        "tasks": result.get("tasks", []),
                        "message": f"已创建 {tasks_created} 个任务"
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=result.get("error", "确认失败"),
                    suggestion="请确认提案ID是否正确或稍后重试"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="确认提案时发生错误，请稍后重试"
            )


class DismissMilestoneProposalTool(BaseTool):
    """Dismiss a milestone task proposal."""
    name = "dismiss_milestone_proposal"
    description = "忽略里程碑提案。当用户表示拒绝、不需要或忽略里程碑推荐的任务时使用。"
    category = ToolCategory.PLAN
    parameters_schema = DismissMilestoneProposalParams
    requires_confirmation = False

    async def execute(
        self,
        params: DismissMilestoneProposalParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        """
        Dismiss a milestone proposal without creating tasks.

        Args:
            params: Tool parameters containing proposal_id
            user_id: User ID
            db_session: Database session
            tool_call_id: Tool call ID for tracking

        Returns:
            ToolResult indicating the proposal was dismissed
        """
        try:
            from app.core.pending_actions import pending_actions_store

            success = await pending_actions_store.delete(params.proposal_id, user_id)

            return ToolResult(
                success=success,
                tool_name=self.name,
                data={
                    "action": "dismissed",
                    "proposal_id": params.proposal_id
                },
                widget_data={
                    "message": "提案已忽略" if success else "提案不存在或已过期"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="忽略提案时发生错误，请稍后重试"
            )
