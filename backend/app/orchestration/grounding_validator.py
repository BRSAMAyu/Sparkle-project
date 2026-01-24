"""
Grounding Validator - Phase 1 & Phase 2

Validates executable plans before execution.
Uses hybrid mode: cached allowlist with refresh interface.

Phase 2 enhancements:
- Business rules validation
- Preflight checks
- Schema v2.0 support
- Snapshot-aware validation
"""
from typing import List, Optional, Set, Dict, Any
from loguru import logger
from dataclasses import dataclass

from app.orchestration.schemas import ExecutablePlan, ValidationResult, StateSnapshot
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry


class GroundingValidator:
    """Grounding Validator (Phase 1 & Phase 2)

    职责:
    1. Schema 校验
    2. Allowlist 工具检查（混合模式：缓存 + 刷新接口）
    3. 参数大小限制
    4. 业务规则校验 (Phase 2)
    5. Preflight 检查 (Phase 2)

    用户选择: 混合模式 - 缓存 allowlist，提供刷新接口
    """

    # 危险工具列表
    DESTRUCTIVE_TOOLS = {"delete_task", "delete_plan", "remove_user"}

    # 参数大小限制 (bytes)
    MAX_PARAMS_SIZE = 10000

    # 业务规则限制 (Phase 2)
    MAX_PENDING_TASKS = 20  # 最大待处理任务数
    DEFAULT_DAILY_QUOTA = 100  # 默认日配额

    # 需要配额检查的工具
    QUOTA_CHECK_TOOLS = {"create_task", "create_plan", "batch_create_tasks"}

    # 需要任务数量检查的工具
    TASK_LIMIT_CHECK_TOOLS = {"create_task", "batch_create_tasks"}

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._allowlist: Optional[Set[str]] = None
        self._allowlist_dirty = True  # 标记是否需要刷新

    async def validate_plan(
        self,
        plan: ExecutablePlan,
        snapshot: Optional[StateSnapshot] = None
    ) -> ValidationResult:
        """验证执行计划 (Phase 1 & Phase 2)

        Phase 1 检查:
        1. schema_version 是否支持
        2. tool_calls 非空
        3. 工具名称在 allowlist 中
        4. 参数大小不超过限制

        Phase 2 检查:
        5. 业务规则校验（如果提供了 snapshot）

        Args:
            plan: 要验证的执行计划
            snapshot: 可选的状态快照（用于业务规则校验）

        Returns:
            ValidationResult: 验证结果
        """
        risk_flags = []

        # === Phase 1 检查 ===

        # 1. Schema version check (support v1.0, v2.0, and v3.0)
        if plan.schema_version not in ["1.0", "2.0", "3.0"]:
            return ValidationResult(
                is_valid=False,
                failure_reason=f"Unsupported schema version: {plan.schema_version}"
            )

        # 2. Tool calls non-empty
        if not plan.tool_calls:
            return ValidationResult(
                is_valid=False,
                failure_reason="Tool calls cannot be empty"
            )

        # 3. Get allowlist (混合模式：使用缓存)
        allowlist = await self._get_allowlist()

        # 4. Validate each tool call
        for tool_call in plan.tool_calls:
            # Tool name check
            if tool_call.name not in allowlist:
                return ValidationResult(
                    is_valid=False,
                    failure_reason=f"Tool '{tool_call.name}' not in allowlist. Available tools: {len(allowlist)}"
                )

            # Params size check
            params_size = len(str(tool_call.params))
            if params_size > self.MAX_PARAMS_SIZE:
                return ValidationResult(
                    is_valid=False,
                    failure_reason=f"Tool params too large: {params_size} bytes (max: {self.MAX_PARAMS_SIZE})"
                )

            # Risk flags
            if tool_call.point_of_no_return:
                risk_flags.append(f"irreversible:{tool_call.name}")
            if tool_call.name in self.DESTRUCTIVE_TOOLS:
                risk_flags.append(f"destructive:{tool_call.name}")

        # === Phase 2: 业务规则校验 ===
        if snapshot:
            business_result = await self._validate_business_rules(plan, snapshot)
            if not business_result["is_valid"]:
                return ValidationResult(
                    is_valid=False,
                    failure_reason=business_result["reason"],
                    requires_confirmation=False
                )

        # 5. Check if confirmation or HITL needed
        requires_confirmation = len(risk_flags) > 0
        requires_hitl = False

        for tool_call in plan.tool_calls:
            tool = dynamic_tool_registry.get_tool(tool_call.name)
            if tool and getattr(tool, "requires_confirmation", False):
                requires_hitl = True
                if f"confirm:{tool_call.name}" not in risk_flags:
                    risk_flags.append(f"confirm:{tool_call.name}")
            if tool_call.point_of_no_return:
                requires_hitl = True

        return ValidationResult(
            is_valid=True,
            risk_flags=risk_flags,
            requires_confirmation=requires_confirmation,
            requires_hitl=requires_hitl
        )

    async def _get_allowlist(self) -> Set[str]:
        """获取工具 allowlist（混合模式：缓存）"""
        if self._allowlist is not None and not self._allowlist_dirty:
            return self._allowlist

        # 从动态工具注册表获取
        tools = dynamic_tool_registry.get_all_tools()
        self._allowlist = {tool.name for tool in tools}
        self._allowlist_dirty = False
        logger.info(f"GroundingValidator allowlist refreshed: {len(self._allowlist)} tools")

        return self._allowlist

    def refresh_allowlist(self):
        """刷新 allowlist（工具注册后主动调用）

        当工具动态注册后调用此方法刷新缓存
        """
        self._allowlist_dirty = True
        logger.info("GroundingValidator allowlist marked for refresh")

    def get_allowlist(self) -> Set[str]:
        """获取当前缓存的 allowlist（同步方法，用于调试）"""
        if self._allowlist is None:
            self._allowlist = set()
        return self._allowlist.copy()

    async def validate_tool_name(self, tool_name: str) -> bool:
        """快速验证单个工具名称是否在 allowlist 中

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否在 allowlist 中
        """
        allowlist = await self._get_allowlist()
        return tool_name in allowlist

    async def get_tool_info(self, tool_name: str) -> Optional[dict]:
        """获取工具的额外信息（用于决策）"""
        allowlist = await self._get_allowlist()

        if tool_name not in allowlist:
            return None

        tool = dynamic_tool_registry.get_tool(tool_name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category.value if hasattr(tool, 'category') else "unknown",
            "is_destructive": tool_name in self.DESTRUCTIVE_TOOLS
        }

    # ========== Phase 2: Business Rules Validation ==========

    async def _validate_business_rules(
        self,
        plan: ExecutablePlan,
        snapshot: StateSnapshot
    ) -> Dict[str, Any]:
        """业务规则校验 (Phase 2)

        Args:
            plan: 执行计划
            snapshot: 状态快照

        Returns:
            Dict with:
            - is_valid: bool
            - reason: str (if invalid)
            - suggestion: str (optional)
        """
        for tool_call in plan.tool_calls:
            # 1. 创建任务配额检查
            if tool_call.name in self.QUOTA_CHECK_TOOLS:
                if snapshot.user_quota_remaining <= 0:
                    return {
                        "is_valid": False,
                        "reason": "Daily quota exceeded. Please try again tomorrow.",
                        "suggestion": "Complete existing tasks or wait for quota reset."
                    }

            # 2. 任务数量限制检查
            if tool_call.name in self.TASK_LIMIT_CHECK_TOOLS:
                if snapshot.pending_tasks_count >= self.MAX_PENDING_TASKS:
                    return {
                        "is_valid": False,
                        "reason": f"Too many pending tasks: {snapshot.pending_tasks_count}/{self.MAX_PENDING_TASKS}",
                        "suggestion": "Please complete some existing tasks first."
                    }

                # Check if batch creation would exceed limit
                if tool_call.name == "batch_create_tasks":
                    batch_size = len(tool_call.params.get("tasks", []))
                    if snapshot.pending_tasks_count + batch_size > self.MAX_PENDING_TASKS:
                        return {
                            "is_valid": False,
                            "reason": f"Batch would exceed task limit: "
                                     f"{snapshot.pending_tasks_count} + {batch_size} > {self.MAX_PENDING_TASKS}",
                            "suggestion": f"Reduce batch size to at most "
                                         f"{self.MAX_PENDING_TASKS - snapshot.pending_tasks_count} tasks."
                        }

            # 3. Focus 时间冲突检查（简化版）
            if tool_call.name in ["create_task", "update_task", "create_focus"]:
                if "due_date" in tool_call.params or "start_time" in tool_call.params:
                    # TODO: 实际应查询 focus_service 检查时间冲突
                    # Phase 2: 简化实现，仅记录日志
                    logger.debug(f"Focus time conflict check for {tool_call.name}")

            # 4. PONR 操作需要额外确认
            if tool_call.point_of_no_return:
                # 检查是否在快照后有状态变化
                if snapshot.context_versions:
                    logger.warning(
                        f"PONR operation {tool_call.name} with snapshot {snapshot.snapshot_id}"
                    )

        return {"is_valid": True}

    async def preflight_check(
        self,
        plan: ExecutablePlan,
        user_id: str
    ) -> Dict[str, Any]:
        """Preflight 检查 (Phase 2)

        检查外部服务的可用性:
        - Redis 连接
        - 数据库连接
        - 外部 API 可用性

        Args:
            plan: 执行计划
            user_id: 用户ID

        Returns:
            Dict with:
            - is_ready: bool
            - blocked_by: List[str]
        """
        blocked = []

        # 1. Check Redis connection
        if self.redis:
            try:
                await self.redis.ping()
            except Exception as e:
                blocked.append(f"Redis unavailable: {str(e)}")
        else:
            blocked.append("Redis not configured")

        # 2. Check for rate limit violations
        if plan.tool_calls:
            rate_key = f"rate_limit:{user_id}"
            try:
                current = await self.redis.get(rate_key)
                if current and int(current) > self.DEFAULT_DAILY_QUOTA:
                    blocked.append("Rate limit exceeded")
            except Exception:
                pass

        # 3. Tool-specific checks
        for tool_call in plan.tool_calls:
            if tool_call.name == "search_knowledge_graph":
                # Check vector service
                try:
                    from app.services.knowledge_service import KnowledgeService
                    # Phase 2: Simplified check
                    logger.debug("Vector service check")
                except Exception as e:
                    blocked.append(f"Vector service unavailable: {str(e)}")

        return {
            "is_ready": len(blocked) == 0,
            "blocked_by": blocked
        }
