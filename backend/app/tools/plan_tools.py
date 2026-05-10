"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.models.plan import PlanStage as ModelPlanStage
from app.models.plan import PlanType as ModelPlanType
from app.models.task import TaskType as ModelTaskType
from app.orchestration.persona_aware_planner import PersonaAwarePlanner
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.knowledge_service import KnowledgeService
from app.services.llm_fallback_utils import plan_llm
from app.services.plan_service import PlanService
from app.services.task_service import TaskService

from .base import BaseTool, ToolCategory, ToolResult
from .entity_cards import (
    build_plan_entity_card,
    build_task_list_entity_card,
    wrap_widget_payload,
)
from .schemas import CreatePlanParams, GenerateTasksForPlanParams


class _GeneratedPlanTaskSchema(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    type: str = Field(pattern="^(learning|training|error_fix|reflection)$")
    estimated_minutes: int = Field(ge=5, le=90)
    priority: int = Field(ge=1, le=5, default=2)


class _LearningPathNodeRef(BaseModel):
    id: UUID
    name: str


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
        tool_call_id: str | None = None,
        locale: str = "en",
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

            plan_payload = {
                "id": str(plan.id),
                "title": plan.name,
                "type": plan.type.value,
                "plan_stage": plan.plan_stage.value if plan.plan_stage else None,
                "description": plan.description,
                "subject": getattr(plan, "subject", None),
                "progress": getattr(plan, "progress", 0),
                "is_active": getattr(plan, "is_active", True),
                "is_primary": getattr(plan, "is_primary", False),
                "task_count": 0,
                "source": getattr(plan, "source", None),
                "target_date": plan.target_date.isoformat() if plan.target_date else None,
                "target_mastery": params.target_mastery,
            }
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"plan_id": str(plan.id)},
                widget_type="plan_card",
                widget_data=wrap_widget_payload(
                    widget_type="plan_card",
                    widget_data=plan_payload,
                    entity_card=build_plan_entity_card(
                        plan_payload,
                        tool_name=self.name,
                        tool_result_id=tool_call_id,
                        locale=locale,
                    ),
                ),
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
    timeout_seconds = 90.0  # LLM-powered generation, may take longer

    @staticmethod
    def _resolve_max_session_minutes(persona_constraints: Any | None) -> int:
        if persona_constraints is None:
            return 45
        return max(
            15,
            min(90, int(getattr(persona_constraints, "max_session_minutes", 45) or 45)),
        )

    @staticmethod
    def _infer_difficulty(task_type: str, priority: int) -> int:
        normalized_type = (task_type or "").lower()
        if normalized_type in {"reflection"}:
            return 1
        if normalized_type in {"training", "error_fix"}:
            return min(5, max(2, priority))
        return min(4, max(1, priority - 1))

    async def execute(
        self,
        params: GenerateTasksForPlanParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
        locale: str = "en"
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_uuid = UUID(params.plan_id)

            # 第一步: 验证计划存在
            plan = await PlanService.get_by_id(db_session, plan_uuid, user_uuid)
            if not plan or plan.user_id != user_uuid:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"计划 {params.plan_id} 不存在或无权访问",
                    suggestion="请检查计划 ID 是否正确"
                )
            plan_snapshot = SimpleNamespace(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                subject=getattr(plan, "subject", None),
                source=getattr(plan, "source", None),
                source_metadata=getattr(plan, "source_metadata", None),
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
                async with AsyncSessionLocal() as rag_session:
                    knowledge_service = KnowledgeService(rag_session)
                    retriever = GraphRAGRetriever(knowledge_service)

                    # 构造查询：结合主题和难度，查询相关知识点和前置依赖
                    query = f"{params.topic} {params.difficulty} learning path prerequisites"
                    rag_result = await asyncio.wait_for(
                        retriever.retrieve(query, str(user_uuid), depth=2),
                        timeout=12,
                    )

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
            try:
                task_list = await asyncio.wait_for(
                    self._generate_tasks_with_llm(
                        plan_title=plan_snapshot.name,
                        plan_description=plan_snapshot.description,
                        topic=params.topic,
                        difficulty=params.difficulty,
                        task_count=params.task_count,
                        knowledge_context=knowledge_context,
                        persona_constraints=persona_constraints,
                        locale=locale,
                    ),
                    timeout=30,
                )
            except TimeoutError:
                logger.warning(
                    f"Task generation timed out for plan {plan_uuid}, using deterministic fallback"
                )
                task_list = None

            if not task_list:
                logger.warning(
                    f"LLM task generation unavailable for plan {plan_uuid}, "
                    "using deterministic fallback tasks"
                )
                task_list = await self._build_fallback_tasks(
                    plan=plan_snapshot,
                    topic=params.topic,
                    task_count=params.task_count,
                    persona_constraints=persona_constraints,
                    db_session=db_session,
                    locale=locale,
                )

            # 第四步: 批量创建任务
            created_tasks = []
            learning_path_node_refs = await self._get_learning_path_node_refs(plan_snapshot, db_session)
            for task_data in task_list:
                try:
                    validated = _GeneratedPlanTaskSchema.model_validate(task_data)
                    knowledge_node_id = self._match_learning_path_node_id(
                        validated=validated,
                        node_refs=learning_path_node_refs,
                        task_index=len(created_tasks),
                    )
                    task_create = TaskCreate(
                        title=validated.title,
                        guide_content=validated.description or None,
                        type=coerce_task_type(validated.type, default=ModelTaskType.LEARNING),
                        estimated_minutes=validated.estimated_minutes,
                        difficulty=self._infer_difficulty(validated.type, validated.priority),
                        energy_cost=1,
                        priority=validated.priority,
                        plan_id=plan_uuid,
                        knowledge_node_id=knowledge_node_id,
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
                        "description": validated.description,
                        "knowledge_node_id": (
                            str(task.knowledge_node_id)
                            if getattr(task, "knowledge_node_id", None)
                            else None
                        ),
                    })

                    logger.debug(f"Created task: {task.id} for plan {plan_uuid}")

                except ValidationError as e:
                    logger.warning(f"Generated task failed schema validation: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to create task: {e}, continuing...")
                    await db_session.rollback()
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
            task_list_payload = {
                "tasks": created_tasks,
                "plan_id": params.plan_id,
                "plan_title": plan_snapshot.name,
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
                widget_data=wrap_widget_payload(
                    widget_type="task_list",
                    widget_data=task_list_payload,
                    entity_card=build_task_list_entity_card(
                        created_tasks,
                        tool_name=self.name,
                        tool_result_id=tool_call_id,
                        plan_id=params.plan_id,
                        plan_title=plan_snapshot.name,
                        rag_quality=rag_quality,
                        locale=locale,
                    ),
                ),
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

    async def _build_fallback_tasks(
        self,
        plan: Any,
        topic: str,
        task_count: int,
        persona_constraints: Any | None,
        db_session: Any,
        locale: str = "en",
    ) -> list[dict[str, Any]]:
        """Deterministic fallback tasks when LLM output is unavailable or malformed."""
        from app.core.i18n import I18n

        def t(key: str, **kwargs) -> str:
            return I18n.t(key, locale=locale, **kwargs)

        max_session_minutes = self._resolve_max_session_minutes(persona_constraints)
        topic_name = (topic or getattr(plan, "subject", None) or getattr(plan, "name", None) or t("planner.fallback_topic_default")).strip()
        node_names = await self._get_learning_path_node_names(plan, db_session)
        tasks: list[dict[str, Any]] = []

        if node_names:
            prerequisite_nodes = node_names[:-1]
            target_node = node_names[-1]

            for index, node_name in enumerate(prerequisite_nodes, start=1):
                tasks.append(
                    {
                        "title": t("planner.fallback_prerequisite_title", node=node_name),
                        "description": t("planner.fallback_prerequisite_desc", node=node_name, target=target_node),
                        "type": "learning",
                        "estimated_minutes": min(max_session_minutes, 25),
                        "priority": min(index + 1, 3),
                    }
                )

            tasks.extend(
                [
                    {
                        "title": t("planner.fallback_concept_framework", target=target_node),
                        "description": t("planner.fallback_concept_framework_desc", target=target_node),
                        "type": "learning",
                        "estimated_minutes": min(max_session_minutes, 35),
                        "priority": 3,
                    },
                    {
                        "title": t("planner.fallback_practice", target=target_node),
                        "description": t("planner.fallback_practice_desc", target=target_node),
                        "type": "training",
                        "estimated_minutes": min(max_session_minutes, 40),
                        "priority": 4,
                    },
                    {
                        "title": t("planner.fallback_review", target=target_node),
                        "description": t("planner.fallback_review_desc", target=target_node),
                        "type": "reflection",
                        "estimated_minutes": min(max_session_minutes, 20),
                        "priority": 4,
                    },
                ]
            )
        else:
            tasks.extend(
                [
                    {
                        "title": t("planner.fallback_core_concepts", topic=topic_name),
                        "description": t("planner.fallback_core_concepts_desc", topic=topic_name),
                        "type": "learning",
                        "estimated_minutes": min(max_session_minutes, 25),
                        "priority": 2,
                    },
                    {
                        "title": t("planner.fallback_basic_practice", topic=topic_name),
                        "description": t("planner.fallback_basic_practice_desc", topic=topic_name),
                        "type": "training",
                        "estimated_minutes": min(max_session_minutes, 35),
                        "priority": 3,
                    },
                    {
                        "title": t("planner.fallback_locate_errors", topic=topic_name),
                        "description": t("planner.fallback_locate_errors_desc", topic=topic_name),
                        "type": "error_fix",
                        "estimated_minutes": min(max_session_minutes, 20),
                        "priority": 4,
                    },
                    {
                        "title": t("planner.fallback_summary", topic=topic_name),
                        "description": t("planner.fallback_summary_desc", topic=topic_name),
                        "type": "reflection",
                        "estimated_minutes": min(max_session_minutes, 15),
                        "priority": 3,
                    },
                ]
            )

        if len(tasks) < task_count:
            next_index = 1
            while len(tasks) < task_count:
                tasks.append(
                    {
                        "title": t("planner.fallback_consolidation", topic=topic_name, index=next_index),
                        "description": t("planner.fallback_consolidation_desc", topic=topic_name),
                        "type": "training",
                        "estimated_minutes": min(max_session_minutes, 25),
                        "priority": 3,
                    }
                )
                next_index += 1

        return tasks[:task_count]

    async def _get_learning_path_node_names(self, plan: Any, db_session: Any) -> list[str]:
        node_refs = await self._get_learning_path_node_refs(plan, db_session)
        return [node_ref.name for node_ref in node_refs]

    async def _get_learning_path_node_refs(
        self,
        plan: Any,
        db_session: Any,
    ) -> list[_LearningPathNodeRef]:
        metadata = getattr(plan, "source_metadata", None)
        if getattr(plan, "source", None) != "learning_path" or not isinstance(metadata, dict):
            return []

        raw_node_ids = metadata.get("path_node_ids", [])
        ordered_node_ids: list[UUID] = []
        for raw_node_id in raw_node_ids:
            try:
                ordered_node_ids.append(UUID(str(raw_node_id)))
            except (TypeError, ValueError):
                continue

        if not ordered_node_ids:
            return []

        result = await db_session.execute(
            select(KnowledgeNode.id, KnowledgeNode.name).where(KnowledgeNode.id.in_(ordered_node_ids))
        )
        rows = result.all()
        refs_by_id = {
            str(row.id): _LearningPathNodeRef(id=row.id, name=row.name)
            for row in rows
        }
        return [refs_by_id[str(node_id)] for node_id in ordered_node_ids if str(node_id) in refs_by_id]

    def _match_learning_path_node_id(
        self,
        *,
        validated: _GeneratedPlanTaskSchema,
        node_refs: list[_LearningPathNodeRef],
        task_index: int,
    ) -> UUID | None:
        if not node_refs:
            return None

        haystack = f"{validated.title} {validated.description}".lower()
        for node_ref in node_refs:
            pattern = r'\b' + re.escape(node_ref.name.lower()) + r'\b'
            if re.search(pattern, haystack):
                return node_ref.id

        if len(node_refs) == 1:
            return node_refs[0].id

        if task_index < len(node_refs) - 1:
            return node_refs[task_index].id

        return node_refs[-1].id

    async def _generate_tasks_with_llm(
        self,
        plan_title: str,
        plan_description: str | None,
        topic: str,
        difficulty: str,
        task_count: int,
        knowledge_context: str = "",
        persona_constraints: Any | None = None,
        locale: str = "en",
    ) -> list[dict] | None:
        """
        使用 LLM 生成结构化的任务建议 (支持 GraphRAG 上下文)
        """
        from app.core.i18n import I18n

        # Helper for localized strings
        def t(key: str, **kwargs) -> str:
            return I18n.t(key, locale=locale, **kwargs)

        context_prompt = ""
        if knowledge_context:
            context_prompt = f"""
{t("planner.graph_context_header")}
--------------------------------------------------
{knowledge_context}
--------------------------------------------------
{t("planner.graph_context_instructions")}:
1. {t("planner.instruction_priority_locked")}
2. {t("planner.instruction_mastery_review")}
3. {t("planner.instruction_cover_gaps")}
"""

        persona_prompt = ""
        max_session_minutes = self._resolve_max_session_minutes(persona_constraints)
        if persona_constraints is not None and hasattr(persona_constraints, "to_prompt_block"):
            persona_prompt = persona_constraints.to_prompt_block()

        prompt = f"""
{t("planner.llm_prompt_header", count=task_count)}

{t("planner.plan_info")}:
- {t("planner.plan_name")}: {plan_title}
- {t("planner.plan_description")}: {plan_description or t("planner.description_unavailable")}
- {t("planner.learning_topic")}: {topic}
- {t("planner.difficulty_level")}: {difficulty}

{context_prompt}

{persona_prompt}

{t("planner.task_requirements")}:
1. {t("planner.task_requirement_duration", max=max_session_minutes)}
2. {t("planner.task_requirement_specific")}
3. {t("planner.task_requirement_prerequisite")}
4. {t("planner.task_requirement_order")}
5. {t("planner.task_types")}
6. {t("planner.priority_allocation")}

{t("planner.return_format", count=task_count)}
```json
[
  {{
    "title": "{t("planner.json_title_example")}",
    "description": "{t("planner.json_desc_example")}",
    "type": "learning|training|error_fix|reflection",
    "estimated_minutes": 25,
    "priority": 2
  }},
  ...
]
```

{t("planner.strict_json")}
"""

        try:
            result = await asyncio.wait_for(
                plan_llm.json_call(
                    messages=[{"role": "user", "content": prompt}],
                    fallback=[],  # 降级返回空列表
                    temperature=0.3
                ),
                timeout=20,
            )
        except TimeoutError:
            logger.warning("LLM plan task generation timed out")
            return None

        if not result:
            logger.warning("LLM returned empty response for plan generation")
            return None

        try:
            # 解析 JSON 响应
            tasks = result if isinstance(result, list) else []

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

        except Exception as e:
            logger.error(f"Plan task generation failed: {e}")
            return None
