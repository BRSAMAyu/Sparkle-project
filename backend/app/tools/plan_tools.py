from typing import Any, Optional, List
from uuid import UUID
import json
from loguru import logger

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreatePlanParams, GenerateTasksForPlanParams
from app.services.plan_service import PlanService
from app.services.task_service import TaskService
from app.services.llm_service import llm_service
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.models.plan import PlanType as ModelPlanType
from app.models.task import TaskType as ModelTaskType


class CreatePlanTool(BaseTool):
    """创建学习计划"""
    name = "create_plan"
    description = """创建冲刺计划或成长计划，并返回计划卡片。"""
    category = ToolCategory.PLAN
    parameters_schema = CreatePlanParams
    requires_confirmation = False

    async def execute(
        self,
        params: CreatePlanParams,
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_type = ModelPlanType(params.plan_type.value)

            plan_create = PlanCreate(
                name=params.title,
                type=plan_type,
                description=params.description,
                subject=params.subject_id,
                target_date=params.target_date.date() if params.target_date else None,
                daily_available_minutes=60,
            )

            plan = await PlanService.create(
                db=db_session,
                obj_in=plan_create,
                user_id=user_uuid
            )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"plan_id": str(plan.id)},
                widget_type="plan_card",
                widget_data={
                    "id": str(plan.id),
                    "title": plan.name,
                    "type": plan.type.value,
                    "description": plan.description,
                    "target_date": plan.target_date.isoformat() if plan.target_date else None,
                    "target_mastery": params.target_mastery,
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请检查计划参数或稍后再试"
            )


class GenerateTasksForPlanTool(BaseTool):
    """P1: 根据学习计划自动生成可执行的微任务"""
    name = "generate_tasks_for_plan"
    description = """根据给定的学习计划和主题，使用 AI 智能生成 3-8 个具体可执行的微任务。
每个任务都在 15-45 分钟内可完成，并自动关联到指定计划。"""
    category = ToolCategory.PLAN
    parameters_schema = GenerateTasksForPlanParams
    requires_confirmation = True  # 需要用户确认才能创建

    async def execute(
        self,
        params: GenerateTasksForPlanParams,
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        """
        为计划生成任务的实现

        流程:
        1. 验证计划存在且属于当前用户
        2. 调用 LLM 生成结构化任务建议
        3. 批量创建任务并关联到计划
        4. 返回卡片化的任务列表
        """
        try:
            user_uuid = UUID(user_id)
            plan_id_uuid = UUID(params.plan_id)

            # 第一步: 验证计划存在
            plan = await PlanService.get_by_id(db_session, plan_id_uuid)
            if not plan or plan.user_id != user_uuid:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"计划 {params.plan_id} 不存在或无权访问",
                    suggestion="请检查计划 ID 是否正确"
                )

            # 第二步: 调用 LLM 生成任务建议
            task_list = await self._generate_tasks_with_llm(
                plan_title=plan.name,
                plan_description=plan.description,
                topic=params.topic,
                difficulty=params.difficulty,
                task_count=params.task_count
            )

            if not task_list:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="LLM 生成任务失败",
                    suggestion="请稍后重试或手动创建任务"
                )

            # 第三步: 批量创建任务
            created_tasks = []
            for task_data in task_list:
                try:
                    task_create = TaskCreate(
                        title=task_data["title"],
                        description=task_data.get("description"),
                        type=ModelTaskType(task_data.get("type", "learning")),
                        estimated_minutes=task_data.get("estimated_minutes", 25),
                        priority=task_data.get("priority", 2),
                        plan_id=plan_id_uuid
                    )

                    task = await TaskService.create(
                        db=db_session,
                        obj_in=task_create,
                        user_id=user_uuid
                    )

                    created_tasks.append({
                        "id": str(task.id),
                        "title": task.title,
                        "type": task.type.value,
                        "estimated_minutes": task.estimated_minutes,
                        "priority": task.priority,
                        "description": task.description
                    })

                    logger.debug(f"Created task: {task.id} for plan {plan_id_uuid}")

                except Exception as e:
                    logger.warning(f"Failed to create task: {e}, continuing...")
                    continue

            if not created_tasks:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="无法创建任何任务",
                    suggestion="请检查计划信息并重试"
                )

            logger.info(f"Generated {len(created_tasks)} tasks for plan {plan_id_uuid}")

            # 第四步: 返回卡片化结果
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "plan_id": params.plan_id,
                    "task_count": len(created_tasks),
                    "tasks": created_tasks
                },
                widget_type="task_list",
                widget_data={
                    "tasks": created_tasks,
                    "plan_title": plan.name,
                    "source": "ai_generated"
                }
            )

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="计划 ID 格式错误",
                suggestion="请使用有效的 UUID 格式"
            )
        except Exception as e:
            logger.error(f"Generate tasks failed: {e}")
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"生成任务失败: {str(e)}",
                suggestion="请检查参数或稍后重试"
            )

    async def _generate_tasks_with_llm(
        self,
        plan_title: str,
        plan_description: Optional[str],
        topic: str,
        difficulty: str,
        task_count: int
    ) -> Optional[List[dict]]:
        """
        使用 LLM 生成结构化的任务建议

        返回任务列表，每个任务包含:
        - title: 任务标题
        - description: 任务描述
        - type: 任务类型 (learning/training/error_fix/reflection)
        - estimated_minutes: 预估时长 (15-45分钟)
        - priority: 优先级 (1-5)
        """
        prompt = f"""
你是一个学习规划专家。根据以下学习计划信息，生成 {task_count} 个具体可执行的微任务。

计划信息:
- 计划名称: {plan_title}
- 计划描述: {plan_description or "未提供"}
- 学习主题: {topic}
- 难度级别: {difficulty}

任务要求:
1. 每个任务必须在 15-45 分钟内可完成
2. 任务要具体可执行，不要模糊（例如"完成第 3-5 题练习题"而非"学习微积分概念"）
3. 按难度递进顺序排列 (简单→中等→困难)
4. 任务类型选择: learning/training/error_fix/reflection
5. 优先级分配: 简单任务 1-2，中等 2-3，困难 4-5

返回格式必须是有效的 JSON 数组，包含 {task_count} 个任务对象:
```json
[
  {{
    "title": "具体任务标题",
    "description": "任务描述和要求",
    "type": "learning|training|error_fix|reflection",
    "estimated_minutes": 25,
    "priority": 2
  }},
  ...
]
```

严格返回 JSON 格式，不要其他文本。
"""

        try:
            response = await llm_service.chat_json(
                prompt=prompt,
                schema=None  # 使用 chat_json 的自动 JSON 提取
            )

            if not response:
                logger.warning("LLM returned empty response")
                return None

            # 解析 JSON 响应
            if isinstance(response, str):
                tasks = json.loads(response)
            else:
                tasks = response

            # 验证和清理任务数据
            validated_tasks = []
            for task in tasks[:task_count]:  # 限制到请求的数量
                try:
                    validated_tasks.append({
                        "title": str(task.get("title", ""))[:100],  # 最多 100 字
                        "description": str(task.get("description", ""))[:500],  # 最多 500 字
                        "type": task.get("type", "learning"),
                        "estimated_minutes": min(max(int(task.get("estimated_minutes", 25)), 15), 45),  # 15-45 分钟
                        "priority": min(max(int(task.get("priority", 2)), 1), 5)  # 1-5 优先级
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse task: {e}, skipping")
                    continue

            if not validated_tasks:
                logger.warning("No valid tasks after validation")
                return None

            logger.info(f"Generated {len(validated_tasks)} validated tasks from LLM")
            return validated_tasks

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
