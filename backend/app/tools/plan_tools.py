import json
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from app.models.plan import PlanStage as ModelPlanStage
from app.models.plan import PlanType as ModelPlanType
from app.models.task import TaskType as ModelTaskType
from app.orchestration.persona_aware_planner import PersonaAwarePlanner
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import llm_service
from app.services.plan_service import PlanService
from app.services.task_service import TaskService

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreatePlanParams, GenerateTasksForPlanParams


class _GeneratedPlanTaskSchema(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    type: str = Field(pattern="^(learning|training|error_fix|reflection)$")
    estimated_minutes: int = Field(ge=5, le=90)
    priority: int = Field(ge=1, le=5, default=2)


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
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_type = ModelPlanType(params.plan_type.value)
            plan_stage = None
            if params.plan_stage:
                plan_stage = ModelPlanStage(params.plan_stage.value)

            plan_create = PlanCreate(
                name=params.title,
                type=plan_type,
                plan_stage=plan_stage,
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
                    "plan_stage": plan.plan_stage.value if plan.plan_stage else None,
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
每个任务都在 15-45 分钟内可完成，并自动关联到指定计划。
自动利用知识图谱 (GraphRAG) 分析用户当前的知识掌握情况，生成更具针对性的任务。"""
    category = ToolCategory.PLAN
    parameters_schema = GenerateTasksForPlanParams
    requires_confirmation = True  # 需要用户确认才能创建

    async def execute(
        self,
        params: GenerateTasksForPlanParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_uuid = UUID(params.plan_id)

            # 第一步: 验证计划存在
            plan = await PlanService.get_by_id(db_session, plan_uuid)
            if not plan or plan.user_id != user_uuid:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"计划 {params.plan_id} 不存在或无权访问",
                    suggestion="请检查计划 ID 是否正确"
                )

            # 第二步: 获取知识图谱上下文 (GraphRAG)
            knowledge_context = ""
            rag_quality = "none"
            persona_constraints = await PersonaAwarePlanner(db_session).build_constraints(
                user_id=user_id,
                user_context_payload={},
                plan_context={},
                plan_id=params.plan_id,
            )
            try:
                from app.orchestration.graph_rag import GraphRAGRetriever
                logger.info(f"Querying Knowledge Graph for context: {params.topic} ({params.difficulty})")
                knowledge_service = KnowledgeService(db_session)
                retriever = GraphRAGRetriever(knowledge_service)

                # 构造查询：结合主题和难度，查询相关知识点和前置依赖
                query = f"{params.topic} {params.difficulty} learning path prerequisites"
                rag_result = await retriever.retrieve(query, str(user_uuid), depth=2)

                rag_context = getattr(rag_result, "fused_context", None)
                if isinstance(rag_context, str) and rag_context.strip() and len(rag_context.strip()) >= 20:
                    knowledge_context = rag_result.fused_context
                    logger.info("Retrieved GraphRAG context successfully")
                    if len(knowledge_context) > 200 and any(
                        keyword in knowledge_context
                        for keyword in ("mastery", "locked", "prerequisite", "前置", "掌握", "依赖")
                    ):
                        rag_quality = "high"
                    elif len(knowledge_context) > 50:
                        rag_quality = "low"
                    else:
                        rag_quality = "minimal"
                elif rag_result is not None:
                    logger.warning("GraphRAG returned invalid context, falling back to non-RAG planning")
                else:
                    logger.info("No relevant GraphRAG context found")
            except Exception as e:
                logger.warning(f"Failed to retrieve knowledge context (non-fatal): {e}")

            # 第三步: 调用 LLM 生成任务建议 (带知识上下文)
            task_list = await self._generate_tasks_with_llm(
                plan_title=plan.name,
                plan_description=plan.description,
                topic=params.topic,
                difficulty=params.difficulty,
                task_count=params.task_count,
                knowledge_context=knowledge_context,
                persona_constraints=persona_constraints,
            )

            if not task_list:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="LLM 生成任务失败",
                    suggestion="请稍后重试或手动创建任务"
                )

            # 第四步: 批量创建任务
            created_tasks = []
            for task_data in task_list:
                try:
                    validated = _GeneratedPlanTaskSchema.model_validate(task_data)
                    task_create = TaskCreate(
                        title=validated.title,
                        description=validated.description,
                        type=ModelTaskType(validated.type.upper()),
                        estimated_minutes=validated.estimated_minutes,
                        priority=validated.priority,
                        plan_id=plan_uuid
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

                    logger.debug(f"Created task: {task.id} for plan {plan_uuid}")

                except ValidationError as e:
                    logger.warning(f"Generated task failed schema validation: {e}")
                    continue
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

            logger.info(f"Generated {len(created_tasks)} tasks for plan {plan_uuid}")

            # 第五步: 返回卡片化结果
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "plan_id": params.plan_id,
                    "task_count": len(created_tasks),
                    "tasks": created_tasks,
                    "has_context": bool(knowledge_context),
                    "rag_quality": rag_quality,
                },
                widget_type="task_list",
                widget_data={
                    "tasks": created_tasks,
                    "plan_title": plan.name,
                    "source": "graph_augmented_ai" if knowledge_context else "ai_generated",
                    "rag_quality": rag_quality,
                    "persona_applied": True,
                    "persona_highlights": {
                        "max_session": getattr(persona_constraints, "max_session_minutes", None),
                        "task_size": getattr(persona_constraints, "preferred_task_size", None),
                        "time_multiplier": getattr(persona_constraints, "time_multiplier", None),
                        "warmup_included": getattr(persona_constraints, "require_warmup_task", False),
                    },
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
        plan_description: str | None,
        topic: str,
        difficulty: str,
        task_count: int,
        knowledge_context: str = "",
        persona_constraints: Any | None = None,
    ) -> list[dict] | None:
        """
        使用 LLM 生成结构化的任务建议 (支持 GraphRAG 上下文)
        """

        context_prompt = ""
        if knowledge_context:
            context_prompt = f"""
参考以下知识图谱上下文 (包含相关概念、前置知识和用户当前的掌握情况):
--------------------------------------------------
{knowledge_context}
--------------------------------------------------
请根据上述上下文调整任务：
1. 优先安排用户尚未掌握 (Status: Locked 或 Mastery 低) 的前置知识。
2. 对于已掌握的知识，可以生成复习或高阶应用任务。
3. 确保任务覆盖上下文中的关键盲点。
"""

        persona_prompt = ""
        max_session_minutes = 45
        if persona_constraints is not None and hasattr(persona_constraints, "to_prompt_block"):
            persona_prompt = persona_constraints.to_prompt_block()
            max_session_minutes = max(
                15,
                min(90, int(getattr(persona_constraints, "max_session_minutes", 45) or 45)),
            )

        prompt = f"""
你是一个学习规划专家。根据以下学习计划信息，生成 {task_count} 个具体可执行的微任务。

计划信息:
- 计划名称: {plan_title}
- 计划描述: {plan_description or "未提供"}
- 学习主题: {topic}
- 难度级别: {difficulty}

{context_prompt}

{persona_prompt}

任务要求:
1. 每个任务必须在 5-{max_session_minutes} 分钟内可完成，并尽量贴合 persona 约束中的 session 长度
2. 任务要具体可执行，不要模糊（例如"完成第 3-5 题练习题"而非"学习微积分概念"）
3. 若存在前置知识盲点，必须优先安排前置补齐任务，再进入主任务
4. 按难度递进顺序排列 (简单→中等→困难)
5. 任务类型选择: learning/training/error_fix/reflection
6. 优先级分配: 简单任务 1-2，中等 2-3，困难 4-5

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
            tasks = json.loads(response) if isinstance(response, str) else response

            # 验证和清理任务数据
            validated_tasks = []
            for task in tasks[:task_count]:  # 限制到请求的数量
                try:
                    normalized = _GeneratedPlanTaskSchema.model_validate(
                        {
                            "title": str(task.get("title", ""))[:100],
                            "description": str(task.get("description", ""))[:500],
                            "type": task.get("type", "learning"),
                            "estimated_minutes": min(
                                max(int(task.get("estimated_minutes", 25)), 5),
                                max_session_minutes,
                            ),
                            "priority": min(max(int(task.get("priority", 2)), 1), 5),
                        }
                    )
                    validated_tasks.append(normalized.model_dump())
                except (ValidationError, ValueError, TypeError) as e:
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
