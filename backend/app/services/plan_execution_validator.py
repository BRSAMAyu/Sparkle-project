"""
PlanExecutionValidator - 方案执行验证服务

负责验证方案执行结果是否符合预期
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from uuid import UUID

if TYPE_CHECKING:
    from app.orchestration.schemas import ExecutablePlan
    from app.tools.base import ToolResult
    from app.services.plan_execution_record_service import PlanExecutionRecordService


@dataclass
class ExecutionValidationResult:
    """
    执行验证结果

    使用统一命名: validation_status (非 status)
    """
    plan_id: str
    validation_status: str  # passed, failed, partial
    quality_score: float  # 0-1
    criteria_results: Dict[str, Any] = field(default_factory=dict)
    tool_summary: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "validation_status": self.validation_status,
            "quality_score": self.quality_score,
            "criteria_results": self.criteria_results,
            "tool_summary": self.tool_summary,
            "issues": self.issues,
            "timestamp": self.timestamp,
        }


class PlanExecutionValidator:
    """方案执行验证器"""

    def __init__(self, record_service: Optional["PlanExecutionRecordService"] = None):
        """
        Args:
            record_service: PlanExecutionRecordService 实例 (可选)
        """
        self.record_service = record_service

    async def validate_and_record(
        self,
        plan: "ExecutablePlan",
        tool_results: List["ToolResult"],
        user_id: UUID,
    ) -> ExecutionValidationResult:
        """
        验证方案执行结果并记录到数据库

        Args:
            plan: 执行的计划
            tool_results: 所有工具执行结果
            user_id: 用户ID

        Returns:
            ExecutionValidationResult: 验证结果
        """
        # 1. 执行验证
        result = await self.validate(
            plan=plan,
            tool_results=tool_results,
        )

        # 2. 持久化记录 (如果提供了 record_service)
        if self.record_service:
            try:
                # 确保 plan_id 是 UUID
                plan_uuid = UUID(plan.plan_id) if isinstance(plan.plan_id, str) else plan.plan_id

                await self.record_service.create_record(
                    plan_id=plan_uuid,
                    user_id=user_id,
                    validation_status=result.validation_status,
                    quality_score=result.quality_score,
                    criteria_results=result.criteria_results,
                    tool_summary=result.tool_summary,
                    issues=result.issues,
                )
            except Exception as e:
                logger.warning(f"Failed to persist execution record: {e}")

        return result

    async def validate(
        self,
        plan: "ExecutablePlan",
        tool_results: List["ToolResult"],
    ) -> ExecutionValidationResult:
        """
        验证方案执行结果 (不持久化)

        Args:
            plan: 执行的计划
            tool_results: 所有工具执行结果

        Returns:
            ExecutionValidationResult: 验证结果
        """
        plan_id = plan.plan_id

        # 1. 工具执行统计
        tool_summary = self._analyze_tool_results(tool_results)

        # 2. 检查成功标准
        criteria_results = await self._check_success_criteria(
            plan, tool_results
        )

        # 3. 计算质量分数
        quality_score = self._calculate_quality_score(
            tool_summary, criteria_results
        )

        # 4. 确定验证状态
        validation_status = self._determine_status(
            quality_score, criteria_results
        )

        # 5. 收集问题
        issues = self._collect_issues(
            tool_results, criteria_results
        )

        logger.info(
            f"Execution validation complete: plan_id={plan_id}, "
            f"validation_status={validation_status}, score={quality_score:.2f}"
        )

        return ExecutionValidationResult(
            plan_id=plan_id,
            validation_status=validation_status,
            quality_score=quality_score,
            criteria_results=criteria_results,
            tool_summary=tool_summary,
            issues=issues,
        )

    def _analyze_tool_results(
        self, tool_results: List["ToolResult"]
    ) -> Dict[str, int]:
        """分析工具执行结果"""
        total = len(tool_results)
        successful = sum(1 for r in tool_results if r.success)
        failed = total - successful

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
        }

    async def _check_success_criteria(
        self,
        plan: "ExecutablePlan",
        tool_results: List["ToolResult"],
    ) -> Dict[str, Any]:
        """
        检查方案的成功标准

        支持的 success_criteria 格式:
        {
            "min_success_rate": 0.8,      # 最小成功率
            "required_tools": [...],       # 必须成功的工具
            "forbidden_errors": [...],     # 不能出现的错误
        }
        """
        criteria = plan.success_criteria or {}
        results: Dict[str, Any] = {
            "criteria_defined": bool(criteria),
            "checks": {},
        }

        if not criteria:
            results["all_passed"] = True  # 无标准视为通过
            return results

        # 检查最小成功率
        if "min_success_rate" in criteria:
            successful = sum(1 for r in tool_results if r.success)
            actual_rate = successful / len(tool_results) if tool_results else 0.0
            min_required = criteria["min_success_rate"]
            results["checks"]["min_success_rate"] = {
                "required": min_required,
                "actual": actual_rate,
                "passed": actual_rate >= min_required,
            }

        # 检查必须成功的工具
        if "required_tools" in criteria:
            required = set(criteria["required_tools"])
            successful_tools = {
                r.tool_name for r in tool_results if r.success
            }
            required_passed = required.issubset(successful_tools)
            results["checks"]["required_tools"] = {
                "required": list(required),
                "successful": list(successful_tools & required),
                "missing": list(required - successful_tools),
                "passed": required_passed,
            }

        # 检查禁止的错误
        if "forbidden_errors" in criteria:
            forbidden = set(criteria["forbidden_errors"])
            actual_errors = {
                r.error_type for r in tool_results
                if not r.success and r.error_type
            }
            has_forbidden = bool(forbidden & actual_errors)
            results["checks"]["forbidden_errors"] = {
                "forbidden": list(forbidden),
                "actual": list(actual_errors),
                "passed": not has_forbidden,
            }

        # 计算总体通过情况
        all_passed = all(
            check.get("passed", False)
            for check in results["checks"].values()
        )
        results["all_passed"] = all_passed

        return results

    def _calculate_quality_score(
        self,
        tool_summary: Dict[str, int],
        criteria_results: Dict[str, Any],
    ) -> float:
        """
        计算执行质量分数 (0-1)

        评分策略:
        - 基础分: 成功率 (权重 0.6)
        - 标准检查分 (权重 0.4)
        """
        score = 0.0

        # 基础分: 成功率 (权重 0.6)
        success_rate = tool_summary.get("success_rate", 0.0)
        score += success_rate * 0.6

        # 标准检查分 (权重 0.4)
        if criteria_results.get("criteria_defined"):
            checks = criteria_results.get("checks", {})
            if checks:
                passed_rate = sum(
                    1 for c in checks.values() if c.get("passed", False)
                ) / len(checks)
                score += passed_rate * 0.4
        else:
            # 无标准时，成功率占全部权重
            score += success_rate * 0.4

        return min(1.0, max(0.0, score))

    def _determine_status(
        self,
        quality_score: float,
        criteria_results: Dict[str, Any],
    ) -> str:
        """
        确定验证状态

        Returns:
            "passed" | "partial" | "failed"
        """
        # 如果所有标准都通过且分数高
        if criteria_results.get("all_passed", True) and quality_score >= 0.8:
            return "passed"
        # 如果分数中等
        elif quality_score >= 0.5:
            return "partial"
        # 否则失败
        else:
            return "failed"

    def _collect_issues(
        self,
        tool_results: List["ToolResult"],
        criteria_results: Dict[str, Any],
    ) -> List[str]:
        """收集问题列表"""
        issues = []

        # 收集工具执行失败
        for result in tool_results:
            if not result.success:
                msg = f"Tool '{result.tool_name}' failed"
                if result.error_message:
                    msg += f": {result.error_message}"
                issues.append(msg)

        # 收集标准检查失败
        for check_name, check_data in criteria_results.get("checks", {}).items():
            if not check_data.get("passed", True):
                issues.append(f"Criteria '{check_name}' not met")

        return issues
