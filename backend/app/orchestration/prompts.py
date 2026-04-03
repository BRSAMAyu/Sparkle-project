from __future__ import annotations
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
import json
import math
import random

from loguru import logger

from app.core.agent_persona import build_agent_persona_prompt_section
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.core.business_metrics import CONTEXT_FOCUS_PROMPT_SECTION_TOTAL
from app.core.plan_context import merge_plan_context
from app.config import settings
from app.orchestration.context_focus import ContextFocusDecision

class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        logger.warning("Prompt template missing placeholder value: {}", key)
        return f"{{missing:{key}}}"


PROMPT_SECTION_SOFT_LIMIT_TOKENS = 4000

# 各 tier 的 prompt token 预算（与 ModelTier 对应但避免循环导入，用字符串 key）
_TIER_PROMPT_BUDGET: dict[str, int] = {
    "free_fast": 1500,
    "fast": 2000,
    "standard": 4000,
    "reasoning": 4000,
    "free_reasoning": 3000,
    "glm_batch": 4000,
}

_SECTION_BUDGET_RATIO: dict[str, tuple[int, float]] = {
    "context_briefing_section": (80, 0.05),
    "intent_section": (100, 0.08),
    "session_feedback_section": (60, 0.05),
    "dual_core_section": (80, 0.05),
    "mode_strategy_section": (120, 0.10),
    "plan_context_section": (200, 0.10),
    "user_context": (350, 0.18),
    "conversation_history_section": (80, 0.16),
    "task_awareness_section": (60, 0.08),
    "cognitive_prism_section": (120, 0.05),
    "preference_instructions": (60, 0.05),
    "persona_section": (40, 0.04),
    "agent_persona_section": (40, 0.04),
    "agent_memory_section": (40, 0.03),
    "understanding_depth_section": (60, 0.05),
    "orchestration_context_section": (60, 0.05),
    "collaboration_narrative_section": (60, 0.05),
    "seed_library_section": (40, 0.04),
}


def _is_cjk_character(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x3040 <= codepoint <= 0x30FF
        or 0xAC00 <= codepoint <= 0xD7AF
    )


def _estimate_prompt_tokens(text: str) -> int:
    normalized = str(text or "")
    if not normalized:
        return 1

    cjk_chars = sum(1 for char in normalized if _is_cjk_character(char))
    non_cjk_chars = len(normalized) - cjk_chars
    estimated_tokens = math.ceil((cjk_chars * 1.5) + (non_cjk_chars / 4))
    return max(1, estimated_tokens)


def _detect_feedback_mode(instruction: str | None) -> str:
    text = str(instruction or "").lower()
    if not text:
        return ""
    if "精简" in text or "太难" in text or "太长" in text or "收短" in text:
        return "simplify"
    if "更详细" in text or "更展开" in text or "例子" in text:
        return "expand"
    if "答偏" in text or "重答" in text or "当前诉求" in text:
        return "mismatch"
    return ""


def _soften_section(content: str, *, reason: str) -> str:
    text = str(content or "").strip()
    if not text:
        return ""
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join([lines[0], f"[冲突预检] {reason}", *lines[1:]]) if lines else text


def _truncate_section(content: str, *, target_tokens: int) -> str:
    text = str(content or "").strip()
    if not text or _estimate_prompt_tokens(text) <= target_tokens:
        return text
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return text
    kept: list[str] = []
    used_tokens = 0
    for idx, line in enumerate(lines):
        line_tokens = _estimate_prompt_tokens(line)
        if idx > 0 and used_tokens + line_tokens > target_tokens:
            break
        kept.append(line)
        used_tokens += line_tokens
    kept.append("...其余低优先级背景已压缩；若与更高优先级指令冲突，以更高优先级为准。")
    return "\n".join(kept)


def _apply_prompt_budget(
    section_map: dict[str, str],
    *,
    priority_map: dict[str, int],
    budget_tokens: int | None = None,
) -> dict[str, str]:
    limit = budget_tokens if budget_tokens is not None else PROMPT_SECTION_SOFT_LIMIT_TOKENS
    total_tokens = sum(_estimate_prompt_tokens(content) for content in section_map.values() if str(content or "").strip())
    if total_tokens <= limit:
        return section_map

    adjusted = dict(section_map)

    def _recount() -> int:
        return sum(
            _estimate_prompt_tokens(item)
            for item in adjusted.values()
            if str(item or "").strip()
        )

    # 先按每个区域的最大占比做一次硬上限裁剪
    for priority in sorted(set(priority_map.values()), reverse=True):
        for section_name, content in list(adjusted.items()):
            if priority_map.get(section_name) != priority:
                continue
            text = str(content or "").strip()
            if not text:
                continue
            min_tokens, max_ratio = _SECTION_BUDGET_RATIO.get(section_name, (60, 0.06))
            current_tokens = _estimate_prompt_tokens(text)
            target_tokens = max(min_tokens, int(limit * max_ratio))
            if current_tokens > target_tokens:
                adjusted[section_name] = _truncate_section(text, target_tokens=target_tokens)
        if _recount() <= limit:
            return adjusted

    # 如果仍超限，则从低优先级开始继续向下压到保底 token
    for priority in sorted(set(priority_map.values()), reverse=True):
        section_names = [
            name for name in adjusted.keys()
            if priority_map.get(name) == priority and str(adjusted.get(name) or "").strip()
        ]
        for section_name in section_names:
            text = str(adjusted.get(section_name) or "").strip()
            if not text:
                continue
            min_tokens, _ = _SECTION_BUDGET_RATIO.get(section_name, (60, 0.06))
            current_tokens = _estimate_prompt_tokens(text)
            if current_tokens <= min_tokens:
                continue
            target_tokens = max(min_tokens, int(current_tokens * 0.75))
            adjusted[section_name] = _truncate_section(text, target_tokens=target_tokens)
            if _recount() <= limit:
                return adjusted
    return adjusted

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

