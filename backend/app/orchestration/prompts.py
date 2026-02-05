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

from typing import Any

from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.core.plan_context import merge_plan_context

class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""

# ============================================
# 通用 Agent Prompt 模板
# ============================================

TASK_AWARENESS_SECTION = """
## 任务感知指南

当用户提到以下内容时，主动查询任务：
- "我还有什么任务" / "今天学什么" → query_plan_tasks
- "换个计划" / "别的计划" → query_all_tasks
- "太难了" / "太简单" → query_plan_tasks + modify_plan_task
- "完成了" / "做完了" → 检查是否达成里程碑
- "生成任务" / "新任务" / "下一步" → 先调用 get_plan_state 获取最新计划状态

可用任务工具：
1. query_plan_tasks - 查询当前计划的任务
2. query_all_tasks - 查询所有计划的任务（跨计划感知）
3. get_plan_state - 获取计划状态（进度、里程碑、任务统计、自适应调整参数）
4. get_task_summary - 获取任务摘要列表（最近N个任务）
5. get_task_detail - 获取单个任务详情
6. modify_plan_task - 修改任务属性（难度、时间、优先级）
7. create_task - 创建新任务
8. update_task_status - 更新任务状态
9. confirm_milestone_proposal - 确认里程碑提案，创建推荐任务
10. dismiss_milestone_proposal - 忽略里程碑提案

**重要提示**：在生成新任务前，务必先调用 get_plan_state 获取：
- 当前进度和已达成里程碑
- 任务完成统计
- 自适应调整参数（difficulty_shift, time_multiplier）
"""

AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



## 当前用户上下文

{user_context}



{intent_section}



{preference_instructions}



