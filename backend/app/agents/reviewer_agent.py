"""
Reviewer Agent - AI内容质量审查系统

核心功能：
1. 使用与生成模型不同的LLM进行审查
2. 量化指标评估（accuracy, completeness, relevance, clarity, safety, feasibility, helpfulness）
3. 精准问题描述和改进建议
4. 支持多种审查对象（LLM响应、执行计划、工具结果）

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger

from app.core.agent_profiles import TaskType
from app.services.llm_service import get_llm_service_for_task

# ============================================
# 审查指标定义
# ============================================

class ReviewMetric(Enum):
    """审查指标枚举"""
    # 内容质量指标
    ACCURACY = "accuracy"           # 准确性：事实正确性
    COMPLETENESS = "completeness"   # 完整性：是否完整回答问题
    RELEVANCE = "relevance"         # 相关性：与用户意图的匹配度
    CLARITY = "clarity"             # 清晰度：表达是否清晰易懂

    # 方案质量指标
    SAFETY = "safety"               # 安全性：是否有危险操作
    FEASIBILITY = "feasibility"     # 可行性：方案是否可执行
    EFFICIENCY = "efficiency"       # 效率性：是否是最优方案

    # 用户体验指标
    HELPFULNESS = "helpfulness"     # 有用性：对用户是否有帮助
    TONE_APPROPRIATENESS = "tone"   # 语气适当性：语气是否得体


class ReviewSeverity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 严重问题，必须修复
    WARNING = "warning"    # 警告问题，建议修复
    INFO = "info"          # 信息提示，可选修复


class ReviewDecision(str, Enum):
    """审查决策"""
    PASSED = "passed"           # 通过审查
    FAILED = "failed"           # 未通过审查
    NEEDS_REFINEMENT = "needs_refinement"  # 需要改进


# ============================================
# 数据结构定义
# ============================================

@dataclass
class QuantifiedMetric:
    """量化指标"""
    metric: ReviewMetric
    score: float           # 0.0 - 1.0
    weight: float = 1.0    # 指标权重
    threshold: float = 0.7 # 通过阈值

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric.value,
            "score": self.score,
            "weight": self.weight,
            "threshold": self.threshold,
            "passed": self.passed,
            "weighted_score": self.weighted_score
        }


@dataclass
class Issue:
    """问题描述"""
    category: str          # 问题类别
    severity: str          # 严重程度: critical/warning/info
    location: str          # 问题位置
    description: str       # 精准描述
    affected_content: str  # 受影响的内容片段
    suggested_fix: str     # 修复建议
    confidence: float      # 建议置信度 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
            "affected_content": self.affected_content[:200] + "..." if len(self.affected_content) > 200 else self.affected_content,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence
        }


@dataclass
class ReviewResult:
    """审查结果"""
    review_id: str                      # 审查ID
    target_type: str                    # 被审查对象类型: plan/response/tool_call
    target_id: str                      # 被审查对象ID
    decision: str                       # 审查决策: passed/failed/needs_refinement
    overall_score: float                # 总体评分 0-1
    metrics: list[QuantifiedMetric]     # 分项指标
    issues: list[Issue]                 # 发现的问题
    improvement_suggestions: list[str]  # 改进建议
    requires_reflection: bool           # 是否需要自我反思修正
    reviewer_model: str                 # 审查使用的模型
    review_timestamp: str               # 审查时间戳

    @property
    def passed(self) -> bool:
        """是否通过审查"""
        return (
            self.decision == ReviewDecision.PASSED and
            self.overall_score >= 0.7 and
            not any(i.severity == ReviewSeverity.CRITICAL.value for i in self.issues)
        )

    @property
    def critical_issues(self) -> list[Issue]:
        """获取严重问题"""
        return [i for i in self.issues if i.severity == ReviewSeverity.CRITICAL.value]

    @property
    def warning_issues(self) -> list[Issue]:
        """获取警告问题"""
        return [i for i in self.issues if i.severity == ReviewSeverity.WARNING.value]

    def get_score_label(self) -> str:
        """获取评分标签"""
        if self.overall_score >= 0.9: return "优秀"
        if self.overall_score >= 0.7: return "良好"
        if self.overall_score >= 0.5: return "及格"
        return "需改进"

    def to_user_facing_dict(self) -> dict[str, Any]:
        """转换为面向用户的字典"""
        return {
            "review_id": self.review_id,
            "overall_score": self.overall_score,
            "score_label": self.get_score_label(),
            "decision": self.decision,
            "metrics": [m.to_dict() for m in self.metrics],
            "issues": [i.to_dict() for i in self.issues],
            "critical_count": len(self.critical_issues),
            "warning_count": len(self.warning_issues),
            "suggestions": self.improvement_suggestions,
            "requires_reflection": self.requires_reflection
        }

    def to_dict(self) -> dict[str, Any]:
        """完整字典表示"""
        return {
            "review_id": self.review_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "decision": self.decision,
            "overall_score": self.overall_score,
            "metrics": [m.to_dict() for m in self.metrics],
            "issues": [i.to_dict() for i in self.issues],
            "improvement_suggestions": self.improvement_suggestions,
            "requires_reflection": self.requires_reflection,
            "reviewer_model": self.reviewer_model,
            "review_timestamp": self.review_timestamp
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewResult":
        """从字典恢复"""
        metrics = [
            QuantifiedMetric(
                metric=ReviewMetric(m["metric"]),
                score=m["score"],
                weight=m.get("weight", 1.0),
                threshold=m.get("threshold", 0.7)
            )
            for m in data.get("metrics", [])
        ]
        issues = [
            Issue(**i) for i in data.get("issues", [])
        ]
        return cls(
            review_id=data["review_id"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            decision=data["decision"],
            overall_score=data["overall_score"],
            metrics=metrics,
            issues=issues,
            improvement_suggestions=data.get("improvement_suggestions", []),
            requires_reflection=data.get("requires_reflection", False),
            reviewer_model=data.get("reviewer_model", "unknown"),
            review_timestamp=data.get("review_timestamp", "")
        )


# ============================================
# 审查提示词模板
# ============================================

REVIEWER_SYSTEM_PROMPT = """你是一位严格但公正的内容审查专家。你的职责是评估AI生成内容的质量。

