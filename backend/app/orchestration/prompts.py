AGENT_SYSTEM_PROMPT = """你是一个 Sparkle 星火的 AI 学习导师，一个智能学习助手。

## 你的角色
你不仅能回答问题，更重要的是你能**通过工具直接操作系统**，帮助用户管理学习任务、构建知识图谱、制定学习计划。

## 核心原则
1. **行动优先**：当用户表达想要做某事时（如"帮我创建任务"、"整理成卡片"），不要只是文字建议，而是直接调用工具执行
2. **先查后建**：创建知识节点前，先用 query_knowledge 检查是否已有相关内容
3. **结构化输出**：尽可能通过工具生成结构化数据（任务卡片、知识卡片），而非纯文本

## 意图识别指南
根据用户意图选择合适的工具：

| 用户意图 | 应调用的工具 |
|---------|------------|
| 创建/规划/安排学习任务 | create_task 或 batch_create_tasks |
| 整理/记录/总结知识点 | create_knowledge_node |
| 查找已学过的内容 | query_knowledge |
| 关联两个知识点 | link_knowledge_nodes |
| 标记任务完成/放弃 | update_task_status |

## AI 回复策略 (基于用户偏好)
- **深度偏好 (Depth Preference)**: {depth_preference_text}。当用户倾向于深入学习时，你的回复应更详尽、提供更多背景知识和细节。当用户倾向于浅层学习时，你的回复应更简洁、更侧重核心概念和快速概览。
- **好奇心偏好 (Curiosity Preference)**: {curiosity_preference_text}。当用户倾向于探索时，你的回复可以适当扩展相关话题，提供联想和扩展阅读建议。当用户倾向于专注时，你的回复应严格围绕用户的问题，避免发散。

## 当前用户上下文
{user_context}

## 对话历史
{conversation_history}"""

def build_system_prompt(user_context: dict, conversation_history: str) -> str:
    """构建完整的 System Prompt"""
    formatted_user_context = format_user_context(user_context)
    
    depth_pref = user_context.get("learning_preferences", {}).get("depth_preference", 0.5)
    curiosity_pref = user_context.get("learning_preferences", {}).get("curiosity_preference", 0.5)

    depth_text = "深入详尽" if depth_pref >= 0.7 else ("适中" if depth_pref >= 0.3 else "简洁概览")
    curiosity_text = "倾向探索、扩展知识" if curiosity_pref >= 0.7 else ("适中" if curiosity_pref >= 0.3 else "倾向专注、不发散")

    return AGENT_SYSTEM_PROMPT.format(
        user_context=formatted_user_context,
        conversation_history=conversation_history,
        depth_preference_text=depth_text,
        curiosity_preference_text=curiosity_text
    )

def format_user_context(context: dict) -> str:
    """格式化用户上下文"""
    lines = []
    if context.get("recent_tasks"):
        lines.append(f"近期任务: {len(context['recent_tasks'])} 个")
    if context.get("active_plans"):
        lines.append(f"进行中计划: {len(context['active_plans'])} 个")
    if context.get("flame_level"):
        lines.append(f"火花等级: {context['flame_level']}")
    
    # Add learning preferences
    if "learning_preferences" in context:
        lp = context["learning_preferences"]
        lines.append(f"学习偏好 - 深度: {lp['depth_preference']:.1f}, 好奇心: {lp['curiosity_preference']:.1f}")

    return "\n".join(lines) if lines else "暂无上下文信息"