学习桥接工具：
11. launch_prediction - 当用户在问学习路径、what-if、跳过某知识点的后果、两周学会某主题时，优先调用
12. run_quick_simulation - 当用户要求模拟学习小组、知识辩论、角色扮演或“帮我演练一下”时，优先调用
13. generate_learning_report - 当用户要求学习报告、阶段复盘、最近学习表现总结时，优先调用

**重要提示**：在生成新任务前，务必先调用 get_plan_state 获取：
- 当前进度和已达成里程碑
- 任务完成统计
- 自适应调整参数（difficulty_shift, time_multiplier）
"""

AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。

{mode_strategy_section}

{task_awareness_section}

{persona_section}

{agent_persona_section}

## 当前用户上下文

{user_context}

{plan_context_section}

{preference_instructions}

## 对话历史

{conversation_history_section}

{context_briefing_section}

{intent_section}

{session_feedback_section}

{dual_core_section}

{understanding_depth_section}

{orchestration_context_section}

{collaboration_narrative_section}

{agent_memory_section}

{cognitive_prism_section}

{seed_library_section}

## 核心原则

1. 始终遵循用户的偏好设置，这是最重要的
2. 如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认
3. 当用户明确确认或纠正偏好时，调用 update_user_preference 工具记录

4. 根据 verbosity 目标调整回答长度

5. 根据 exploration_level 决定是否扩展话题

6. 保持角色一致性

7. 提供准确、有帮助的回答

8. 如果有活跃计划上下文，优先考虑计划相关的任务和目标

"""

