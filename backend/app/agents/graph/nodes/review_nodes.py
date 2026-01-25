"""
Review Nodes - LangGraph审查节点

Phase 1: 全流程审查系统
- generation_review_node: 审查LLM生成后的响应
- execution_review_node: 审查工具执行结果
- reflection_node: 基于审查结果进行自我反思修正

Phase 2a: 使用ReflectionAgent进行完整的多轮反思修正

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from app.agents.graph.state import (
    SparkleState,
    ReviewStatus,
    ReviewTargetType,
    ReviewContext,
    ReviewHistoryEntry,
)
from app.agents.reviewer_agent import ReviewerAgent, get_reviewer_agent, ReviewResult
from app.agents.reflection_agent import ReflectionAgent, get_reflection_agent


# ============================================
# 全局ReviewerAgent实例
# ============================================

_reviewer_agent: Optional[ReviewerAgent] = None


def _get_reviewer() -> ReviewerAgent:
    """获取ReviewerAgent单例"""
    global _reviewer_agent
    if _reviewer_agent is None:
        _reviewer_agent = get_reviewer_agent()
    return _reviewer_agent


# ============================================
# 审查配置
# ============================================

REVIEW_CONFIG_DEFAULTS = {
    "enable_review": True,           # 是否启用审查
    "overall_threshold": 0.7,        # 总体通过阈值
    "critical_threshold": 0.9,       # 关键指标阈值
    "max_reflection_rounds": 3,      # 最大反思轮次
    "skip_simple_responses": True,   # 跳过简单响应的审查
    "simple_response_length": 100,   # 简单响应长度阈值
    "skip_patterns": ["你好", "hi", "hello"],  # 跳过审查的模式
}


def _should_skip_review(state: SparkleState) -> bool:
    """
    判断是否应该跳过审查

    Args:
        state: 当前状态

    Returns:
        bool: True表示跳过审查
    """
    # 检查用户配置
    enable_deep_review = state.get("enable_deep_review", True)
    if not enable_deep_review:
        return True

    # 获取审查配置
    review_config = state.get("review_config", {})
    config = {**REVIEW_CONFIG_DEFAULTS, **review_config}

    if not config.get("enable_review", True):
        return True

    # 检查是否是简单响应
    if config.get("skip_simple_responses"):
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            content_lower = content.lower()

            # 检查长度
            if len(content) < config.get("simple_response_length", 100):
                return True

            # 检查跳过模式
            skip_patterns = config.get("skip_patterns", [])
            for pattern in skip_patterns:
                if pattern.lower() in content_lower:
                    return True

    return False


# ============================================
# 审查节点实现
# ============================================

async def generation_review_node(state: SparkleState) -> Dict[str, Any]:
    """
    生成后审查节点 - 审查LLM生成的响应

    这是Phase 1的核心审查节点，位于generation节点之后。

    工作流程:
    1. 检查是否需要跳过审查
    2. 提取用户查询和LLM响应
    3. 调用ReviewerAgent进行审查
    4. 根据审查结果决定下一步：
       - passed → 继续执行（tool_execution或结束）
       - failed + requires_reflection → reflection节点
       - failed → user_approval或直接结束

    Args:
        state: 当前LangGraph状态

    Returns:
        状态更新字典
    """
    logger.info("[ReviewNode] generation_review_node invoked")

    # 1. 检查是否跳过审查
    if _should_skip_review(state):
        logger.info("[ReviewNode] Skipping review (configuration or simple response)")
        return {
            "next_step": state.get("next_step", "__end__"),
            "review_context": {
                "status": ReviewStatus.SKIPPED,
                "review_id": f"skipped_{int(time.time())}",
            }
        }

    # 2. 获取最后生成的响应
    messages = state.get("messages", [])
    if not messages:
        logger.warning("[ReviewNode] No messages to review")
        return {"next_step": "__end__"}

    # 找到最后一条assistant消息
    last_assistant_msg = None
    last_assistant_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = getattr(msg, 'role', None)
        if role == "assistant":
            last_assistant_msg = msg
            last_assistant_idx = i
            break

    if not last_assistant_msg:
        logger.warning("[ReviewNode] No assistant message to review")
        return {"next_step": "__end__"}

    llm_response = getattr(last_assistant_msg, 'content', '')
    if not llm_response:
        logger.warning("[ReviewNode] Empty response, skipping review")
        return {"next_step": "__end__"}

    # 3. 获取用户查询
    user_query = ""
    if last_assistant_idx > 0:
        user_msg = messages[last_assistant_idx - 1]
        user_query = getattr(user_msg, 'content', '')

    logger.info(f"[ReviewNode] Reviewing response: {len(llm_response)} chars")

    # 4. 执行审查
    reviewer = _get_reviewer()
    review_result: ReviewResult = await reviewer.review_llm_response(
        user_query=user_query,
        llm_response=llm_response,
        context={
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "conversation_history": messages[:last_assistant_idx],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    logger.info(
        f"[ReviewNode] Review complete: "
        f"decision={review_result.decision}, score={review_result.overall_score:.2f}, "
        f"issues={len(review_result.issues)}"
    )

    # 5. 构建审查上下文
    review_context: ReviewContext = {
        "review_id": review_result.review_id,
        "status": ReviewStatus.PASSED if review_result.passed else ReviewStatus.FAILED,
        "target_type": ReviewTargetType.LLM_RESPONSE,
        "result": review_result.to_dict(),
        "reflection_round": 0,
        "reviewer_model": review_result.reviewer_model,
        "original_content": llm_response,
        "reviewed_content": None,
    }

    # 6. 记录审查历史
    history_entry: ReviewHistoryEntry = {
        "review_id": review_result.review_id,
        "timestamp": datetime.utcnow().isoformat(),
        "target_type": ReviewTargetType.LLM_RESPONSE,
        "decision": review_result.decision,
        "overall_score": review_result.overall_score,
        "issues_count": len(review_result.issues),
        "user_satisfied": None,  # 将由用户反馈填充
    }

    # 7. 决定下一步
    next_step = "__end__"

    if review_result.passed:
        # 审查通过
        logger.info(f"[ReviewNode] Review PASSED: score={review_result.overall_score:.2f}")
        # 如果有工具调用，去执行；否则结束
        if state.get("context_data", {}).get("tool_calls"):
            next_step = "tool_execution"
        else:
            next_step = "__end__"
    else:
        # 审查未通过
        if review_result.requires_reflection:
            # 需要自我反思修正
            logger.info(f"[ReviewNode] Review FAILED, entering reflection")
            review_context["status"] = ReviewStatus.REFLECTING
            next_step = "reflection"
        else:
            # 不需要反思，直接结束或需要用户批准
            if review_result.critical_issues:
                logger.warning(f"[ReviewNode] Review FAILED with critical issues")
                # 可以选择通知用户或记录问题
                next_step = "__end__"
            else:
                # 警告级别问题，可以继续
                logger.info(f"[ReviewNode] Review passed with warnings")
                next_step = "tool_execution" if state.get("context_data", {}).get("tool_calls") else "__end__"

    return {
        "next_step": next_step,
        "review_context": review_context,
        "review_history": [history_entry],  # Annotated list with operator.add
    }


async def execution_review_node(state: SparkleState) -> Dict[str, Any]:
    """
    执行后审查节点 - 审查工具执行结果

    位于tool_execution节点之后，检查工具执行结果的有效性。

    Args:
        state: 当前LangGraph状态

    Returns:
        状态更新字典
    """
    logger.info("[ReviewNode] execution_review_node invoked")

    # 获取工具执行结果
    context_data = state.get("context_data", {})
    tool_results = context_data.get("tool_results", [])

    if not tool_results:
        logger.info("[ReviewNode] No tool results to review")
        # 如果没有工具结果，回到generation继续对话
        return {"next_step": "generation"}

    reviewer = _get_reviewer()
    all_passed = True
    issues_summary = []

    for tool_result in tool_results:
        tool_name = tool_result.get("name", "unknown")
        result_data = tool_result.get("result", {})

        review_result = await reviewer.review_tool_result(
            tool_name=tool_name,
            tool_result=result_data,
            context={
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        if not review_result.passed:
            all_passed = False
            for issue in review_result.issues:
                issues_summary.append(f"[{tool_name}] {issue.description}")

    if issues_summary:
        logger.warning(f"[ReviewNode] Tool execution issues: {issues_summary}")
        # 存储问题但不中断流程
        context_data["tool_review_issues"] = issues_summary

    # 工具执行后，回到generation解释结果
    return {
        "next_step": "generation",
        "context_data": context_data
    }


async def reflection_node(state: SparkleState) -> Dict[str, Any]:
    """
    反思修正节点 - 基于审查结果自动修正内容 (Phase 2a: 完整版)

    使用ReflectionAgent进行多轮反思修正，智能选择修正策略。

    工作流程:
    1. 获取审查上下文和结果
    2. 创建ReviewResult对象
    3. 调用ReflectionAgent进行多轮反思
    4. 根据反思结果决定下一步

    Args:
        state: 当前LangGraph状态

    Returns:
        状态更新字典
    """
    logger.info("[ReviewNode] reflection_node invoked (Phase 2a: full ReflectionAgent)")

    # 获取当前审查上下文
    review_context: Optional[ReviewContext] = state.get("review_context")
    if not review_context:
        logger.warning("[ReviewNode] No review context, ending reflection")
        return {"next_step": "__end__"}

    reflection_round = review_context.get("reflection_round", 0)
    MAX_REFLECTION_ROUNDS = 3

    if reflection_round >= MAX_REFLECTION_ROUNDS:
        logger.warning(f"[ReviewNode] Max reflection rounds ({MAX_REFLECTION_ROUNDS}) reached")
        return {"next_step": "__end__"}

    # 获取审查结果
    review_result_dict = review_context.get("result")
    if not review_result_dict:
        logger.warning("[ReviewNode] No review result, ending reflection")
        return {"next_step": "__end__"}

    # 获取原始内容和用户查询
    original_content = review_context.get("original_content", "")
    messages = state.get("messages", [])

    # 找到用户查询
    user_query = ""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = getattr(msg, 'role', None)
        if role == "user":
            user_query = getattr(msg, 'content', '')
            break

    if not user_query:
        logger.warning("[ReviewNode] No user query found")
        return {"next_step": "__end__"}

    # 重建ReviewResult对象
    review_result = ReviewResult.from_dict(review_result_dict)

    logger.info(
        f"[ReviewNode] Starting ReflectionAgent: "
        f"initial_score={review_result.overall_score:.2f}, "
        f"issues={len(review_result.issues)}, "
        f"round={reflection_round + 1}/{MAX_REFLECTION_ROUNDS}"
    )

    try:
        # 获取ReflectionAgent并执行反思
        reflector = get_reflection_agent()

        # 执行反思修正
        reflection_result = await reflector.reflect_and_fix(
            user_query=user_query,
            original_content=original_content,
            review_result=review_result,
            context={
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
                "messages": messages,
            }
        )

        logger.info(
            f"[ReviewNode] Reflection complete: "
            f"outcome={reflection_result.final_outcome.value}, "
            f"score_delta={reflection_result.score_delta:+.2f}, "
            f"rounds={reflection_result.total_rounds}"
        )

        # 构建更新后的审查上下文
        updated_review_context: ReviewContext = {
            **review_context,
            "reflection_round": reflection_round + reflection_result.total_rounds,
            "result": {
                **review_result_dict,
                "overall_score": reflection_result.final_score,
                "decision": "passed" if reflection_result.success else "needs_refinement",
            },
            "reviewed_content": reflection_result.final_content,
        }

        # 决定下一步
        context_data = state.get("context_data", {})
        stream_callback = context_data.get("stream_callback")

        if reflection_result.success:
            # 反思成功
            updated_review_context["status"] = ReviewStatus.PASSED

            # 通知用户
            if stream_callback:
                from app.gen.agent.v1 import agent_service_pb2
                try:
                    rounds_info = f" ({reflection_result.total_rounds}轮)" if reflection_result.total_rounds > 1 else ""
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=f"\n\n[系统已基于审查意见优化回答{rounds_info}]"
                    ))
                except Exception as e:
                    logger.warning(f"[ReviewNode] Failed to send stream notification: {e}")

            # 决定下一步
            if context_data.get("tool_calls"):
                next_step = "tool_execution"
            else:
                next_step = "__end__"

        else:
            # 反思未成功
            updated_review_context["status"] = ReviewStatus.FAILED

            if reflection_result.final_outcome.value == "improved":
                # 有改善，可以继续下一轮
                if reflection_round + reflection_result.total_rounds < MAX_REFLECTION_ROUNDS:
                    next_step = "reflection"
                    updated_review_context["status"] = ReviewStatus.REFLECTING
                else:
                    next_step = "__end__"
            else:
                # 无改善或变差，停止
                next_step = "__end__"

        # 传递修正后的内容
        return {
            "next_step": next_step,
            "review_context": updated_review_context,
            "context_data": {
                **context_data,
                "fixed_response": reflection_result.final_content,
                "reflection_result": reflection_result.final_outcome.value,
                "reflection_completed": reflection_result.success,
                "reflection_score_delta": reflection_result.score_delta,
            }
        }

    except Exception as e:
        logger.error(f"[ReviewNode] Reflection failed: {e}", exc_info=True)
        return {
            "next_step": "__end__",
            "review_context": {
                **review_context,
                "status": ReviewStatus.FAILED
            }
        }


# ============================================
# 条件路由函数
# ============================================

def route_after_generation_review(state: SparkleState) -> str:
    """
    生成后审查的条件路由

    Args:
        state: 当前状态

    Returns:
        下一步节点名称
    """
    next_step = state.get("next_step", "__end__")

    # 如果有工具调用需要执行
    context_data = state.get("context_data", {})
    if context_data.get("tool_calls") and next_step != "reflection":
        return "tool_execution"

    if next_step == "reflection":
        return "reflection"

    if next_step == "user_approval":
        return "user_approval"

    return "__end__"


def route_after_reflection(state: SparkleState) -> str:
    """
    反思后的条件路由

    Args:
        state: 当前状态

    Returns:
        下一步节点名称
    """
    next_step = state.get("next_step", "__end__")

    # 如果反思成功且有工具调用
    context_data = state.get("context_data", {})
    if context_data.get("tool_calls") and context_data.get("reflection_completed"):
        return "tool_execution"

    return "__end__"


def route_after_execution_review(state: SparkleState) -> str:
    """
    执行后审查的条件路由

    Args:
        state: 当前状态

    Returns:
        下一步节点名称
    """
    next_step = state.get("next_step", "__end__")

    if next_step == "generation":
        return "generation"

    return "__end__"


# ============================================
# 导出的节点映射
# ============================================

REVIEW_NODES = {
    "generation_review": generation_review_node,
    "execution_review": execution_review_node,
    "reflection": reflection_node,
}

REVIEW_CONDITIONS = {
    "route_after_generation_review": route_after_generation_review,
    "route_after_reflection": route_after_reflection,
    "route_after_execution_review": route_after_execution_review,
}