## 审查原则

1. **客观性**：基于事实和标准进行评估，不带个人偏见
2. **建设性**：指出问题时必须给出可操作的改进建议
3. **精准性**：问题描述要具体，定位到具体位置
4. **用户视角**：始终考虑最终用户的需求和体验

## 评估维度

| 维度 | 说明 | 权重 | 阈值 |
|------|------|------|------|
| accuracy | 内容是否事实正确，无错误信息 | 1.5 | 0.8 |
| completeness | 是否完整回答了用户的问题 | 1.2 | 0.7 |
| relevance | 内容是否与用户意图高度相关 | 1.3 | 0.7 |
| clarity | 表达是否清晰易懂，结构是否合理 | 1.0 | 0.6 |
| safety | 是否包含危险、有害或不当内容 | 2.0 | 0.9 |
| helpfulness | 对用户是否有实际帮助 | 1.0 | 0.7 |

## 输出格式

请以JSON格式返回审查结果：
{
  "overall_score": 0.0-1.0,
  "decision": "passed|failed|needs_refinement",
  "metrics": [
    {"metric": "accuracy", "score": 0.8, "weight": 1.5, "threshold": 0.8},
    ...
  ],
  "issues": [
    {
      "category": "类别",
      "severity": "critical|warning|info",
      "location": "具体位置（如：第2段）",
      "description": "精准描述问题",
      "affected_content": "受影响的内容片段",
      "suggested_fix": "具体修复建议",
      "confidence": 0.9
    }
  ],
  "improvement_suggestions": ["改进建议1", "改进建议2"],
  "requires_reflection": true/false
}

## 审查流程

1. **理解用户意图**：分析用户真正想要什么
2. **评估内容质量**：对照各维度进行评分
3. **识别问题**：找出内容中的具体问题
4. **给出建议**：提供可操作的改进方案
5. **做出决策**：判断是否通过审查"""


PLAN_REVIEW_PROMPT = """请审查以下执行计划：

