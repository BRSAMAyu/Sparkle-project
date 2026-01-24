"""
Prompt 管理系统 - 统一的Agent Prompt管理

重构说明：
- 整合 AgentProfile 的系统 prompt
- 支持按角色获取专用 prompt
- 与 core/agent_profiles.py 配合使用

使用方式：
    from app.orchestration.prompts import get_system_prompt

    # 获取通用 prompt（原有逻辑）
    prompt = get_system_prompt(user_context, conversation_history)

    # 获取角色专用 prompt（新增）
    from app.core.agent_profiles import AgentRole
    prompt = get_system_prompt_for_role(AgentRole.GALAXY_GUIDE, user_context, query)
"""

from typing import Dict, Optional, Any
from app.core.agent_profiles import AgentRole, agent_profile_registry


# ============================================
# 通用 Agent Prompt 模板
# ============================================

AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。

## 当前用户上下文
{user_context}

{preference_instructions}

{plan_context_section}

## 对话历史
{conversation_history_section}

## 核心原则
1. 始终遵循用户的偏好设置，这是最重要的
2. 根据 verbosity 目标调整回答长度
3. 根据 exploration_level 决定是否扩展话题
4. 保持角色一致性
5. 提供准确、有帮助的回答
6. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
"""


# ============================================
# 主入口函数
# ============================================

def build_system_prompt(
    user_context: dict,
    conversation_history: dict = None,
    prompt_version: str = "v1",
    agent_role: AgentRole = AgentRole.GENERATION,
    plan_context: dict = None,
) -> str:
    """
    构建完整的 System Prompt，深度集成用户偏好

    Args:
        user_context: 用户上下文（从UserService等获取）
        conversation_history: 对话历史（从ContextPruner获取）
        prompt_version: prompt版本（v1/v2）
        agent_role: Agent角色（用于获取角色专用prompt）
        plan_context: 计划上下文（从PlanContextBuilder获取）

    Returns:
        完整的系统prompt字符串
    """
    # Ensure user_context is never None
    if user_context is None:
        user_context = {}
    if conversation_history is None:
        conversation_history = {}

    # 1. 首先检查 AgentProfile 是否有专用 prompt
    profile = agent_profile_registry.get_profile(agent_role)
    base_prompt = profile.system_prompt_template or AGENT_SYSTEM_PROMPT

    # 2. 格式化上下文
    formatted_user_context = format_user_context(user_context)

    llm_profile = user_context.get("llm_profile")
    if llm_profile is None:
        llm_profile = {}
    preference_instructions = llm_profile.get(
        "system_prompt_additions",
        _get_default_preference_instructions(user_context)
    )

    conversation_history_section = _format_conversation_history(conversation_history)

    # 2.5 格式化计划上下文
    plan_context_section = _format_plan_context(plan_context)

    # 3. 如果是通用模板，进行完整渲染
    if base_prompt == AGENT_SYSTEM_PROMPT or "{user_context}" in base_prompt:
        prompt = base_prompt.format(
            user_context=formatted_user_context,
            conversation_history_section=conversation_history_section,
            preference_instructions=preference_instructions,
            plan_context_section=plan_context_section,
        )
    else:
        # 角色专用模板，简单替换
        prompt = base_prompt.format(
            user_context=formatted_user_context,
            query=user_context.get("current_query", ""),
        )

    # 4. 版本特定修饰
    if prompt_version == "v2":
        prompt += "\n\n## 输出风格\n- 更简洁\n- 先给结论，再给要点\n- 列表优先"

    return prompt


def get_system_prompt_for_role(
    agent_role: AgentRole,
    user_context: dict,
    query: str = "",
    conversation_history: dict = None,
) -> str:
    """
    获取指定角色的系统 Prompt

    Args:
        agent_role: Agent 角色（如 AgentRole.GALAXY_GUIDE）
        user_context: 用户上下文
        query: 当前用户查询（用于渲染模板）
        conversation_history: 对话历史（可选）

    Returns:
        角色专用的系统 prompt

    Example:
        from app.core.agent_profiles import AgentRole
        prompt = get_system_prompt_for_role(
            AgentRole.GALAXY_GUIDE,
            user_context,
            query="什么是神经网络？"
        )
    """
    profile = agent_profile_registry.get_profile(agent_role)
    base_template = profile.system_prompt_template

    if not base_template:
        # 回退到通用prompt
        return build_system_prompt(
            user_context=user_context,
            conversation_history=conversation_history,
            agent_role=agent_role,
        )

    # 格式化上下文
    formatted_user_context = format_user_context(user_context)

    # 渲染角色专用模板
    try:
        prompt = base_template.format(
            user_context=formatted_user_context,
            query=query,
        )
    except KeyError as e:
        # 模板变量不匹配，回退
        from loguru import logger
        logger.warning(f"Prompt template missing key {e} for {agent_role}, using fallback")
        prompt = base_template

    return prompt


def get_system_prompt(
    user_context: dict,
    conversation_history: dict = None,
    prompt_version: str = "v1",
) -> str:
    """
    向后兼容的函数名

    等同于 build_system_prompt，但使用默认的 GENERATION 角色
    """
    return build_system_prompt(
        user_context=user_context,
        conversation_history=conversation_history,
        prompt_version=prompt_version,
        agent_role=AgentRole.GENERATION,
    )


def _format_conversation_history(conversation_history: dict = None) -> str:
    """
    格式化对话历史

    策略:
    - 有总结：显示总结 + 最近几条消息
    - 无总结但有历史：显示最近消息
    - 无历史：不显示此部分
    """
    if not conversation_history or not isinstance(conversation_history, dict):
        return ""

    messages = conversation_history.get("messages", [])
    summary = conversation_history.get("summary")
    original_count = conversation_history.get("original_count", 0)
    pruned_count = conversation_history.get("pruned_count", 0)
    summary_used = conversation_history.get("summary_used", False)

    if not messages and not summary:
        return ""

    parts = ["\n\n## 对话历史"]

    # 如果使用了总结，先显示总结
    if summary_used and summary:
        parts.append("\n### 前情提要")
        parts.append(f"{summary}")
        parts.append("\n### 最近对话")
    elif summary and not summary_used:
        # 有总结但未使用（可能只是缓存），可以选择显示或不显示
        parts.append("\n### 历史摘要")
        parts.append(f"{summary}")

    # 显示最近的消息
    if messages:
        if summary_used:
            # 已显示总结，只显示最近几条作为补充
            parts.append("（以下是最近的对话片段）")
        else:
            parts.append("\n### 最近对话")

        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg.get("content", "")
            # 限制每条消息长度，避免过长
            if len(content) > 200:
                content = content[:200] + "..."
            parts.append(f"{role}: {content}")

    # 添加统计信息（用于调试）
    if original_count > pruned_count:
        parts.append(f"\n\n（历史记录: {original_count} 条 → 优化为 {pruned_count} 条）")

    return "\n".join(parts)


def _get_default_preference_instructions(user_context: dict) -> str:
    """默认的偏好指令（兜底）"""
    prefs = user_context.get("preferences", {})
    depth = prefs.get("depth_preference", 0.5)
    curiosity = prefs.get("curiosity_preference", 0.5)

    depth_text = "深入详尽" if depth >= 0.7 else ("简洁概览" if depth < 0.3 else "适中")
    curiosity_text = "探索扩展" if curiosity >= 0.7 else ("专注聚焦" if curiosity < 0.3 else "适中")

    return f"""
