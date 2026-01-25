"""
MilestoneHandler - 里程碑驱动的任务生成服务

Handles automatic task generation when milestones are achieved.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import llm_service, get_llm_service_for_task
from app.core.agent_profiles import TaskType

class ProposalDecision(str, Enum):
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
    proposed_tasks: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
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
        "ms-50pct-completion",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def on_milestone_achieved(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: Dict[str, Any],
        pending_task_count: int,
        current_plan_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskGenerationProposal]:
        """
        Handle a newly achieved milestone.

        Args:
            user_id: User ID
            plan_id: Plan ID
            milestone: The milestone data (dict)
            pending_task_count: Current number of pending tasks
            current_plan_context: Context for LLM generation (optional)

        Returns:
            TaskGenerationProposal if generated, else None
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

        return proposal

    async def _trigger_galaxy_update(
        self,
        user_id: UUID,
        plan_id: UUID,
        milestone: Dict[str, Any],
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
        milestone: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Optional[TaskGenerationProposal]:
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
            logger.error(f"Failed to generate milestone proposal: {e}")
            return None