## 用户请求
{user_query}

## 计划内容
{plan_content}

**置信度**: {confidence}
**工具数量**: {tool_count}
**风险标记**: {risk_flags}

请评估：
1. **安全性**：是否有危险操作（删除、修改等）
2. **完整性**：是否包含所有必要步骤
3. **可行性**：工具参数是否正确，工具是否可用
4. **效率性**：是否是最优执行路径"""


RESPONSE_REVIEW_PROMPT = """请审查以下AI响应：

## 用户问题
{user_query}

## AI响应
{llm_response}

## 上下文信息
- 对话轮数: {turn_count}
- 包含工具调用: {has_tools}
- 工具列表: {tool_list}

请评估：
1. **准确性**：事实是否正确，信息是否准确
2. **完整性**：是否完整回答了用户问题
3. **相关性**：是否与用户意图匹配
4. **清晰度**：表达是否清晰易懂
5. **安全性**：是否包含有害内容
6. **有用性**：对用户是否有实际帮助"""


# ============================================
# ReviewerAgent 实现
# ============================================

class ReviewerAgent:
    """
    审查者Agent - 使用独立LLM模型进行审查

    特点：
    1. 使用与生成模型不同的LLM
    2. 量化指标评估
    3. 结构化问题描述
    4. 可操作的改进建议
    """

    # 默认阈值配置
    DEFAULT_OVERALL_THRESHOLD = 0.7
    DEFAULT_METRIC_THRESHOLD = 0.7

    def __init__(self, reviewer_llm=None):
        """
        初始化审查Agent

        Args:
            reviewer_llm: 可选的LLM服务实例，默认使用REVIEW任务类型的服务
        """
        if reviewer_llm is None:
            # 使用专门用于审查任务的LLM服务
            self.llm = get_llm_service_for_task(TaskType.REVIEW)
        else:
            self.llm = reviewer_llm

        self.reviewer_model = getattr(self.llm, 'default_model', 'reviewer_model')
        logger.info(f"[ReviewerAgent] Initialized with model: {self.reviewer_model}")

    async def review_llm_response(
        self,
        user_query: str,
        llm_response: str,
        context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        审查LLM生成的响应

        Args:
            user_query: 用户原始问题
            llm_response: LLM生成的响应
            context: 额外上下文信息

        Returns:
            ReviewResult: 审查结果
        """
        review_id = f"review_{uuid.uuid4().hex[:12]}"
        logger.info(f"[ReviewerAgent] Reviewing LLM response: {review_id}")

        # 构建审查提示词
        conversation_history = context.get("conversation_history", []) if context else []
        tool_calls = context.get("tool_calls", []) if context else []

        prompt = RESPONSE_REVIEW_PROMPT.format(
            user_query=user_query,
            llm_response=llm_response[:2000],  # 限制长度避免token超限
            turn_count=len(conversation_history) // 2,
            has_tools="是" if tool_calls else "否",
            tool_list=[tc.get("name", "unknown") for tc in tool_calls] if tool_calls else "无"
        )

        try:
            # 调用LLM进行审查
            response = await self.llm.chat_json(
                system_prompt=REVIEWER_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.2
            )

            return self._parse_review_result(
                response=response,
                target_type="response",
                target_id=review_id
            )

        except Exception as e:
            logger.error(f"[ReviewerAgent] Review failed: {e}")
            # 返回一个默认的审查结果
            return ReviewResult(
                review_id=review_id,
                target_type="response",
                target_id=review_id,
                decision=ReviewDecision.NEEDS_REFINEMENT.value,
                overall_score=0.5,
                metrics=[
                    QuantifiedMetric(ReviewMetric.ACCURACY, 0.5),
                    QuantifiedMetric(ReviewMetric.COMPLETENESS, 0.5),
                    QuantifiedMetric(ReviewMetric.RELEVANCE, 0.5)
                ],
                issues=[Issue(
                    category="system",
                    severity="warning",
                    location="system",
                    description=f"审查过程出错: {str(e)}",
                    affected_content="",
                    suggested_fix="建议人工审核此内容",
                    confidence=0.5
                )],
                improvement_suggestions=["审查系统出现错误，建议人工复核"],
                requires_reflection=False,
                reviewer_model=self.reviewer_model,
                review_timestamp=context.get("timestamp", "") if context else ""
            )

    async def review_plan(
        self,
        plan: dict[str, Any],
        user_query: str,
        context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        审查执行计划

        Args:
            plan: 执行计划（ExecutablePlan）
            user_query: 用户原始问题
            context: 额外上下文信息

        Returns:
            ReviewResult: 审查结果
        """
        review_id = f"plan_review_{uuid.uuid4().hex[:12]}"
        logger.info(f"[ReviewerAgent] Reviewing plan: {review_id}")

        # 提取计划信息
        tool_calls = plan.get("tool_calls", [])
        rationale = plan.get("rationale", "")
        confidence = plan.get("confidence", 0.0)
        risk_flags = plan.get("risk_flags", [])

        # 构建工具列表
        tool_summary = []
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
            params = tc.get("params") if isinstance(tc, dict) else getattr(tc, "params", {})
            tool_summary.append(f"- {name}: {json.dumps(params, ensure_ascii=False)[:100]}")

        prompt = PLAN_REVIEW_PROMPT.format(
            user_query=user_query,
            plan_content=f"**理由**: {rationale}\n\n**工具调用**:\n" + "\n".join(tool_summary),
            confidence=f"{confidence:.1%}",
            tool_count=len(tool_calls),
            risk_flags=", ".join(risk_flags) if risk_flags else "无"
        )

        try:
            response = await self.llm.chat_json(
                system_prompt=REVIEWER_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.2
            )

            return self._parse_review_result(
                response=response,
                target_type="plan",
                target_id=review_id
            )

        except Exception as e:
            logger.error(f"[ReviewerAgent] Plan review failed: {e}")
            return ReviewResult(
                review_id=review_id,
                target_type="plan",
                target_id=review_id,
                decision=ReviewDecision.NEEDS_REFINEMENT.value,
                overall_score=0.5,
                metrics=[
                    QuantifiedMetric(ReviewMetric.SAFETY, 0.5),
                    QuantifiedMetric(ReviewMetric.FEASIBILITY, 0.5)
                ],
                issues=[],
                improvement_suggestions=[f"计划审查出错: {str(e)}"],
                requires_reflection=False,
                reviewer_model=self.reviewer_model,
                review_timestamp=""
            )

    async def review_tool_result(
        self,
        tool_name: str,
        tool_result: Any,
        context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        审查工具执行结果

        Args:
            tool_name: 工具名称
            tool_result: 工具执行结果
            context: 额外上下文信息

        Returns:
            ReviewResult: 审查结果
        """
        review_id = f"tool_review_{uuid.uuid4().hex[:12]}"
        logger.info(f"[ReviewerAgent] Reviewing tool result: {tool_name}")

        # 简化版工具结果审查
        # 主要检查：结果是否有效，是否有错误

        is_valid = True
        issues = []

        if isinstance(tool_result, dict) and not tool_result.get("success", True):
            is_valid = False
            issues.append(Issue(
                category="execution",
                severity="warning",
                location=f"tool:{tool_name}",
                description="工具执行未成功",
                affected_content=str(tool_result.get("error_message", "")),
                suggested_fix="检查工具参数或重试",
                confidence=0.8
            ))

        return ReviewResult(
            review_id=review_id,
            target_type="tool_result",
            target_id=tool_name,
            decision=ReviewDecision.PASSED.value if is_valid else ReviewDecision.NEEDS_REFINEMENT.value,
            overall_score=0.9 if is_valid else 0.5,
            metrics=[
                QuantifiedMetric(ReviewMetric.ACCURACY, 0.9 if is_valid else 0.5),
                QuantifiedMetric(ReviewMetric.COMPLETENESS, 0.9 if is_valid else 0.5)
            ],
            issues=issues,
            improvement_suggestions=[],
            requires_reflection=False,
            reviewer_model=self.reviewer_model,
            review_timestamp=context.get("timestamp", "") if context else ""
        )

    def _parse_review_result(
        self,
        response: dict[str, Any],
        target_type: str,
        target_id: str
    ) -> ReviewResult:
        """
        解析LLM审查响应

        Args:
            response: LLM返回的JSON响应
            target_type: 目标类型
            target_id: 目标ID

        Returns:
            ReviewResult: 解析后的审查结果
        """
        try:
            overall_score = float(response.get("overall_score", 0.7))
            decision = response.get("decision", ReviewDecision.NEEDS_REFINEMENT.value)
            requires_reflection = response.get("requires_reflection", False)

            # 解析指标
            metrics = []
            for m in response.get("metrics", []):
                metric_name = m.get("metric", "accuracy")
                try:
                    metric_enum = ReviewMetric(metric_name)
                except ValueError:
                    metric_enum = ReviewMetric.ACCURACY

                metrics.append(QuantifiedMetric(
                    metric=metric_enum,
                    score=float(m.get("score", 0.7)),
                    weight=float(m.get("weight", 1.0)),
                    threshold=float(m.get("threshold", 0.7))
                ))

            # 解析问题
            issues = []
            for i in response.get("issues", []):
                issues.append(Issue(
                    category=i.get("category", "general"),
                    severity=i.get("severity", "info"),
                    location=i.get("location", ""),
                    description=i.get("description", ""),
                    affected_content=i.get("affected_content", ""),
                    suggested_fix=i.get("suggested_fix", ""),
                    confidence=float(i.get("confidence", 0.7))
                ))

            # 确保决策与分数一致
            if overall_score >= 0.7 and not any(i["severity"] == "critical" for i in response.get("issues", [])):
                decision = ReviewDecision.PASSED.value
            elif overall_score < 0.5:
                decision = ReviewDecision.FAILED.value
            else:
                decision = ReviewDecision.NEEDS_REFINEMENT.value

            return ReviewResult(
                review_id=target_id,
                target_type=target_type,
                target_id=target_id,
                decision=decision,
                overall_score=overall_score,
                metrics=metrics,
                issues=issues,
                improvement_suggestions=response.get("improvement_suggestions", []),
                requires_reflection=requires_reflection,
                reviewer_model=self.reviewer_model,
                review_timestamp=response.get("timestamp", "")
            )

        except Exception as e:
            logger.error(f"[ReviewerAgent] Failed to parse review result: {e}")
            # 返回默认结果
            return ReviewResult(
                review_id=target_id,
                target_type=target_type,
                target_id=target_id,
                decision=ReviewDecision.NEEDS_REFINEMENT.value,
                overall_score=0.5,
                metrics=[
                    QuantifiedMetric(ReviewMetric.ACCURACY, 0.5),
                    QuantifiedMetric(ReviewMetric.COMPLETENESS, 0.5)
                ],
                issues=[],
                improvement_suggestions=[f"解析审查结果时出错: {str(e)}"],
                requires_reflection=False,
                reviewer_model=self.reviewer_model,
                review_timestamp=""
            )


# ============================================
# 全局单例
# ============================================

_reviewer_agent_instance: ReviewerAgent | None = None


def get_reviewer_agent() -> ReviewerAgent:
    """获取审查Agent单例"""
    global _reviewer_agent_instance
    if _reviewer_agent_instance is None:
        _reviewer_agent_instance = ReviewerAgent()
    return _reviewer_agent_instance


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":

    async def test_review():
        """测试审查功能"""
        reviewer = ReviewerAgent()

        # 测试响应审查
        result = await reviewer.review_llm_response(
            user_query="什么是神经网络？",
            llm_response="神经网络是一种模仿生物神经网络的计算模型...",
            context={"conversation_history": []}
        )

        print(f"审查结果: {result.decision}")
        print(f"总体评分: {result.overall_score:.1%}")
        print(f"问题数量: {len(result.issues)}")
        for issue in result.issues:
            print(f"  - [{issue.severity}] {issue.description}")

    # asyncio.run(test_review())
