"""
PlanExecutionValidator - 方案执行验证服务

负责验证方案执行结果是否符合预期
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger

if TYPE_CHECKING:
    from app.orchestration.executor import PlanExecutionResult, StepResult
    from app.orchestration.schemas import ExecutablePlan
    from app.services.plan_execution_record_service import PlanExecutionRecordService
    from app.tools.base import ToolResult


@dataclass
class StepValidation:
    """Per-step validation result."""
    step_id: str
    tool_name: str
    passed: bool
    duration_ms: int = 0
    max_duration_ms: int = 0
    duration_ok: bool = True
    output_keys_ok: bool = True
    missing_output_keys: list[str] = field(default_factory=list)
    required: bool = True


@dataclass
class ExecutionValidationResult:
    """
    执行验证结果

    使用统一命名: validation_status (非 status)
    """
    plan_id: str
    validation_status: str  # passed, failed, partial
    quality_score: float  # 0-1
    criteria_results: dict[str, Any] = field(default_factory=dict)
    tool_summary: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    step_validations: list[StepValidation] = field(default_factory=list)
    aborted: bool = False
    timestamp: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "validation_status": self.validation_status,
            "quality_score": self.quality_score,
            "criteria_results": self.criteria_results,
            "tool_summary": self.tool_summary,
            "issues": self.issues,
            "step_validations": [
                {
                    "step_id": sv.step_id,
                    "tool_name": sv.tool_name,
                    "passed": sv.passed,
                    "duration_ms": sv.duration_ms,
                    "duration_ok": sv.duration_ok,
                    "output_keys_ok": sv.output_keys_ok,
                    "missing_output_keys": sv.missing_output_keys,
                    "required": sv.required,
                }
                for sv in self.step_validations
            ],
            "aborted": self.aborted,
            "timestamp": self.timestamp,
        }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PlanExecutionValidator:
    """方案执行验证器"""

    def __init__(self, record_service: PlanExecutionRecordService | None = None):
        """
        Args:
            record_service: PlanExecutionRecordService 实例 (可选)
        """
        self.record_service = record_service

    async def validate_and_record(
        self,
        plan: ExecutablePlan,
        tool_results: list[ToolResult],
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
        plan: ExecutablePlan,
        tool_results: list[ToolResult],
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
        self, tool_results: list[ToolResult]
    ) -> dict[str, int]:
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
        plan: ExecutablePlan,
        tool_results: list[ToolResult],
    ) -> dict[str, Any]:
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
        results: dict[str, Any] = {
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
        tool_summary: dict[str, int],
        criteria_results: dict[str, Any],
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
        criteria_results: dict[str, Any],
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
        tool_results: list[ToolResult],
        criteria_results: dict[str, Any],
    ) -> list[str]:
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

    # ------------------------------------------------------------------
    # DAG-aware validation (Phase 5)
    # ------------------------------------------------------------------

    async def validate_plan_execution(
        self,
        plan: ExecutablePlan,
        plan_result: PlanExecutionResult,
        user_id: UUID | None = None,
    ) -> ExecutionValidationResult:
        """Validate a PlanExecutionResult with per-step criteria.

        Combines plan-level success_criteria validation with per-step
        StepCriteria checks (expected_output_keys, max_duration_ms).
        """
        # Build a spec lookup: step_id -> ToolCallSpec
        spec_map = {tc.id: tc for tc in plan.tool_calls}

        # 1. Per-step criteria validation
        step_validations: list[StepValidation] = []
        for sr in plan_result.step_results:
            spec = spec_map.get(sr.step_id)
            criteria = spec.success_criteria if spec else None
            sv = self._validate_step(sr, criteria)
            step_validations.append(sv)

        # 2. Plan-level tool summary
        tool_summary = self._analyze_tool_results(plan_result.tool_results)

        # 3. Plan-level success criteria
        criteria_results = await self._check_success_criteria(
            plan, plan_result.tool_results
        )

        # 4. Incorporate step-level results into criteria
        step_pass_count = sum(1 for sv in step_validations if sv.passed)
        step_total = len(step_validations) or 1
        step_pass_rate = step_pass_count / step_total

        required_failures = [
            sv for sv in step_validations
            if not sv.passed and sv.required
        ]

        criteria_results["checks"]["step_criteria"] = {
            "step_pass_rate": step_pass_rate,
            "required_failures": len(required_failures),
            "passed": len(required_failures) == 0,
        }
        criteria_results["criteria_defined"] = True

        # Recompute all_passed
        criteria_results["all_passed"] = all(
            check.get("passed", False)
            for check in criteria_results["checks"].values()
        )

        # 5. Quality score (weighted: tool 0.4, plan criteria 0.3, step criteria 0.3)
        quality_score = self._calculate_dag_quality_score(
            tool_summary, criteria_results, step_pass_rate, plan_result.aborted,
        )

        # 6. Status
        validation_status = self._determine_status(quality_score, criteria_results)
        if plan_result.aborted:
            validation_status = "failed"

        # 7. Issues
        issues = self._collect_issues(plan_result.tool_results, criteria_results)
        for sv in step_validations:
            if not sv.duration_ok:
                issues.append(
                    f"Step '{sv.tool_name}' ({sv.step_id}) exceeded timeout: "
                    f"{sv.duration_ms}ms > {sv.max_duration_ms}ms"
                )
            if not sv.output_keys_ok:
                issues.append(
                    f"Step '{sv.tool_name}' ({sv.step_id}) missing output keys: "
                    f"{sv.missing_output_keys}"
                )
        if plan_result.aborted:
            issues.append(f"Execution aborted: {plan_result.abort_reason}")

        result = ExecutionValidationResult(
            plan_id=plan.plan_id,
            validation_status=validation_status,
            quality_score=quality_score,
            criteria_results=criteria_results,
            tool_summary=tool_summary,
            issues=issues,
            step_validations=step_validations,
            aborted=plan_result.aborted,
        )

        # Persist if record_service available
        if self.record_service and user_id:
            try:
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

        logger.info(
            "DAG validation complete: plan_id={}, status={}, score={:.2f}, "
            "steps={}/{} passed, aborted={}",
            plan.plan_id, validation_status, quality_score,
            step_pass_count, step_total, plan_result.aborted,
        )

        return result

    def _validate_step(
        self,
        sr: StepResult,
        criteria: Any | None,
    ) -> StepValidation:
        """Validate a single step against its StepCriteria."""
        passed = sr.tool_result.success
        duration_ok = True
        output_keys_ok = True
        missing_keys: list[str] = []
        max_duration = 0
        required = True

        if criteria:
            required = criteria.required
            max_duration = criteria.max_duration_ms

            # Duration check
            if max_duration > 0 and sr.duration_ms > max_duration:
                duration_ok = False
                if required:
                    passed = False

            # Output keys check
            if criteria.expected_output_keys and sr.tool_result.success:
                actual_keys = set(sr.output_data.keys()) if sr.output_data else set()
                expected = set(criteria.expected_output_keys)
                missing_keys = list(expected - actual_keys)
                if missing_keys:
                    output_keys_ok = False
                    if required:
                        passed = False

        return StepValidation(
            step_id=sr.step_id,
            tool_name=sr.tool_name,
            passed=passed,
            duration_ms=sr.duration_ms,
            max_duration_ms=max_duration,
            duration_ok=duration_ok,
            output_keys_ok=output_keys_ok,
            missing_output_keys=missing_keys,
            required=required,
        )

    @staticmethod
    def _calculate_dag_quality_score(
        tool_summary: dict[str, int],
        criteria_results: dict[str, Any],
        step_pass_rate: float,
        aborted: bool,
    ) -> float:
        """Quality score with step-level weighting."""
        if aborted:
            return max(0.0, step_pass_rate * 0.3)

        score = 0.0
        success_rate = tool_summary.get("success_rate", 0.0)

        # Tool success rate (weight 0.4)
        score += success_rate * 0.4

        # Plan-level criteria (weight 0.3)
        checks = criteria_results.get("checks", {})
        non_step_checks = {
            k: v for k, v in checks.items() if k != "step_criteria"
        }
        if non_step_checks:
            passed_rate = sum(
                1 for c in non_step_checks.values() if c.get("passed", False)
            ) / len(non_step_checks)
            score += passed_rate * 0.3
        else:
            score += success_rate * 0.3

        # Step criteria (weight 0.3)
        score += step_pass_rate * 0.3

        return min(1.0, max(0.0, score))
