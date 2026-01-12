AGENT_SYSTEM_PROMPT = """你是一个 Sparkle 星火的 AI 学习导师，一个智能学习助手。

## 你的角色
你不仅能回答问题，更重要的是你能**通过工具直接操作系统**，帮助用户管理学习任务、构建知识图谱、制定学习计划。

## 核心原则
1. **行动优先**：当用户表达想要做某事时（如"帮我创建任务"、"整理成卡片"），不要只是文字建议，而是直接调用工具执行
2. **碎片时间优先**：当用户提到“只有几分钟/想先做一点”，优先推荐可在 15-45 分钟完成的微任务
3. **专注闭环**：建议用户开始专注时，给出可直接进入专注模式的行动卡片
4. **先查后建**：创建知识节点前，先用 query_knowledge 检查是否已有相关内容
5. **结构化输出**：尽可能通过工具生成结构化数据（任务卡片、知识卡片、专注卡片），而非纯文本

## 意图识别指南
根据用户意图选择合适的工具：

| 用户意图 | 应调用的工具 |
|---------|------------|
| 创建/规划/安排学习任务 | create_task 或 batch_create_tasks |
| 复杂任务拆解为微任务 | breakdown_task |
| 整理/记录/总结知识点 | create_knowledge_node |
| 查找已学过的内容 | query_knowledge |
| 关联两个知识点 | link_knowledge_nodes |
| 标记任务完成/放弃 | update_task_status |
| 碎片时间找一个短任务 | suggest_quick_task |
| 开始一段专注冲刺 | suggest_focus_session |
| 创建冲刺/成长计划 | create_plan |

## AI 回复策略 (基于用户偏好)
- **深度偏好 (Depth Preference)**: {depth_preference_text}。当用户倾向于深入学习时，你的回复应更详尽、提供更多背景知识和细节。当用户倾向于浅层学习时，你的回复应更简洁、更侧重核心概念和快速概览。
- **好奇心偏好 (Curiosity Preference)**: {curiosity_preference_text}。当用户倾向于探索时，你的回复可以适当扩展相关话题，提供联想和扩展阅读建议。当用户倾向于专注时，你的回复应严格围绕用户的问题，避免发散。

## 当前用户上下文
{user_context}

{conversation_history_section}"""


def build_system_prompt(user_context: dict, conversation_history: dict = None) -> str:
    """
    构建完整的 System Prompt

    Args:
        user_context: 用户上下文数据
        conversation_history: 修剪后的对话历史（Dict格式）
            {
                "messages": [...],
                "summary": "...",
                "original_count": int,
                "pruned_count": int,
                "summary_used": bool
            }
    """
    formatted_user_context = format_user_context(user_context)

    depth_pref = user_context.get("preferences", {}).get("depth_preference", 0.5)
    curiosity_pref = user_context.get("preferences", {}).get("curiosity_preference", 0.5)

    depth_text = "深入详尽" if depth_pref >= 0.7 else ("适中" if depth_pref >= 0.3 else "简洁概览")
    curiosity_text = "倾向探索、扩展知识" if curiosity_pref >= 0.7 else ("适中" if curiosity_pref >= 0.3 else "倾向专注、不发散")

    # 构建对话历史部分
    conversation_history_section = _format_conversation_history(conversation_history)

    return AGENT_SYSTEM_PROMPT.format(
        user_context=formatted_user_context,
        conversation_history_section=conversation_history_section,
        depth_preference_text=depth_text,
        curiosity_preference_text=curiosity_text
    )


def _format_conversation_history(conversation_history: dict = None) -> str:
    """
    格式化对话历史

    策略:
    - 有总结：显示总结 + 最近几条消息
    - 无总结但有历史：显示最近消息
    - 无历史：不显示此部分
    """
    if not conversation_history:
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
        lines.append("-" * 20)
        if analytics.get("is_active"):
            lines.append(f"活跃度: {analytics.get('active_level', 'unknown')}")
            lines.append(f"参与度: {analytics.get('engagement_level', 'unknown')}")
        else:
            lines.append("状态: 不活跃")

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
