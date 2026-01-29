"""
Unified Intent Router - 统一意图路由系统

整合三层路由机制：
1. Layer 1: 显式声明 (confidence=1.0)
2. Layer 2: 规则匹配 (confidence=0.7-0.9)
3. Layer 3: LLM辅助 (上下文感知)

替代原 IntentRouter (17行简单版本)，提供智能路由能力。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from loguru import logger

from app.services.llm_service import LLMService


class UnifiedIntentType(str, Enum):
    """统一意图类型枚举"""
    CHAT = "chat"
    TASK = "task"
    PLAN = "plan"
    SPRINT_PLAN = "sprint_plan"
    COGNITIVE_PRISM = "cognitive_prism"
    TRANSLATION = "translation"
    KNOWLEDGE = "knowledge"
    ERROR_DIAGNOSIS = "error_diagnosis"
    MULTI_INTENT = "multi_intent"

    # 向后兼容：映射到旧系统
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    LEARN = "learn"
    REVIEW = "review"


@dataclass
class IntentRoutingResult:
    """统一路由结果"""
    primary_intent: UnifiedIntentType
    sub_intents: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    routing_layer: str = "unknown"  # "explicit", "rule", "llm"
    execution_mode: str = "direct"  # "direct", "langgraph", "hybrid"
    context_signals: dict[str, Any] = field(default_factory=dict)

    # 上下文感知
    conversation_context: str | None = None
    active_plan_id: UUID | None = None
    recent_intents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "primary_intent": self.primary_intent.value,
            "sub_intents": self.sub_intents,
            "confidence": self.confidence,
            "routing_layer": self.routing_layer,
            "execution_mode": self.execution_mode,
            "context_signals": self.context_signals,
            "active_plan_id": str(self.active_plan_id) if self.active_plan_id else None,
            "recent_intents": self.recent_intents
        }


class IntentPattern:
    """意图模式匹配器"""

    def __init__(
        self,
        keywords: set,
        weight: float = 0.7,
        context_hints: set | None = None
    ):
        self.keywords = keywords
        self.weight = weight
        self.context_hints = context_hints or set()

    def match(self, message: str) -> float:
        """计算匹配分数"""
        score = 0.0
        msg_lower = message.lower()

        # 关键词匹配
        for keyword in self.keywords:
            if keyword.lower() in msg_lower:
                score += self.weight

        # 上下文提示匹配
        if self.context_hints:
            for hint in self.context_hints:
                if hint.lower() in msg_lower:
                    score += self.weight * 0.5

        return min(score, 1.0)  # 限制最大值为1.0


class UnifiedIntentRouter:
    """
    统一意图路由器

    三层级联路由：
    1. Layer 1: 显式声明检查 (最高优先级)
    2. Layer 2: 规则匹配 (关键词+模式)
    3. Layer 3: LLM辅助分类 (上下文感知)
    """

    # Layer 2: 规则模式
    INTENT_PATTERNS = {
        UnifiedIntentType.TRANSLATION: IntentPattern(
            keywords={
                "翻译", "translate", "解释意思", "what does this mean",
                "怎么说", "in english", "in chinese", "翻译成"
            },
            weight=0.85
        ),
        UnifiedIntentType.COGNITIVE_PRISM: IntentPattern(
            keywords={
                "行为分析", "behavior analysis", "我的画像", "user profile",
                "认知棱镜", "cognitive prism", "学习习惯", "study habits",
                "周报", "weekly report", "日报", "daily report",
                "学习分析", "学习数据", "学习统计"
            },
            weight=0.85
        ),
        UnifiedIntentType.SPRINT_PLAN: IntentPattern(
            keywords={
                "冲刺", "sprint", "专注模式", "focus mode",
                "突击", "cram", "考试冲刺", "进入冲刺"
            },
            weight=0.85
        ),
        UnifiedIntentType.PLAN: IntentPattern(
            keywords={
                "学习计划", "study plan", "制定计划", "make a plan",
                "复习计划", "review plan", "时间安排", "schedule",
                "学习规划", "制定学习计划", "创建计划"
            },
            weight=0.75
        ),
        UnifiedIntentType.ERROR_DIAGNOSIS: IntentPattern(
            keywords={
                "错题", "错误", "不懂", "为什么错了",
                "错题本", "错误分析", "错误诊断"
            },
            weight=0.8
        ),
        UnifiedIntentType.TASK: IntentPattern(
            keywords={
                "任务", "task", "todo", "待办",
                "完成任务", "添加任务", "创建任务"
            },
            weight=0.7
        ),
        UnifiedIntentType.KNOWLEDGE: IntentPattern(
            keywords={
                "知识图谱", "knowledge graph", "知识关联",
                "学习路径", "learning path", "知识树"
            },
            weight=0.75
        ),
    }

    # 复杂意图指示词
    COMPLEX_INTENT_KEYWORDS = {
        "学习计划", "制定计划", "复习策略", "时间规划",
        "考试预测", "知识图谱", "知识关联", "多步骤",
        "一系列", "然后", "接着", "之后", "首先"
    }

    def __init__(
        self,
        redis_client=None,
        llm_service: LLMService | None = None,
        context_window_size: int = 5
    ):
        """
        Args:
            redis_client: Redis客户端（用于缓存）
            llm_service: LLM服务（Layer 3）
            context_window_size: 上下文窗口大小
        """
        self.redis = redis_client
        self.llm_service = llm_service
        self.context_window_size = context_window_size
        logger.info("UnifiedIntentRouter initialized")

    async def route(
        self,
        message: str,
        user_id: str,
        session_id: str,
        payload: dict[str, Any] | None = None,
        conversation_history: list[dict] | None = None
    ) -> IntentRoutingResult:
        """
        主路由方法 - 三层级联

        Args:
            message: 用户消息
            user_id: 用户ID
            session_id: 会话ID
            payload: 请求payload（可能包含显式intent）
            conversation_history: 对话历史（用于上下文感知）

        Returns:
            IntentRoutingResult: 路由结果
        """
        payload = payload or {}

        # Layer 1: 检查显式声明
        explicit_result = self._check_explicit_intent(payload)
        if explicit_result and explicit_result.confidence >= 0.95:
            logger.info(f"Layer 1 (explicit): {explicit_result.primary_intent}")
            return explicit_result

        # Layer 2: 规则匹配
        rule_result = await self._rule_based_match(message, user_id)
        if rule_result.confidence >= 0.75:
            logger.info(
                f"Layer 2 (rule): {rule_result.primary_intent} "
                f"confidence={rule_result.confidence:.2f}"
            )
            return rule_result

        # Layer 3: LLM辅助分类
        logger.info(f"Layer 3 (llm): rule confidence={rule_result.confidence:.2f}, using LLM assist")
        llm_result = await self._llm_classify(
            message,
            conversation_history or [],
            rule_result
        )

        # 检测多意图
        if llm_result.sub_intents:
            llm_result.primary_intent = UnifiedIntentType.MULTI_INTENT
            llm_result.execution_mode = "langgraph"

        return llm_result

    def _check_explicit_intent(self, payload: dict[str, Any]) -> IntentRoutingResult | None:
        """
        Layer 1: 检查显式声明的意图

        检查位置：
        1. payload.intent
        2. payload.extra_context.intent
        3. payload.context.intent
        """
        intent = (
            payload.get("intent") or
            (payload.get("extra_context") or {}).get("intent") or
            (payload.get("context") or {}).get("intent")
        )

        if not intent:
            return None

        # 映射到统一意图类型
        try:
            intent_type = UnifiedIntentType(intent)
        except ValueError:
            # 如果不是标准类型，尝试模糊匹配
            intent_lower = intent.lower()
            if "translation" in intent_lower or "翻译" in intent_lower:
                intent_type = UnifiedIntentType.TRANSLATION
            elif "prism" in intent_lower or "棱镜" in intent_lower:
                intent_type = UnifiedIntentType.COGNITIVE_PRISM
            elif "sprint" in intent_lower or "冲刺" in intent_lower:
                intent_type = UnifiedIntentType.SPRINT_PLAN
            elif "plan" in intent_lower or "计划" in intent_lower:
                intent_type = UnifiedIntentType.PLAN
            else:
                intent_type = UnifiedIntentType.CHAT  # 默认

        return IntentRoutingResult(
            primary_intent=intent_type,
            confidence=1.0,
            routing_layer="explicit",
            execution_mode="direct"
        )

    async def _rule_based_match(
        self,
        message: str,
        user_id: str
    ) -> IntentRoutingResult:
        """
        Layer 2: 基于规则的关键词匹配

        使用 IntentPattern 进行加权匹配
        """
        scores = {}
        message.lower()

        # 使用意图模式进行匹配
        for intent_type, pattern in self.INTENT_PATTERNS.items():
            score = pattern.match(message)
            if score > 0:
                scores[intent_type] = score

        if not scores:
            # 检查是否为复杂意图
            is_complex = self._is_complex_intent(message)
            execution_mode = "langgraph" if is_complex else "direct"

            return IntentRoutingResult(
                primary_intent=UnifiedIntentType.CHAT,
                confidence=0.5,
                routing_layer="rule",
                execution_mode=execution_mode,
                context_signals={"is_complex": is_complex}
            )

        # 返回得分最高的意图
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]

        # 判断执行模式
        execution_mode = "direct"
        if confidence >= 0.8 and best_intent in [
            UnifiedIntentType.PLAN,
            UnifiedIntentType.ERROR_DIAGNOSIS
        ]:
            execution_mode = "langgraph"

        return IntentRoutingResult(
            primary_intent=best_intent,
            confidence=confidence,
            routing_layer="rule",
            execution_mode=execution_mode,
            context_signals={"matched_keywords": list(scores.keys())}
        )

    async def _llm_classify(
        self,
        message: str,
        conversation_history: list[dict],
        rule_hints: IntentRoutingResult
    ) -> IntentRoutingResult:
        """
        Layer 3: LLM辅助分类（上下文感知）

        Args:
            message: 用户消息
            conversation_history: 对话历史
            rule_hints: Layer 2的规则匹配结果（作为提示）

        Returns:
            IntentRoutingResult: LLM分类结果
        """
        if not self.llm_service:
            logger.warning("LLM service not available, returning rule hints")
            return rule_hints

        # 构建上下文字符串
        context_str = self._build_context_string(conversation_history)

        # 构建提示词
        prompt = f"""你是一个意图分类专家。请分析用户消息并分类意图。