## 用户偏好适配
- 回答深度：{depth_text}
- 探索倾向：{curiosity_text}
"""


def _format_plan_context(plan_context: dict = None) -> str:
    """
    格式化计划上下文

    Args:
        plan_context: 计划上下文字典（从PlanContextBuilder获取）

    Returns:
        格式化后的计划上下文字符串，为空时返回空字符串
    """
    if not plan_context or not isinstance(plan_context, dict):
        return ""

    lines = ["## 当前计划上下文"]

    # Plan ID and status
    plan_id = plan_context.get("plan_id")
    status = plan_context.get("status")
    if plan_id:
        lines.append(f"计划ID: {plan_id}")
    if status:
        lines.append(f"状态: {status}")

    # Facts (core plan-level knowledge)
    facts = plan_context.get("facts", {})
    if facts:
        lines.append("\n### 计划事实")
        for key, value in facts.items():
            lines.append(f"- {key}: {value}")

    # Task summary
    task_summary = plan_context.get("task_summary")
    if task_summary:
        total = task_summary.get("total", 0)
        completed = task_summary.get("completed", 0)
        rate = task_summary.get("avg_completion_rate")
        rate_str = f" ({rate:.0%})" if rate is not None else ""
        lines.append(f"\n### 任务进度: {completed}/{total}{rate_str}")

        # By type breakdown
        by_type = task_summary.get("by_type", {})
        if by_type:
            for task_type, stats in by_type.items():
                t_total = stats.get("total", 0)
                t_completed = stats.get("completed", 0)
                lines.append(f"  - {task_type}: {t_completed}/{t_total}")

    # Milestones
    milestones = plan_context.get("milestones", [])
    if milestones:
        lines.append("\n### 已达成里程碑")
        for m in milestones:
            title = m.get("title", "未知")
            lines.append(f"- {title}")

    # Constraints
    constraints = plan_context.get("constraints", {})
    if constraints:
        lines.append("\n### 运行时约束")
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def format_user_context(context: dict) -> str:
    """格式化用户上下文"""
    lines = []

    # 用户基本信息
    if context.get("user_context"):
        user_ctx = context["user_context"]
        if hasattr(user_ctx, "model_dump"):
            user_ctx = user_ctx.model_dump()
        lines.append(f"用户昵称: {user_ctx.get('nickname', '未知')}")
        lines.append(f"时区: {user_ctx.get('timezone', 'Asia/Shanghai')}")
        lines.append(f"Pro状态: {'是' if user_ctx.get('is_pro') else '否'}")

    # 分析摘要
    if context.get("analytics_summary"):
        analytics = context["analytics_summary"]
        # Handle both dict and string formats for analytics_summary
        if isinstance(analytics, dict):
            lines.append("-" * 20)
            if analytics.get("is_active"):
                lines.append(f"活跃度: {analytics.get('active_level', 'unknown')}")
                lines.append(f"参与度: {analytics.get('engagement_level', 'unknown')}")
            else:
                lines.append("状态: 不活跃")
        elif isinstance(analytics, str) and analytics:
            # If it's a string summary, just append it
            lines.append("-" * 20)
            lines.append(f"分析摘要: {analytics}")

    # 火花等级
    if context.get("user_context") and context["user_context"].get("preferences"):
        prefs = context["user_context"]["preferences"]
        if "flame_level" in prefs:
            lines.append(f"火花等级: {prefs['flame_level']}")

    # 学习偏好
    if context.get("preferences"):
        prefs = context["preferences"]
        lines.append("-" * 20)
        lines.append(f"学习偏好 - 深度: {prefs.get('depth_preference', 0.5):.1f}, 好奇心: {prefs.get('curiosity_preference', 0.5):.1f}")

    # 碎片时间推荐线索：待办任务
    if context.get("next_actions"):
        lines.append("-" * 20)
        lines.append("待办任务(Top 3):")
        for task in context["next_actions"][:3]:
            lines.append(f"- {task.get('title')} ({task.get('estimated_minutes')}m, {task.get('type')})")

    # 专注统计
    if context.get("focus_stats"):
        stats = context["focus_stats"]
        lines.append("-" * 20)
        lines.append(f"今日专注: {stats.get('total_minutes', 0)} 分钟, 番茄钟次数: {stats.get('pomodoro_count', 0)}")

    # 活跃计划
    if context.get("active_plans"):
        lines.append("-" * 20)
        lines.append("活跃计划:")
        for plan in context["active_plans"][:3]:
            lines.append(f"- {plan.get('title')} ({plan.get('type')}, 进度 {plan.get('progress', 0):.0%})")

    # 工具偏好 (P4)
    if context.get("preferred_tools"):
        lines.append("-" * 20)
        lines.append(f"工具偏好 (用户历史常用): {', '.join(context['preferred_tools'])}")

    # 考试紧迫度
    if isinstance(context.get("exam_urgency"), dict):
        urgency = context["exam_urgency"]
        days_left = urgency.get("days_left")
        if days_left is not None:
            lines.append("-" * 20)
            urgency_label = "紧急" if urgency.get("urgent") else "一般"
            lines.append(f"考试倒计时: {days_left} 天 ({urgency_label})")

    return "\n".join(lines) if lines else "暂无上下文信息"
