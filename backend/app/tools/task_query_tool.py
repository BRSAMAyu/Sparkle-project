"""
P0-3: Task Query Tool - 任务卡片查询与修改工具

Allows LLM to query and modify specific task cards within a plan.
Tools:
- QueryPlanTasksTool: Query tasks with filters (status, type, limit)
- ModifyPlanTaskTool: Modify task properties (title, status, priority, guide_content)
"""
from __future__ import annotations
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from app.models.plan import Plan
from app.models.task import Task
from app.models.task import TaskStatus as ModelTaskStatus
from app.models.task import TaskType as ModelTaskType
from app.models.task_resources import TaskKnowledgeLink, TaskResourceLink, TaskResourceType
from app.schemas.task import TaskUpdate
from app.services.task_service import TaskService

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import (
    GetTaskDetailsParams,
    ModifyPlanTaskParams,
    QueryAllTasksParams,
    QueryPlanTasksParams,
    TaskStatusFilter,
)


class QueryPlanTasksTool(BaseTool):
    """查询计划内的任务列表"""

    name = "query_plan_tasks"
    description = """查询计划内的任务列表，支持按状态和类型筛选。
    当需要了解计划中有哪些任务、或查找特定状态的任务时使用，例如：
    - "这个计划里有哪些待办任务？"
    - "帮我看看已完成的任务"
    - "查找所有学习类型的任务"
    """
    category = ToolCategory.TASK
    parameters_schema = QueryPlanTasksParams
    requires_confirmation = False

    async def execute(
        self,
        params: QueryPlanTasksParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_uuid = UUID(params.plan_id)

            # Build query
            query = select(Task).where(
                and_(
                    Task.user_id == user_uuid,
                    Task.plan_id == plan_uuid,
                    Task.deleted_at.is_(None),
                )
            )

            # Apply status filter
            if params.status_filter != TaskStatusFilter.ALL:
                status_map = {
                    TaskStatusFilter.PENDING: ModelTaskStatus.PENDING,
                    TaskStatusFilter.IN_PROGRESS: ModelTaskStatus.IN_PROGRESS,
                    TaskStatusFilter.COMPLETED: ModelTaskStatus.COMPLETED,
                    TaskStatusFilter.ABANDONED: ModelTaskStatus.ABANDONED,
                }
                query = query.where(Task.status == status_map[params.status_filter])

            # Apply type filter
            if params.type_filter:
                query = query.where(Task.type == ModelTaskType(params.type_filter.value))

            # Order and limit
            query = query.order_by(Task.priority.desc(), Task.created_at.desc()).limit(
                params.limit
            )

            result = await db_session.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={"task_count": 0},
                    widget_type="task_list",
                    widget_data={"tasks": [], "message": "该计划下暂无符合条件的任务"},
                )

            # Format tasks for response
            task_list = []
            for task in tasks:
                task_list.append(
                    {
                        "id": str(task.id),
                        "title": task.title,
                        "guide_content": task.guide_content,  # 🔧 修复：添加guide_content字段
                        "type": task.type.value,
                        "status": task.status.value,
                        "priority": task.priority,
                        "difficulty": task.difficulty,
                        "energy_cost": task.energy_cost,  # 🔧 补充：能量消耗
                        "estimated_minutes": task.estimated_minutes,
                        "tags": task.tags or [],
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "user_id": str(user_uuid),  # 🔧 补充：用户ID
                    }
                )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_count": len(task_list)},
                widget_type="task_list",
                widget_data={
                    "tasks": task_list,
                    "plan_id": params.plan_id,
                    "filter": params.status_filter.value,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查 plan_id 是否为有效的 UUID 格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="查询失败，请稍后重试或检查参数",
            )