## 对话上下文（最近{self.context_window_size}轮）
{context_str if context_str else "（无历史对话）"}

## 用户消息
"{message}"

## 规则匹配提示
主意图: {rule_hints.primary_intent.value}
置信度: {rule_hints.confidence:.2f}

## 意图类别说明
- chat: 日常对话、问候、闲聊
- task: 任务管理（创建、更新、删除、查询任务）
- plan: 学习计划制定、复习规划
- sprint_plan: 冲刺模式、专注模式
- cognitive_prism: 行为分析、学习习惯、认知档案
- translation: 翻译请求
- knowledge: 知识图谱、知识关联查询
- error_diagnosis: 错题分析、错误诊断
- multi_intent: 包含多个意图

请返回JSON格式：
{{
  "primary_intent": "意图类别",
  "confidence": 0.85,
  "reasoning": "简短推理过程",
  "is_complex": false,
  "suggested_execution_mode": "direct|langgraph"
}}

注意：
- 如果用户消息包含多个明确请求，将 primary_intent 设为 "multi_intent"
- confidence 应基于你的确定性程度
- reasoning 用中文简短说明"""

        try:
            # 使用低温度确保分类稳定
            response = await self.llm_service.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            # 解析结果
            primary_intent_str = response.get("primary_intent", "chat").lower()
            confidence = float(response.get("confidence", 0.7))
            reasoning = response.get("reasoning", "")
            is_complex = response.get("is_complex", False)
            suggested_mode = response.get("suggested_execution_mode", "direct")

            # 映射到统一意图类型
            try:
                primary_intent = UnifiedIntentType(primary_intent_str)
            except ValueError:
                # 尝试模糊匹配
                primary_intent = self._map_fuzzy_intent(primary_intent_str)

            # 确定执行模式
            execution_mode = suggested_mode
            if is_complex:
                execution_mode = "langgraph"

            result = IntentRoutingResult(
                primary_intent=primary_intent,
                confidence=confidence,
                routing_layer="llm",
                execution_mode=execution_mode,
                context_signals={
                    "llm_reasoning": reasoning,
                    "is_complex": is_complex,
                    "rule_hint": rule_hints.primary_intent.value
                },
                conversation_context=context_str
            )

            logger.info(
                f"Layer 3 (llm): {primary_intent} "
                f"confidence={confidence:.2f} "
                f"reasoning={reasoning[:50]}..."
            )

            return result

        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}, falling back to rule hints")
            # 降级到规则匹配结果
            rule_hints.routing_layer = "llm_fallback"
            return rule_hints

    def _build_context_string(self, conversation_history: list[dict]) -> str:
        """构建上下文字符串"""
        if not conversation_history:
            return ""

        # 取最近 N 轮对话
        recent = conversation_history[-self.context_window_size:]

        context_parts = []
        for i, msg in enumerate(recent, 1):
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # 限制长度
            context_parts.append(f"{i}. [{role}]: {content}")

        return "\n".join(context_parts)

    def _is_complex_intent(self, message: str) -> bool:
        """检查是否为复杂意图"""
        msg_lower = message.lower()

        # 检查复杂意图关键词
        for keyword in self.COMPLEX_INTENT_KEYWORDS:
            if keyword.lower() in msg_lower:
                return True

        # 检查多步骤指示词
        multi_step_indicators = ["然后", "接着", "之后", "and then", "after that", "next"]
        for indicator in multi_step_indicators:
            if indicator.lower() in msg_lower:
                return True

        # 检查消息长度和多句性
        if len(message) > 100:
            sentence_count = (
                message.count('。') +
                message.count('.') +
                message.count('!') +
                message.count('?')
            )
            if sentence_count >= 2:
                return True

        return False

    def _map_fuzzy_intent(self, intent_str: str) -> UnifiedIntentType:
        """模糊意图映射"""
        intent_str = intent_str.lower()

        if "translation" in intent_str or "翻译" in intent_str:
            return UnifiedIntentType.TRANSLATION
        if "prism" in intent_str or "棱镜" in intent_str or "behavior" in intent_str:
            return UnifiedIntentType.COGNITIVE_PRISM
        if "sprint" in intent_str or "冲刺" in intent_str or "focus" in intent_str:
            return UnifiedIntentType.SPRINT_PLAN
        if "plan" in intent_str or "计划" in intent_str:
            return UnifiedIntentType.PLAN
        if "task" in intent_str or "任务" in intent_str:
            return UnifiedIntentType.TASK
        if "knowledge" in intent_str or "知识" in intent_str:
            return UnifiedIntentType.KNOWLEDGE
        if "error" in intent_str or "错误" in intent_str or "diagnosis" in intent_str:
            return UnifiedIntentType.ERROR_DIAGNOSIS
        if "multi" in intent_str:
            return UnifiedIntentType.MULTI_INTENT

        return UnifiedIntentType.CHAT
