"""
MilestoneHandler - 里程碑驱动的任务生成服务

Handles automatic task generation when milestones are achieved.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import TaskType
from app.models.task import TaskType as ModelTaskType
from app.services.llm_service import get_llm_service_for_task


class ProposalDecision(StrEnum):
    GENERATE = "generate"
    SKIP = "skip"
    DEFER = "defer"

@dataclass
class TaskGenerationProposal:
    proposal_id: str
    milestone_id: str
    plan_id: str
    reasoning: str
    suggested_count: int
    proposed_tasks: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class MilestoneHandler:
    """
    MilestoneHandler - 里程碑后自动任务生成处理器
    """

    # Milestones that trigger generation
    GENERATIVE_MILESTONES = {
        "ms-first-10-tasks",
        "ms-25-tasks",
        "ms-50-tasks",
        "ms-25pct-completion",   # 新增
        "ms-50pct-completion",
        "ms-75pct-completion",   # 新增
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def on_milestone_achieved(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: dict[str, Any],
        pending_task_count: int,
        current_plan_context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Handle a newly achieved milestone.

        Args:
            user_id: User ID
            plan_id: Plan ID
            milestone: The milestone data (dict)
            pending_task_count: Current number of pending tasks
            current_plan_context: Context for LLM generation (optional)

        Returns:
            action_id if proposal was stored, else None
        """
        milestone_id = milestone.get("id")

        # P1: Trigger knowledge galaxy update for any milestone achievement
        await self._trigger_galaxy_update(
            user_id=user_id,
            plan_id=plan_id,
            milestone=milestone,
            trigger_type="milestone_reached",
        )

        if not milestone_id or milestone_id not in self.GENERATIVE_MILESTONES:
            return None

        # 1. Evaluate need
        decision = await self._evaluate_generation_need(
            milestone_id, pending_task_count
        )
        if decision != ProposalDecision.GENERATE:
            logger.info(f"Milestone {milestone_id} handled: {decision}")
            return None

        # 2. Generate proposal
        logger.info(f"Generating tasks for milestone {milestone_id}")
        proposal = await self._generate_proposal(
            user_id, plan_id, milestone, current_plan_context
        )

        # 3. Store proposal to pending_actions
        if proposal:
            action_id = await self._store_proposal(proposal, user_id)
            return action_id

        return None

    async def _trigger_galaxy_update(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: dict[str, Any],
        trigger_type: str = "milestone_reached",
    ):
        """
        P1: Trigger knowledge galaxy update via Celery task

        Args:
            user_id: User ID
            plan_id: Plan ID
            milestone: Milestone data
            trigger_type: Type of trigger (milestone_reached/plan_complete)
        """
        try:
            from app.core.celery_app import celery_app

            # Prepare milestone data for the task
            milestone_data = {
                "id": milestone.get("id"),
                "name": milestone.get("title") or milestone.get("name"),
                "description": milestone.get("description", ""),
                "tags": milestone.get("tags", []),
                "learning_outcomes": milestone.get("learning_outcomes", []),
            }

            # Send task to Celery queue
            celery_app.send_task(
                "update_knowledge_galaxy",
                args=(str(user_id), str(plan_id), trigger_type),
                kwargs={"milestone_data": milestone_data},
                queue="default",
            )

            logger.info(
                f"Scheduled knowledge galaxy update for plan {plan_id}, "
                f"milestone {milestone.get('id')}"
            )

        except Exception as e:
            # Don't fail the milestone handler if galaxy update fails
            logger.warning(f"Failed to schedule galaxy update: {e}")

    async def _evaluate_generation_need(
        self, milestone_id: str, pending_count: int
    ) -> ProposalDecision:
        """
        Evaluate if we should generate new tasks.
        """
        # If user still has many pending tasks, maybe defer
        if pending_count >= 5:
             # But for major milestones like 50% completion, we might still want to propose next phase
            if milestone_id == "ms-50pct-completion":
                return ProposalDecision.GENERATE
            return ProposalDecision.DEFER

        return ProposalDecision.GENERATE

    async def _generate_proposal(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> TaskGenerationProposal | None:
        """
        Use LLM to generate task proposal.
        """
        import uuid

        # Prepare context for LLM
        plan_title = context.get("title", "Unknown Plan") if context else "Current Plan"
        milestone_title = milestone.get("title", milestone.get("id"))

        system_prompt = f"""
        You are an expert curriculum planner.
        The user has just achieved a milestone: "{milestone_title}" in their plan "{plan_title}".

        Goal: Propose 3-5 follow-up tasks to maintain momentum.
        Focus on:
        1. Progressive difficulty (slightly harder than previous)
        2. Variety (mix of learning and practice)
        3. Clear, actionable titles

        Return JSON format:
        {{
            "reasoning": "Brief explanation of why these tasks...",
            "tasks": [
                {{
                    "title": "Task Title",
                    "type": "learning|training",
                    "estimated_minutes": 30,
                    "difficulty": 3,
                    "priority": "high|medium|low"
                }}
            ]
        }}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please generate the next set of tasks."}
        ]

        try:
            # Use TaskType.TASK_DECOMPOSITION which maps to study_planner
            llm = get_llm_service_for_task(TaskType.TASK_DECOMPOSITION)
            result = await llm.chat_json(messages)

            tasks = result.get("tasks", [])
            if not tasks:
                return None

            proposal = TaskGenerationProposal(
                proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
                milestone_id=milestone.get("id"),
                plan_id=str(plan_id),
                reasoning=result.get("reasoning", "Generated based on milestone achievement."),
                suggested_count=len(tasks),
                proposed_tasks=tasks
            )
            return proposal

        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, using rule-based fallback")
            return await self._generate_rule_based(user_id, plan_id, milestone, context)

    async def _generate_rule_based(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> TaskGenerationProposal | None:
        """
        Rule-based fallback for task generation when LLM fails.
        """
        import uuid

        # Determine difficulty based on completed task count
        completed = 0
        if context and "task_index" in context:
            completed = context.get("task_index", {}).get("completed", 0)

        if completed < 15:
            _difficulty, task_difficulty = "easy", 2
        elif completed < 35:
            _difficulty, task_difficulty = "medium", 3
        else:
            _difficulty, task_difficulty = "hard", 4

        # Get plan title for context
        plan_title = "学习内容"
        if context:
            plan_title = context.get("title", context.get("name", "学习内容"))

        # Template tasks
        templates = [
            {
                "title": f"巩固练习 - {plan_title}",
                "type": "training",
                "estimated_minutes": 30,
                "priority": 2,
                "difficulty": task_difficulty,
            },
            {
                "title": "知识点回顾",
                "type": "reflection",
                "estimated_minutes": 15,
                "priority": 1,
                "difficulty": 2,
            },
            {
                "title": "拓展练习",
                "type": "learning",
                "estimated_minutes": 45,
                "priority": 3,
                "difficulty": min(5, task_difficulty + 1),
            },
        ]

        return TaskGenerationProposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
            milestone_id=milestone.get("id"),
            plan_id=str(plan_id),
            reasoning=f"基于已完成的 {completed} 个任务，为你推荐继续学习的内容",
            suggested_count=len(templates),
            proposed_tasks=templates,
        )

    async def _store_proposal(
        self,
        proposal: TaskGenerationProposal,
        user_id: UUID,
    ) -> str:
        """
        Store proposal to pending_actions for later user confirmation.
        """
        from app.core.pending_actions import pending_actions_store

        action_id = await pending_actions_store.save(
            tool_name="milestone_task_proposal",
            arguments={
                "proposal_id": proposal.proposal_id,
                "plan_id": proposal.plan_id,
                "milestone_id": proposal.milestone_id,
            },
            user_id=str(user_id),
            description=f"🎉 里程碑达成！为你推荐 {proposal.suggested_count} 个新任务",
            preview_data=proposal.to_dict(),
        )
        logger.info(f"Milestone proposal stored: {action_id}")
        return action_id

    async def confirm_proposal(
        self,
        proposal_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        User confirms proposal - create actual tasks.
        """
        from app.core.pending_actions import pending_actions_store
        from app.schemas.task import TaskCreate, coerce_task_type
        from app.services.task_service import TaskService

        # Get proposal from pending_actions
        action = await pending_actions_store.get(proposal_id, user_id)
        if not action:
            return {"success": False, "error": "Proposal not found or expired"}

        preview = action.get("preview_data", {})
        proposed_tasks = preview.get("proposed_tasks", [])
        plan_id_str = preview.get("plan_id")

        created_tasks = []
        try:
            for task_data in proposed_tasks:
                # Map task type string to enum
                task_type_str = task_data.get("type", "learning")
                task_type = coerce_task_type(task_type_str, default=ModelTaskType.LEARNING)

                # Map priority string to int
                priority_str = task_data.get("priority", "medium")
                if isinstance(priority_str, str):
                    priority_map = {"high": 3, "medium": 2, "low": 1}
                    priority = priority_map.get(priority_str.lower(), 2)
                else:
                    priority = int(priority_str) if priority_str else 2

                task_create = TaskCreate(
                    title=task_data.get("title", "New Task"),
                    type=task_type,
                    plan_id=UUID(plan_id_str) if plan_id_str else None,
                    estimated_minutes=task_data.get("estimated_minutes", 25),
                    priority=priority,
                    difficulty=task_data.get("difficulty", 2),
                )

                task = await TaskService.create(
                    db=self.db,
                    obj_in=task_create,
                    user_id=UUID(user_id),
                )
                created_tasks.append({"id": str(task.id), "title": task.title})

            # Clean up proposal
            await pending_actions_store.delete(proposal_id, user_id)

            logger.info(f"Created {len(created_tasks)} tasks from proposal {proposal_id}")

            return {
                "success": True,
                "proposal_id": proposal_id,
                "tasks_created": len(created_tasks),
                "tasks": created_tasks,
            }

        except Exception as e:
            logger.error(f"Failed to create tasks from proposal: {e}")
            return {
                "success": False,
                "error": str(e),
                "proposal_id": proposal_id,
            }