class ModifyPlanTaskTool(BaseTool):
    """修改计划内某个任务的属性"""

    name = "modify_plan_task"
    description = """修改计划内某个任务的属性，支持修改标题、状态、优先级和执行指南。
    当需要更新任务信息时使用，例如：
    - "把这个任务优先级设为5"
    - "更新任务的执行指南"
    - "把任务标记为完成"
    """
    category = ToolCategory.TASK
    parameters_schema = ModifyPlanTaskParams
    requires_confirmation = False

    async def execute(
        self,
        params: ModifyPlanTaskParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            task_uuid = UUID(params.task_id)

            # Fetch the task
            task = await TaskService.get_by_id(db_session, task_uuid, user_uuid)
            if not task:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="任务不存在或无权访问",
                    suggestion="请确认任务 ID 是否正确",
                )

            # Build update payload
            update_fields = {}

            if params.title is not None:
                update_fields["title"] = params.title

            if params.status is not None:
                status_map = {
                    "pending": ModelTaskStatus.PENDING,
                    "in_progress": ModelTaskStatus.IN_PROGRESS,
                    "completed": ModelTaskStatus.COMPLETED,
                    "abandoned": ModelTaskStatus.ABANDONED,
                }
                if params.status.lower() not in status_map:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        error_message=f"无效的状态值: {params.status}",
                        suggestion="状态应为 pending/in_progress/completed/abandoned 之一",
                    )
                update_fields["status"] = status_map[params.status.lower()]

            if params.priority is not None:
                update_fields["priority"] = params.priority

            if params.guide_content is not None:
                update_fields["guide_content"] = params.guide_content

            if not update_fields:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="未提供任何修改内容",
                    suggestion="请至少指定一个要修改的字段 (title/status/priority/guide_content)",
                )

            # Apply update
            task_update = TaskUpdate(**update_fields)
            updated_task = await TaskService.update(db_session, task, task_update)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "task_id": str(updated_task.id),
                    "updated_fields": list(update_fields.keys()),
                },
                widget_type="task_card",
                widget_data={
                    "id": str(updated_task.id),
                    "title": updated_task.title,
                    "guide_content": updated_task.guide_content,
                    "type": updated_task.type.value,
                    "status": updated_task.status.value,
                    "priority": updated_task.priority,
                    "estimated_minutes": updated_task.estimated_minutes,  # 🔧 补充：预计时间
                    "difficulty": updated_task.difficulty,  # 🔧 补充：难度
                    "energy_cost": updated_task.energy_cost,  # 🔧 补充：能量消耗
                    "tags": updated_task.tags or [],  # 🔧 补充：标签
                    "created_at": updated_task.created_at.isoformat() if updated_task.created_at else None,
                    "updated_at": updated_task.updated_at.isoformat()
                    if updated_task.updated_at
                    else None,
                    "user_id": str(user_uuid),  # 🔧 补充：用户ID
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查 task_id 是否为有效的 UUID 格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="修改失败，请稍后重试或检查参数",
            )


