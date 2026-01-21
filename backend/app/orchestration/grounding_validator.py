"""
Grounding Validator - Phase 1

Validates executable plans before execution.
Uses hybrid mode: cached allowlist with refresh interface.
"""
from typing import List, Optional, Set
from loguru import logger
from dataclasses import dataclass

from app.orchestration.schemas import ExecutablePlan, ValidationResult
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry


class GroundingValidator:
    """Grounding Validator (Phase 1)

    职责:
    1. Schema 校验
    2. Allowlist 工具检查（混合模式：缓存 + 刷新接口）
    3. 参数大小限制

    用户选择: 混合模式 - 缓存 allowlist，提供刷新接口
    """

    # 危险工具列表
    DESTRUCTIVE_TOOLS = {"delete_task", "delete_plan", "remove_user"}

    # 参数大小限制 (bytes)
    MAX_PARAMS_SIZE = 10000

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._allowlist: Optional[Set[str]] = None
        self._allowlist_dirty = True  # 标记是否需要刷新

    async def validate_plan(self, plan: ExecutablePlan) -> ValidationResult:
        """验证执行计划

        Phase 1 检查:
        1. schema_version 是否支持
        2. tool_calls 非空
        3. 工具名称在 allowlist 中
        4. 参数大小不超过限制

        Args:
            plan: 要验证的执行计划

        Returns:
            ValidationResult: 验证结果
        """
        risk_flags = []

        # 1. Schema version check
        if plan.schema_version != "1.0":
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

        # 5. Check if confirmation needed
        requires_confirmation = len(risk_flags) > 0

        return ValidationResult(
            is_valid=True,
            risk_flags=risk_flags,
            requires_confirmation=requires_confirmation
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