{plan_context_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



{cognitive_prism_section}



## 核心原则

1. 始终遵循用户的偏好设置，这是最重要的
2. 如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认

3. 根据 verbosity 目标调整回答长度

4. 根据 exploration_level 决定是否扩展话题

5. 保持角色一致性

6. 提供准确、有帮助的回答

7. 如果有活跃计划上下文，优先考虑计划相关的任务和目标

"""

MODE_SYSTEM_PROMPTS = {
    "standard": AGENT_SYSTEM_PROMPT,
    "deep_analysis": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



## 当前用户上下文

{user_context}



{intent_section}



{preference_instructions}



{plan_context_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



{cognitive_prism_section}



## 深度解析模式指令

目标：帮助用户获得深层、可验证、可执行的理解与方案。
原则：
1. 先澄清问题边界与假设，必要时列出需补充的信息
2. 结构化拆解问题（因果、约束、权衡、关键变量）
3. 多视角验证（反例、风险、替代路径）
4. 输出可执行建议，并说明验证方式

输出要求（Markdown）：
- 问题复述与边界
- 关键因素/约束
- 分析过程（可用要点或小节）
- 结论与可执行方案
- 风险与验证步骤（含可观测指标/验收标准）



## 核心原则

1. 始终遵循用户的偏好设置，这是最重要的
2. 如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认

3. 根据 verbosity 目标调整回答长度

4. 根据 exploration_level 决定是否扩展话题

5. 保持角色一致性

6. 提供准确、有帮助的回答

7. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
""",
    "study_plan": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



## 当前用户上下文

{user_context}



{intent_section}



{preference_instructions}



{plan_context_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



{cognitive_prism_section}



## 学习计划模式指令

目标：把学习目标转化为可执行、可跟踪、可调整的计划。
原则：
1. 明确学习目标与评估标准（能做什么/达到什么水平）
2. 自顶向下拆解为阶段与任务，并标注先后依赖
3. 给出时间估算与每周节奏（可调整）
4. 加入复盘与纠错机制，避免只学不练

输出要求（Markdown）：
- 目标与评估标准
- 阶段拆解（阶段目标/任务/产出）
- 时间安排（每周节奏与里程碑）
- 学习建议（资源类型、练习方式、复盘机制）
- 风险与应对（可能掉队的点与补救方式）



## 核心原则

1. 始终遵循用户的偏好设置，这是最重要的
2. 如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认

3. 根据 verbosity 目标调整回答长度

4. 根据 exploration_level 决定是否扩展话题

5. 保持角色一致性

6. 提供准确、有帮助的回答

7. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
""",
    "error_diagnosis": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



## 当前用户上下文

{user_context}



{intent_section}



{preference_instructions}



{plan_context_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



{cognitive_prism_section}



## 错题分析模式指令

目标：定位错误根因并形成可执行的改进闭环。
原则：
1. 先复述题意与用户思路，确保对齐
2. 明确错误类型与触发点（概念/计算/方法/审题/步骤遗漏）
3. 给出可操作的修正步骤与通用化方法
4. 提供防错清单与练习策略

输出要求（Markdown）：
- 题意与思路对齐
- 错误类型与触发点
- 根因分析
- 修正步骤（含正确解法/关键步骤）
- 防错清单与训练建议



## 核心原则

1. 始终遵循用户的偏好设置，这是最重要的
2. 如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认

3. 根据 verbosity 目标调整回答长度

4. 根据 exploration_level 决定是否扩展话题

5. 保持角色一致性

6. 提供准确、有帮助的回答

7. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
""",
}





# ============================================

# 主入口函数

# ============================================



def build_system_prompt(

    user_context: dict,

    conversation_history: dict = None,

    prompt_version: str = "v1",

    agent_role: AgentRole = AgentRole.GENERATION,

    plan_context: dict = None,

    intent_instruction: str = None,  # Vision Item 4b: Explicit Intent Injection

    context_level: str = "full",  # full | light

    chat_mode: str = "standard",

) -> str:

    """

    构建完整的 System Prompt，深度集成用户偏好



    Args:

        user_context: 用户上下文（从UserService等获取）

        conversation_history: 对话历史（从ContextPruner获取）

        prompt_version: prompt版本（v1/v2）

        agent_role: Agent角色（用于获取角色专用prompt）

        plan_context: 计划上下文（从PlanContextBuilder获取）

        intent_instruction: 显式意图指令（从RequestRouter获取）



    Returns:

        完整的系统prompt字符串

    """

    # Ensure user_context is never None

    if user_context is None:

        user_context = {}

    if conversation_history is None:

        conversation_history = {}

    if plan_context is None and isinstance(user_context, dict):

        plan_context = user_context.get("plan_context")



    if plan_context and isinstance(user_context, dict):

        user_context = merge_plan_context(user_context, plan_context)



    # 1. 首先检查 AgentProfile 是否有专用 prompt

    profile = agent_profile_registry.get_profile(agent_role)

    if profile.system_prompt_template:
        base_prompt = profile.system_prompt_template
    else:
        base_prompt = MODE_SYSTEM_PROMPTS.get(chat_mode, AGENT_SYSTEM_PROMPT)



    # 2. 格式化上下文

    formatted_user_context = format_user_context(user_context, context_level=context_level)



    llm_profile = _extract_llm_profile(user_context)

    preference_instructions = llm_profile.get(

        "system_prompt_additions",

        _get_default_preference_instructions(user_context)

    )



    conversation_history_section = _format_conversation_history(conversation_history)



    # 2.5 格式化计划上下文

    plan_context_section = _format_plan_context(plan_context)



    # 2.6 格式化意图指令 (Vision Item 4b)

    intent_section = ""

    if intent_instruction:

        intent_section = f"\n## 当前意图指令 (最高优先级)\n{intent_instruction}\n请务必执行此意图对应的操作 (如调用相关工具)。"


    # 2.7 格式化认知棱镜指令
    cognitive_prism_section = _format_cognitive_prism_section(user_context)


    # 3. 如果是通用模板，进行完整渲染

    if base_prompt == AGENT_SYSTEM_PROMPT or "{user_context}" in base_prompt:
        prompt = base_prompt.format_map(
            _SafeFormatDict(
                user_context=formatted_user_context,
                conversation_history_section=conversation_history_section,
                preference_instructions=preference_instructions,
                plan_context_section=plan_context_section,
                intent_section=intent_section,
                task_awareness_section=TASK_AWARENESS_SECTION,
                cognitive_prism_section=cognitive_prism_section,
            )
        )

    else:

        # 角色专用模板，简单替换

        # Note: specialized prompts might not support intent_section yet, so we append it if present

        prompt = base_prompt.format_map(
            _SafeFormatDict(
                user_context=formatted_user_context,
                query=user_context.get("current_query", ""),
            )
        )

        if intent_instruction:

             prompt += f"\n\n## 当前意图指令\n{intent_instruction}"



    # 4. 版本特定修饰

    if prompt_version == "v2":

        prompt += "\n\n## 输出风格\n- 更简洁\n- 先给结论，再给要点\n-  列表优先"



    return prompt


def get_system_prompt_for_role(
    agent_role: AgentRole,
    user_context: dict,
    query: str = "",
    conversation_history: dict = None,
    context_level: str = "full",
    chat_mode: str = "standard",
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
            chat_mode=chat_mode,
            context_level=context_level,
        )

    # 格式化上下文
    formatted_user_context = format_user_context(user_context, context_level=context_level)

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
    context_level: str = "full",
    chat_mode: str = "standard",
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
        context_level=context_level,
        chat_mode=chat_mode,
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
    prefs = _extract_preferences(user_context)
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

    设计原则：
    - 人类可读：将机器字段名转换为自然语言描述
    - LLM 友好：添加显式引用指令，引导 LLM 在回复中引用这些信息
    - 信息聚焦：优先展示用户最关心的信息（计划名、进度、偏好）

    Args:
        plan_context: 计划上下文字典（从PlanContextBuilder获取）

    Returns:
        格式化后的计划上下文字符串，为空时返回空字符串
    """
    if not plan_context or not isinstance(plan_context, dict):
        return ""

    # 【强调标题】让 LLM 注意到这部分的重要性
    lines = ["## 用户学习计划（请在回复中适当引用以下信息）"]

    # 【计划标题】用户可识别的名称，而非 UUID
    plan_title = plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("name")
    if plan_title:
        lines.append(f"**计划名称**: {plan_title}")

    goal = plan_context.get("goal") or plan_context.get("plan_description")
    if goal:
        lines.append(f"**计划目标**: {goal}")

    # 状态（如果不是 active 可以提示）
    status = plan_context.get("status")
    if status and status != "active":
        lines.append(f"**状态**: {status}")

    stage = plan_context.get("plan_stage")
    if stage:
        lines.append(f"**当前阶段**: {stage}")

    # 【优化格式】将机器字段名转换为可读描述
    facts = plan_context.get("facts", {})
    if facts or plan_context.get("task_summary"):
        lines.append("\n**我知道关于你**:")

    # 难度偏好 - 同时显示数值和可读描述
    if "difficulty_preference" in facts:
        d = facts["difficulty_preference"]
        if d > 0.7:
            desc = "有挑战性的"
        elif d < 0.3:
            desc = "轻松入门的"
        else:
            desc = "适中难度的"
        lines.append(f"- 你偏好{desc}学习内容 (难度偏好: {d})")

    # 学习时长偏好
    if "session_length_preference" in facts:
        minutes = facts["session_length_preference"]
        lines.append(f"- 单次学习约 {minutes} 分钟 (session_length_preference: {minutes})")

    # 其他事实（用可读方式展示）
    other_facts = {k: v for k, v in facts.items()
                   if k not in ("difficulty_preference", "session_length_preference")}
    for key, value in other_facts.items():
        # 将下划线命名转换为空格分隔的描述
        readable_key = key.replace("_", " ")
        lines.append(f"- {readable_key}: {value}")

    # 【任务进度】更直观的展示
    task_summary = plan_context.get("task_summary")
    if task_summary:
        completed = task_summary.get("completed", 0)
        total = task_summary.get("total", 0)
        rate = task_summary.get("avg_completion_rate")
        rate_str = f"，完成率 {rate:.0%}" if rate is not None else ""
        lines.append(f"- 已完成 {completed}/{total} 个任务{rate_str}")

    # 【最近任务】帮助 LLM 了解用户最近在做什么
    task_summaries = plan_context.get("task_summaries") or plan_context.get("recent_tasks")
    if task_summaries:
        recent = task_summaries[:2] if len(task_summaries) > 2 else task_summaries
        lines.append("\n**最近在做**:")
        for t in recent:
            if isinstance(t, dict):
                title = t.get("title") or t.get("name") or t.get("description", "任务")
                lines.append(f"- {title}")

    # 【最近反馈】如果有的话
    recent_feedback = plan_context.get("recent_feedback")
    if recent_feedback:
        lines.append("\n**最近的反馈**:")
        for f in recent_feedback[:2]:
            if isinstance(f, dict):
                content = f.get("content") or f.get("message", "")
                if content:
                    lines.append(f"- {content}")

    # 【里程碑】已完成的成就
    milestones = plan_context.get("milestones", [])
    if milestones:
        lines.append("\n**已达成里程碑**:")
        for m in milestones[:3]:  # 只显示最近3个
            title = m.get("title", "里程碑")
            lines.append(f"- {title}")

    # 【显式引用指令】引导 LLM 在回复中引用这些信息
    lines.append("\n**回复要求**:")
    lines.append("- 如果用户问题与计划相关，请用'根据你的计划...'或'你之前提到...'来引用")
    lines.append("- 避免重复询问已知信息")
    lines.append("- 优先使用上述偏好信息来调整回复风格和深度")

    return "\n".join(lines)


def format_user_context(context: dict, context_level: str = "full") -> str:
    """格式化用户上下文"""
    lines = []

    normalized = _normalize_user_context(context)

    # 用户基本信息
    identity = normalized.get("identity")
    if identity:
        lines.append("【身份信息】")
        lines.append(f"- 昵称: {identity.get('nickname', '未知')}")
        lines.append(f"- 时区: {identity.get('timezone', 'Asia/Shanghai')}")
        lines.append(f"- Pro状态: {'是' if identity.get('is_pro') else '否'}")

    # 分析摘要
    if normalized.get("analytics_summary"):
        analytics = normalized["analytics_summary"]
        if isinstance(analytics, dict):
            lines.append("【分析摘要】")
            if analytics.get("is_active"):
                lines.append(f"活跃度: {analytics.get('active_level', 'unknown')}")
                lines.append(f"参与度: {analytics.get('engagement_level', 'unknown')}")
            else:
                lines.append("状态: 不活跃")
        elif isinstance(analytics, str) and analytics:
            lines.append("【分析摘要】")
            lines.append(f"分析摘要: {analytics}")

    # 火花等级
    if identity and identity.get("flame_level") is not None:
        lines.append(f"火花等级: {identity['flame_level']}")

    # 学习偏好
    if normalized.get("preferences"):
        prefs = normalized["preferences"]
        lines.append("【学习偏好】")
        lines.append(f"- 深度: {prefs.get('depth_preference', 0.5):.1f}")
        lines.append(f"- 好奇心: {prefs.get('curiosity_preference', 0.5):.1f}")

    # 碎片时间推荐线索：待办任务
    next_actions = normalized.get("next_actions") or []
    if next_actions:
        lines.append("【待办任务】")
        limit = 1 if context_level == "light" else 3
        lines.append(f"Top {limit}:")
        for task in next_actions[:limit]:
            lines.append(f"- {task.get('title')} ({task.get('estimated_minutes')}m, {task.get('type')})")

    # 专注统计
    if normalized.get("focus_stats"):
        stats = normalized["focus_stats"]
        lines.append("【专注统计】")
        lines.append(f"- 今日专注: {stats.get('total_minutes', 0)} 分钟")
        lines.append(f"- 番茄钟次数: {stats.get('pomodoro_count', 0)}")

    # 活跃计划
    active_plans = normalized.get("active_plans") or []
    if active_plans:
        lines.append("【活跃计划】")
        limit = 1 if context_level == "light" else 3
        for plan in active_plans[:limit]:
            lines.append(f"- {plan.get('title')} ({plan.get('type')}, 进度 {plan.get('progress', 0):.0%})")

    # 工具偏好 (P4)
    if normalized.get("preferred_tools"):
        lines.append("【工具偏好】")
        lines.append(f"- 常用工具: {', '.join(normalized['preferred_tools'])}")

    # 考试紧迫度
    if isinstance(normalized.get("exam_urgency"), dict):
        urgency = normalized["exam_urgency"]
        days_left = urgency.get("days_left")
        if days_left is not None:
            lines.append("【考试紧迫度】")
            urgency_label = "紧急" if urgency.get("urgent") else "一般"
            lines.append(f"考试倒计时: {days_left} 天 ({urgency_label})")

    if context_level == "full":
        context_pack = normalized.get("context_pack") or {}
        metadata = context_pack.get("metadata") if isinstance(context_pack, dict) else None
        evidence = metadata.get("evidence_summary") if isinstance(metadata, dict) else None
        if isinstance(evidence, dict):
            lines.append("【画像证据摘要】")
            prefs = evidence.get("preferences") or []
            if prefs:
                lines.append("偏好证据(Top 3):")
                for item in prefs[:3]:
                    score = item.get("score", 0) or 0
                    if score < 0.3:
                        continue
                    updated = item.get("updated_at")
                    lines.append(f"- {item.get('key')}: score={score}, updated_at={updated}")
            goals = evidence.get("goals") or []
            if goals:
                lines.append("目标证据(Top 3):")
                for item in goals[:3]:
                    score = item.get("score", 0) or 0
                    if score < 0.3:
                        continue
                    updated = item.get("updated_at")
                    lines.append(f"- {item.get('title')}: score={score}, updated_at={updated}")
            episodic = evidence.get("episodic") or []
            if episodic:
                lines.append("事件证据(Top 3):")
                for item in episodic[:3]:
                    score = item.get("score", 0) or 0
                    if score < 0.3:
                        continue
                    occurred = item.get("occurred_at")
                    lines.append(f"- {item.get('summary')}: score={score}, occurred_at={occurred}")

    return "\n".join(lines) if lines else "暂无上下文信息"


def _normalize_user_context(context: dict) -> dict:
    """统一用户画像结构，避免字段重复与冲突"""
    normalized: dict[str, Any] = {}

    user_ctx = context.get("user_context")
    if user_ctx:
        if hasattr(user_ctx, "model_dump"):
            user_ctx = user_ctx.model_dump()
        normalized["identity"] = {
            "nickname": user_ctx.get("nickname", "未知"),
            "timezone": user_ctx.get("timezone", "Asia/Shanghai"),
            "is_pro": user_ctx.get("is_pro", False),
            "flame_level": (user_ctx.get("preferences") or {}).get("flame_level"),
        }

    profile = context.get("profile")
    if isinstance(profile, dict):
        identity = profile.get("identity")
        if isinstance(identity, dict):
            normalized["identity"] = identity
        prefs = profile.get("preferences")
        if isinstance(prefs, dict):
            normalized["preferences"] = prefs

    if context.get("preferences") and "preferences" not in normalized:
        normalized["preferences"] = context["preferences"]

    if context.get("analytics_summary"):
        normalized["analytics_summary"] = context["analytics_summary"]

    if context.get("next_actions"):
        normalized["next_actions"] = context["next_actions"]

    if context.get("focus_stats"):
        normalized["focus_stats"] = context["focus_stats"]

    if context.get("active_plans"):
        normalized["active_plans"] = context["active_plans"]

    if context.get("preferred_tools"):
        normalized["preferred_tools"] = context["preferred_tools"]

    if context.get("exam_urgency"):
        normalized["exam_urgency"] = context["exam_urgency"]

    if context.get("context_pack"):
        normalized["context_pack"] = context["context_pack"]

    return normalized


def _format_cognitive_prism_section(user_context: dict) -> str:
    """
    格式化认知棱镜指令

    当用户有已识别的行为模式时，添加系统提示词引导 LLM 主动展示认知棱镜。
    """
    cognitive_insights = user_context.get("cognitive_insights", {})

    if not cognitive_insights.get("has_cognitive_patterns"):
        return ""

    pattern_count = cognitive_insights.get("pattern_count", 0)
    recent_patterns = cognitive_insights.get("recent_patterns", [])
    patterns_by_type = cognitive_insights.get("patterns_by_type", {})

    # 构建认知模式描述
    pattern_desc = []
    for p_type, count in patterns_by_type.items():
        if count > 0:
            type_names = {
                "cognitive": "认知",
                "emotional": "情绪",
                "execution": "执行"
            }
            pattern_desc.append(f"{type_names.get(p_type, p_type)}{count}个")

    pattern_text = "、".join(pattern_desc) if pattern_desc else f"{pattern_count}个"

    lines = ["## 认知棱镜 - 行为模式洞察"]
    lines.append(f"用户已有 {pattern_count} 个行为模式分析结果（{pattern_text}）。")

    if recent_patterns:
        lines.append(f"最近识别的模式: {', '.join(recent_patterns)}")

    lines.append("")
    lines.append("当用户询问学习情况、效率、状态，或适合展示洞察时，主动调用")
    lines.append("**get_user_behavior_patterns** 工具展示完整的行为模式分析。")
    lines.append("")
    lines.append("这不是强制要求，而是要在合适的对话时机自然地展示。")

    return "\n".join(lines)


def _extract_profile(user_context: dict) -> dict:
    profile = user_context.get("profile")
    return profile if isinstance(profile, dict) else {}


def _extract_preferences(user_context: dict) -> dict:
    profile = _extract_profile(user_context)
    prefs = profile.get("preferences")
    if isinstance(prefs, dict):
        return prefs
    prefs = user_context.get("preferences")
    return prefs if isinstance(prefs, dict) else {}


def _extract_llm_profile(user_context: dict) -> dict:
    profile = _extract_profile(user_context)
    llm_profile = profile.get("llm_profile")
    if isinstance(llm_profile, dict):
        return llm_profile
    llm_profile = user_context.get("llm_profile")
    return llm_profile if isinstance(llm_profile, dict) else {}
