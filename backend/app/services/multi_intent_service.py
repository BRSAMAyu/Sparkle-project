"""
多意图拆分服务
Multi-Intent Splitting Service

从简单字符串匹配升级为 LLM 驱动的智能意图识别
支持多意图检测、依赖分析、并行执行规划
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.intent import (
    IntentType, SubIntent, MultiIntentResult,
    IntentParseRequest, IntentExecuteRequest, IntentExecuteResponse,
    IntentAnalysisPreview
)
from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import LLMService


class MultiIntentService:
    """
    多意图拆分服务

    功能：
    1. 使用 LLM 快速模型识别多个意图
    2. 分析意图之间的依赖关系
    3. 规划执行顺序和并行策略
    4. 集成现有的 orchestrator 执行意图
    """

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

        # 调用 LLM 进行意图识别
        messages = [
            {
                "role": "system",
                "content": "你是Sparkle AI的意图识别专家。返回严格的JSON格式。"
            },
            {
                "role": "user",
                "content": self.INTENT_DETECTION_PROMPT.format(
                    message=request.message,
                    context=context_str or "无"
                )
            }
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.1)

            # 验证并构造返回结果
            if not result or "intents" not in result:
                # 默认为单意图
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
        start_time = datetime.utcnow()

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

            total_time = (datetime.utcnow() - start_time).total_seconds()

            return IntentExecuteResponse(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                total_time=total_time
            )

        except Exception as e:
            logger.error(f"Intent execution failed: {e}")
            total_time = (datetime.utcnow() - start_time).total_seconds()

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

    def _format_context(self, context: Optional[Dict[str, Any]]) -> str:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    user_id: Optional[UUID] = None,
    context: Optional[Dict[str, Any]] = None
) -> MultiIntentResult:
    """解析用户意图的便捷函数"""
    service = MultiIntentService(db)
    request = IntentParseRequest(
        message=message,
        context=context,
        user_id=user_id
    )
    return await service.parse_intents(request)
