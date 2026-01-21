"""
Request Router - Phase 1

Simple rule-based router for deciding execution mode.
In Phase 1, all requests go to "direct" mode.
Phase 2 will introduce LangGraph as a planner.
"""
from typing import Optional
from loguru import logger

from app.orchestration.schemas import RouteDecision


class RequestRouter:
    """简单规则路由器 (Phase 1)

    职责:
    1. 分析用户消息意图
    2. 评估请求风险等级
    3. 返回路由决策

    Phase 1 规则:
    - 所有请求走 direct 模式
    - 基于关键词进行意图分类
    - 简单风险评估
    """

    # 工具到复杂度映射 (Phase 2 使用)
    SIMPLE_TOOLS = {
        "get_task", "get_plan", "get_knowledge", "query_knowledge",
        "get_focus_stats", "get_user_context"
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def decide(
        self,
        message: str,
        user_id: str,
        session_id: str
    ) -> RouteDecision:
        """路由决策

        Phase 1 规则:
        - 单个简单工具 → direct
        - 多个工具或复杂工具 → direct (Phase 1 都是 direct)
        - LangGraph 规划 → Phase 2

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

        # Phase 1: 所有请求走 direct
        return RouteDecision(
            execution_mode="direct",
            reason=f"Intent: {intent}, Phase 1 default routing",
            risk_level=risk_level,
            confidence=0.7,
            context_version=context_version
        )

    def _classify_intent(self, message: str) -> str:
        """简单意图分类

        基于关键词的规则分类
        """
        msg_lower = message.lower()

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