class GetTaskDetailsTool(BaseTool):
    """获取任务完整详情 - 供LLM深入了解任务内容"""

    name = "get_task_details"
    description = """获取某个任务的完整详情，包括执行指南、子任务、关联知识节点等。
    当需要了解任务具体内容、如何执行任务、或回答用户关于任务细节的问题时使用。
    例如：
    - "这个任务具体要做什么？"
    - "任务的学习指南是什么？"
    - "这个任务有哪些子任务？"
    - "任务关联了哪些知识点？"
    """
    category = ToolCategory.TASK
    parameters_schema = GetTaskDetailsParams
    requires_confirmation = False

    async def execute(
        self,
        params: GetTaskDetailsParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            task_uuid = UUID(params.task_id)

            # Fetch the task with relationships
            task = await TaskService.get_by_id(db_session, task_uuid, user_uuid)
            if not task:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="任务不存在或无权访问",
                    suggestion="请确认任务 ID 是否正确",
                )

            # Build comprehensive task details
            details = {
                "id": str(task.id),
                "title": task.title,
                "type": task.type.value,
                "status": task.status.value,
                "priority": task.priority,
                "difficulty": task.difficulty,
                "energy_cost": task.energy_cost,
                "estimated_minutes": task.estimated_minutes,
                "actual_minutes": task.actual_minutes,
                "tags": task.tags or [],
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }

            # Include plan info if available
            if task.plan_id:
                details["plan_id"] = str(task.plan_id)
                if task.plan:
                    details["plan_title"] = task.plan.name

            # Include guide content
            if params.include_guide and task.guide_content:
                details["guide_content"] = task.guide_content

            # Include user notes
            if task.user_note:
                details["user_note"] = task.user_note

            # Include subtasks
            if params.include_subtasks:
                subtasks = []
                try:
                    from app.models.task import SubTask
                    subtask_result = await db_session.execute(
                        select(SubTask)
                        .where(SubTask.parent_task_id == task_uuid)
                        .order_by(SubTask.order)
                    )
                    subtask_list = subtask_result.scalars().all()
                    for st in subtask_list:
                        subtasks.append({
                            "id": str(st.id),
                            "title": st.title,
                            "description": st.description,
                            "status": st.status.value,
                            "order": st.order,
                        })
                except Exception:
                    pass  # Subtasks not available

                details["subtasks"] = subtasks
                details["subtasks_total"] = task.subtasks_total
                details["subtasks_completed"] = task.subtasks_completed

            # Include knowledge context
            if params.include_knowledge_context and task.knowledge_node_id:
                details["knowledge_node_id"] = str(task.knowledge_node_id)
                # Try to fetch knowledge node info
                try:
                    from app.models.galaxy import KnowledgeNode
                    kn_result = await db_session.execute(
                        select(KnowledgeNode).where(KnowledgeNode.id == task.knowledge_node_id)
                    )
                    kn = kn_result.scalar_one_or_none()
                    if kn:
                        details["knowledge_context"] = {
                            "node_id": str(kn.id),
                            "title": kn.name,
                            "summary": kn.description[:200] if kn.description else None,
                            "mastery_level": None,
                        }
                except Exception:
                    pass  # Knowledge node not available

            if params.include_knowledge_context:
                related_nodes = []
                try:
                    from app.models.galaxy import KnowledgeNode
                    link_result = await db_session.execute(
                        select(TaskKnowledgeLink, KnowledgeNode)
                        .join(KnowledgeNode, TaskKnowledgeLink.knowledge_node_id == KnowledgeNode.id)
                        .where(TaskKnowledgeLink.task_id == task_uuid)
                        .order_by(TaskKnowledgeLink.order_index.asc())
                    )
                    link_rows = link_result.all()
                    for link, node in link_rows:
                        related_nodes.append(
                            {
                                "node_id": str(node.id),
                                "title": node.name,
                                "summary": node.description[:200] if node.description else None,
                                "relation_type": link.relation_type,
                                "strength": link.strength,
                                "is_primary": link.is_primary,
                            }
                        )
                except Exception:
                    related_nodes = []

                if task.knowledge_node_id and all(
                    n.get("node_id") != str(task.knowledge_node_id) for n in related_nodes
                ):
                    related_nodes.insert(
                        0,
                        {
                            "node_id": str(task.knowledge_node_id),
                            "title": details.get("knowledge_context", {}).get("title"),
                            "summary": details.get("knowledge_context", {}).get("summary"),
                            "relation_type": "primary",
                            "strength": None,
                            "is_primary": True,
                        },
                    )

                details["related_knowledge_nodes"] = related_nodes

            if params.include_learning_resources:
                learning_resources = []
                try:
                    link_result = await db_session.execute(
                        select(TaskResourceLink)
                        .where(TaskResourceLink.task_id == task_uuid)
                        .order_by(TaskResourceLink.order_index.asc())
                    )
                    links = link_result.scalars().all()

                    seed_item_ids = [
                        link.resource_id
                        for link in links
                        if link.resource_type == TaskResourceType.SEED_ITEM.value and link.resource_id
                    ]
                    seed_library_ids = [
                        link.resource_id
                        for link in links
                        if link.resource_type == TaskResourceType.SEED_LIBRARY.value and link.resource_id
                    ]

                    seed_items_by_id = {}
                    seed_libraries_by_id = {}

                    if seed_item_ids:
                        from app.models.seed_content import SeedItem
                        seed_items = await db_session.execute(
                            select(SeedItem).where(SeedItem.id.in_(seed_item_ids))
                        )
                        seed_items_by_id = {item.id: item for item in seed_items.scalars().all()}

                    if seed_library_ids:
                        from app.models.seed_content import SeedLibrary
                        seed_libs = await db_session.execute(
                            select(SeedLibrary).where(SeedLibrary.id.in_(seed_library_ids))
                        )
                        seed_libraries_by_id = {lib.id: lib for lib in seed_libs.scalars().all()}

                    for link in links:
                        resource = {
                            "id": str(link.id),
                            "resource_type": link.resource_type,
                            "resource_id": str(link.resource_id) if link.resource_id else None,
                            "title": link.title,
                            "summary": link.summary,
                            "url": link.url,
                            "metadata": link.resource_metadata,
                            "order_index": link.order_index,
                            "is_primary": link.is_primary,
                        }

                        if link.resource_type == TaskResourceType.SEED_ITEM.value and link.resource_id:
                            seed_item = seed_items_by_id.get(link.resource_id)
                            if seed_item:
                                summary = seed_item.content
                                if summary and len(summary) > 300:
                                    summary = summary[:300]
                                resource.update(
                                    {
                                        "title": resource["title"] or seed_item.title,
                                        "summary": resource["summary"] or summary,
                                        "seed_item_type": seed_item.item_type,
                                    }
                                )
                        elif link.resource_type == TaskResourceType.SEED_LIBRARY.value and link.resource_id:
                            seed_lib = seed_libraries_by_id.get(link.resource_id)
                            if seed_lib:
                                resource.update(
                                    {
                                        "title": resource["title"] or seed_lib.name,
                                        "summary": resource["summary"] or seed_lib.description,
                                        "seed_library_category": seed_lib.category,
                                        "seed_library_visibility": seed_lib.visibility,
                                    }
                                )

                        learning_resources.append(resource)
                except Exception:
                    learning_resources = []

                details["learning_resources"] = learning_resources

            # Include progress history (feedbacks)
            if params.include_progress_history:
                history = []
                try:
                    from app.models.task_feedback import TaskFeedback
                    fb_result = await db_session.execute(
                        select(TaskFeedback)
                        .where(TaskFeedback.task_id == task_uuid)
                        .order_by(TaskFeedback.created_at.desc())
                        .limit(10)
                    )
                    fb_list = fb_result.scalars().all()
                    for fb in fb_list:
                        history.append({
                            "id": str(fb.id),
                            "category": fb.category,
                            "feedback_text": fb.feedback_text,
                            "completion_quality": fb.completion_quality,
                            "created_at": fb.created_at.isoformat() if fb.created_at else None,
                        })
                except Exception:
                    pass  # Feedbacks not available

                details["progress_history"] = history

            return ToolResult(
                success=True,
                tool_name=self.name,
                data=details,
                widget_type="task_detail",
                widget_data=details,
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查 task_id 是否为有效的 UUID 格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="查询失败，请稍后重试",
            )