MODE_SYSTEM_PROMPTS = {
    "standard": AGENT_SYSTEM_PROMPT,
    "deep_analysis": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



{context_briefing_section}



{intent_section}



{session_feedback_section}



{dual_core_section}



{understanding_depth_section}



{orchestration_context_section}



{collaboration_narrative_section}



{mode_strategy_section}



{persona_section}



{agent_memory_section}



## 当前用户上下文

{user_context}



{preference_instructions}



{plan_context_section}



{cognitive_prism_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



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
3. 当用户明确确认或纠正偏好时，调用 update_user_preference 工具记录

4. 根据 verbosity 目标调整回答长度

5. 根据 exploration_level 决定是否扩展话题

6. 保持角色一致性

7. 提供准确、有帮助的回答

8. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
""",
    "study_plan": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



{context_briefing_section}



{intent_section}



{session_feedback_section}



{dual_core_section}



{understanding_depth_section}



{orchestration_context_section}



{collaboration_narrative_section}



{mode_strategy_section}



{persona_section}



{agent_memory_section}



## 当前用户上下文

{user_context}



{preference_instructions}



{plan_context_section}



{cognitive_prism_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



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
3. 当用户明确确认或纠正偏好时，调用 update_user_preference 工具记录

4. 根据 verbosity 目标调整回答长度

5. 根据 exploration_level 决定是否扩展话题

6. 保持角色一致性

7. 提供准确、有帮助的回答

8. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
""",
    "error_diagnosis": """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。



{context_briefing_section}



{intent_section}



{session_feedback_section}



{dual_core_section}



{understanding_depth_section}



{orchestration_context_section}



{collaboration_narrative_section}



{mode_strategy_section}



{persona_section}



{agent_memory_section}



## 当前用户上下文

{user_context}



{preference_instructions}



{plan_context_section}



{cognitive_prism_section}



## 对话历史

{conversation_history_section}



{task_awareness_section}



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
3. 当用户明确确认或纠正偏好时，调用 update_user_preference 工具记录

4. 根据 verbosity 目标调整回答长度

5. 根据 exploration_level 决定是否扩展话题

6. 保持角色一致性

7. 提供准确、有帮助的回答

8. 如果有活跃计划上下文，优先考虑计划相关的任务和目标
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

    session_feedback_instruction: str = None,

    dual_core_instruction: str = None,

    context_focus: dict | None = None,

    context_briefing_note: str | None = None,

    context_level: str = "full",  # full | light

    chat_mode: str = "standard",

    model_key: str | None = None,  # P2: model-aware prompt budget

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
        session_feedback_instruction: 会话内即时反馈指令（优先级低于显式意图，高于 dual-core/一般偏好）
        dual_core_instruction: 双核心路由指令（优先级低于显式意图与会话内反馈，高于一般偏好）
        context_focus: 上下文聚焦决策
        context_briefing_note: 本轮关键上下文摘要



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

    if context_focus is None and isinstance(user_context, dict):
        raw_context_focus = user_context.get("context_focus")
        if isinstance(raw_context_focus, dict):
            context_focus = raw_context_focus

    if not context_briefing_note and isinstance(user_context, dict):
        context_briefing_note = str(user_context.get("context_briefing_note") or "").strip()

    orchestration_trace = None
    mode_strategy_payload = None
    persona_constraints_summary = ""
    agent_memory_context = ""
    collaboration_narrative = ""
    agent_persona_section = ""
    if isinstance(user_context, dict):
        raw_trace = user_context.get("orchestration_trace")
        if isinstance(raw_trace, str) and raw_trace:
            try:
                raw_trace = json.loads(raw_trace)
            except Exception:
                raw_trace = None
        if isinstance(raw_trace, dict):
            orchestration_trace = raw_trace

        raw_strategy = user_context.get("mode_strategy")
        if isinstance(raw_strategy, str) and raw_strategy:
            try:
                raw_strategy = json.loads(raw_strategy)
            except Exception:
                raw_strategy = None
        if isinstance(raw_strategy, dict):
            mode_strategy_payload = raw_strategy

        persona_constraints_summary = str(user_context.get("persona_constraints_summary") or "").strip()
        agent_memory_context = str(user_context.get("agent_memory_context") or "").strip()
        collaboration_narrative = str(user_context.get("collaboration_narrative") or "").strip()


    # 1. 首先检查 AgentProfile 是否有专用 prompt

    profile = agent_profile_registry.get_profile(agent_role)
    agent_persona_section = build_agent_persona_prompt_section(
        agent_role=agent_role,
        user_context=user_context,
        profile=profile,
    )

    if profile.system_prompt_template:
        base_prompt = profile.system_prompt_template
    else:
        base_prompt = MODE_SYSTEM_PROMPTS.get(chat_mode, AGENT_SYSTEM_PROMPT)



    # 2. 格式化上下文

    formatted_user_context = format_user_context(
        user_context,
        context_level=context_level,
        context_focus=context_focus,
    )



    llm_profile = _extract_llm_profile(user_context)
    understanding_depth_hint = None
    if isinstance(user_context, dict):
        raw_depth_hint = user_context.get("understanding_depth_hint")
        if isinstance(raw_depth_hint, dict):
            understanding_depth_hint = raw_depth_hint

    preference_instructions = _resolve_preference_instructions(
        user_context=user_context,
        llm_profile=llm_profile,
        context_focus=context_focus,
    )



    conversation_history_section = _format_conversation_history(conversation_history)



    # 2.5 格式化计划上下文

    plan_context_section = _format_plan_context(
        plan_context,
        context_focus=context_focus,
        query_text=str(user_context.get("current_query", "") or ""),
    )



    # 2.6 格式化意图指令 (Vision Item 4b)

    intent_section = ""

    if intent_instruction:

        intent_section = (
            "\n## 当前意图指令 [L1 强制]\n"
            "[冲突处理] 若与其他指令冲突，优先执行本节。\n"
            f"{intent_instruction}\n"
            "请务必执行此意图对应的操作 (如调用相关工具)。"
        )

    session_feedback_section = ""
    if session_feedback_instruction:
        session_feedback_section = (
            "\n## 会话内反馈适配 [L1 强制]\n"
            "[冲突处理] 这是本轮即时适配，优先于引导层和背景层。\n"
            f"{session_feedback_instruction}\n"
            "这是一轮内即时调整，优先于长期偏好，但不会更新长期画像。"
        )

    dual_core_section = ""
    if dual_core_instruction:
        dual_core_section = (
            "\n## 双核心路由指令 [L2 引导]\n"
            f"{dual_core_instruction}\n"
            "请先遵循这组路径与约束，再结合用户一般偏好组织回答。"
        )

    orchestration_context_section = ""
    if isinstance(orchestration_trace, dict):
        mode_label = str(orchestration_trace.get("mode") or "").strip()
        agents = orchestration_trace.get("agents") or []
        agent_list = [str(agent).strip() for agent in agents if str(agent).strip()]
        persona_step = orchestration_trace.get("persona_step") or {}
        review_step = orchestration_trace.get("review_step") or {}
        summary_lines: list[str] = []
        if mode_label or agent_list:
            agent_text = "、".join(agent_list) if agent_list else "系统自动选择"
            summary_lines.append(f"本次由 {mode_label or 'standard'} 模式驱动，调度 {agent_text} 协作。")
        if isinstance(persona_step, dict) and persona_step.get("decision"):
            summary_lines.append(f"画像提示：{persona_step.get('decision')}")
        if isinstance(review_step, dict) and review_step.get("decision"):
            summary_lines.append(f"计划审查：{review_step.get('decision')}")
        if summary_lines:
            orchestration_context_section = "\n## 编排上下文 [L2 引导]\n" + "\n".join(summary_lines)

    collaboration_narrative_section = ""
    if collaboration_narrative:
        collaboration_narrative_section = (
            "\n## 协作叙事提示 [L2 引导]\n"
            "请在回答开头用一句自然的话提及协作过程，不要像系统通知。\n"
            f"{collaboration_narrative}"
        )

    mode_strategy_section = ""
    if isinstance(mode_strategy_payload, dict):
        output_structure = mode_strategy_payload.get("output_structure") or []
        synthesis_instruction = str(mode_strategy_payload.get("synthesis_instruction") or "").strip()
        output_text = ""
        if isinstance(output_structure, list):
            output_items = [str(item).strip() for item in output_structure if str(item).strip()]
            if output_items:
                output_text = f"请严格按以下结构组织回答：{'、'.join(output_items)}。"
        if output_text or synthesis_instruction:
            mode_strategy_section = "\n## 输出要求 [L2 引导]\n"
            if output_text:
                mode_strategy_section += output_text
            if synthesis_instruction:
                mode_strategy_section += f"\n{synthesis_instruction}"

    persona_section = ""
    if persona_constraints_summary:
        persona_section = "\n## 用户画像提示 [L2 引导]\n" + persona_constraints_summary
    companion_persona_section = _format_companion_persona_section(
        user_context=user_context,
        plan_context=plan_context,
    )
    if companion_persona_section:
        persona_section = (
            persona_section + "\n" + companion_persona_section.strip()
            if persona_section
            else companion_persona_section
        )

    agent_memory_section = ""
    if agent_memory_context:
        agent_memory_section = "\n## 专家交互记忆 [L2 引导]\n" + agent_memory_context

    understanding_depth_section = ""
    if isinstance(understanding_depth_hint, dict):
        natural_hint = str(understanding_depth_hint.get("natural_hint") or "").strip()
        if natural_hint:
            level = str(understanding_depth_hint.get("level") or "").strip()
            description = str(understanding_depth_hint.get("description") or "").strip()
            understanding_depth_section = (
                "\n## 理解深度升级提示 [L2 引导]\n"
                "仅当本轮表达自然且不打断当前任务时，用一句话轻带过，不要像系统通知。\n"
                f"{natural_hint}\n"
                + (f"当前升级: {level}\n" if level else "")
                + (f"提示背景: {description}\n" if description else "")
            )


    # 2.7 格式化认知棱镜指令
    cognitive_prism_section = _format_cognitive_prism_section(user_context, context_focus=context_focus)

    # 2.8 格式化种子库 few-shot 示例
    seed_library_section = ""
    seed_lib = user_context.get("seed_library") if isinstance(user_context, dict) else None
    if isinstance(seed_lib, dict) and seed_lib.get("has_seed_library"):
        examples = seed_lib.get("few_shot_examples", [])
        if examples:
            example_lines = []
            for ex in examples[:3]:
                inp = str(ex.get("input", "")).strip()
                out = str(ex.get("output", "")).strip()
                if inp and out:
                    example_lines.append(f"- 问: {inp}\n  答: {out}")
            if example_lines:
                seed_library_section = (
                    "\n## 参考示例（来自用户订阅的种子库） [L3 背景]\n"
                    "以下是该学科/领域的高质量问答示例，请参考其风格和深度：\n"
                    + "\n".join(example_lines)
                )

    context_briefing_section = ""
    if context_briefing_note:
        context_briefing_section = f"## 本轮关键上下文摘要 [L0 简报]\n{context_briefing_note}"

    feedback_mode = _detect_feedback_mode(session_feedback_instruction)
    if feedback_mode == "simplify":
        preference_instructions = _soften_section(
            preference_instructions,
            reason="本轮以精简表达为准；以下偏好仅在不增加篇幅时参考。",
        )
        if dual_core_section:
            dual_core_section = _soften_section(
                dual_core_section,
                reason="本轮即时反馈要求更精简；保留路径约束，但避免展开过多说明。",
            )
        if cognitive_prism_section:
            cognitive_prism_section = _soften_section(
                cognitive_prism_section,
                reason="本轮以精简表达为准；认知洞察仅作软建议。",
            )
        if orchestration_context_section:
            orchestration_context_section = _soften_section(
                orchestration_context_section,
                reason="本轮以精简为主；编排背景只保留最小必要信息。",
            )
        if collaboration_narrative_section:
            collaboration_narrative_section = _soften_section(
                collaboration_narrative_section,
                reason="本轮以精简为主；协作提示仅作轻量说明。",
            )
        if persona_section:
            persona_section = _soften_section(
                persona_section,
                reason="本轮以精简为主；画像信息仅作轻量提示。",
            )
        if agent_persona_section:
            agent_persona_section = _soften_section(
                agent_persona_section,
                reason="本轮以精简为主；导师人格保持稳定但不需展开描述。",
            )
        if agent_memory_section:
            agent_memory_section = _soften_section(
                agent_memory_section,
                reason="本轮以精简为主；交互记忆仅作轻量提示。",
            )
    elif feedback_mode == "expand":
        preference_instructions = _soften_section(
            preference_instructions,
            reason="本轮需要更展开说明；简洁偏好降为背景参考。",
        )
    elif feedback_mode == "mismatch":
        if conversation_history_section:
            conversation_history_section = _soften_section(
                conversation_history_section,
                reason="用户刚纠正了方向；历史对话仅作背景，不能覆盖当前诉求。",
            )
        if cognitive_prism_section:
            cognitive_prism_section = _soften_section(
                cognitive_prism_section,
                reason="当前以纠正后的问题方向为准；认知洞察只能作为补充。",
            )

    focus_decision = ContextFocusDecision.from_dict(context_focus)
    cognitive_priority = 2 if focus_decision and focus_decision.focus_mode in {"emotional_focus", "cognitive_focus"} else 3
    section_map = {
        "context_briefing_section": context_briefing_section,
        "intent_section": intent_section,
        "session_feedback_section": session_feedback_section,
        "user_context": f"[优先级：L3 背景]\n{formatted_user_context}".strip(),
        "preference_instructions": f"[优先级：L3 背景]\n{preference_instructions}".strip(),
        "plan_context_section": plan_context_section,
        "dual_core_section": dual_core_section,
        "understanding_depth_section": understanding_depth_section,
        "orchestration_context_section": orchestration_context_section,
        "collaboration_narrative_section": collaboration_narrative_section,
        "mode_strategy_section": mode_strategy_section,
        "persona_section": persona_section,
        "agent_persona_section": agent_persona_section,
        "agent_memory_section": agent_memory_section,
        "cognitive_prism_section": cognitive_prism_section,
        "seed_library_section": seed_library_section,
        "conversation_history_section": f"[优先级：L3 背景]\n{conversation_history_section}".strip() if conversation_history_section else "",
        "task_awareness_section": f"[优先级：L3 背景]\n{TASK_AWARENESS_SECTION}".strip(),
    }
    # P2: 根据 model_key 的 tier 动态调整 prompt token 预算
    _model_tier_str: str | None = None
    if model_key:
        try:
            from app.core.llm_router import llm_router as _lr
            _mc = _lr._available_models.get(model_key)
            if _mc and hasattr(_mc, "tier"):
                _model_tier_str = _mc.tier.value
        except Exception:
            pass
    _prompt_budget = _TIER_PROMPT_BUDGET.get(_model_tier_str or "", PROMPT_SECTION_SOFT_LIMIT_TOKENS)

    section_map = _apply_prompt_budget(
        section_map,
        priority_map={
            "context_briefing_section": 0,
            "intent_section": 1,
            "session_feedback_section": 1,
            "user_context": 3,
            "preference_instructions": 3,
            "plan_context_section": 2,
            "dual_core_section": 2,
            "understanding_depth_section": 2,
            "orchestration_context_section": 2,
            "collaboration_narrative_section": 2,
            "mode_strategy_section": 2,
            "persona_section": 2,
            "agent_persona_section": 2,
            "agent_memory_section": 2,
            "cognitive_prism_section": cognitive_priority,
            "seed_library_section": 3,
            "conversation_history_section": 3,
            "task_awareness_section": 3,
        },
        budget_tokens=_prompt_budget,
    )
    context_briefing_section = section_map["context_briefing_section"]
    intent_section = section_map["intent_section"]
    session_feedback_section = section_map["session_feedback_section"]
    formatted_user_context = section_map["user_context"]
    preference_instructions = section_map["preference_instructions"]
    plan_context_section = section_map["plan_context_section"]
    dual_core_section = section_map["dual_core_section"]
    understanding_depth_section = section_map["understanding_depth_section"]
    orchestration_context_section = section_map["orchestration_context_section"]
    collaboration_narrative_section = section_map["collaboration_narrative_section"]
    mode_strategy_section = section_map["mode_strategy_section"]
    persona_section = section_map["persona_section"]
    agent_persona_section = section_map["agent_persona_section"]
    agent_memory_section = section_map["agent_memory_section"]
    cognitive_prism_section = section_map["cognitive_prism_section"]
    conversation_history_section = section_map["conversation_history_section"]
    task_awareness_section = section_map["task_awareness_section"]
    seed_library_section = section_map["seed_library_section"]


    # 3. 如果是通用模板，进行完整渲染

    if base_prompt == AGENT_SYSTEM_PROMPT or "{user_context}" in base_prompt:
        prompt = base_prompt.format_map(
            _SafeFormatDict(
                user_context=formatted_user_context,
                conversation_history_section=conversation_history_section,
                preference_instructions=preference_instructions,
                plan_context_section=plan_context_section,
                intent_section=intent_section,
                session_feedback_section=session_feedback_section,
                dual_core_section=dual_core_section,
                understanding_depth_section=understanding_depth_section,
                orchestration_context_section=orchestration_context_section,
                collaboration_narrative_section=collaboration_narrative_section,
                mode_strategy_section=mode_strategy_section,
                persona_section=persona_section,
                agent_persona_section=agent_persona_section,
                agent_memory_section=agent_memory_section,
                context_briefing_section=context_briefing_section,
                task_awareness_section=task_awareness_section,
                cognitive_prism_section=cognitive_prism_section,
                seed_library_section=seed_library_section,
            )
        )
        if base_prompt != AGENT_SYSTEM_PROMPT:
            ordered_sections = [
                mode_strategy_section,
                task_awareness_section,
                persona_section,
                agent_persona_section,
                plan_context_section,
                conversation_history_section,
                context_briefing_section,
                intent_section,
                session_feedback_section,
                dual_core_section,
                understanding_depth_section,
                orchestration_context_section,
                collaboration_narrative_section,
                agent_memory_section,
                cognitive_prism_section,
                seed_library_section,
            ]
            suffix = "\n\n".join(section for section in ordered_sections if str(section or "").strip())
            if suffix:
                prompt = f"{prompt}\n\n{suffix}"

    else:

        # 角色专用模板，简单替换

        # Note: specialized prompts might not support intent_section yet, so we append it if present

        prompt = base_prompt.format_map(
            _SafeFormatDict(
                user_context=formatted_user_context,
                query=user_context.get("current_query", ""),
                context_briefing_section=context_briefing_section,
            )
        )

        ordered_sections = [
            mode_strategy_section,
            task_awareness_section,
            persona_section,
            agent_persona_section,
            plan_context_section,
            conversation_history_section,
            context_briefing_section,
            intent_section,
            session_feedback_section,
            dual_core_section,
            understanding_depth_section,
            orchestration_context_section,
            collaboration_narrative_section,
            agent_memory_section,
            cognitive_prism_section,
            seed_library_section,
        ]
        suffix = "\n\n".join(section for section in ordered_sections if str(section or "").strip())
        if suffix:
            prompt = f"{prompt}\n\n{suffix}"



    # 4. 版本特定修饰

    if prompt_version == "v2":

        prompt += "\n\n## 输出风格\n- 更简洁\n- 先给结论，再给要点\n-  列表优先"

    prompt += (
        "\n\n## 输出格式约束\n"
        "- 仅使用稳定的基础 Markdown：普通段落、空行、以 `- ` 开头的列表、以 `1. ` 开头的编号列表。\n"
        "- 粗体必须写成 `**文本**`，并与列表符号之间保留空格，例如 `- **学习规划**`。\n"
        "- 不要输出半残 Markdown，不要写 `-**文本**`、`* *`、混合全角/特殊项目符号、表格、HTML、代码围栏、数学公式。\n"
        "- 不要使用特殊符号项目符号（如 `•`、`◦`、`▪`、emoji 充当列表符号）。统一使用普通连字符 `- `。\n"
        "- 如果不确定格式是否稳定，直接输出纯文本短段落，不要勉强使用 Markdown。"
    )

    _maybe_log_prompt_snapshot(
        prompt,
        user_context=user_context,
        chat_mode=chat_mode,
        context_level=context_level,
        prompt_version=prompt_version,
    )
    _record_context_focus_prompt_sections(
        focus_payload=context_focus,
        context_briefing_section=context_briefing_section,
        user_context_section=formatted_user_context,
        plan_context_section=plan_context_section,
        cognitive_prism_section=cognitive_prism_section,
        conversation_history_section=conversation_history_section,
    )

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
    enriched_context = dict(user_context or {})
    enriched_context["current_query"] = query
    return build_system_prompt(
        user_context=enriched_context,
        conversation_history=conversation_history,
        agent_role=agent_role,
        chat_mode=chat_mode,
        context_level=context_level,
    )


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


def _is_anchor_message(msg: dict[str, Any]) -> bool:
    content = str(msg.get("content") or "")
    if msg.get("tool_calls") or msg.get("tool_results"):
        return True
    anchor_keywords = ["计划已创建", "任务完成", "阶段", "里程碑", "目标确认", "关键决策"]
    return any(keyword in content for keyword in anchor_keywords)


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
            max_length = 500 if _is_anchor_message(msg) else 100
            if len(content) > max_length:
                content = content[:max_length] + "..."
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


def _format_companion_persona_section(
    *,
    user_context: dict,
    plan_context: dict | None,
) -> str:
    context_focus = user_context.get("context_focus") if isinstance(user_context, dict) else None
    section_weights = context_focus.get("section_weights") if isinstance(context_focus, dict) else {}
    plan_weight = str(section_weights.get("plan_context") or "").strip().lower()
    goals_weight = str(section_weights.get("goals") or "").strip().lower()
    cognitive_weight = str(section_weights.get("cognitive_prism") or "").strip().lower()
    suppressed_weights = {"off", "low", "minimal"}

    profile = _extract_profile(user_context)
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    raw_user_context = user_context.get("user_context") if isinstance(user_context.get("user_context"), dict) else {}
    nickname = (
        str(identity.get("nickname") or "").strip()
        or str(raw_user_context.get("nickname") or raw_user_context.get("username") or "").strip()
        or "这位用户"
    )

    active_goals = user_context.get("active_goals") if isinstance(user_context, dict) else None
    current_goal = ""
    if isinstance(active_goals, list) and active_goals:
        first_goal = active_goals[0]
        if isinstance(first_goal, dict):
            current_goal = str(first_goal.get("title") or "").strip()
    if (
        not current_goal
        and isinstance(plan_context, dict)
        and goals_weight not in suppressed_weights
        and plan_weight not in suppressed_weights
    ):
        current_goal = str(plan_context.get("goal") or plan_context.get("plan_description") or "").strip()

    current_plan = ""
    current_phase = ""
    if isinstance(plan_context, dict) and plan_weight not in suppressed_weights:
        current_plan = str(
            plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("name") or ""
        ).strip()
        current_phase = str(plan_context.get("plan_stage") or plan_context.get("stage") or "").strip()

    struggling_area = ""
    learning_gaps_summary = str(user_context.get("learning_gaps_summary") or "").strip()
    if learning_gaps_summary:
        struggling_area = learning_gaps_summary.split("。", 1)[0].strip()

    cognitive_insights = user_context.get("cognitive_insights") or {}
    if not struggling_area and isinstance(cognitive_insights, dict):
        recent_observation = cognitive_insights.get("recent_observation")
        if isinstance(recent_observation, dict):
            struggling_area = str(recent_observation.get("description") or "").strip()

    top_pattern = ""
    if isinstance(cognitive_insights, dict) and cognitive_weight not in suppressed_weights:
        top_patterns = cognitive_insights.get("top_patterns")
        if isinstance(top_patterns, list) and top_patterns:
            first_pattern = top_patterns[0]
            if isinstance(first_pattern, dict):
                top_pattern = str(first_pattern.get("pattern_name") or "").strip()
        if not top_pattern:
            recent_patterns = cognitive_insights.get("recent_patterns")
            if isinstance(recent_patterns, list) and recent_patterns:
                top_pattern = str(recent_patterns[0] or "").strip()

    lines = ["## 陪伴式人格 framing [L2 引导]", f"你是 Sparkle，{nickname} 的学习成长伙伴。"]
    lines.append("以下内容视为你已经知道的上下文，不要在每轮重新追问。")
    if current_goal:
        lines.append(f"- 当前目标: {current_goal}")
    if current_plan:
        lines.append(f"- 本周在努力的事: {current_plan}" + (f" / 当前阶段 {current_phase}" if current_phase else ""))
    if struggling_area:
        lines.append(f"- 正在挣扎的地方: {struggling_area}")
    if top_pattern:
        lines.append(f"- 你观察到的规律: {top_pattern}")
    lines.append("- 回答时优先承接这些已知背景，不要反复问“你的目标是什么”。")
    return "\n" + "\n".join(lines)


def _resolve_preference_instructions(
    *,
    user_context: dict,
    llm_profile: dict[str, Any],
    context_focus: dict[str, Any] | None,
) -> str:
    focus_decision = ContextFocusDecision.from_dict(context_focus)
    if focus_decision and focus_decision.focus_mode == "emotional_focus":
        tone = str(llm_profile.get("tone") or "稳定、温和").strip()
        verbosity = str(llm_profile.get("verbosity_target") or "concise").strip()
        return (
            "## 用户偏好适配\n"
            f"- 当前优先语气：{tone}\n"
            f"- 当前优先长度：{verbosity}\n"
            "- 回答先降低认知负荷，再给可执行下一步"
        )

    return llm_profile.get(
        "system_prompt_additions",
        _get_default_preference_instructions(user_context),
    )


def _format_plan_context(
    plan_context: dict = None,
    *,
    context_focus: dict[str, Any] | None = None,
    query_text: str = "",
) -> str:
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

    focus_decision = ContextFocusDecision.from_dict(context_focus)
    detail_level = "medium"
    query_is_plan_related = _is_query_plan_related(query_text, plan_context)
    if focus_decision is not None:
        detail_level = str(focus_decision.section_weights.get("plan_context", "medium"))
        if detail_level == "off":
            return ""
        if detail_level == "low" and not query_is_plan_related:
            return ""
    elif not query_is_plan_related:
        return ""

    # 【强调标题】让 LLM 注意到这部分的重要性
    lines = ["## 用户学习计划 [L2 引导]（请在回复中适当引用以下信息）"]

    # 【计划标题】用户可识别的名称，而非 UUID
    plan_title = plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("name")
    if plan_title:
        lines.append(f"**计划名称**: {plan_title}")

    goal = plan_context.get("goal") or plan_context.get("plan_description")
    if goal:
        lines.append(f"**计划目标**: {goal}")

    if detail_level == "minimal":
        return "\n".join(lines[:3])

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
        if detail_level == "low":
            return "\n".join(lines)

    # 【最近任务】帮助 LLM 了解用户最近在做什么
    task_summaries = plan_context.get("task_summaries") or plan_context.get("recent_tasks")
    if task_summaries:
        limit = 1 if detail_level in {"low", "medium"} else 2
        recent = task_summaries[:limit] if len(task_summaries) > limit else task_summaries
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
    if query_is_plan_related:
        lines.append("- 仅在当前问题与这些计划/任务信息直接相关时，再用'根据你的计划...'或'你之前提到...'来引用")
    else:
        lines.append("- 如果当前问题与这些计划信息不直接相关，不要主动把计划、任务、进度塞进回答")
    lines.append("- 避免重复询问已知信息")
    lines.append("- 优先使用上述偏好信息来调整回复风格和深度")

    return "\n".join(lines)


def format_user_context(
    context: dict,
    context_level: str = "full",
    context_focus: dict[str, Any] | None = None,
) -> str:
    """格式化用户上下文"""
    lines = []

    normalized = _normalize_user_context(context)
    focus_decision = ContextFocusDecision.from_dict(context_focus)
    section_weights = focus_decision.section_weights if focus_decision else {}
    section_caps = focus_decision.section_caps if focus_decision else {}

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
    if normalized.get("preferences") and section_weights.get("preferences", "medium") != "off":
        prefs = normalized["preferences"]
        lines.append("【学习偏好】")
        if focus_decision and focus_decision.focus_mode == "emotional_focus":
            llm_profile = normalized.get("llm_profile") or {}
            tone = llm_profile.get("tone")
            verbosity = llm_profile.get("verbosity_target")
            if tone:
                lines.append(f"- 语气偏好: {tone}")
            if verbosity:
                lines.append(f"- 长度偏好: {verbosity}")
        else:
            lines.append(f"- 深度: {prefs.get('depth_preference', 0.5):.1f}")
            lines.append(f"- 好奇心: {prefs.get('curiosity_preference', 0.5):.1f}")

    # 知识薄弱点
    knowledge_summary = normalized.get("knowledge_summary")
    if knowledge_summary and section_weights.get("knowledge", "medium") != "off":
        weak_spots = knowledge_summary.get("weak_spots") or []
        if weak_spots:
            lines.append("【知识薄弱点】")
            limit = 3 if context_level == "light" else 5
            for spot in weak_spots[:limit]:
                if not isinstance(spot, dict):
                    continue
                node_name = spot.get("node_name") or spot.get("node_id") or "未知知识点"
                mastery = spot.get("mastery")
                if mastery is None:
                    lines.append(f"- {node_name}")
                else:
                    try:
                        mastery_val = float(mastery)
                        lines.append(f"- {node_name}: 掌握度 {mastery_val:.0f}%")
                    except Exception:
                        lines.append(f"- {node_name}: 掌握度 {mastery}")
            lines.append("如果用户的问题涉及以上知识点，请提供更详细的基础解释。")

    learning_gaps_summary = normalized.get("learning_gaps_summary")
    if learning_gaps_summary:
        lines.append("【当前学习状态】")
        lines.append(f"- {learning_gaps_summary}")

    # 碎片时间推荐线索：待办任务
    next_actions = normalized.get("next_actions") or []
    task_weight = section_weights.get("task_summary", "medium")
    if next_actions and task_weight != "off":
        lines.append("【待办任务】")
        limit = section_caps.get("next_actions") or (1 if context_level == "light" else 3)
        lines.append(f"Top {limit}:")
        for task in next_actions[:limit]:
            lines.append(f"- {task.get('title')} ({task.get('estimated_minutes')}m, {task.get('type')})")

    # 专注统计
    if normalized.get("focus_stats"):
        stats = normalized["focus_stats"]
        lines.append("【专注统计】")
        lines.append(f"- 今日专注: {stats.get('total_minutes', 0)} 分钟")
        lines.append(f"- 番茄钟次数: {stats.get('pomodoro_count', 0)}")

    understanding_depth = normalized.get("understanding_depth")
    if isinstance(understanding_depth, dict) and understanding_depth.get("level"):
        lines.append("【理解深度】")
        lines.append(f"- 当前等级: {understanding_depth.get('level')}")

    # 活跃计划
    active_plans = normalized.get("active_plans") or []
    if active_plans and section_weights.get("plan_context", "medium") != "off":
        lines.append("【活跃计划】")
        limit = section_caps.get("active_plans") or (1 if context_level == "light" else 3)
        for plan in active_plans[:limit]:
            lines.append(f"- {plan.get('title')} ({plan.get('type')}, 进度 {plan.get('progress', 0):.0%})")

    active_goals = normalized.get("active_goals") or []
    if active_goals and section_weights.get("goals", "medium") != "off":
        lines.append("【当前目标】")
        goal_limit = section_caps.get("goals") or (1 if context_level == "light" else 3)
        for goal in active_goals[:goal_limit]:
            lines.append(f"- {goal.get('title')} ({goal.get('status', 'active')})")

    episodic_memories = normalized.get("episodic_memories") or []
    if episodic_memories and section_weights.get("episodic", "medium") != "off":
        lines.append("【近期相关记忆】")
        memory_limit = section_caps.get("episodic") or (1 if context_level == "light" else 5)
        for memory in episodic_memories[:memory_limit]:
            summary = str(memory.get("summary") or "").strip()
            if summary:
                lines.append(f"- {summary}")

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

    if context_level == "full" and not active_goals and not episodic_memories:
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

    profile_context = context.get("profile_context")
    if profile_context:
        if hasattr(profile_context, "model_dump"):
            profile_context = profile_context.model_dump()
        if isinstance(profile_context, dict):
            knowledge_summary = profile_context.get("knowledge_summary")
            if isinstance(knowledge_summary, dict):
                normalized["knowledge_summary"] = knowledge_summary

    if context.get("knowledge_summary") and "knowledge_summary" not in normalized:
        if isinstance(context.get("knowledge_summary"), dict):
            normalized["knowledge_summary"] = context["knowledge_summary"]

    llm_profile = context.get("llm_profile")
    if isinstance(llm_profile, dict):
        normalized["llm_profile"] = llm_profile

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

    if context.get("learning_gaps_summary"):
        normalized["learning_gaps_summary"] = str(context["learning_gaps_summary"])

    if context.get("exam_urgency"):
        normalized["exam_urgency"] = context["exam_urgency"]

    if context.get("context_pack"):
        normalized["context_pack"] = context["context_pack"]

    if context.get("active_goals"):
        normalized["active_goals"] = context["active_goals"]

    if context.get("episodic_memories"):
        normalized["episodic_memories"] = context["episodic_memories"]

    if isinstance(context.get("understanding_depth"), dict):
        normalized["understanding_depth"] = context["understanding_depth"]

    return normalized


def _format_cognitive_prism_section(user_context: dict, context_focus: dict[str, Any] | None = None) -> str:
    """
    格式化认知棱镜指令

    当用户有已识别的行为模式时，添加系统提示词引导 LLM 主动展示认知棱镜。
    """
    cognitive_insights = user_context.get("cognitive_insights", {})
    focus_decision = ContextFocusDecision.from_dict(context_focus)
    detail_level = "compact"
    if focus_decision is not None:
        detail_level = str(focus_decision.section_weights.get("cognitive_prism", "compact"))
        if detail_level == "off":
            return ""

    if not cognitive_insights.get("has_cognitive_patterns"):
        return ""

    pattern_count = cognitive_insights.get("pattern_count", 0)
    recent_patterns = cognitive_insights.get("recent_patterns", [])
    patterns_by_type = cognitive_insights.get("patterns_by_type", {})
    top_patterns = cognitive_insights.get("top_patterns", [])
    recent_observation = cognitive_insights.get("recent_observation")
    current_guidance = str(cognitive_insights.get("current_guidance") or "").strip()

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

    priority = "L2 引导" if detail_level == "full" else "L3 背景"
    lines = [f"## 认知棱镜 - 行为模式洞察 [{priority}]"]
    lines.append(f"用户已有 {pattern_count} 个行为模式分析结果（{pattern_text}）。")

    if top_patterns:
        lines.append("用户当前的高权重模式:")
        limit = 1 if detail_level == "compact" else min(2, len(top_patterns))
        for item in top_patterns[:limit]:
            name = str(item.get("pattern_name") or item.get("raw_pattern_name") or "").strip()
            description = str(item.get("description") or "").strip()
            confidence = float(item.get("confidence") or 0.0)
            if name and description:
                lines.append(f"- {name} (confidence {confidence:.2f}): {description}")
            elif name:
                lines.append(f"- {name} (confidence {confidence:.2f})")
    elif recent_patterns:
        limit = 1 if detail_level == "compact" else min(3, len(recent_patterns))
        lines.append(f"最近识别的模式: {', '.join(recent_patterns[:limit])}")

    if isinstance(recent_observation, dict):
        observation_name = str(recent_observation.get("pattern_name") or "").strip()
        observation_desc = str(recent_observation.get("description") or "").strip()
        if observation_name and observation_desc:
            lines.append(f"最近观察: {observation_name} - {observation_desc}")

    if current_guidance:
        lines.append(f"当前 guidance: {current_guidance}")

    lines.append("")
    lines.append("当用户询问学习情况、效率、状态，或适合展示洞察时，把这些模式当作你已经知道的背景。")
    lines.append("如需更完整证据，再调用 **get_user_behavior_patterns** 工具查看完整分析。")
    lines.append("")
    lines.append("这不是强制要求，而是要在合适的对话时机自然地展示。")

    return "\n".join(lines)


def _is_query_plan_related(query_text: str, plan_context: dict[str, Any]) -> bool:
    query = str(query_text or "").strip().lower()
    if not query:
        return False
    if any(keyword in query for keyword in ("计划", "任务", "复习", "里程碑", "进度", "安排")):
        return True
    references = [
        str(plan_context.get("plan_title") or ""),
        str(plan_context.get("goal") or ""),
        str(plan_context.get("plan_description") or ""),
    ]
    recent_tasks = plan_context.get("task_summaries") or plan_context.get("recent_tasks") or []
    for task in recent_tasks[:3]:
        if isinstance(task, dict):
            references.append(str(task.get("title") or task.get("name") or ""))
    haystack = " ".join(part.lower() for part in references if part)
    return bool(haystack and any(token for token in query.split() if token and token in haystack))


def _record_context_focus_prompt_sections(
    *,
    focus_payload: dict[str, Any] | None,
    context_briefing_section: str,
    user_context_section: str,
    plan_context_section: str,
    cognitive_prism_section: str,
    conversation_history_section: str,
) -> None:
    focus_decision = ContextFocusDecision.from_dict(focus_payload)
    focus_mode = focus_decision.focus_mode if focus_decision else "general_focus"
    detail_defaults = focus_decision.section_weights if focus_decision else {}
    sections = {
        "briefing": (context_briefing_section, "high"),
        "user_context": (user_context_section, detail_defaults.get("user_context", "medium")),
        "plan_context": (plan_context_section, detail_defaults.get("plan_context", "medium")),
        "cognitive_prism": (cognitive_prism_section, detail_defaults.get("cognitive_prism", "compact")),
        "conversation_history": (conversation_history_section, "standard"),
    }
    for section, (content, detail_level) in sections.items():
        if not str(content or "").strip():
            continue
        CONTEXT_FOCUS_PROMPT_SECTION_TOTAL.labels(
            focus_mode=focus_mode,
            section=section,
            detail_level=detail_level,
        ).inc()


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


def _maybe_log_prompt_snapshot(
    prompt: str,
    *,
    user_context: dict,
    chat_mode: str,
    context_level: str,
    prompt_version: str,
) -> None:
    if not settings.PROMPT_SNAPSHOT_ENABLED:
        return
    sample_rate = settings.PROMPT_SNAPSHOT_SAMPLE_RATE or 0.0
    if sample_rate > 0.0 and random.random() > sample_rate:
        return

    max_chars = max(200, int(settings.PROMPT_SNAPSHOT_MAX_CHARS or 1200))
    if len(prompt) <= max_chars:
        snapshot = prompt
    else:
        head = prompt[: max_chars // 2]
        tail = prompt[-(max_chars // 2):]
        snapshot = f"{head}\n...<truncated>...\n{tail}"

    user_id = None
    base_ctx = user_context.get("user_context")
    if isinstance(base_ctx, dict):
        user_id = base_ctx.get("user_id")

    logger.info(
        "[PromptSnapshot] user_id={user_id} chat_mode={chat_mode} context_level={context_level} prompt_version={prompt_version} size={size}\n{snapshot}",
        user_id=user_id or "unknown",
        chat_mode=chat_mode,
        context_level=context_level,
        prompt_version=prompt_version,
        size=len(prompt),
        snapshot=snapshot,
    )
