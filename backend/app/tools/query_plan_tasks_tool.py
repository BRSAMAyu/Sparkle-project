"""
Query Plan Tasks Tool - LLM查询任务卡工具

允许 LLM 查询特定计划的任务卡，支持多种过滤条件。
这是反馈闭环系统的关键组件，使 LLM 能够感知特定计划的任务状态。
"""
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.models.task import Task
from app.tools.base import BaseTool, ToolCategory, ToolContext


class QueryPlanTasksTool(BaseTool):
    """
    查询计划任务卡工具

    供 LLM 使用，查询特定计划的任务卡，支持:
    - 按状态过滤 (PENDING, IN_PROGRESS, COMPLETED, ABANDONED)
    - 按类型过滤 (LEARNING, TRAINING, ERROR_FIX, etc.)
    - 按难度范围过滤
    - 按知识节点过滤
    """

    name = "query_plan_tasks"
    category = ToolCategory.QUERY
    description = """
查询特定学习计划的任务卡。

用途:
- 查看某个计划的待完成任务
- 获取已完成任务列表
- 按难度或类型筛选任务
- 了解计划进度

使用场景:
- 用户询问"这个计划还有什么任务"
- 需要根据任务状态调整计划
- 分析任务分布和难度
    """

    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "计划ID (必需)"
            },
            "status_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "状态过滤: PENDING, IN_PROGRESS, COMPLETED, ABANDONED",
                "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "ABANDONED"]
            },
            "type_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "类型过滤: LEARNING, TRAINING, ERROR_FIX, REFLECTION, SOCIAL, PLANNING, OCR"
            },
            "difficulty_range": {
                "type": "object",
                "properties": {
                    "min": {"type": "integer", "minimum": 1, "maximum": 5},
                    "max": {"type": "integer", "minimum": 1, "maximum": 5}
                },
                "description": "难度范围 (1-5)"
            },
            "knowledge_node": {
                "type": "string",
                "description": "按知识节点过滤 (存储在 tags.knowledge_nodes 中)"
            },
            "limit": {
                "type": "integer",
                "description": "返回数量限制 (默认20，最大50)",
                "default": 20,
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["plan_id"]
    }

    async def execute(
        self,
        params: dict[str, Any],
        context: ToolContext
    ) -> dict[str, Any]:
        """
        执行查询

        Args:
            params: 查询参数
            context: 工具上下文

        Returns:
            Dict: 查询结果
        """
        plan_id_str = params.get("plan_id")
        if not plan_id_str:
            return {
                "success": False,
                "error": "plan_id is required",
                "tasks": []
            }

        try:
            plan_id = UUID(plan_id_str)
        except ValueError:
            return {
                "success": False,
                "error": "Invalid plan_id format",
                "tasks": []
            }

        # 获取参数
        status_filter = params.get("status_filter")
        type_filter = params.get("type_filter")
        difficulty_range = params.get("difficulty_range")
        knowledge_node = params.get("knowledge_node")
        limit = min(params.get("limit", 20), 50)  # 限制最大50条

        # 构建查询
        query = select(Task).where(
            Task.plan_id == plan_id,
            Task.user_id == context.user_id,
            Task.deleted_at.is_(None)
        )

        # 应用过滤
        if status_filter:
            query = query.where(Task.status.in_(status_filter))

        if type_filter:
            query = query.where(Task.type.in_(type_filter))

        if difficulty_range:
            min_diff = difficulty_range.get("min", 1)
            max_diff = difficulty_range.get("max", 5)
            query = query.where(Task.difficulty.between(min_diff, max_diff))

        query = query.order_by(Task.order_index).limit(limit)

        # 执行查询
        result = await context.db_session.execute(query)
        tasks = result.scalars().all()

        # 过滤知识节点（需要JSON查询）
        if knowledge_node:
            filtered_tasks = []
            for task in tasks:
                task_tags = task.tags or {}
                task_nodes = task_tags.get("knowledge_nodes", [])
                if knowledge_node in task_nodes:
                    filtered_tasks.append(task)
            tasks = filtered_tasks

        # 转换为字典格式
        task_dicts = []
        for task in tasks:
            task_dict = {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "type": task.type.value,
                "estimated_minutes": task.estimated_minutes,
                "difficulty": task.difficulty,
                "energy_cost": task.energy_cost,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "tags": task.tags or {},
                "subtasks_total": task.subtasks_total,
                "guide_content": task.guide_content[:200] if task.guide_content else None  # 截断长内容
            }

            # 添加执行统计（如果有）
            if task.actual_minutes:
                task_dict["actual_minutes"] = task.actual_minutes
            if task.completed_at:
                task_dict["completed_at"] = task.completed_at.isoformat()

            task_dicts.append(task_dict)

        logger.info(
            f"Query plan tasks: plan_id={plan_id}, "
            f"found={len(task_dicts)} tasks, "
            f"filters={params}"
        )

        return {
            "success": True,
            "plan_id": plan_id_str,
            "count": len(task_dicts),
            "tasks": task_dicts
        }
