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

        # 3. Store proposal via authoritative command path (action_proposals)
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
            # Prepare milestone data for the task
            milestone_data = {
                "id": milestone.get("id"),
                "name": milestone.get("title") or milestone.get("name"),
                "description": milestone.get("description", ""),
                "tags": milestone.get("tags", []),
                "learning_outcomes": milestone.get("learning_outcomes", []),
            }

            # Send task to Celery queue（P2DISPATCH：改接统一投递面，带背压）
            from app.core.celery_dispatch import dispatch_task_async

            dispatched_ok = await dispatch_task_async(
                "update_knowledge_galaxy",
                args=(str(user_id), str(plan_id), trigger_type),
                kwargs={"milestone_data": milestone_data},
                queue="default",
            )
            if not dispatched_ok:
                logger.warning(
                    f"Knowledge galaxy update dispatch dropped/failed for plan {plan_id}, "
                    f"milestone {milestone.get('id')}"
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
    ) -> str | None:
        """
        Store proposal for later user confirmation.

        X-03 R2 P2-1 返修：走统一权威 command path（``task.create_batch`` proposal
        落账 action_proposals，source=system），不再写 Redis 侧 pending_actions——
        里程碑提案获得持久状态/授权门/恰一次/receipt 全套协议语义；幂等键绑定
        (milestone, plan)，同里程碑重复触发恰一条 proposal。
        """
        from app.core.action_command import ActionCommandError
        from app.services.action_command_service import ActionCommandService

        try:
            result = await ActionCommandService(self.db).create_proposal(
                user_id=user_id,
                command_type="task.create_batch",
                payload={
                    "tasks": self._normalize_proposed_tasks(
                        proposal.proposed_tasks, plan_id=proposal.plan_id
                    )
                },
                source="system",
                idempotency_key=f"milestone:{proposal.milestone_id}:{proposal.plan_id}",
                summary=f"里程碑达成！为你推荐 {proposal.suggested_count} 个新任务",
            )
        except ActionCommandError as exc:
            # 预筛拒绝（如 title 校验失败）不阻断里程碑流程——降级为无提案
            logger.warning(f"Milestone proposal rejected by command path: {exc}")
            return None
        logger.info(f"Milestone proposal stored: {result.proposal.id}")
        return str(result.proposal.id)

    @staticmethod
    def _normalize_proposed_tasks(
        proposed_tasks: list[dict[str, Any]],
        *,
        plan_id: str,
    ) -> list[dict[str, Any]]:
        """LLM/模板产出的任务规格 → TaskCreate 兼容规格（原 confirm 路径的归一逻辑前移）."""
        from app.schemas.task import coerce_task_type

        normalized: list[dict[str, Any]] = []
        for task_data in proposed_tasks:
            task_type = coerce_task_type(
                task_data.get("type", "learning"), default=ModelTaskType.LEARNING
            )
            priority_raw = task_data.get("priority", 2)
            if isinstance(priority_raw, str):
                priority_map = {"high": 3, "medium": 2, "low": 1}
                priority = priority_map.get(priority_raw.lower(), 2)
            else:
                priority = int(priority_raw) if priority_raw else 2
            normalized.append(
                {
                    "title": str(task_data.get("title") or "New Task").strip()[:255],
                    "type": task_type.value if task_type is not None else "learning",
                    "plan_id": plan_id,
                    "estimated_minutes": task_data.get("estimated_minutes", 25),
                    "priority": priority,
                    "difficulty": task_data.get("difficulty", 2),
                }
            )
        return normalized

    async def confirm_proposal(
        self,
        proposal_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        User confirms proposal - create actual tasks.

        X-03 R2 P2-1 返修：确认走统一权威 command path（``ActionCommandService
        .approve``）。V2 缺陷（get→create×N→delete 非原子，双确认竞窗内重复建
        任务）由协议恰一次语义幂等根治：重复确认重放 ``already_committed`` 零新
        写；崩溃后重放亦恰一次（守卫写与领域写同 commit）。返回结构保持旧契约
        （success/proposal_id/tasks_created/tasks）。
        """
        from app.core.action_command import ActionCommandError, ProposalNotFoundError
        from app.services.action_command_service import ActionCommandService

        service = ActionCommandService(self.db)
        try:
            result = await service.approve(proposal_id, user_id=user_id)
        except ProposalNotFoundError:
            return {"success": False, "error": "Proposal not found or expired"}
        except ActionCommandError as exc:
            # 过期/终态封闭/版本冲突等协议拒绝——结构化错误透传旧契约形态
            return {"success": False, "error": str(exc), "proposal_id": proposal_id}

        receipt = result.proposal.receipt or {}
        created = (receipt.get("subject_after") or {}).get("created") or []
        tasks = [
            {"id": str(item.get("ref", "")).removeprefix("task://"), "title": item.get("title")}
            for item in created
        ]
        if not tasks:
            effects = receipt.get("effects") or []
            if effects and effects[0].get("kind") == "task.created_batch":
                tasks = [
                    {"id": ref.removeprefix("task://"), "title": ""} for ref in effects[0].get("refs", [])
                ]

        logger.info(
            f"Confirmed milestone proposal {proposal_id}: "
            f"{'replay' if result.already_committed else 'committed'}, {len(tasks)} tasks"
        )
        return {
            "success": True,
            "proposal_id": proposal_id,
            "tasks_created": len(tasks),
            "tasks": tasks,
        }
