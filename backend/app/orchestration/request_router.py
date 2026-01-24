"""
Request Router - Phase 1 & Phase 2

Rule-based router for deciding execution mode.
Phase 1: All requests go to "direct" mode.
Phase 2: Introduces "langgraph" and "hybrid" modes for complex intents.
"""
from typing import Optional
from loguru import logger

from app.orchestration.schemas import RouteDecision


class RequestRouter:
    """路由器 (Phase 1 & Phase 2)

    职责:
    1. 分析用户消息意图
    2. 评估请求风险等级
    3. 返回路由决策

    Phase 1 规则:
    - 所有请求走 direct 模式
    - 基于关键词进行意图分类
    - 简单风险评估

    Phase 2 规则:
    - 简单查询 → direct
    - 复杂规划 → langgraph
    - 高风险 → direct (安全优先)
    """

    # 简单工具列表 (适合 direct 模式)
    SIMPLE_TOOLS = {
        "get_task", "get_plan", "get_knowledge", "query_knowledge",
        "get_focus_stats", "get_user_context", "get_progress"
    }

    # 复杂意图关键词 (需要 LangGraph 规划) - Phase 2
    COMPLEX_INTENTS = {
        "学习计划", "study plan", "制定计划", "make a plan",
        "复习策略", "review strategy", "复习计划",
        "时间安排", "schedule", "时间管理", "time management",
        "考试预测", "exam prediction", "考试重点",
        "知识图谱", "knowledge graph", "知识关联",
        "多步骤", "multi-step", "一系列", "一系列任务"
    }

    # 多步骤模式关键词 - Phase 2
    MULTI_STEP_INDICATORS = {
        "然后", "然后", "接着", "之后",
        "and then", "after that", "next", "followed by",
        "第一步", "第一步", "首先", "first"
    }

    # Vision: Translation Keywords (5c)
    TRANSLATION_KEYWORDS = {
        "翻译", "translate", "解释意思", "what does this mean",
        "怎么说", "in english", "in chinese"
    }

    # Vision: Prism/Behavior Keywords (5b, 15)
    PRISM_KEYWORDS = {
        "行为分析", "behavior analysis", "我的画像", "user profile",
        "认知棱镜", "cognitive prism", "学习习惯", "study habits",
        "周报", "weekly report", "日报", "daily report"
    }

    # Vision: Sprint Keywords (5d)
    SPRINT_KEYWORDS = {
        "冲刺", "sprint", "专注模式", "focus mode",
        "突击", "cram", "考试冲刺"
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def decide(
        self,
        message: str,
        user_id: str,
        session_id: str
    ) -> RouteDecision:
        """路由决策 (Phase 2)

        规则 (优先级顺序):
        1. 高风险 → direct (安全优先，最高优先级)
        2. 复杂规划 → langgraph
        3. 特殊功能 (Translation/Prism/Sprint) → direct (Specific Tools)
        4. 其他 → direct

        Args:
            message: 用户消息
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            RouteDecision: 路由决策
        """
        # 获取 context_version
        context_version = await self._get_context_version(user_id)

        # 意图分析
        intent = self._classify_intent(message)

        # 风险评估
        risk_level = self._assess_risk(message, intent)

        # Phase 2: 根据风险优先级决定执行模式
        execution_mode = "direct"
        confidence = 0.7
        reason = f"Intent: {intent}, Phase 2 routing"

        # === 优先级1: 高风险操作 → direct (安全优先) ===
        if risk_level == "high":
            execution_mode = "direct"
            confidence = 0.9
            reason = f"Intent: {intent}, HIGH RISK - direct mode for safety"
            logger.info(f"High risk detected, forcing direct mode: {intent}")

        # === 优先级2: 复杂意图 → langgraph (仅在非高风险时) ===
        elif self._is_complex_intent(message) and intent not in ["translation", "sprint", "prism"]:
            # Note: Translation/Sprint might be complex, but usually handled by specific tools/flows better in Direct or specialized nodes.
            # For now, we prioritize specific intent detection.
            execution_mode = "langgraph"
            confidence = 0.8
            reason = f"Intent: {intent}, complex routing via LangGraph"
            logger.info(f"Complex intent detected, using LangGraph: {intent}")

        # === 优先级3: 特殊意图 → direct (with tool intent) ===
        elif intent in ["translation", "prism", "sprint"]:
            execution_mode = "direct"
            confidence = 0.85
            reason = f"Intent: {intent}, specialized feature routing"
            logger.info(f"Specialized intent detected: {intent}")

        # === 优先级4: 默认 → direct ===
        else:
            execution_mode = "direct"
            confidence = 0.7
            reason = f"Intent: {intent}, standard direct routing"

        return RouteDecision(
            execution_mode=execution_mode,
            reason=reason,
            risk_level=risk_level,
            confidence=confidence,
            context_version=context_version
        )

    def _classify_intent(self, message: str) -> str:
        """简单意图分类

        基于关键词的规则分类
        """
        msg_lower = message.lower()

        # Specialized Intents (High Priority)
        if any(k in msg_lower for k in self.TRANSLATION_KEYWORDS):
            return "translation"
        if any(k in msg_lower for k in self.PRISM_KEYWORDS):
            return "prism"
        if any(k in msg_lower for k in self.SPRINT_KEYWORDS):
            return "sprint"

        # Standard Intents
        if any(k in msg_lower for k in ["创建", "create", "新建", "添加", "add", "new"]):
            return "create"
        if any(k in msg_lower for k in ["查询", "query", "获取", "get", "搜索", "search", "看看"]):
            return "query"
        if any(k in msg_lower for k in ["更新", "update", "修改", "edit", "改变", "change", "改"]):
            return "update"
        if any(k in msg_lower for k in ["删除", "delete", "remove", "移除"]):
            return "delete"
        if any(k in msg_lower for k in ["学习", "learn", "study", "练习", "practice"]):
            return "learn"
        if any(k in msg_lower for k in ["复习", "review", "复习"]):
            return "review"

        return "chat"

    def _assess_risk(self, message: str, intent: str) -> str:
        """风险评估

        基于意图和关键词的风险等级评估
        """
        msg_lower = message.lower()

        # High risk: 删除操作
        if intent == "delete":
            return "high"

        # High risk keywords
        high_risk_keywords = ["全部", "all", "所有", "清空", "clear"]
        if any(k in msg_lower for k in high_risk_keywords):
            return "high"

        # Medium risk: 创建和更新
        if intent in ["create", "update"]:
            return "medium"

        # Low risk: 查询和聊天
        return "low"

    async def _get_context_version(self, user_id: str) -> str:
        """获取当前 context version

        从 Redis 读取用户的 context version
        """
        if self.redis:
            from app.orchestration.orchestrator import CONTEXT_VERSION_KEY_PREFIX
            import json

            key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
            try:
                raw = await self.redis.get(key)
                if raw:
                    versions = json.loads(raw)
                    return versions.get("tasks", "v0")
            except Exception as e:
                logger.warning(f"Failed to get context version: {e}")

        return "v0"

    def _is_complex_intent(self, message: str) -> bool:
        """检查是否为复杂意图 (Phase 2)

        复杂意图的判断标准:
        1. 包含复杂意图关键词
        2. 包含多步骤指示词
        3. 消息长度超过阈值（可能包含多个请求）

        Args:
            message: 用户消息

        Returns:
            bool: 是否为复杂意图
        """
        msg_lower = message.lower()

        # 1. 检查是否包含复杂意图关键词
        for keyword in self.COMPLEX_INTENTS:
            if keyword.lower() in msg_lower:
                logger.debug(f"Complex intent detected: {keyword}")
                return True

        # 2. 检查是否为多步骤任务
        for indicator in self.MULTI_STEP_INDICATORS:
            if indicator.lower() in msg_lower:
                logger.debug(f"Multi-step intent detected: {indicator}")
                return True

        # 3. 消息长度检查（简化实现）
        # 较长的消息可能包含多个请求或复杂描述
        if len(message) > 100:
            # 检查是否包含多个句子（可能表示多个任务）
            sentence_count = message.count('。') + message.count('.') + message.count('!') + message.count('?')
            if sentence_count >= 2:
                logger.debug(f"Multi-sentence intent detected: {sentence_count} sentences")
                return True

        return False