class QueryAllTasksTool(BaseTool):
    """跨计划查询任务 - 帮助LLM了解用户全局任务情况"""

    name = "query_all_tasks"
    description = """跨计划查询用户所有任务，用于计划切换或全局任务感知。
    当用户想了解所有任务情况、跨计划查看任务、或切换到其他计划时使用。
    例如：
    - "我还有哪些任务没完成？"
    - "看看其他计划的任务"
    - "我所有计划的待办任务"
    - "帮我找找数学计划的任务"
    """
    category = ToolCategory.TASK
    parameters_schema = QueryAllTasksParams
    requires_confirmation = False

    async def execute(
        self,
        params: QueryAllTasksParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)

            # Build plan query
            plan_query = select(Plan).where(
                and_(
                    Plan.user_id == user_uuid,
                    Plan.deleted_at.is_(None),
                )
            )

            # Filter by plan status if needed
            if not params.include_inactive_plans:
                plan_query = plan_query.where(
                    Plan.is_active
                )

            plan_query = plan_query.order_by(Plan.updated_at.desc())
            plan_result = await db_session.execute(plan_query)
            plans = plan_result.scalars().all()

            if not plans:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={"plan_count": 0, "task_count": 0},
                    widget_type="task_overview",
                    widget_data={
                        "plans": [],
                        "message": "暂无活跃计划",
                    },
                )

            # Query tasks for each plan
            plans_with_tasks = []
            total_task_count = 0

            for plan in plans:
                if total_task_count >= params.total_limit:
                    break

                # Build task query for this plan
                task_query = select(Task).where(
                    and_(
                        Task.user_id == user_uuid,
                        Task.plan_id == plan.id,
                        Task.deleted_at.is_(None),
                    )
                )

                # Apply status filter
                if params.status_filter != TaskStatusFilter.ALL:
                    status_map = {
                        TaskStatusFilter.PENDING: ModelTaskStatus.PENDING,
                        TaskStatusFilter.IN_PROGRESS: ModelTaskStatus.IN_PROGRESS,
                        TaskStatusFilter.COMPLETED: ModelTaskStatus.COMPLETED,
                        TaskStatusFilter.ABANDONED: ModelTaskStatus.ABANDONED,
                    }
                    task_query = task_query.where(
                        Task.status == status_map[params.status_filter]
                    )

                # Limit per plan
                remaining = params.total_limit - total_task_count
                limit = min(params.limit_per_plan, remaining)
                task_query = task_query.order_by(
                    Task.priority.desc(), Task.created_at.desc()
                ).limit(limit)

                task_result = await db_session.execute(task_query)
                tasks = task_result.scalars().all()

                if tasks:
                    task_list = []
                    for task in tasks:
                        task_list.append({
                            "id": str(task.id),
                            "title": task.title,
                            "guide_content": task.guide_content,  # 🔧 修复：添加guide_content
                            "type": task.type.value,
                            "status": task.status.value,
                            "priority": task.priority,
                            "difficulty": task.difficulty,
                            "energy_cost": task.energy_cost,  # 🔧 补充：能量消耗
                            "estimated_minutes": task.estimated_minutes,
                            "tags": task.tags or [],  # 🔧 补充：标签
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                            "user_id": str(user_uuid),  # 🔧 补充：用户ID
                        })

                    plans_with_tasks.append({
                        "plan_id": str(plan.id),
                        "plan_title": plan.name,
                        "plan_type": plan.type.value if plan.type else None,
                        "plan_status": "active" if plan.is_active else "inactive",
                        "task_count": len(task_list),
                        "tasks": task_list,
                    })

                    total_task_count += len(task_list)

            # Also query tasks without a plan (standalone tasks)
            if total_task_count < params.total_limit:
                standalone_query = select(Task).where(
                    and_(
                        Task.user_id == user_uuid,
                        Task.plan_id.is_(None),
                        Task.deleted_at.is_(None),
                    )
                )

                if params.status_filter != TaskStatusFilter.ALL:
                    status_map = {
                        TaskStatusFilter.PENDING: ModelTaskStatus.PENDING,
                        TaskStatusFilter.IN_PROGRESS: ModelTaskStatus.IN_PROGRESS,
                        TaskStatusFilter.COMPLETED: ModelTaskStatus.COMPLETED,
                        TaskStatusFilter.ABANDONED: ModelTaskStatus.ABANDONED,
                    }
                    standalone_query = standalone_query.where(
                        Task.status == status_map[params.status_filter]
                    )

                remaining = params.total_limit - total_task_count
                limit = min(params.limit_per_plan, remaining)
                standalone_query = standalone_query.order_by(
                    Task.priority.desc(), Task.created_at.desc()
                ).limit(limit)

                standalone_result = await db_session.execute(standalone_query)
                standalone_tasks = standalone_result.scalars().all()

                if standalone_tasks:
                    task_list = []
                    for task in standalone_tasks:
                        task_list.append({
                            "id": str(task.id),
                            "title": task.title,
                            "guide_content": task.guide_content,  # 🔧 修复：添加guide_content
                            "type": task.type.value,
                            "status": task.status.value,
                            "priority": task.priority,
                            "difficulty": task.difficulty,
                            "energy_cost": task.energy_cost,  # 🔧 补充：能量消耗
                            "estimated_minutes": task.estimated_minutes,
                            "tags": task.tags or [],  # 🔧 补充：标签
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                            "user_id": str(user_uuid),  # 🔧 补充：用户ID
                        })

                    plans_with_tasks.append({
                        "plan_id": None,
                        "plan_title": "独立任务",
                        "plan_type": None,
                        "plan_status": None,
                        "task_count": len(task_list),
                        "tasks": task_list,
                    })

                    total_task_count += len(task_list)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "plan_count": len(plans_with_tasks),
                    "task_count": total_task_count,
                },
                widget_type="task_overview",
                widget_data={
                    "plans": plans_with_tasks,
                    "status_filter": params.status_filter.value,
                    "total_tasks": total_task_count,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查参数格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="查询失败，请稍后重试",
            )
