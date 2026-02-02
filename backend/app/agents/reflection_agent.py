"""
Reflection Agent - 自我反思与修正Agent

核心功能：
1. 基于审查意见分析问题
2. 生成修正策略
3. 执行内容修正
4. 多轮迭代管理
5. 反思历史追踪与学习

与ReviewerAgent配合使用，形成完整的审查-反思-修正闭环。

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger

from app.agents.reviewer_agent import (
    Issue,
    ReviewDecision,
    ReviewerAgent,
    ReviewResult,
)

# ============================================
# 反思策略定义
# ============================================

class ReflectionStrategy(str, Enum):
    """反思修正策略"""
    DIRECT_FIX = "direct_fix"           # 直接修复：根据建议直接修改
    REGENERATE = "regenerate"            # 重新生成：完全重新生成内容
    TARGETED_REFINE = "targeted_refine"  # 精准优化：只修改问题部分
    CLARIFY_AND_FIX = "clarify_and_fix"  # 澄清后修复：先理解再修正
    ESCALATE = "escalate"                # 升级处理：无法自动修正


class ReflectionOutcome(str, Enum):
    """反思结果"""
    FIXED = "fixed"                     # 已修正
    IMPROVED = "improved"               # 有改善
    NO_CHANGE = "no_change"             # 无变化
    DEGRADED = "degraded"               # 变差了
    FAILED = "failed"                   # 修正失败


@dataclass
class ReflectionRound:
    """单轮反思记录"""
    round_number: int
    timestamp: str
    original_score: float
    original_content: str
    strategy: ReflectionStrategy
    fixed_content: str
    new_score: float
    issues_addressed: list[str]        # 本轮解决的问题
    issues_remaining: list[str]        # 仍存在的问题
    outcome: ReflectionOutcome
    reasoning: str                      # 反思推理过程


@dataclass
class ReflectionResult:
    """反思结果"""
    reflection_id: str
    target_id: str                      # 原始审查ID
    total_rounds: int
    final_outcome: ReflectionOutcome
    initial_score: float
    final_score: float
    score_delta: float
    rounds: list[ReflectionRound]
    success: bool
    final_content: str
    reasoning: str                      # 总体推理说明


# ============================================
# 反思提示词模板
# ============================================

REFLECTION_SYSTEM_PROMPT = """你是一位内容优化专家，负责基于审查反馈修正AI生成的内容。

## 修正原则

1. **精准定位**：针对审查中指出的具体问题进行修正
2. **保持优势**：保留原内容中做得好的部分
3. **适度调整**：修正幅度以解决问题为限，不过度调整
4. **用户导向**：始终考虑用户的原始需求和意图

## 修正流程

1. **理解审查意见**：
   - 仔细阅读审查结果，理解每个问题的核心
   - 识别问题优先级（critical > warning > info）

2. **分析修正策略**：
   - critical问题：必须修复
   - warning问题：应该修复
   - info问题：可选修复

3. **执行修正**：
   - 准确修改问题部分
   - 保持整体结构和风格
   - 确保不引入新问题

4. **自我验证**：
   - 修正后重新检查
   - 确认所有关键问题已解决

## 输出要求

请直接输出修正后的内容，不需要解释或说明。
保持原内容的格式和风格。"""


DIRECT_FIX_PROMPT = """请修正以下内容中的问题：

【原始内容】
{original_content}

【需要修复的问题】
{issues_summary}

【具体修复建议】
{fix_suggestions}

请直接输出修正后的完整内容。"""


REGENERATE_PROMPT = """审查发现当前内容存在严重问题，需要重新生成：

【用户问题】
{user_query}

【当前内容（存在严重问题）】
{original_content}

【审查发现的问题】
{critical_issues}

请重新生成一个更好的回答，确保解决上述所有问题。"""


TARGETED_REFINE_PROMPT = """请精准优化以下内容中的特定部分：

【原始内容】
{original_content}

【需要优化的部分】
{targeted_sections}

【优化建议】
{fix_suggestions}

