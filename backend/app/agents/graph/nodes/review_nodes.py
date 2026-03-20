from __future__ import annotations
"""
Review Nodes - LangGraph审查节点

Phase 1: 全流程审查系统
- generation_review_node: 审查LLM生成后的响应
- execution_review_node: 审查工具执行结果
- reflection_node: 基于审查结果进行自我反思修正

Phase 2a: 使用ReflectionAgent进行完整的多轮反思修正

Phase 2c: 集成审查历史和反馈学习

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import time
import json
from datetime import timezone, datetime
from typing import Any

from loguru import logger

from app.agents.graph.state import (
    ReviewContext,
    ReviewHistoryEntry,
    ReviewStatus,
    ReviewTargetType,
    SparkleState,
)
from app.agents.reflection_agent import get_reflection_agent
from app.agents.reviewer_agent import ReviewerAgent, ReviewResult, get_reviewer_agent
from app.agents.workflow_experience import build_workflow_context, resolve_review_profile_id
from app.core.agent_profiles import TaskType
from app.core.llm_router import ModelProvider, llm_router

# Phase 2c: 导入审查历史服务
try:
    from app.services.review_history_service import get_review_history_service
    REVIEW_HISTORY_AVAILABLE = True
except ImportError:
    REVIEW_HISTORY_AVAILABLE = False
    logger.warning("[ReviewNode] Review history service not available")

# Phase 2d: 导入模型降级服务
try:
    from app.services.model_fallback_service import get_model_fallback_service
    FALLBACK_SERVICE_AVAILABLE = True
except ImportError:
    FALLBACK_SERVICE_AVAILABLE = False
    logger.warning("[ReviewNode] Model fallback service not available")


# ============================================
# 全局ReviewerAgent实例
# ============================================

_reviewer_agent: ReviewerAgent | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_reviewer(
    avoid_providers: list[ModelProvider] | None = None,
    task_type_override: TaskType | None = None,
) -> ReviewerAgent:
    """获取ReviewerAgent单例"""
    if avoid_providers or task_type_override is not None:
        return get_reviewer_agent(
            avoid_providers=avoid_providers,
            task_type_override=task_type_override,
        )

    global _reviewer_agent
    if _reviewer_agent is None:
        _reviewer_agent = get_reviewer_agent()
    return _reviewer_agent


def _get_review_label(review_result: ReviewResult) -> str:
    """获取审查结果的用户友好标签"""
    if review_result.passed:
        return "已通过"
    if review_result.critical_issues:
        return "未通过"
    if review_result.requires_reflection:
        return "需要优化"
    return "需要审查"


# ============================================
# Phase 2c: Review History Integration
# ============================================

def _get_review_history_service(state: SparkleState):
    """获取审查历史服务（如果可用）"""
    if not REVIEW_HISTORY_AVAILABLE:
        return None

    try:
        db_session = _state_get(state, "db_session")
        if db_session:
            return get_review_history_service(db_session)
    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to get review history service: {e}")
    return None


async def _record_review_to_history(
    state: SparkleState,
    review_result: ReviewResult,
    target_id: str,
    target_type: str,
    review_duration_ms: int = 0,
    content_snapshot: str | None = None,
    user_query: str | None = None,
) -> None:
    """记录审查到历史"""
    history_service = _get_review_history_service(state)
    if not history_service:
        return

    try:
        await history_service.record_review(
            review_id=review_result.review_id,
            target_id=target_id,
            target_type=target_type,
            user_id=_state_get(state, "user_id", ""),
            session_id=_state_get(state, "session_id", ""),
            decision=review_result.decision,
            overall_score=review_result.overall_score,
            metrics=[m.to_dict() for m in review_result.metrics],
            issues_count=len(review_result.issues),
            critical_count=len(review_result.critical_issues),
            warning_count=len(review_result.warning_issues),
            reviewer_model=review_result.reviewer_model,
            review_duration_ms=review_duration_ms,
            requires_reflection=review_result.requires_reflection,
            content_snapshot=content_snapshot,
            user_query=user_query,
            review_profile_id=review_result.review_profile_id,
            workflow_context=review_result.workflow_context or {},
        )
    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to record review history: {e}")


# ============================================
# Phase 2d: Model Fallback Integration
# ============================================

def _get_fallback_service(state: SparkleState):
    """获取模型降级服务（如果可用）"""
    if not FALLBACK_SERVICE_AVAILABLE:
        return None

    try:
        db_session = _state_get(state, "db_session")
        if db_session:
            return get_model_fallback_service()
    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to get fallback service: {e}")
    return None


async def _record_model_performance(
    state: SparkleState,
    model_name: str,
    review_passed: bool,
    review_score: float,
    issues_count: int,
    response_time_ms: int = 0,
) -> None:
    """记录模型性能到降级服务"""
    fallback_service = _get_fallback_service(state)
    if not fallback_service:
        return

    try:
        fallback_service.record_performance(
            model_name=model_name,
            task_type="generation",
            review_passed=review_passed,
            review_score=review_score,
            issues_count=issues_count,
            response_time_ms=response_time_ms,
        )
    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to record model performance: {e}")


async def _check_and_execute_fallback(
    state: SparkleState,
    current_model: str,
    review_score: float,
    review_passed: bool,
) -> str | None:
    """
    检查并执行模型降级

    Returns:
        如果发生降级，返回新的模型名称；否则返回None
    """
    fallback_service = _get_fallback_service(state)
    if not fallback_service:
        return None

    try:
        decision = fallback_service.should_fallback(
            model_name=current_model,
            task_type="generation",
        )

        if decision.should_fallback:
            logger.warning(
                f"[ReviewNode] Model fallback triggered: {current_model} -> {decision.suggested_model} "
                f"(reason: {decision.reason.value}, {decision.description})"
            )

            # 检查是否已经在生成过程中
            context_data = _state_get(state, "context_data", {})
            if context_data.get("stream_callback"):
                from app.gen.agent.v1 import agent_service_pb2
                try:
                    await context_data["stream_callback"](agent_service_pb2.ChatResponse(
                        delta="\n\n[系统] 检测到质量问题，切换到更强大的模型重新生成..."
                    ))
                except Exception as e:
                    logger.warning(f"[ReviewNode] Failed to send fallback notification: {e}")

            return decision.suggested_model

    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to check fallback: {e}")

    return None


def _get_fallback_model(state: SparkleState, current_model: str, retry_count: int) -> str:
    """
    获取降级后的模型

    Args:
        state: 当前状态
        current_model: 当前模型
        retry_count: 重试次数

    Returns:
        模型名称
    """
    fallback_service = _get_fallback_service(state)
    if not fallback_service:
        return current_model

    try:
        from app.core.agent_profiles import TaskType
        return fallback_service.get_model_for_task(
            task_type=TaskType.STANDARD_RESPONSE,
            current_model=current_model,
            retry_count=retry_count,
        )
    except Exception as e:
        logger.warning(f"[ReviewNode] Failed to get fallback model: {e}")
        return current_model


# ============================================
# 审查配置
# ============================================

REVIEW_CONFIG_DEFAULTS = {
    "enable_review": True,           # 是否启用审查
    "overall_threshold": 0.7,        # 总体通过阈值
    "critical_threshold": 0.9,       # 关键指标阈值
    "max_reflection_rounds": 3,      # 最大反思轮次
    "skip_simple_responses": True,   # 跳过简单响应的审查
    "simple_response_length": 400,   # 简单响应长度阈值
    "skip_patterns": ["你好", "hi", "hello"],  # 跳过审查的模式
}


def _state_get(state: SparkleState, key: str, default=None):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _message_attr(message: Any, key: str, default=None):
    """Read a message field from either dict-based or object-based state."""
    if isinstance(message, dict):
        return message.get(key, default)
    return getattr(message, key, default)


def _resolve_workflow_context(state: SparkleState, *, target_type: str = "response") -> dict[str, str]:
    context_data = _state_get(state, "context_data", {}) or {}
    workflow_type = str(context_data.get("workflow_type") or "").strip().lower()
    chat_mode = str(context_data.get("chat_mode") or "standard").strip().lower()
    collaboration_mode = str(_state_get(state, "collaboration_mode") or context_data.get("collaboration_mode") or "").strip().lower()

    if not workflow_type:
        if context_data.get("selected_experts"):
            workflow_type = "explicit_expert_collaboration"
        elif chat_mode == "study_plan":
            workflow_type = "task_decomposition"
        elif chat_mode == "deep_analysis":
            workflow_type = "progressive_exploration"
        elif chat_mode == "error_diagnosis":
            workflow_type = "error_diagnosis"

    return build_workflow_context(
        workflow_type=workflow_type,
        chat_mode=chat_mode,
        collaboration_mode=collaboration_mode,
        target_type=target_type,
    )


def _should_skip_review(state: SparkleState) -> bool:
    """
    判断是否应该跳过审查

    Args:
        state: 当前状态

    Returns:
        bool: True表示跳过审查
    """
    # 检查用户配置
    enable_deep_review = _state_get(state, "enable_deep_review", True)
    if not enable_deep_review:
        return True

    # 获取审查配置
    review_config = _state_get(state, "review_config", {})
    config = {**REVIEW_CONFIG_DEFAULTS, **review_config}

    if not config.get("enable_review", True):
        return True

    context_data = _state_get(state, "context_data", {}) or {}
    messages = _state_get(state, "messages", [])
    if not messages:
        return False

    last_message = messages[-1]
    content = _message_attr(last_message, "content", "") or str(last_message)
    content_lower = content.lower()
    last_user_message = next(
        (_message_attr(msg, "content", "") for msg in reversed(messages[:-1]) if _message_attr(msg, "role") == "user"),
        "",
    )
    chat_mode = str(context_data.get("chat_mode") or "standard").strip().lower()
    has_tool_calls = bool(context_data.get("tool_calls"))
    has_selected_experts = bool(context_data.get("selected_experts") or context_data.get("answer_experts"))
    workflow_type = str(context_data.get("workflow_type") or "").strip().lower()

    if has_tool_calls and len(content) <= 120:
        tool_progress_cues = ("我先", "先帮", "正在", "我来", "让我", "先查询", "先查看", "先检查")
        if any(cue in content for cue in tool_progress_cues):
            return True

    if (
        has_tool_calls
        and chat_mode in {"standard", "chat"}
        and len(content) <= 120
        and "\n" not in content
        and "：" not in content
    ):
        return True

    if (
        chat_mode == "deep_analysis"
        and not has_tool_calls
        and not has_selected_experts
    ):
        return True

    if (
        chat_mode in {"study_plan", "error_diagnosis"}
        and not has_tool_calls
        and not has_selected_experts
        and workflow_type in {"", "task_decomposition", "error_diagnosis"}
    ):
        return True

    # 标准轻对话优先保证首轮响应速度：无工具、无显式专家、无复杂工作流时跳过重审查。
    if (
        chat_mode in {"standard", "chat"}
        and not has_tool_calls
        and not has_selected_experts
        and workflow_type in {"", "standard_chat", "conversation", "qa"}
        and len(content) <= 1200
        and len(last_user_message) <= 240
    ):
        return True

    is_standard_like_chat = (
        chat_mode in {"standard", "chat"}
        and not has_tool_calls
        and not has_selected_experts
        and workflow_type in {"", "standard_chat", "conversation", "qa"}
    )

    # 检查是否是简单响应
    if config.get("skip_simple_responses") and is_standard_like_chat:
        # 检查长度
        if len(content) < config.get("simple_response_length", 400):
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

async def generation_review_node(state: SparkleState) -> dict[str, Any]:
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
            "next_step": _state_get(state, "next_step", "__end__"),
            "review_context": {
                "status": ReviewStatus.SKIPPED,
                "review_id": f"skipped_{int(time.time())}",
            }
        }

    # 2. 获取最后生成的响应
    messages = _state_get(state, "messages", [])
    if not messages:
        logger.warning("[ReviewNode] No messages to review")
        return {"next_step": "__end__"}

    # 找到最后一条assistant消息
    last_assistant_msg = None
    last_assistant_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = _message_attr(msg, "role")
        if role == "assistant":
            last_assistant_msg = msg
            last_assistant_idx = i
            break

    if not last_assistant_msg:
        logger.warning("[ReviewNode] No assistant message to review")
        return {"next_step": "__end__"}

    llm_response = _message_attr(last_assistant_msg, "content", "")
    if not llm_response:
        logger.warning("[ReviewNode] Empty response, skipping review")
        return {"next_step": "__end__"}

    # 3. 获取用户查询
    user_query = ""
    if last_assistant_idx > 0:
        user_msg = messages[last_assistant_idx - 1]
        user_query = _message_attr(user_msg, "content", "")

    logger.info(f"[ReviewNode] Reviewing response: {len(llm_response)} chars")

    # 记录审查开始时间
    review_start_time = time.time() * 1000

    # 4. 执行审查
    context_data = _state_get(state, "context_data", {})
    generation_model_key = str(context_data.get("generation_model_key") or "")
    generation_provider = llm_router.get_model_provider(generation_model_key) if generation_model_key else None
    run_ledger = context_data.get("run_ledger")
    workflow_context = _resolve_workflow_context(state, target_type="response")
    review_profile_id = resolve_review_profile_id(workflow_context=workflow_context, target_type="response")
    reviewer = _get_reviewer(
        avoid_providers=[generation_provider] if generation_provider is not None else None,
    )
    review_result: ReviewResult = await reviewer.review_llm_response(
        user_query=user_query,
        llm_response=llm_response,
        context={
            "user_id": _state_get(state, "user_id"),
            "session_id": _state_get(state, "session_id"),
            "conversation_history": messages[:last_assistant_idx],
            "timestamp": _utcnow().isoformat()
        },
        review_profile_id=review_profile_id,
        workflow_context=workflow_context,
    )

    logger.info(
        f"[ReviewNode] Review complete: "
        f"decision={review_result.decision}, score={review_result.overall_score:.2f}, "
        f"issues={len(review_result.issues)}"
    )
    if run_ledger is not None:
        await run_ledger.record_event(
            event_type="review_completed",
            label="内容审查完成",
            workflow_stage="review",
            metadata={
                "role": "review",
                "target_type": "llm_response",
                "decision": review_result.decision,
                "overall_score": review_result.overall_score,
                "critical_count": len(review_result.critical_issues),
                "warning_count": len(review_result.warning_issues),
                "requires_reflection": review_result.requires_reflection,
                "review_profile_id": review_result.review_profile_id,
                "workflow_type": workflow_context.get("workflow_type", ""),
                "chat_mode": workflow_context.get("chat_mode", ""),
                "model_key": getattr(reviewer, "model_key", ""),
                "provider": getattr(reviewer, "provider_name", ""),
                "tier": getattr(getattr(reviewer, "get_current_selection", lambda: None)(), "tier_used", ""),
                "estimated_cost_per_1k": getattr(
                    getattr(reviewer, "get_current_selection", lambda: None)(),
                    "estimated_cost_per_1k",
                    0.0,
                ),
            },
            emit_snapshot=False,
        )

    # Phase 2c: Record review to history
    target_id = context_data.get("response_id") or _message_attr(last_assistant_msg, "id", "")
    review_duration = int(time.time() * 1000 - review_start_time) if 'review_start_time' in locals() else 0
    await _record_review_to_history(
        state=state,
        review_result=review_result,
        target_id=target_id,
        target_type="llm_response",
        review_duration_ms=review_duration,
        content_snapshot=llm_response,
        user_query=user_query,
    )

    # Phase 2d: Record model performance and check for fallback
    # 获取生成模型（从context_data或使用默认值）
    generation_model = (
        context_data.get("generation_model_key")
        or context_data.get("model_used")
        or "unknown"
    )
    if generation_model == "unknown":
        # 尝试从其他来源获取模型名称
        generation_model = getattr(review_result, 'reviewer_model', 'unknown')

    await _record_model_performance(
        state=state,
        model_name=generation_model,
        review_passed=review_result.passed,
        review_score=review_result.overall_score,
        issues_count=len(review_result.issues),
        response_time_ms=review_duration,
    )

    # 4.5. Phase 2b: Send review result to frontend via stream_callback
    context_data = _state_get(state, "context_data", {})
    stream_callback = context_data.get("stream_callback")
    if stream_callback and not review_result.passed:
        # Send review widget event to frontend
        try:
            from app.gen.agent.v1 import agent_service_pb2
            review_metadata = {
                "has_review_result": "true",
                "review_id": review_result.review_id,
                "decision": review_result.decision,
                "overall_score": str(review_result.overall_score),
                "critical_count": str(len(review_result.critical_issues)),
                "warning_count": str(len(review_result.warning_issues)),
                "requires_reflection": "true" if review_result.requires_reflection else "false",
                "review_profile_id": review_result.review_profile_id,
            }

            # Format review message for display
            review_delta = f"\n\n[内容审查: {_get_review_label(review_result)}]"
            if review_result.critical_issues:
                review_delta += f"\n发现 {len(review_result.critical_issues)} 个严重问题需要处理"

            await stream_callback(agent_service_pb2.ChatResponse(
                delta=review_delta,
                metadata={
                    **review_metadata,
                    "review_data": json.dumps(review_result.to_dict(), ensure_ascii=False),
                }
            ))

            logger.info("[ReviewNode] Review result sent to frontend")
        except Exception as e:
            logger.warning(f"[ReviewNode] Failed to send review to frontend: {e}")

    # 5. 构建审查上下文
    review_context: ReviewContext = {
        "review_id": review_result.review_id,
        "status": ReviewStatus.PASSED if review_result.passed else ReviewStatus.FAILED,
        "target_type": ReviewTargetType.LLM_RESPONSE,
        "result": review_result.to_dict(),
        "reflection_round": 0,
        "reviewer_model": review_result.reviewer_model,
        "reviewer_model_key": getattr(reviewer, "model_key", ""),
        "reviewer_provider": getattr(reviewer, "provider_name", ""),
        "original_content": llm_response,
        "reviewed_content": None,
        "review_profile_id": review_result.review_profile_id,
        "workflow_context": workflow_context,
    }

    # 6. 记录审查历史
    history_entry: ReviewHistoryEntry = {
        "review_id": review_result.review_id,
        "timestamp": _utcnow().isoformat(),
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
        next_step = "tool_execution" if _state_get(state, "context_data", {}).get("tool_calls") else "__end__"
    else:
        # 审查未通过
        if review_result.requires_reflection:
            # 需要自我反思修正
            logger.info("[ReviewNode] Review FAILED, entering reflection")
            review_context["status"] = ReviewStatus.REFLECTING

            # Phase 2d: 检查是否需要切换模型（连续反思失败）
            fallback_model = await _check_and_execute_fallback(
                state=state,
                current_model=generation_model,
                review_score=review_result.overall_score,
                review_passed=False,
            )
            if fallback_model:
                # 记录建议的模型切换
                review_context["fallback_model"] = fallback_model

            next_step = "reflection"
        else:
            # 不需要反思，直接结束或需要用户批准
            if review_result.critical_issues:
                logger.warning("[ReviewNode] Review FAILED with critical issues")

                # Phase 2d: 严重问题，检查是否需要模型切换
                fallback_model = await _check_and_execute_fallback(
                    state=state,
                    current_model=generation_model,
                    review_score=review_result.overall_score,
                    review_passed=False,
                )
                if fallback_model:
                    # 将建议的模型存储在context中，供下次生成使用
                    context_data = _state_get(state, "context_data", {})
                    context_data["suggested_model"] = fallback_model
                    review_context["fallback_model"] = fallback_model

                next_step = "__end__"
            else:
                # 警告级别问题，可以继续
                logger.info("[ReviewNode] Review passed with warnings")
                next_step = "tool_execution" if _state_get(state, "context_data", {}).get("tool_calls") else "__end__"

    return {
        "next_step": next_step,
        "review_context": review_context,
        "review_history": [history_entry],  # Annotated list with operator.add
    }


async def execution_review_node(state: SparkleState) -> dict[str, Any]:
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
    context_data = _state_get(state, "context_data", {})
    tool_results = context_data.get("tool_results", [])

    if not tool_results:
        logger.info("[ReviewNode] No tool results to review")
        # 如果没有工具结果，回到generation继续对话
        return {"next_step": "generation"}

    reviewer = _get_reviewer(task_type_override=TaskType.STANDARD_RESPONSE)
    issues_summary = []

    for tool_result in tool_results:
        tool_name = tool_result.get("name", "unknown")
        result_data = tool_result.get("result", {})

        review_result = await reviewer.review_tool_result(
            tool_name=tool_name,
            tool_result=result_data,
            context={
                "user_id": _state_get(state, "user_id"),
                "session_id": _state_get(state, "session_id"),
                "timestamp": _utcnow().isoformat()
            }
        )

        if not review_result.passed:
            for issue in review_result.issues:
                issues_summary.append(f"[{tool_name}] {issue.description}")

    if issues_summary:
        logger.warning(f"[ReviewNode] Tool execution issues: {issues_summary}")
        # 存储问题但不中断流程
        context_data["tool_review_issues"] = issues_summary
    run_ledger = context_data.get("run_ledger")
    if run_ledger is not None:
        await run_ledger.record_event(
            event_type="tool_reviewed",
            label="工具执行审查完成",
            workflow_stage="review",
            metadata={
                "issue_count": len(issues_summary),
                "issue_preview": issues_summary[:3],
            },
            emit_snapshot=False,
        )

    # 工具执行后，回到generation解释结果
    return {
        "next_step": "generation",
        "context_data": context_data
    }


async def reflection_node(state: SparkleState) -> dict[str, Any]:
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
    review_context: ReviewContext | None = _state_get(state, "review_context")
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
    messages = _state_get(state, "messages", [])

    # 找到用户查询
    user_query = ""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = _message_attr(msg, "role")
        if role == "user":
            user_query = _message_attr(msg, "content", "")
            break

    if not user_query:
        logger.warning("[ReviewNode] No user query found")
        return {"next_step": "__end__"}

    # 重建ReviewResult对象
    review_result = ReviewResult.from_dict(review_result_dict)
    workflow_context = review_context.get("workflow_context") or _resolve_workflow_context(state, target_type="response")
    review_profile_id = str(review_context.get("review_profile_id") or review_result.review_profile_id or "").strip()
    if not review_profile_id:
        review_profile_id = resolve_review_profile_id(workflow_context=workflow_context, target_type="response")

    # Phase 2d: 获取生成模型名称
    context_data = _state_get(state, "context_data", {})
    generation_model = (
        context_data.get("model_used") or
        review_context.get("reviewer_model") or
        getattr(review_result, 'reviewer_model', 'unknown')
    )

    logger.info(
        f"[ReviewNode] Starting ReflectionAgent: "
        f"initial_score={review_result.overall_score:.2f}, "
        f"issues={len(review_result.issues)}, "
        f"round={reflection_round + 1}/{MAX_REFLECTION_ROUNDS}"
    )

    try:
        reflection_avoid_providers: list[ModelProvider] = []
        generation_provider_name = str(context_data.get("generation_provider") or "").strip()
        reviewer_provider_name = str(review_context.get("reviewer_provider") or "").strip()
        for provider_name in (generation_provider_name, reviewer_provider_name):
            if not provider_name:
                continue
            try:
                provider = ModelProvider(provider_name)
            except ValueError:
                continue
            if provider not in reflection_avoid_providers:
                reflection_avoid_providers.append(provider)

        reviewer_model_key = str(review_context.get("reviewer_model_key") or "").strip()
        reviewer_provider = llm_router.get_model_provider(reviewer_model_key) if reviewer_model_key else None
        reviewer_agent = _get_reviewer(
            avoid_providers=[provider for provider in reflection_avoid_providers if provider != reviewer_provider],
        )

        # 获取ReflectionAgent并执行反思
        reflector = get_reflection_agent(
            avoid_providers=reflection_avoid_providers or None,
            reviewer=reviewer_agent,
        )
        run_ledger = context_data.get("run_ledger")

        # 执行反思修正
        reflection_result = await reflector.reflect_and_fix(
            user_query=user_query,
            original_content=original_content,
            review_result=review_result,
            context={
                "user_id": _state_get(state, "user_id"),
                "session_id": _state_get(state, "session_id"),
                "messages": messages,
            },
            review_profile_id=review_profile_id,
            workflow_context=workflow_context,
        )

        logger.info(
            f"[ReviewNode] Reflection complete: "
            f"outcome={reflection_result.final_outcome.value}, "
            f"score_delta={reflection_result.score_delta:+.2f}, "
            f"rounds={reflection_result.total_rounds}"
        )
        if run_ledger is not None:
            reflection_selection = getattr(reflector.generator, "get_current_selection", lambda: None)()
            await run_ledger.record_event(
                event_type="reflection_completed",
                label="反思修正完成",
                workflow_stage="reflection",
                metadata={
                    "role": "reflection",
                    "success": reflection_result.success,
                    "score_delta": reflection_result.score_delta,
                    "rounds": reflection_result.total_rounds,
                    "initial_score": reflection_result.initial_score,
                    "final_score": reflection_result.final_score,
                    "review_profile_id": reflection_result.review_profile_id,
                    "early_stop_reason": reflection_result.early_stop_reason or "",
                    "best_round_number": reflection_result.best_round_number,
                    "issue_delta": reflection_result.issue_delta,
                    "model_key": getattr(reflector.generator, "model_key", ""),
                    "provider": getattr(reflector.generator, "provider_name", ""),
                    "tier": getattr(reflection_selection, "tier_used", ""),
                    "estimated_cost_per_1k": getattr(reflection_selection, "estimated_cost_per_1k", 0.0),
                },
                emit_snapshot=False,
            )

        # Phase 2c: Record reflection to history
        history_service = _get_review_history_service(state)
        if history_service:
            try:
                await history_service.record_reflection(
                    review_id=review_result.review_id,
                    reflection_round=reflection_result.total_rounds,
                    outcome=reflection_result.final_outcome.value,
                    score_delta=reflection_result.score_delta,
                )
            except Exception as e:
                logger.warning(f"[ReviewNode] Failed to record reflection: {e}")

        # 构建更新后的审查上下文
        updated_review_context: ReviewContext = {
            **review_context,
            "reflection_round": reflection_round + reflection_result.total_rounds,
            "result": {
                **(reflection_result.best_review_result or review_result_dict),
                "overall_score": reflection_result.final_score,
                "decision": "passed" if reflection_result.success else "needs_refinement",
                "review_profile_id": reflection_result.review_profile_id,
                "workflow_context": workflow_context,
            },
            "reviewed_content": reflection_result.final_content,
            "best_review_score": reflection_result.final_score,
            "best_content": reflection_result.final_content,
            "early_stop_reason": reflection_result.early_stop_reason,
            "reflection_profile_id": reflection_result.review_profile_id,
            "workflow_context": workflow_context,
        }

        # 决定下一步
        context_data = _state_get(state, "context_data", {})
        stream_callback = context_data.get("stream_callback")

        if reflection_result.success:
            # 反思成功
            updated_review_context["status"] = ReviewStatus.PASSED

            # 通知用户 - Phase 2b: 发送反思结果事件
            if stream_callback:
                from app.gen.agent.v1 import agent_service_pb2
                try:
                    rounds_info = f" ({reflection_result.total_rounds}轮)" if reflection_result.total_rounds > 1 else ""

                    # 发送反思结果事件
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=f"\n\n[系统已基于审查意见优化回答{rounds_info}]",
                        metadata={
                            "has_reflection_result": "true",
                            "reflection_id": reflection_result.reflection_id,
                            "outcome": reflection_result.final_outcome.value,
                            "score_delta": str(reflection_result.score_delta),
                            "rounds": str(reflection_result.total_rounds),
                            "initial_score": str(reflection_result.initial_score),
                            "final_score": str(reflection_result.final_score),
                            "success": "true" if reflection_result.success else "false",
                            "review_profile_id": reflection_result.review_profile_id,
                            "early_stop_reason": str(reflection_result.early_stop_reason or ""),
                        }
                    ))
                except Exception as e:
                    logger.warning(f"[ReviewNode] Failed to send stream notification: {e}")

            # 决定下一步
            next_step = "tool_execution" if context_data.get("tool_calls") else "__end__"

        else:
            # 反思未成功
            updated_review_context["status"] = ReviewStatus.FAILED

            # Phase 2d: 记录反思失败到降级服务
            fallback_service = _get_fallback_service(state)
            if fallback_service:
                try:
                    fallback_service.record_reflection_failure(
                        model_name=generation_model,
                        original_score=review_result.overall_score,
                        rounds_attempted=reflection_result.total_rounds,
                    )
                except Exception as e:
                    logger.warning(f"[ReviewNode] Failed to record reflection failure: {e}")

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
                "reflection_profile_id": reflection_result.review_profile_id,
                "reflection_early_stop_reason": reflection_result.early_stop_reason,
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
    next_step = _state_get(state, "next_step", "__end__")

    # 如果有工具调用需要执行
    context_data = _state_get(state, "context_data", {})
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
    _state_get(state, "next_step", "__end__")

    # 如果反思成功且有工具调用
    context_data = _state_get(state, "context_data", {})
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
    next_step = _state_get(state, "next_step", "__end__")

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
