"""
多意图拆分服务
Multi-Intent Splitting Service

从简单字符串匹配升级为 LLM 驱动的智能意图识别
支持多意图检测、依赖分析、并行执行规划
"""
from __future__ import annotations
import asyncio
from datetime import datetime, UTC
import re
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import llm_router
from app.schemas.intent import (
    IntentAnalysisPreview,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentParseRequest,
    IntentType,
    MultiIntentResult,
    SubIntent,
)
from app.services.llm_service import LLMService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MultiIntentService:
    """
    多意图拆分服务

    功能：
    1. 使用 LLM 快速模型识别多个意图
    2. 分析意图之间的依赖关系
    3. 规划执行顺序和并行策略
    4. 集成现有的 orchestrator 执行意图
    """

    FREE_FAST_TIMEOUT_SECONDS = 0.9
    FAST_TIMEOUT_SECONDS = 2.2
    MAX_FREE_FAST_ATTEMPTS = 1
    MAX_FAST_ATTEMPTS = 2
    _CLAUSE_SPLIT_PATTERN = re.compile(
        r"(?:，然后|然后|并且|同时|再去|接着|另外|;\s*|；\s*|\n+|\band then\b|\band\b)",
        re.IGNORECASE,
    )
    _INTENT_KEYWORDS: list[tuple[IntentType, tuple[str, ...]]] = [
        (IntentType.TASK_MANAGEMENT, ("创建任务", "建个任务", "新增任务", "待办", "todo", "任务", "提醒我")),
        (IntentType.TIME_PLANNING, ("安排", "计划", "排一下", "日历", "几点", "明天", "今天", "下周", "会议")),
        (IntentType.KNOWLEDGE_QUERY, ("什么是", "为什么", "怎么", "解释", "原理", "区别", "总结一下")),
        (IntentType.LEARNING, ("学习", "复习", "练习", "刷题", "背单词", "课程")),
        (IntentType.SOCIAL, ("好友", "群组", "社群", "伙伴", "拉群", "加入群")),
        (IntentType.REFLECTION, ("复盘", "反思", "总结", "回顾")),
        (IntentType.TOOL_CALL, ("番茄钟", "计时器", "翻译", "查词", "闪卡", "专注")),
    ]

    # 意图识别系统提示词
    INTENT_DETECTION_PROMPT = """你是Sparkle AI的意图识别专家。

分析用户输入，识别其中包含的所有意图。

意图类型：
- task_management: 任务管理（创建、修改、删除任务）
- knowledge_query: 知识查询（概念解释、原理说明）
- time_planning: 时间规划（制定计划、安排时间）
- social: 社交互动（好友、群组相关）
- learning: 学习内容（学习新知识、练习）
- reflection: 复习反思（回顾总结）
- tool_call: 工具调用（需要调用特定工具）

请返回JSON格式：
{
  "is_multi_intent": true/false,
  "intents": [
    {
      "type": "意图类型",
      "confidence": 0.95,
      "content": "意图的具体内容",
      "entities": {"key": "value"},
      "agent_role": "推荐的Agent角色"
    }
  ],
  "execution_order": [0, 1, 2],  // 执行顺序（索引）
  "dependencies": [[0, 1], [2]],  // 依赖组：[0,1]可并行，[2]依赖前面
  "should_parallel": [true, true, false],  // 是否可并行执行
  "estimated_total_time": 45  // 预计总时间（秒）
}

用户输入：{message}

上下文信息：{context}

只返回JSON，不要其他内容。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        # 使用 FAST tier 模型进行快速意图识别
        self.llm = LLMService(agent_role=AgentRole.ROUTER)

    async def parse_intents(
        self,
        request: IntentParseRequest
    ) -> MultiIntentResult:
        """
        解析用户输入中的多个意图

        Args:
            request: 意图解析请求

        Returns:
            MultiIntentResult: 解析结果
        """
        # 构建上下文字符串
        context_str = self._format_context(request.context)
        heuristic_result = self._heuristic_parse(request.message)

        # 对于已经被规则稳定识别出的明显多意图，直接返回，避免实时场景被 LLM 试探拖慢。
        if (
            heuristic_result is not None
            and heuristic_result.is_multi_intent
            and all(intent.type is not IntentType.UNKNOWN for intent in heuristic_result.intents)
        ):
            return heuristic_result

        # 调用 LLM 进行意图识别
        messages = [
            {
                "role": "system",
                "content": "你是Sparkle AI的意图识别专家。返回严格的JSON格式。"
            },
            {
                "role": "user",
                "content": self.INTENT_DETECTION_PROMPT
                .replace("{message}", request.message)
                .replace("{context}", context_str or "无")
            }
        ]

        try:
            result = await self._parse_with_llm(messages)

            # 验证并构造返回结果
            if not result or "intents" not in result:
                if heuristic_result is not None:
                    return heuristic_result
                return self._fallback_single_intent(request.message)

            # 验证意图类型
            intents = []
            for intent_data in result.get("intents", []):
                try:
                    intent_type = IntentType(intent_data.get("type", "unknown"))
                except ValueError:
                    intent_type = IntentType.UNKNOWN

                sub_intent = SubIntent(
                    type=intent_type,
                    confidence=float(intent_data.get("confidence", 0.8)),
                    content=str(intent_data.get("content", request.message)),
                    entities=intent_data.get("entities", {}),
                    agent_role=intent_data.get("agent_role")
                )
                intents.append(sub_intent)

            return MultiIntentResult(
                is_multi_intent=result.get("is_multi_intent", len(intents) > 1),
                intents=intents,
                execution_order=result.get("execution_order", list(range(len(intents)))),
                dependencies=result.get("dependencies", []),
                should_parallel=result.get("should_parallel", [False] * len(intents)),
                estimated_total_time=result.get("estimated_total_time")
            )

        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            if heuristic_result is not None:
                return heuristic_result
            return self._fallback_single_intent(request.message)

    async def execute_intents(
        self,
        request: IntentExecuteRequest
    ) -> IntentExecuteResponse:
        """
        执行多个意图

        Args:
            request: 意图执行请求

        Returns:
            IntentExecuteResponse: 执行结果
        """
        start_time = _utcnow()

        if not request.confirmed:
            return IntentExecuteResponse(
                success=False,
                results=[],
                errors=["用户取消执行"],
                total_time=0
            )

        results = []
        errors = []

        try:
            # 导入 orchestrator
            from app.orchestration.orchestrator import Orchestrator

            orchestrator = Orchestrator(
                user_id=str(request.user_id),
                db_session=self.db
            )

            # 按执行顺序处理意图
            for intent_idx in request.parse_result.execution_order:
                intent = request.parse_result.intents[intent_idx]

                try:
                    # 根据意图类型调用相应的处理逻辑
                    result = await self._execute_single_intent(
                        intent, orchestrator, request.user_id
                    )
                    results.append({
                        "intent_type": intent.type.value,
                        "content": intent.content,
                        "result": result
                    })

                except Exception as e:
                    logger.error(f"Failed to execute intent {intent.type}: {e}")
                    errors.append(f"{intent.type.value}: {str(e)}")

            total_time = (_utcnow() - start_time).total_seconds()

            return IntentExecuteResponse(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                total_time=total_time
            )

        except Exception as e:
            logger.error(f"Intent execution failed: {e}")
            total_time = (_utcnow() - start_time).total_seconds()

            return IntentExecuteResponse(
                success=False,
                results=[],
                errors=[str(e)],
                total_time=total_time
            )

    async def create_preview(
        self,
        request: IntentParseRequest
    ) -> IntentAnalysisPreview:
        """
        创建意图分析预览

        Args:
            request: 意图解析请求

        Returns:
            IntentAnalysisPreview: 预览信息
        """
        result = await self.parse_intents(request)

        # 生成执行计划描述
        plan_description = self._generate_execution_plan(result)

        # 提取建议的 Agent 角色
        suggested_roles = list({
            intent.agent_role for intent in result.intents
            if intent.agent_role
        })

        return IntentAnalysisPreview(
            original_message=request.message,
            detected_intents=result.intents,
            execution_plan=plan_description,
            estimated_time=result.estimated_total_time,
            suggested_agent_roles=suggested_roles
        )

    def _format_context(self, context: dict[str, Any] | None) -> str:
        """格式化上下文信息"""
        if not context:
            return ""

        parts = []
        for key, value in context.items():
            parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def _fallback_single_intent(self, message: str) -> MultiIntentResult:
        """LLM 失败时的降级处理"""
        return MultiIntentResult(
            is_multi_intent=False,
            intents=[
                SubIntent(
                    type=IntentType.UNKNOWN,
                    confidence=0.5,
                    content=message,
                    entities={}
                )
            ],
            execution_order=[0],
            dependencies=[],
            should_parallel=[False]
        )

    async def _parse_with_llm(self, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        """短超时分层尝试，避免 free_fast 限流拖挂整条主链。"""
        last_error: Exception | None = None

        for model_key, timeout_seconds in self._select_model_attempts():
            try:
                llm = LLMService(agent_role=AgentRole.ROUTER)
                await llm.switch_to_specific_model(model_key)
                result = await asyncio.wait_for(
                    llm.chat_json(messages, temperature=0.1),
                    timeout=timeout_seconds,
                )
                if isinstance(result, dict) and result.get("intents"):
                    return result
                logger.warning("Multi-intent parse returned empty result from {}", model_key)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Multi-intent parse failed on model {} within {:.2f}s: {}",
                    model_key,
                    timeout_seconds,
                    exc,
                )

        if last_error is not None:
            logger.warning(
                "Multi-intent parse exhausted LLM attempts, falling back to heuristics: {}",
                last_error,
            )
        return None

    def _select_model_attempts(self) -> list[tuple[str, float]]:
        attempts: list[tuple[str, float]] = []

        def _append_attempts(
            tier: ModelTier,
            timeout_seconds: float,
            preferred_order: list[str],
            limit: int,
        ) -> None:
            candidates = llm_router.resolve_candidate_models(
                AgentRole.ROUTER,
                TaskType.QUICK_QUERY,
                force_tier=tier,
            )
            ordered = [model for model in preferred_order if model in candidates]
            ordered.extend(model for model in candidates if model not in ordered)
            for model_key in ordered[:limit]:
                attempts.append((model_key, timeout_seconds))

        _append_attempts(
            ModelTier.FREE_FAST,
            timeout_seconds=self.FREE_FAST_TIMEOUT_SECONDS,
            preferred_order=["glm_4_5_air_free", "glm_4_7_flash_thinking", "siliconflow_free"],
            limit=self.MAX_FREE_FAST_ATTEMPTS,
        )
        _append_attempts(
            ModelTier.FAST,
            timeout_seconds=self.FAST_TIMEOUT_SECONDS,
            preferred_order=["xiaomi_chat", "dashscope_fast", "glm_4_7_flash_no_thinking"],
            limit=self.MAX_FAST_ATTEMPTS,
        )
        return attempts

    def _heuristic_parse(self, message: str) -> MultiIntentResult | None:
        """在 LLM 超时/限流时提供稳定、快速的规则兜底。"""
        clauses = [
            segment.strip(" ，,。.；;！!？?")
            for segment in self._CLAUSE_SPLIT_PATTERN.split(message)
            if segment and segment.strip(" ，,。.；;！!？?")
        ]

        if not clauses:
            return None

        intents = [self._classify_clause(clause) for clause in clauses[:3]]
        if not intents:
            return None

        is_multi = len(intents) > 1
        return MultiIntentResult(
            is_multi_intent=is_multi,
            intents=intents,
            execution_order=list(range(len(intents))),
            dependencies=[] if not is_multi else [[index] for index in range(len(intents))],
            should_parallel=[is_multi] * len(intents),
            estimated_total_time=15 * len(intents) if is_multi else 15,
        )

    def _classify_clause(self, clause: str) -> SubIntent:
        normalized = clause.lower()
        intent_type = IntentType.UNKNOWN

        for candidate_type, keywords in self._INTENT_KEYWORDS:
            if any(keyword.lower() in normalized for keyword in keywords):
                intent_type = candidate_type
                break

        agent_role = None
        if intent_type in {IntentType.KNOWLEDGE_QUERY, IntentType.LEARNING}:
            agent_role = AgentRole.STUDY_BUDDY.value
        elif intent_type in {IntentType.TASK_MANAGEMENT, IntentType.TIME_PLANNING}:
            agent_role = AgentRole.TIME_TUTOR.value
        elif intent_type == IntentType.SOCIAL:
            agent_role = AgentRole.STUDY_BUDDY.value

        return SubIntent(
            type=intent_type,
            confidence=0.72 if intent_type is not IntentType.UNKNOWN else 0.45,
            content=clause,
            entities={},
            agent_role=agent_role,
        )

    def _generate_execution_plan(self, result: MultiIntentResult) -> str:
        """生成执行计划描述"""
        if not result.is_multi_intent or len(result.intents) <= 1:
            return "单任务执行"

        parts = []
        for i, intent in enumerate(result.intents):
            parallel_mark = "（可并行）" if result.should_parallel[i] else ""
            parts.append(f"{i + 1}. {intent.type.value}: {intent.content[:30]}...{parallel_mark}")

        return ";\n".join(parts)

    async def _execute_single_intent(
        self,
        intent: SubIntent,
        orchestrator,
        user_id: UUID
    ) -> dict[str, Any]:
        """执行单个意图"""
        # 这里将意图转发给 orchestrator 或相应的服务
        # 根据意图类型选择不同的处理逻辑

        if intent.type == IntentType.TASK_MANAGEMENT:
            # 任务管理相关
            return await self._handle_task_management(intent, user_id)
        elif intent.type == IntentType.KNOWLEDGE_QUERY:
            # 知识查询
            return await self._handle_knowledge_query(intent, user_id)
        elif intent.type == IntentType.TIME_PLANNING:
            # 时间规划
            return await self._handle_time_planning(intent, user_id)
        else:
            # 通用处理：通过 orchestrator
            return await self._handle_via_orchestrator(intent, orchestrator, user_id)

    async def _handle_task_management(
        self,
        intent: SubIntent,
        user_id: UUID
    ) -> dict[str, Any]:
        """处理任务管理意图"""
        # 这里可以调用 task_service
        return {
            "action": "task_management",
            "content": intent.content,
            "status": "processed"
        }

    async def _handle_knowledge_query(
        self,
        intent: SubIntent,
        user_id: UUID
    ) -> dict[str, Any]:
        """处理知识查询意图"""
        # 调用 galaxy_service 进行知识查询
        return {
            "action": "knowledge_query",
            "query": intent.content,
            "status": "processed"
        }

    async def _handle_time_planning(
        self,
        intent: SubIntent,
        user_id: UUID
    ) -> dict[str, Any]:
        """处理时间规划意图"""
        return {
            "action": "time_planning",
            "content": intent.content,
            "status": "processed"
        }

    async def _handle_via_orchestrator(
        self,
        intent: SubIntent,
        orchestrator,
        user_id: UUID
    ) -> dict[str, Any]:
        """通过 orchestrator 处理意图"""
        # 构造消息发送给 orchestrator
        response = await orchestrator.process_message(
            message=intent.content,
            user_id=str(user_id)
        )

        return {
            "action": "orchestrator",
            "response": response,
            "status": "processed"
        }


# 便捷函数
async def parse_user_intents(
    db: AsyncSession,
    message: str,
    user_id: UUID | None = None,
    context: dict[str, Any] | None = None
) -> MultiIntentResult:
    """解析用户意图的便捷函数"""
    service = MultiIntentService(db)
    request = IntentParseRequest(
        message=message,
        context=context,
        user_id=user_id
    )
    return await service.parse_intents(request)