只修改需要优化的部分，保持其他内容不变。输出完整修正后的内容。"""


# ============================================
# ReflectionAgent 实现
# ============================================

class ReflectionAgent:
    """
    反思修正Agent - 基于审查结果自动修正内容

    特点：
    1. 智能选择修正策略
    2. 多轮迭代管理
    3. 反思历史追踪
    4. 自动终止判断
    """

    # 默认配置
    DEFAULT_MAX_ROUNDS = 3
    DEFAULT_MIN_IMPROVEMENT = 0.05  # 最小改善幅度
    DEFAULT_TARGET_SCORE = 0.8      # 目标分数

    def __init__(
        self,
        generator_llm=None,
        reviewer: ReviewerAgent | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        min_improvement: float = DEFAULT_MIN_IMPROVEMENT,
        target_score: float = DEFAULT_TARGET_SCORE
    ):
        """
        初始化反思Agent

        Args:
            generator_llm: 用于生成修正内容的LLM
            reviewer: 用于重新审查的ReviewerAgent
            max_rounds: 最大反思轮次
            min_improvement: 最小改善幅度（低于此值停止迭代）
            target_score: 目标分数（达到此值停止迭代）
        """
        if generator_llm is None:
            from app.agents.reviewer_agent import TaskType
            from app.services.llm_service import get_llm_service_for_task
            generator_llm = get_llm_service_for_task(TaskType.STANDARD_RESPONSE)

        self.generator = generator_llm
        self.reviewer = reviewer or ReviewerAgent()
        self.max_rounds = max_rounds
        self.min_improvement = min_improvement
        self.target_score = target_score

        logger.info(
            f"[ReflectionAgent] Initialized: max_rounds={max_rounds}, "
            f"min_improvement={min_improvement}, target_score={target_score}"
        )

    async def reflect_and_fix(
        self,
        user_query: str,
        original_content: str,
        review_result: ReviewResult,
        context: dict[str, Any] | None = None
    ) -> ReflectionResult:
        """
        基于审查结果进行反思和修正

        Args:
            user_query: 用户原始问题
            original_content: 原始生成内容
            review_result: 审查结果
            context: 额外上下文

        Returns:
            ReflectionResult: 反思结果
        """
        reflection_id = f"reflection_{uuid.uuid4().hex[:12]}"
        logger.info(f"[ReflectionAgent] Starting reflection {reflection_id}")

        rounds_history: list[ReflectionRound] = []
        current_content = original_content
        current_score = review_result.overall_score

        for round_num in range(1, self.max_rounds + 1):
            logger.info(
                f"[ReflectionAgent] Round {round_num}/{self.max_rounds}, "
                f"current_score={current_score:.2f}"
            )

            # 1. 分析问题并选择策略
            strategy = self._select_strategy(
                review_result,
                round_num,
                current_score
            )

            # 2. 执行修正
            fixed_content, reasoning = await self._execute_fix(
                user_query=user_query,
                current_content=current_content,
                review_result=review_result,
                strategy=strategy,
                context=context or {}
            )

            # 3. 重新审查
            new_review = await self.reviewer.review_llm_response(
                user_query=user_query,
                llm_response=fixed_content,
                context={
                    **(context or {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # 4. 评估本轮结果
            outcome = self._evaluate_outcome(
                current_score,
                new_review.overall_score,
                review_result,
                new_review
            )

            # 5. 记录本轮
            round_record = ReflectionRound(
                round_number=round_num,
                timestamp=datetime.utcnow().isoformat(),
                original_score=current_score,
                original_content=current_content,
                strategy=strategy,
                fixed_content=fixed_content,
                new_score=new_review.overall_score,
                issues_addressed=self._get_addressed_issues(review_result, new_review),
                issues_remaining=[i.description for i in new_review.issues],
                outcome=outcome,
                reasoning=reasoning
            )
            rounds_history.append(round_record)

            logger.info(
                f"[ReflectionAgent] Round {round_num} complete: "
                f"{outcome.value}, {current_score:.2f} -> {new_review.overall_score:.2f}"
            )

            # 6. 决定是否继续
            if new_review.passed or new_review.overall_score >= self.target_score:
                logger.info("[ReflectionAgent] Target achieved, stopping")
                current_content = fixed_content
                current_score = new_review.overall_score
                break

            if outcome == ReflectionOutcome.NO_CHANGE:
                logger.warning("[ReflectionAgent] No improvement, stopping")
                break

            if outcome == ReflectionOutcome.DEGRADED:
                logger.warning("[ReflectionAgent] Content degraded, reverting")
                break

            # 继续下一轮
            current_content = fixed_content
            current_score = new_review.overall_score
            review_result = new_review

        # 7. 构建最终结果
        success = (
            current_score >= self.target_score or
            rounds_history[-1].outcome == ReflectionOutcome.FIXED
        )

        result = ReflectionResult(
            reflection_id=reflection_id,
            target_id=review_result.review_id,
            total_rounds=len(rounds_history),
            final_outcome=rounds_history[-1].outcome if rounds_history else ReflectionOutcome.FAILED,
            initial_score=original_content and review_result.overall_score or 0,
            final_score=current_score,
            score_delta=current_score - (review_result.overall_score if original_content else 0),
            rounds=rounds_history,
            success=success,
            final_content=current_content,
            reasoning=self._generate_summary_reasoning(rounds_history)
        )

        logger.info(
            f"[ReflectionAgent] Reflection complete: "
            f"success={success}, score_delta={result.score_delta:.2f}, "
            f"rounds={result.total_rounds}"
        )

        return result

    def _select_strategy(
        self,
        review_result: ReviewResult,
        round_num: int,
        current_score: float
    ) -> ReflectionStrategy:
        """
        选择修正策略

        Args:
            review_result: 当前审查结果
            round_num: 当前轮次
            current_score: 当前分数

        Returns:
            ReflectionStrategy: 选择的策略
        """
        critical_count = len(review_result.critical_issues)
        len(review_result.warning_issues)

        # 严重问题多，直接重新生成
        if critical_count >= 2 or (critical_count >= 1 and current_score < 0.4):
            return ReflectionStrategy.REGENERATE

        # 第一轮且分数很低，重新生成
        if round_num == 1 and current_score < 0.3:
            return ReflectionStrategy.REGENERATE

        # 问题集中在特定部分，精准优化
        if review_result.issues and self._are_issues_localized(review_result.issues):
            return ReflectionStrategy.TARGETED_REFINE

        # 默认直接修复
        return ReflectionStrategy.DIRECT_FIX

    def _are_issues_localized(self, issues: list[Issue]) -> bool:
        """检查问题是否集中在特定部分"""
        if not issues:
            return False

        # 检查问题位置是否有共同特征
        locations = [i.location for i in issues if i.location]
        if len(locations) < 2:
            return True

        # 检查是否有超过50%的问题在同一位置
        location_counts = {}
        for loc in locations:
            location_counts[loc] = location_counts.get(loc, 0) + 1

        max_count = max(location_counts.values()) if location_counts else 0
        return max_count >= len(issues) / 2

    async def _execute_fix(
        self,
        user_query: str,
        current_content: str,
        review_result: ReviewResult,
        strategy: ReflectionStrategy,
        context: dict[str, Any]
    ) -> tuple[str, str]:
        """
        执行修正

        Args:
            user_query: 用户问题
            current_content: 当前内容
            review_result: 审查结果
            strategy: 修正策略
            context: 上下文

        Returns:
            (fixed_content, reasoning): 修正后的内容和推理说明
        """
        # 构建问题描述
        issues_summary = self._format_issues(review_result.issues)
        fix_suggestions = self._format_suggestions(review_result)

        if strategy == ReflectionStrategy.REGENERATE:
            prompt = REGENERATE_PROMPT.format(
                user_query=user_query,
                original_content=current_content[:1000],
                critical_issues=self._format_issues(review_result.critical_issues)
            )
            reasoning = f"重新生成（发现{len(review_result.critical_issues)}个严重问题）"

        elif strategy == ReflectionStrategy.TARGETED_REFINE:
            # 找出需要优化的部分
            targeted_sections = self._extract_targeted_sections(review_result.issues, current_content)
            prompt = TARGETED_REFINE_PROMPT.format(
                original_content=current_content,
                targeted_sections=targeted_sections,
                fix_suggestions=fix_suggestions
            )
            reasoning = f"精准优化（{len(review_result.issues)}个问题）"

        else:  # DIRECT_FIX
            prompt = DIRECT_FIX_PROMPT.format(
                original_content=current_content,
                issues_summary=issues_summary,
                fix_suggestions=fix_suggestions
            )
            reasoning = f"直接修复（{len(review_result.issues)}个问题）"

        try:
            fixed_content = await self.generator.chat(
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.6  # 略低于原始生成，保持一致性
            )

            return fixed_content, reasoning

        except Exception as e:
            logger.error(f"[ReflectionAgent] Fix execution failed: {e}")
            return current_content, f"修正失败: {str(e)}"

    def _format_issues(self, issues: list[Issue]) -> str:
        """格式化问题列表"""
        if not issues:
            return "无问题"

        lines = []
        for i, issue in enumerate(issues, 1):
            severity_marker = {"critical": "!!", "warning": "!", "info": "i"}
            marker = severity_marker.get(issue.severity, "?")
            lines.append(f"{i}. [{marker}] {issue.description}")
            if issue.suggested_fix:
                lines.append(f"   建议: {issue.suggested_fix}")

        return "\n".join(lines)

    def _format_suggestions(self, review_result: ReviewResult) -> str:
        """格式化改进建议"""
        suggestions = review_result.improvement_suggestions
        if not suggestions:
            return "无具体建议"
        return "\n".join(f"- {s}" for s in suggestions)

    def _extract_targeted_sections(
        self,
        issues: list[Issue],
        content: str
    ) -> str:
        """提取需要优化的内容部分"""
        sections = []
        for issue in issues:
            if issue.affected_content:
                sections.append(f"- {issue.category}: {issue.affected_content[:100]}...")
            else:
                sections.append(f"- {issue.category}: {issue.location}")
        return "\n".join(sections) if sections else "需要审查的部分"

    def _get_addressed_issues(
        self,
        old_review: ReviewResult,
        new_review: ReviewResult
    ) -> list[str]:
        """获取本轮已解决的问题"""
        old_descriptions = {i.description for i in old_review.issues}
        new_descriptions = {i.description for i in new_review.issues}

        addressed = old_descriptions - new_descriptions
        return list(addressed)

    def _evaluate_outcome(
        self,
        old_score: float,
        new_score: float,
        old_review: ReviewResult,
        new_review: ReviewResult
    ) -> ReflectionOutcome:
        """
        评估本轮反思结果

        Args:
            old_score: 修正前分数
            new_score: 修正后分数
            old_review: 修正前审查结果
            new_review: 修正后审查结果

        Returns:
            ReflectionOutcome: 反思结果
        """
        score_delta = new_score - old_score

        # 检查是否通过
        if new_review.passed:
            if score_delta > 0:
                return ReflectionOutcome.FIXED
            return ReflectionOutcome.IMPROVED

        # 检查改善幅度
        if score_delta >= self.min_improvement:
            return ReflectionOutcome.IMPROVED

        # 检查是否变差
        if score_delta < -self.min_improvement:
            return ReflectionOutcome.DEGRADED

        # 检查问题数量变化
        if len(new_review.issues) < len(old_review.issues):
            return ReflectionOutcome.IMPROVED

        return ReflectionOutcome.NO_CHANGE

    def _generate_summary_reasoning(self, rounds: list[ReflectionRound]) -> str:
        """生成总体推理说明"""
        if not rounds:
            return "无反思记录"

        parts = []
        parts.append(f"共执行 {len(rounds)} 轮反思")

        for round_record in rounds:
            parts.append(
                f"第{round_record.round_number}轮: "
                f"{round_record.strategy.value}, "
                f"{round_record.original_score:.2f} → {round_record.new_score:.2f}, "
                f"结果: {round_record.outcome.value}"
            )

        final_outcome = rounds[-1].outcome
        parts.append(f"最终结果: {final_outcome.value}")

        return "\n".join(parts)


# ============================================
# 全局单例
# ============================================

_reflection_agent_instance: ReflectionAgent | None = None


def get_reflection_agent() -> ReflectionAgent:
    """获取反思Agent单例"""
    global _reflection_agent_instance
    if _reflection_agent_instance is None:
        _reflection_agent_instance = ReflectionAgent()
    return _reflection_agent_instance


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":

    async def test_reflection():
        """测试反思功能"""
        from app.agents.reviewer_agent import Issue, ReviewSeverity

        # 创建模拟的审查结果
        mock_review = ReviewResult(
            review_id="test_review",
            target_type="response",
            target_id="test_123",
            decision=ReviewDecision.NEEDS_REFINEMENT.value,
            overall_score=0.5,
            metrics=[],
            issues=[
                Issue(
                    category="completeness",
                    severity=ReviewSeverity.WARNING.value,
                    location="整体",
                    description="回答不够完整，缺少关键细节",
                    affected_content="...",
                    suggested_fix="补充更多细节和例子",
                    confidence=0.8
                )
            ],
            improvement_suggestions=["添加具体例子", "提供更多细节"],
            requires_reflection=True,
            reviewer_model="test_model",
            review_timestamp=""
        )

        reflector = ReflectionAgent()

        result = await reflector.reflect_and_fix(
            user_query="什么是机器学习？",
            original_content="机器学习是人工智能的一个分支。",
            review_result=mock_review
        )

        print(f"反思完成: {result.final_outcome}")
        print(f"分数变化: {result.initial_score:.2f} → {result.final_score:.2f}")
        print(f"执行轮数: {result.total_rounds}")

    # asyncio.run(test_reflection())
