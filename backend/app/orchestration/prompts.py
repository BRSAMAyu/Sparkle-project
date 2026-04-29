"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

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

from datetime import datetime, timezone
from typing import Any
import json
import math
import random
import re

from loguru import logger

from app.core.agent_persona import build_agent_persona_prompt_section
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.core.business_metrics import CONTEXT_FOCUS_PROMPT_SECTION_TOTAL
from app.core.i18n import I18n
from app.core.kill_switch import normalize_mode
from app.core.metrics import SPARKLE_PROMPT_FIELD_RENDER_COVERAGE_RATIO
from app.core.plan_context import merge_plan_context
from app.config import settings
from app.core.user_insight_state import UserInsightState
from app.orchestration.ai_strategy_renderer import build_semantic_control, format_semantic_control_lines
from app.orchestration.context_focus import ContextFocusDecision
from app.orchestration.social_context_renderer import render_social_context_lines
from app.orchestration.situation_brief import format_situation_brief_section
from app.services.srl_phase_types import SRLPhaseHint


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        logger.warning("Prompt template missing placeholder value: {}", key)
        return f"{{missing:{key}}}"


PROMPT_SECTION_SOFT_LIMIT_TOKENS = 4000
CONVERSATION_MEMORY_MIN_MESSAGE_COUNT = 4
CONVERSATION_MEMORY_RECENT_MESSAGE_LIMIT = 6
CONVERSATION_MEMORY_ITEM_LIMIT = 2

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
    "situation_brief_section": (140, 0.12),
    "decision_policy_section": (110, 0.08),
    "user_material_grounding_section": (120, 0.08),
    "intervention_language_contract_section": (90, 0.06),
    "scaffolding_state_section": (90, 0.06),
    "galaxy_snapshot_section": (120, 0.07),
    "context_briefing_section": (80, 0.05),
    "intent_section": (100, 0.08),
    "session_feedback_section": (60, 0.05),
    "visible_intelligence_section": (120, 0.10),
    "dual_core_section": (80, 0.05),
    "mode_strategy_section": (120, 0.10),
    "plan_context_section": (200, 0.10),
    "user_context": (350, 0.18),
    "conversation_history_section": (80, 0.16),
    "task_awareness_section": (60, 0.08),
    "cognitive_prism_section": (120, 0.05),
    "preference_instructions": (60, 0.05),
    "persona_section": (40, 0.04),
    "companion_persona_section": (180, 0.16),
    "constitution_guardrail_section": (60, 0.04),
    "agent_persona_section": (40, 0.04),
    "agent_memory_section": (40, 0.03),
    "understanding_depth_section": (60, 0.05),
    "orchestration_context_section": (60, 0.05),
    "collaboration_narrative_section": (60, 0.05),
    "seed_library_section": (40, 0.04),
}

_PROMPT_UTILIZATION_SECTION_ALIASES: dict[str, str] = {
    "situation_brief_section": "situation_brief",
    "decision_policy_section": "decision_policy",
    "planning_strategy_section": "planning_strategy",
    "user_material_grounding_section": "user_material_grounding",
    "intervention_language_contract_section": "intervention_language_contract",
    "visible_intelligence_section": "visible_intelligence",
    "plan_context_section": "plan_context",
    "intent_section": "intent",
    "session_feedback_section": "session_feedback",
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


def _coalesce_mapping_value(source: dict[str, Any], key: str, default: Any) -> Any:
    value = source.get(key)
    return default if value is None else value


def _format_aurora_planning_sidecar_section(
    *,
    sidecar_payload: dict[str, Any] | None,
    legacy_prompt: str = "",
) -> str:
    payload = dict(sidecar_payload or {})
    if not payload:
        prompt = str(legacy_prompt or "").strip()
        return "\n## AURORA PLANNING SIDECAR [L2 引导]\n" + prompt if prompt else ""

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        decision = {}
    scaffold = payload.get("scaffold")
    if not isinstance(scaffold, dict):
        scaffold = {}
    directive = decision.get("chat_directive")
    if not isinstance(directive, dict):
        directive = {}
    top_tension = scaffold.get("top_tension")
    if not isinstance(top_tension, dict):
        top_tension = {}
    top_thread = scaffold.get("top_latent_thread")
    if not isinstance(top_thread, dict):
        top_thread = {}

    action = str(decision.get("action") or "wait").strip() or "wait"
    lines = [
        "## AURORA PLANNING SIDECAR [L2 引导]",
        "这是 Aurora decision loop 给主聊天链的意图级指令，不是可直接复述给用户的话术。",
        f"Aurora action: {action}",
    ]

    if action == "soft_return_topic":
        lines.append("先处理用户当前需求；如果收口自然，再用一句短桥接带回规划，不要生硬切题。")
    elif action == "drop_thread":
        lines.append("把先前那条规划追问放下，本轮不要带回，也不要补问刚才那块信息。")
    else:
        lines.append("本轮先处理当前需求，不要主动把话题拉回规划；只在用户自己回到规划时继续。")

    intent = str(directive.get("intent") or "").strip()
    if intent:
        lines.append(f"Directive intent: {intent}")
    brief = str(directive.get("brief") or "").strip()
    if brief:
        lines.append(f"Directive brief: {brief}")

    goal_raw = str(scaffold.get("goal_raw") or "").strip()
    if goal_raw:
        lines.append(f"Planning goal: {goal_raw}")

    if action != "drop_thread" and top_tension:
        domain = str(top_tension.get("domain") or "").strip()
        description = str(top_tension.get("description") or "").strip()
        if domain and description:
            lines.append(f"Only unresolved tension worth tracking now: {domain} - {description}")

    if action == "soft_return_topic":
        context_snapshot = str(top_thread.get("context_snapshot") or "").strip()
        if context_snapshot:
            lines.append(f"Latent thread to recover naturally: {context_snapshot}")

    resolved_facts = [str(item).strip() for item in list(scaffold.get("resolved_facts") or []) if str(item).strip()]
    if resolved_facts:
        lines.append("Already resolved facts: " + "；".join(resolved_facts[:3]))

    lines.append("不要把已经补齐的信息重新问一遍。")
    return "\n" + "\n".join(lines)


def _describe_warmth_level(value: float) -> str:
    if value <= 0.2:
        return I18n.t("prompts.companion.warmth_restrained", locale="zh")
    if value <= 0.45:
        return I18n.t("prompts.companion.warmth_stable", locale="zh")
    if value <= 0.7:
        return I18n.t("prompts.companion.warmth_warm", locale="zh")
    return I18n.t("prompts.companion.warmth_proactive", locale="zh")


def _describe_candor_level(value: float) -> str:
    if value <= 0.2:
        return I18n.t("prompts.companion.candor_gentle", locale="zh")
    if value <= 0.45:
        return I18n.t("prompts.companion.candor_soft", locale="zh")
    if value <= 0.75:
        return I18n.t("prompts.companion.candor_direct", locale="zh")
    return I18n.t("prompts.companion.candor_blunt", locale="zh")


def _describe_relationship_stage(stage: str) -> str:
    return {
        "early": I18n.t("prompts.companion.relationship_early", locale="zh"),
        "building": I18n.t("prompts.companion.relationship_building", locale="zh"),
        "trusted": I18n.t("prompts.companion.relationship_trusted", locale="zh"),
        "deepening": I18n.t("prompts.companion.relationship_deepening", locale="zh"),
    }.get(stage, I18n.t("prompts.companion.relationship_default", locale="zh"))


def _describe_challenge_style(style: str) -> str:
    return {
        "gentle": I18n.t("prompts.companion.challenge_gentle", locale="zh"),
        "balanced": I18n.t("prompts.companion.challenge_balanced", locale="zh"),
        "firm": I18n.t("prompts.companion.challenge_firm", locale="zh"),
    }.get(style, I18n.t("prompts.companion.challenge_default", locale="zh"))


def _describe_truth_style(style: str) -> str:
    return {
        "honest_warm": I18n.t("prompts.companion.truth_honest_warm", locale="zh"),
        "direct_structured": I18n.t("prompts.companion.truth_direct_structured", locale="zh"),
        "gentle_reflective": I18n.t("prompts.companion.truth_gentle_reflective", locale="zh"),
    }.get(style, I18n.t("prompts.companion.truth_default", locale="zh"))


def _format_intervention_language_contract_section(
    *,
    user_context: dict[str, Any],
    prompt_signal_telemetry: dict[str, Any] | None = None,
) -> str:
    if not isinstance(user_context, dict):
        return ""

    learning_state_fragment = user_context.get("learning_state_fragment")
    if not isinstance(learning_state_fragment, dict):
        situation_brief = user_context.get("situation_brief")
        if isinstance(situation_brief, dict):
            learning_state_fragment = situation_brief.get("learning_state_fragment")

    pain_visible = False
    win_visible = False
    if isinstance(prompt_signal_telemetry, dict):
        high_value_fields = prompt_signal_telemetry.get("high_value_fields") or {}
        if isinstance(high_value_fields, dict):
            pain_visible = bool(
                high_value_fields.get("error_summary", {}).get("rendered")
                or high_value_fields.get("recent_errors", {}).get("rendered")
            )
            win_visible = bool(high_value_fields.get("recent_mastery_changes", {}).get("rendered"))

    has_fragment = isinstance(learning_state_fragment, dict) and bool(learning_state_fragment)
    if not (pain_visible or win_visible or has_fragment):
        return ""

    signal_note = ""
    if pain_visible and win_visible:
        signal_note = "信号：痛点+进展并存，先承接推进，再提一个最小下一步。"
    elif pain_visible:
        signal_note = "信号：痛点主导，先站到用户同侧，不先下失败判词。"
    elif win_visible:
        signal_note = "信号：进展主导，先肯定已有推进，再谈放大。"
    elif has_fragment:
        signal_note = "信号：读取到 learning_state_fragment，先承接痛点与进展，再决定下一步。"

    lines = [
        "## 干预语言契约 [L2 引导]",
        "适用：近期痛点 / 近期进展 / `learning_state_fragment`。",
        "关系：Sparkle 是朋友，不是教练、工具或队友；像 a friend helping me restart。",
    ]
    if signal_note:
        lines.append(signal_note)
    lines.extend(
        [
            "Anchor §3.3：不审判；不羞辱；不替用户做道德评价；不先说“你又失败了”；先站到用户同侧；优先好奇和重新启动，不造羞耻和焦虑。",
            "执行：先承接已有进展，再给最小可行改动。",
        ]
    )
    return "\n".join(lines)


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
    total_tokens = sum(
        _estimate_prompt_tokens(content) for content in section_map.values() if str(content or "").strip()
    )
    if total_tokens <= limit:
        return section_map

    adjusted = dict(section_map)

    def _recount() -> int:
        return sum(_estimate_prompt_tokens(item) for item in adjusted.values() if str(item or "").strip())

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
            name
            for name in adjusted.keys()
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

成长自省工具：
14. get_situation_brief - 当你需要当前局面的高密度摘要，而不是靠长上下文猜测时，优先调用
15. get_user_strategy_state - 当你需要确认当前节奏、讲解方式、支持力度时，优先调用
16. adjust_user_strategy_state - 当用户明确要求换一种节奏、难度、解释方式或支持方式时，调用记录
17. retrieve_user_material - 当回答应优先依赖用户上传材料时，优先调用
18. get_intervention_track_record - 当你要判断哪些提示/干预对这个用户更有效时，优先调用
19. record_intervention_feedback - 当用户直接评价某次提醒/推动有没有帮助时，调用绑定反馈
20. write_episode_note - 当用户说明短期情境变化（如考试周、高压、降载）时，调用写入回合备注
21. get_profile_front_door - 当用户问“你怎么看我 / 你现在是怎么理解我的 / 我最近是什么状态”时，先调用，基于 canonical 画像回答，并明确哪些是编译结论、哪些是预测
22. apply_profile_correction - 当用户明确说“这条不对 / 以前对但现在不对 / 只在考试模式成立”并且 target_id 已明确时，调用这条用户纠正通道；不要改用 Aurora、dual-core 或 strategy lane

**重要提示**：在生成新任务前，务必先调用 get_plan_state 获取：
- 当前进度和已达成里程碑
- 任务完成统计
- 自适应调整参数（difficulty_shift, time_multiplier）
当你需要精确的成长状态、用户材料证据、干预记录或用户画像前门时，优先使用以上成长自省工具，不要只依赖 prompt 里的静态上下文。涉及聊天内画像纠正时，先识别 target_id，再走 apply_profile_correction，不要把用户纠正偷换成策略调节。
"""

AGENT_SYSTEM_PROMPT = """你是 Sparkle（星火），一个智能学习助手。你的目标是帮助用户高效学习，同时保持学习的乐趣。

{mode_strategy_section}

{task_awareness_section}

{persona_section}

{companion_persona_section}

{constitution_guardrail_section}

{agent_persona_section}

{situation_brief_section}

{decision_policy_section}

{intervention_language_contract_section}

{user_material_grounding_section}

## 当前用户上下文

{user_context}

{plan_context_section}

{preference_instructions}

{capsule_preference_section}

{spine_model_claims_section}

{spine_community_skill_section}

## 对话历史

{conversation_history_section}

{context_briefing_section}

{visible_intelligence_section}

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

{situation_brief_section}



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

{situation_brief_section}



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

{situation_brief_section}



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
    spine_response_directive: dict | None = None,  # Signal-to-Action Spine ResponseDirective
    spine_chronicle_summary: str | None = None,  # Growth chronicle narrative
    spine_fatigue_context: dict | None = None,  # Fatigue/crisis state for tone modulation
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
    aurora_planning_sidecar = {}
    aurora_planning_sidecar_prompt = ""
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
        raw_sidecar = user_context.get("aurora_planning_sidecar")
        if isinstance(raw_sidecar, dict):
            aurora_planning_sidecar = raw_sidecar
        aurora_planning_sidecar_prompt = str(user_context.get("aurora_planning_sidecar_prompt") or "").strip()

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

    formatted_user_context, prompt_signal_telemetry = _render_user_context_content(
        user_context,
        context_level=context_level,
        context_focus=context_focus,
    )
    past_session_memory_section = _format_past_session_memory_section(user_context)
    capsule_preference_section = _format_capsule_preference_section(user_context)
    spine_model_claims_section = _format_spine_model_claims_section(user_context)
    spine_community_skill_section = _format_spine_community_skill_section(user_context)

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

    conversation_memory_section = build_conversation_memory_fragment(conversation_history)
    raw_conversation_history_section = _format_conversation_history(conversation_history)
    conversation_history_section = "\n\n".join(
        section for section in (conversation_memory_section, raw_conversation_history_section) if section
    )

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
    constitution_guardrail_section = _format_constitution_guardrail_section(user_context=user_context)
    visible_intelligence_section = _format_visible_intelligence_section(user_context=user_context)
    decision_policy_section = _format_decision_policy_section(user_context=user_context)
    planning_strategy_section = _format_planning_strategy_section(user_context=user_context)
    user_material_grounding_section = _format_user_material_grounding_section(user_context=user_context)
    process_scaffolding_section = _format_process_scaffolding_section(user_context=user_context)
    scaffolding_state_section = _format_scaffolding_state_section(user_context=user_context)
    galaxy_snapshot_section = _format_galaxy_snapshot_section(user_context=user_context)
    idiographic_section = _format_idiographic_section(user_context=user_context)
    intervention_language_contract_section = _format_intervention_language_contract_section(
        user_context=user_context,
        prompt_signal_telemetry=prompt_signal_telemetry,
    )

    agent_memory_section = ""
    if agent_memory_context:
        agent_memory_section = "\n## 专家交互记忆 [L2 引导]\n" + agent_memory_context

    aurora_planning_sidecar_section = _format_aurora_planning_sidecar_section(
        sidecar_payload=aurora_planning_sidecar,
        legacy_prompt=aurora_planning_sidecar_prompt,
    )

    situation_brief_section = ""
    if isinstance(user_context, dict):
        situation_brief_section = format_situation_brief_section(user_context.get("situation_brief"))

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
                    "以下是该学科/领域的高质量问答示例，请参考其风格和深度：\n" + "\n".join(example_lines)
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
        if companion_persona_section:
            companion_persona_section = _soften_section(
                companion_persona_section,
                reason="本轮以精简为主；保留陪伴 framing，但不要展开成长背景。",
            )
        if constitution_guardrail_section:
            constitution_guardrail_section = _soften_section(
                constitution_guardrail_section,
                reason="本轮以精简为主；只保留最短的宪法护栏提醒。",
            )
        if visible_intelligence_section:
            visible_intelligence_section = _soften_section(
                visible_intelligence_section,
                reason="本轮以精简为主；只保留最关键的一句已观察到的变化。",
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
    cognitive_priority = (
        2 if focus_decision and focus_decision.focus_mode in {"emotional_focus", "cognitive_focus"} else 3
    )
    section_map = {
        "situation_brief_section": situation_brief_section,
        "decision_policy_section": decision_policy_section,
        "planning_strategy_section": planning_strategy_section,
        "user_material_grounding_section": user_material_grounding_section,
        "process_scaffolding_section": process_scaffolding_section,
        "scaffolding_state_section": scaffolding_state_section,
        "galaxy_snapshot_section": galaxy_snapshot_section,
        "idiographic_section": idiographic_section,
        "intervention_language_contract_section": intervention_language_contract_section,
        "context_briefing_section": context_briefing_section,
        "visible_intelligence_section": visible_intelligence_section,
        "intent_section": intent_section,
        "session_feedback_section": session_feedback_section,
        "user_context": f"[优先级：L3 背景]\n{formatted_user_context}".strip(),
        "preference_instructions": f"[优先级：L3 背景]\n{preference_instructions}".strip(),
        "capsule_preference_section": capsule_preference_section,
        "plan_context_section": plan_context_section,
        "dual_core_section": dual_core_section,
        "understanding_depth_section": understanding_depth_section,
        "orchestration_context_section": orchestration_context_section,
        "collaboration_narrative_section": collaboration_narrative_section,
        "mode_strategy_section": mode_strategy_section,
        "persona_section": persona_section,
        "companion_persona_section": companion_persona_section,
        "constitution_guardrail_section": constitution_guardrail_section,
        "agent_persona_section": agent_persona_section,
        "agent_memory_section": agent_memory_section,
        "aurora_planning_sidecar_section": aurora_planning_sidecar_section,
        "cognitive_prism_section": cognitive_prism_section,
        "seed_library_section": seed_library_section,
        "conversation_history_section": (
            f"[优先级：L3 背景]\n{conversation_history_section}".strip() if conversation_history_section else ""
        ),
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
            logger.debug("Failed to resolve model tier for key=%s", model_key, exc_info=True)
    _prompt_budget = _TIER_PROMPT_BUDGET.get(_model_tier_str or "", PROMPT_SECTION_SOFT_LIMIT_TOKENS)

    pre_budget_section_map = dict(section_map)
    section_map = _apply_prompt_budget(
        section_map,
        priority_map={
            "situation_brief_section": 0,
            "decision_policy_section": 1,
            "planning_strategy_section": 1,
            "user_material_grounding_section": 1,
            "process_scaffolding_section": 1,
            "scaffolding_state_section": 1,
            "galaxy_snapshot_section": 2,
            "idiographic_section": 1,
            "intervention_language_contract_section": 1,
            "context_briefing_section": 0,
            "visible_intelligence_section": 1,
            "intent_section": 1,
            "session_feedback_section": 1,
            "user_context": 3,
            "preference_instructions": 3,
            "capsule_preference_section": 2,
            "plan_context_section": 2,
            "dual_core_section": 2,
            "understanding_depth_section": 2,
            "orchestration_context_section": 2,
            "collaboration_narrative_section": 2,
            "mode_strategy_section": 2,
            "persona_section": 2,
            "companion_persona_section": 1,
            "constitution_guardrail_section": 1,
            "agent_persona_section": 2,
            "agent_memory_section": 2,
            "aurora_planning_sidecar_section": 2,
            "cognitive_prism_section": cognitive_priority,
            "seed_library_section": 3,
            "conversation_history_section": 3,
            "task_awareness_section": 3,
        },
        budget_tokens=_prompt_budget,
    )
    situation_brief_section = section_map["situation_brief_section"]
    decision_policy_section = section_map["decision_policy_section"]
    planning_strategy_section = section_map["planning_strategy_section"]
    user_material_grounding_section = section_map["user_material_grounding_section"]
    process_scaffolding_section = section_map["process_scaffolding_section"]
    scaffolding_state_section = section_map["scaffolding_state_section"]
    galaxy_snapshot_section = section_map["galaxy_snapshot_section"]
    idiographic_section = section_map["idiographic_section"]
    intervention_language_contract_section = section_map["intervention_language_contract_section"]
    context_briefing_section = section_map["context_briefing_section"]
    visible_intelligence_section = section_map["visible_intelligence_section"]
    intent_section = section_map["intent_section"]
    session_feedback_section = section_map["session_feedback_section"]
    formatted_user_context = section_map["user_context"]
    preference_instructions = section_map["preference_instructions"]
    capsule_preference_section = section_map["capsule_preference_section"]
    plan_context_section = section_map["plan_context_section"]
    dual_core_section = section_map["dual_core_section"]
    understanding_depth_section = section_map["understanding_depth_section"]
    orchestration_context_section = section_map["orchestration_context_section"]
    collaboration_narrative_section = section_map["collaboration_narrative_section"]
    mode_strategy_section = section_map["mode_strategy_section"]
    persona_section = section_map["persona_section"]
    companion_persona_section = section_map["companion_persona_section"]
    constitution_guardrail_section = section_map["constitution_guardrail_section"]
    agent_persona_section = section_map["agent_persona_section"]
    agent_memory_section = section_map["agent_memory_section"]
    aurora_planning_sidecar_section = section_map["aurora_planning_sidecar_section"]
    cognitive_prism_section = section_map["cognitive_prism_section"]
    conversation_history_section = section_map["conversation_history_section"]
    task_awareness_section = section_map["task_awareness_section"]
    seed_library_section = section_map["seed_library_section"]
    embed_situation_brief_in_user_context = bool(
        situation_brief_section and base_prompt != AGENT_SYSTEM_PROMPT and "{user_context}" in base_prompt
    )
    rendered_user_context = formatted_user_context
    if embed_situation_brief_in_user_context:
        rendered_user_context = "\n\n".join(
            section for section in (situation_brief_section, formatted_user_context) if str(section or "").strip()
        )
    if isinstance(prompt_signal_telemetry, dict):
        visible_fields = [
            key for key, meta in prompt_signal_telemetry.get("high_value_fields", {}).items() if meta.get("rendered")
        ]
        prompt_signal_telemetry["prompt_visible_high_value_fields"] = visible_fields
        for key in prompt_signal_telemetry["tracked_fields"]:
            meta = prompt_signal_telemetry["high_value_fields"].get(key, {})
            meta["prompt_visible"] = key in visible_fields
        prompt_signal_telemetry["dropped_high_value_fields"] = [
            key
            for key, meta in prompt_signal_telemetry["high_value_fields"].items()
            if meta.get("collected") and not meta.get("prompt_visible")
        ]
        prompt_signal_telemetry["model_facing_section_sizes"] = {
            key: value for key, value in prompt_signal_telemetry.get("section_sizes", {}).items()
        }
        prompt_signal_telemetry["utilization"] = _build_prompt_utilization_snapshot(
            pre_budget_section_map=pre_budget_section_map,
            model_facing_section_map=section_map,
            prompt_signal_telemetry=prompt_signal_telemetry,
        )
        collected_count = sum(
            1 for meta in prompt_signal_telemetry["high_value_fields"].values() if meta.get("collected")
        )
        rendered_count = sum(
            1 for meta in prompt_signal_telemetry["high_value_fields"].values() if meta.get("rendered")
        )
        coverage_ratio = (rendered_count / collected_count) if collected_count else 1.0
        prompt_signal_telemetry["field_render_coverage_ratio"] = coverage_ratio
        SPARKLE_PROMPT_FIELD_RENDER_COVERAGE_RATIO.set(coverage_ratio)
        if isinstance(user_context, dict):
            user_context["prompt_signal_telemetry"] = prompt_signal_telemetry

    # 3. 如果是通用模板，进行完整渲染

    if base_prompt == AGENT_SYSTEM_PROMPT or "{user_context}" in base_prompt:
        prompt = base_prompt.format_map(
            _SafeFormatDict(
                user_context=rendered_user_context,
                conversation_history_section=conversation_history_section,
                preference_instructions=preference_instructions,
                capsule_preference_section=capsule_preference_section,
                plan_context_section=plan_context_section,
                intent_section=intent_section,
                session_feedback_section=session_feedback_section,
                visible_intelligence_section=visible_intelligence_section,
                dual_core_section=dual_core_section,
                understanding_depth_section=understanding_depth_section,
                orchestration_context_section=orchestration_context_section,
                collaboration_narrative_section=collaboration_narrative_section,
                mode_strategy_section=mode_strategy_section,
                persona_section=persona_section,
                companion_persona_section=companion_persona_section,
                constitution_guardrail_section=constitution_guardrail_section,
                agent_persona_section=agent_persona_section,
                agent_memory_section=agent_memory_section,
                aurora_planning_sidecar_section=aurora_planning_sidecar_section,
                situation_brief_section=situation_brief_section,
                decision_policy_section=decision_policy_section,
                planning_strategy_section=planning_strategy_section,
                user_material_grounding_section=user_material_grounding_section,
                process_scaffolding_section=process_scaffolding_section,
                scaffolding_state_section=scaffolding_state_section,
                galaxy_snapshot_section=galaxy_snapshot_section,
                idiographic_section=idiographic_section,
                intervention_language_contract_section=intervention_language_contract_section,
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
                companion_persona_section,
                constitution_guardrail_section,
                agent_persona_section,
                "" if embed_situation_brief_in_user_context else situation_brief_section,
                decision_policy_section,
                planning_strategy_section,
                user_material_grounding_section,
                process_scaffolding_section,
                scaffolding_state_section,
                galaxy_snapshot_section,
                idiographic_section,
                intervention_language_contract_section,
                capsule_preference_section,
                plan_context_section,
                conversation_history_section,
                context_briefing_section,
                visible_intelligence_section,
                intent_section,
                session_feedback_section,
                dual_core_section,
                understanding_depth_section,
                orchestration_context_section,
                collaboration_narrative_section,
                agent_memory_section,
                aurora_planning_sidecar_section,
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
                user_context=rendered_user_context,
                query=user_context.get("current_query", ""),
                context_briefing_section=context_briefing_section,
                visible_intelligence_section=visible_intelligence_section,
                companion_persona_section=companion_persona_section,
                constitution_guardrail_section=constitution_guardrail_section,
                situation_brief_section=situation_brief_section,
                decision_policy_section=decision_policy_section,
                planning_strategy_section=planning_strategy_section,
                user_material_grounding_section=user_material_grounding_section,
                process_scaffolding_section=process_scaffolding_section,
                scaffolding_state_section=scaffolding_state_section,
                galaxy_snapshot_section=galaxy_snapshot_section,
                idiographic_section=idiographic_section,
                intervention_language_contract_section=intervention_language_contract_section,
            )
        )

        ordered_sections = [
            mode_strategy_section,
            task_awareness_section,
            persona_section,
            companion_persona_section,
            constitution_guardrail_section,
            agent_persona_section,
            situation_brief_section,
            decision_policy_section,
            planning_strategy_section,
            user_material_grounding_section,
            process_scaffolding_section,
            scaffolding_state_section,
            galaxy_snapshot_section,
            idiographic_section,
            intervention_language_contract_section,
            capsule_preference_section,
            plan_context_section,
            conversation_history_section,
            context_briefing_section,
            visible_intelligence_section,
            intent_section,
            session_feedback_section,
            dual_core_section,
            understanding_depth_section,
            orchestration_context_section,
            collaboration_narrative_section,
            agent_memory_section,
            aurora_planning_sidecar_section,
            cognitive_prism_section,
            seed_library_section,
        ]
        suffix = "\n\n".join(section for section in ordered_sections if str(section or "").strip())
        if suffix:
            prompt = f"{prompt}\n\n{suffix}"

    if past_session_memory_section:
        prompt = f"{past_session_memory_section}\n\n{prompt}"

    # 4. 版本特定修饰

    if prompt_version == "v2":

        prompt += "\n\n## 输出风格\n- 更简洁\n- 先给结论，再给要点\n-  列表优先"

    # Signal-to-Action Spine: inject ResponseDirective constraints
    if spine_response_directive:
        tone = spine_response_directive.get("tone", "calm_direct")
        length = spine_response_directive.get("length", "medium")
        avoid_list = spine_response_directive.get("avoid", [])
        must_acknowledge = spine_response_directive.get("must_acknowledge", [])
        include_options = spine_response_directive.get("include_user_options", True)

        tone_map = {
            "calm_direct": "稳定、直接",
            "calm_urgent": "稳定但紧迫",
            "direct_but_reassuring": "直接但让人安心",
            "encouraging_diagnostic": "鼓励性诊断",
            "encouraging_low_pressure": "鼓励、低压",
            "recognition_not_praise": "认可但不空洞赞美",
            "helpful_suggestion": "有帮助的建议",
        }
        length_map = {"short": "简短（1-3句）", "medium": "适中", "long": "详细"}

        spine_section = "\n\n## 策略调整指令\n"
        spine_section += f"- 语气：{tone_map.get(tone, tone)}\n"
        spine_section += f"- 长度：{length_map.get(length, length)}\n"
        if avoid_list:
            spine_section += f"- 避免：{', '.join(avoid_list)}\n"
        if must_acknowledge:
            spine_section += f"- 必须承认：{', '.join(must_acknowledge)}\n"
        if include_options:
            spine_section += "- 提供可操作选项\n"
        prompt += spine_section

    # Signal-to-Action Spine: inject growth chronicle summary
    if spine_chronicle_summary:
        prompt += (
            f"\n\n## 用户成长叙事\n"
            f"{spine_chronicle_summary}\n"
            f"- 参考这些叙事来校准鼓励的力度和方向\n"
            f"- 不要逐条重复，而是内化后自然融入回复\n"
        )

    # Signal-to-Action Spine: inject fatigue/crisis context
    if spine_fatigue_context:
        level = spine_fatigue_context.get("fatigue_level", "")
        if level in ("high", "critical"):
            prompt += (
                "\n\n## 用户疲劳状态\n"
                "- 用户当前处于高疲劳状态，主动减轻负担\n"
                "- 缩短回复，降低任务密度建议\n"
                "- 优先关注健康节奏，而非学习效率\n"
            )
        crisis = spine_fatigue_context.get("crisis_mode")
        if crisis:
            prompt += (
                "\n\n## 考前高压状态\n"
                "- 用户处于考前高压，避免增加焦虑\n"
                "- 聚焦「已经掌握的」和「最可能拿分的」\n"
                "- 不建议大幅调整计划，微调为主\n"
            )

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


_CLAUSE_SPLIT_RE = re.compile(r"[。！？!?；;\n]+")
_CONVERSATION_MEMORY_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "困难": (
        re.compile(
            r"(?:最)?(?:头疼|头痛|困难|难点|痛点|短板|薄弱|卡在|卡住|搞不懂|不懂|不会|不熟)"
            r"(?:的是|是|在|：|:)?\s*(?P<item>[^，,。！？!?；;\n]{2,40})"
        ),
        re.compile(
            r"(?P<item>[\w\u4e00-\u9fff（）()·/+\-\s]{2,40}?)"
            r"(?:很|太|特别|有点|还是)?(?:难|头疼|头痛|搞不懂|不懂|不会|不熟|卡住)"
        ),
    ),
    "目标": (
        re.compile(
            r"(?:目标|目的|这次想要|希望|打算|准备|想要|想拿|想把|想在|要)"
            r"(?:是|：|:)?\s*(?P<item>[^，,。！？!?；;\n]{2,40})"
        ),
    ),
    "已完成": (
        re.compile(
            r"(?:已完成|已经完成|完成了|做完了|刷完了|看完了|复述了|"
            r"背完了|过完了|搞定了)"
            r"\s*(?P<item>[^，,。！？!?；;\n]{2,40})"
        ),
        re.compile(
            r"(?P<item>[\w\u4e00-\u9fff（）()·/+\-\s]{2,40}?)"
            r"(?:已完成|已经完成|完成了|做完了|刷完了|看完了|复述完了|"
            r"背完了|过完了|搞定了)"
        ),
        re.compile(r"(?:能|可以)?闭卷复述\s*(?P<item>[^，,。！？!?；;\n]{2,40})"),
    ),
}


def _conversation_messages_from_context(conversation_context: Any) -> tuple[list[dict[str, Any]], int]:
    if isinstance(conversation_context, dict):
        raw_messages = conversation_context.get("messages")
        if not isinstance(raw_messages, list):
            raw_messages = conversation_context.get("recent_messages")
        messages = [msg for msg in raw_messages or [] if isinstance(msg, dict)]
        raw_count = conversation_context.get("message_count")
        if raw_count is None:
            raw_count = conversation_context.get("original_count")
        try:
            message_count = int(raw_count)
        except (TypeError, ValueError):
            message_count = len(messages)
        return messages, max(message_count, len(messages))

    if isinstance(conversation_context, list):
        messages = [msg for msg in conversation_context if isinstance(msg, dict)]
        return messages, len(messages)

    return [], 0


def _message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return " ".join(parts)
    text = message.get("text")
    return str(text or "")


def _clean_conversation_memory_item(raw_item: str, *, category: str) -> str:
    item = " ".join(str(raw_item or "").split()).strip(" ：:，,。！？!?；;")
    if not item:
        return ""

    item = re.sub(r"\s+(?=[\u4e00-\u9fff])|(?<=[\u4e00-\u9fff])\s+", "", item)
    item = re.sub(
        r"^(我|我的|目前|现在|最近|这一轮|这次|最|觉得|感觉|" r"对我来说|主要|就是|是|在|还|还是)+",
        "",
        item,
    )
    item = re.sub(r"^(的是|的是：|的是:|是|在|为|要|想要|希望|打算|准备)", "", item)

    if category == "困难":
        item = re.sub(
            r"(很|太|特别|有点|还是)?(难|头疼|头痛|搞不懂|不懂|不会|不熟|卡住|卡在)$",
            "",
            item,
        )
    elif category == "目标":
        item = re.sub(r"(一下|一下子|吧|了)$", "", item)
    elif category == "已完成":
        item = re.sub(
            r"(已完成|已经完成|完成了|做完了|刷完了|看完了|复述完了|" r"背完了|过完了|搞定了|了)$",
            "",
            item,
        )

    item = item.strip(" ：:，,。！？!?；;")
    if not item or len(item) < 2:
        return ""
    if len(item) > 28:
        item = item[:28].rstrip(" ：:，,。！？!?；;") + "..."
    return item


def _extract_conversation_key_points(messages: list[dict[str, Any]]) -> dict[str, list[str]]:
    key_points: dict[str, list[str]] = {"困难": [], "目标": [], "已完成": []}
    for message in messages:
        if str(message.get("role") or "").lower() != "user":
            continue
        content = _message_content(message)
        if not content:
            continue
        clauses = [clause.strip() for clause in _CLAUSE_SPLIT_RE.split(content) if clause.strip()]
        for clause in clauses:
            if any(negation in clause for negation in ("不难", "没那么难", "不是很难")):
                continue
            for category, patterns in _CONVERSATION_MEMORY_PATTERNS.items():
                if len(key_points[category]) >= CONVERSATION_MEMORY_ITEM_LIMIT:
                    continue
                for pattern in patterns:
                    match = pattern.search(clause)
                    if not match:
                        continue
                    item = _clean_conversation_memory_item(match.group("item"), category=category)
                    if item and item not in key_points[category]:
                        key_points[category].append(item)
                    break
    return key_points


def build_conversation_memory_fragment(conversation_context: Any) -> str:
    """Render compact, non-transcript key points from the recent conversation."""
    messages, message_count = _conversation_messages_from_context(conversation_context)
    if message_count < CONVERSATION_MEMORY_MIN_MESSAGE_COUNT or not messages:
        return ""

    recent_messages = messages[-CONVERSATION_MEMORY_RECENT_MESSAGE_LIMIT:]
    key_points = _extract_conversation_key_points(recent_messages)
    lines = ["## 对话记忆片段", "本轮对话中用户已提及："]
    for category in ("困难", "目标", "已完成"):
        for item in key_points[category]:
            lines.append(f"- {category}：{item}")

    return "\n".join(lines) if len(lines) > 2 else ""


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
    soul_runtime_context = (
        user_context.get("soul_runtime_context") if isinstance(user_context.get("soul_runtime_context"), dict) else None
    )
    effective_companion_state = (
        user_context.get("effective_companion_state")
        if isinstance(user_context.get("effective_companion_state"), dict)
        else None
    )
    if isinstance(soul_runtime_context, dict) and isinstance(effective_companion_state, dict):
        return _format_soul_driven_companion_persona_section(
            user_context=user_context,
            plan_context=plan_context,
            soul_runtime_context=soul_runtime_context,
            effective_companion_state=effective_companion_state,
        )

    context_focus = user_context.get("context_focus") if isinstance(user_context, dict) else None
    section_weights = (
        context_focus.get("section_weights")
        if isinstance(context_focus, dict) and isinstance(context_focus.get("section_weights"), dict)
        else {}
    )
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

    # Community peer context - surface sprint progress or peer insights naturally.
    cognitive_ctx = user_context.get("cognitive_context") if isinstance(user_context, dict) else None
    community_ctx = (
        cognitive_ctx.get("community_context")
        if isinstance(cognitive_ctx, dict)
        else user_context.get("community_context") if isinstance(user_context, dict) else None
    )
    if isinstance(community_ctx, dict) and community_ctx.get("active_group_count", 0) > 0:
        sprint_progress = community_ctx.get("sprint_progress") or []
        if sprint_progress:
            lines.append(f"- 群组进展: {sprint_progress[0]}")
        elif community_ctx.get("recent_interaction"):
            lines.append(f"- 群组动态: 你最近 {community_ctx['recent_interaction']} 和学习群组有互动。")

    lines.append("- 回答时优先承接这些已知背景，不要反复问“你的目标是什么”。")
    # If peer context is present, hint that the AI can reference it naturally
    if isinstance(community_ctx, dict) and community_ctx.get("active_group_count", 0) > 0:
        lines.append("- 如果适合，可以自然提及同学的进展作为激励或参考，但不要施压。")
    return "\n" + "\n".join(lines)


def _format_soul_driven_companion_persona_section(
    *,
    user_context: dict,
    plan_context: dict | None,
    soul_runtime_context: dict[str, Any],
    effective_companion_state: dict[str, Any],
) -> str:
    profile = _extract_profile(user_context)
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    raw_user_context = user_context.get("user_context") if isinstance(user_context.get("user_context"), dict) else {}
    nickname = (
        str(identity.get("nickname") or "").strip()
        or str(raw_user_context.get("nickname") or raw_user_context.get("username") or "").strip()
        or "这位用户"
    )
    relationship_stage = str(
        _coalesce_mapping_value(effective_companion_state, "relationship_stage", "building")
    ).strip()
    warmth = float(_coalesce_mapping_value(effective_companion_state, "warmth_calibration", 0.55))
    candor = float(_coalesce_mapping_value(effective_companion_state, "candor_calibration", 0.75))
    challenge_style = str(_coalesce_mapping_value(effective_companion_state, "challenge_style", "balanced")).strip()
    truth_style = str(
        _coalesce_mapping_value(effective_companion_state, "preferred_truth_style", "honest_warm")
    ).strip()
    current_goal = ""
    active_goals = user_context.get("active_goals") if isinstance(user_context.get("active_goals"), list) else []
    if active_goals and isinstance(active_goals[0], dict):
        current_goal = str(active_goals[0].get("title") or "").strip()
    if not current_goal and isinstance(plan_context, dict):
        current_goal = str(plan_context.get("goal") or plan_context.get("plan_description") or "").strip()
    current_plan = ""
    if isinstance(plan_context, dict):
        current_plan = str(plan_context.get("plan_title") or plan_context.get("title") or "").strip()

    lines = [
        "## 陪伴式人格 framing [L2 引导]",
        f"你是 Sparkle，{nickname} 的成长伙伴，不是 generic assistant。",
        f"- 当前 companion stance: {str(soul_runtime_context.get('companion_stance') or '').strip()}",
        (
            f"- 当前陪伴取向: {_describe_relationship_stage(relationship_stage)}；"
            f"{_describe_warmth_level(warmth)}；{_describe_candor_level(candor)}；"
            f"{_describe_challenge_style(challenge_style)}；{_describe_truth_style(truth_style)}。"
        ),
        f"- 关系连续性: {str(soul_runtime_context.get('relationship_context') or '').strip()}",
    ]
    if current_goal:
        lines.append(f"- 当前目标: {current_goal}")
    if current_plan:
        lines.append(f"- 当前计划背景: {current_plan}")
    lines.append("- 通过连续性、诚实和结构感来体现陪伴，不要把陪伴写成表演或情绪堆砌。")
    lines.append("- 不要原样复述 companion notes，也不要暴露 runtime 字段名。")
    return "\n" + "\n".join(lines)


def _format_constitution_guardrail_section(*, user_context: dict) -> str:
    soul_runtime_context = (
        user_context.get("soul_runtime_context") if isinstance(user_context.get("soul_runtime_context"), dict) else None
    )
    if not isinstance(soul_runtime_context, dict):
        return ""

    constitutional_summary = str(soul_runtime_context.get("constitutional_summary") or "").strip()
    no_drift_flags = [
        str(item).strip() for item in (soul_runtime_context.get("no_drift_flags") or []) if str(item).strip()
    ]
    if not constitutional_summary and not no_drift_flags:
        return ""

    lines = [
        "## 宪法护栏 [L1 护栏]",
        constitutional_summary or "优先保护用户成长、真实感和自由度。",
    ]
    for item in no_drift_flags[:2]:
        lines.append(f"- {item}")
    return "\n" + "\n".join(lines)


def _format_visible_intelligence_section(*, user_context: dict) -> str:
    proactive_opening = str(user_context.get("proactive_opening_message") or "").strip()
    pending_observation = str(user_context.get("pending_observation") or "").strip()
    post_adaptation_question = str(user_context.get("post_adaptation_question") or "").strip()
    evolution_highlights = [
        str(item).strip() for item in (user_context.get("evolution_highlights") or []) if str(item).strip()
    ]

    if not proactive_opening and evolution_highlights:
        proactive_opening = evolution_highlights[0]
    if not proactive_opening and not pending_observation and not post_adaptation_question:
        return ""

    lines = [
        "## 本轮可感知智能 [L1 开场]",
        "如果这轮回答适合自然开场，请先用 1-2 句话把你观察到的变化说出来，再进入任务或解释。",
    ]
    if proactive_opening:
        lines.append(f"- 已发生的调整或观察: {proactive_opening}")
    if pending_observation:
        lines.append(f"- 可自然提起的观察问题: {pending_observation}")
    if post_adaptation_question:
        lines.append(f"- 若提到调整，可顺手确认: {post_adaptation_question}")
    lines.append("- 语气要像一直在关注用户的学习伙伴，不要像系统通知或播报日志。")
    return "\n" + "\n".join(lines)


def _format_decision_policy_section(*, user_context: dict) -> str:
    situation_brief = user_context.get("situation_brief") if isinstance(user_context, dict) else None
    decision_context = user_context.get("residual_decision_context") if isinstance(user_context, dict) else None
    if not isinstance(decision_context, dict):
        if isinstance(situation_brief, dict):
            decision_context = situation_brief.get("decision_context")
    if not isinstance(decision_context, dict):
        return ""

    experience_mode = str(decision_context.get("experience_mode") or "").strip()
    intervention_family = str(decision_context.get("intervention_family") or "").strip()
    visible_expression = decision_context.get("user_visible_expression")
    visible_expression = visible_expression if isinstance(visible_expression, dict) else {}
    feedback_hook = decision_context.get("feedback_hook")
    feedback_hook = feedback_hook if isinstance(feedback_hook, dict) else {}
    adjustments = decision_context.get("system_adjustments")
    adjustments = [item for item in adjustments if isinstance(item, dict)] if isinstance(adjustments, list) else []
    body_guidance = decision_context.get("body_awareness_guidance")
    body_guidance = body_guidance if isinstance(body_guidance, dict) else {}
    semantic_control = {}
    if isinstance(situation_brief, dict):
        semantic_control = situation_brief.get("semantic_control") or {}
    if not isinstance(semantic_control, dict) or not semantic_control:
        semantic_control = build_semantic_control(
            decision_context=decision_context,
            planning_strategy=(situation_brief.get("planning_strategy") if isinstance(situation_brief, dict) else {}),
            body_awareness_guidance=body_guidance,
            user_strategy_state=user_context.get("user_strategy_state") if isinstance(user_context, dict) else {},
            outcome_learning=(situation_brief.get("outcome_learning") if isinstance(situation_brief, dict) else {}),
            language="zh",
        ).to_dict()
    what_matters_now = str(decision_context.get("what_matters_now") or "").strip()
    planning_readiness = str(decision_context.get("planning_readiness") or "").strip()
    planning_action = str(decision_context.get("planning_readiness_action") or "").strip()
    predicted_overload_risk = str(decision_context.get("predicted_overload_risk") or "").strip()
    predicted_schedule_fit = str(decision_context.get("predicted_schedule_fit") or "").strip()
    predicted_plan_slippage_risk = str(decision_context.get("predicted_plan_slippage_risk") or "").strip()
    planning_unknowns = decision_context.get("planning_blocking_unknowns")
    planning_unknowns = (
        [item for item in planning_unknowns if str(item).strip()] if isinstance(planning_unknowns, list) else []
    )
    clarification_questions = decision_context.get("strategic_clarification_questions")
    clarification_questions = (
        [item for item in clarification_questions if str(item).strip()]
        if isinstance(clarification_questions, list)
        else []
    )

    if not any(
        [
            experience_mode,
            intervention_family,
            what_matters_now,
            adjustments,
            body_guidance,
            planning_readiness,
            predicted_overload_risk,
            predicted_schedule_fit,
            predicted_plan_slippage_risk,
            planning_unknowns,
            clarification_questions,
        ]
    ):
        return ""

    lines = ["## 当前决策策略 [L1 引导]"]
    if what_matters_now:
        lines.append(f"- 当前最重要的是: {what_matters_now}")
    if planning_readiness:
        readiness_bits = [planning_readiness]
        if planning_action:
            readiness_bits.append(planning_action)
        lines.append(f"- 规划前置信号: {' / '.join(readiness_bits)}")
    if predicted_overload_risk:
        lines.append(f"- 预测负荷风险: {predicted_overload_risk}")
    if predicted_schedule_fit or predicted_plan_slippage_risk:
        fit_bits = []
        if predicted_schedule_fit:
            fit_bits.append(f"时段适配 {predicted_schedule_fit}")
        if predicted_plan_slippage_risk:
            fit_bits.append(f"计划滑移风险 {predicted_plan_slippage_risk}")
        lines.append(f"- 预测前瞻: {' / '.join(fit_bits)}")
    if planning_unknowns:
        lines.append(f"- 计划前仍需补齐: {', '.join(str(item) for item in planning_unknowns[:3])}")
    if clarification_questions:
        lines.append(f"- 若要追问，优先问: {str(clarification_questions[0]).strip()}")
    doctrine_lines = format_semantic_control_lines(semantic_control, language="zh", section="decision")
    for item in doctrine_lines[:3]:
        lines.append(f"- {item}")
    opening_intent = str(visible_expression.get("opening_intent") or "").strip()
    response_shape_lines = format_semantic_control_lines(semantic_control, language="zh", section="response_shape")
    if opening_intent:
        lines.append(f"- 开场原则: {opening_intent}")
    if response_shape_lines:
        lines.append(f"- 回答结构: {response_shape_lines[0]}")
    if adjustments:
        first = adjustments[0]
        field = str(first.get("field") or "").strip()
        value = str(first.get("recommended_value") or "").strip()
        reason = str(first.get("reason") or "").strip()
        if field and value:
            lines.append(
                f"- 建议中的系统调整要服务于当前语义控制：先把 {field} 调整到更贴近「{value}」"
                + (f"；原因：{reason}" if reason else "")
            )
    body_lines = format_semantic_control_lines(semantic_control, language="zh", section="body")
    if body_lines:
        lines.append(f"- {body_lines[0]}")
    feedback_ask = str(feedback_hook.get("ask") or "").strip()
    if feedback_ask:
        lines.append(f"- 回合结束前最好确认: {feedback_ask}")
    lines.append("- 不要暴露 residual、policy、runtime 等内部术语，用自然语言把这套判断落到回答里。")
    return "\n" + "\n".join(lines)


def _format_planning_strategy_section(*, user_context: dict) -> str:
    situation_brief = user_context.get("situation_brief") if isinstance(user_context, dict) else None
    strategy = {}
    semantic_control = {}
    if isinstance(situation_brief, dict) and isinstance(situation_brief.get("planning_strategy"), dict):
        strategy = situation_brief.get("planning_strategy")
        semantic_control = situation_brief.get("semantic_control") or {}
    elif isinstance(user_context, dict) and isinstance(user_context.get("planning_strategy"), dict):
        strategy = user_context.get("planning_strategy")
    if not strategy:
        return ""

    if not isinstance(semantic_control, dict) or not semantic_control:
        semantic_control = build_semantic_control(
            decision_context=(situation_brief.get("decision_context") if isinstance(situation_brief, dict) else {}),
            planning_strategy=strategy,
            body_awareness_guidance=(
                (situation_brief.get("decision_context") or {}).get("body_awareness_guidance")
                if isinstance(situation_brief, dict)
                else {}
            ),
            user_strategy_state=user_context.get("user_strategy_state") if isinstance(user_context, dict) else {},
            outcome_learning=(situation_brief.get("outcome_learning") if isinstance(situation_brief, dict) else {}),
            language="zh",
        ).to_dict()
    doctrine_lines = format_semantic_control_lines(semantic_control, language="zh", section="planning")
    if not doctrine_lines:
        return ""

    lines = ["## 规划生成约束 [L1 引导]"]
    for item in doctrine_lines[:4]:
        lines.append(f"- {item}")
    lines.append("- 不要暴露字段名，要把这些约束翻译成自然、可执行、非专家友好的计划。")
    return "\n" + "\n".join(lines)


def _format_user_material_grounding_section(*, user_context: dict) -> str:
    grounding = user_context.get("user_material_grounding") if isinstance(user_context, dict) else None
    if not isinstance(grounding, dict):
        return ""

    status = str(grounding.get("status") or "").strip()
    query = str(grounding.get("query") or "").strip()
    results = [item for item in (grounding.get("results") or []) if isinstance(item, dict)]
    if not status and not results:
        return ""

    lines = ["## 用户材料依据 [L1 证据]"]
    if query:
        lines.append(f"- 本轮已按该查询预取用户材料: {query}")

    if status == "grounded" and results:
        lines.append("- 回答时优先用这些用户材料片段校准概念、范围和措辞；若材料不足，再补通用知识。")
        for item in results[:3]:
            label_parts = [str(item.get("file_name") or "").strip()]
            section_title = str(item.get("section_title") or "").strip()
            if section_title:
                label_parts.append(section_title)
            page_numbers = item.get("page_numbers") or []
            if isinstance(page_numbers, list) and page_numbers:
                label_parts.append(f"p.{','.join(str(page) for page in page_numbers[:3])}")
            label = " / ".join(part for part in label_parts if part)
            snippet = str(item.get("snippet") or "").strip()
            if label and snippet:
                lines.append(f"- {label}: {snippet}")
            elif snippet:
                lines.append(f"- {snippet}")
    elif status in {"no_hits", "no_scoped_files", "retrieval_failed", "file_resolution_failed"}:
        lines.append("- 当前策略要求先看用户材料，但这轮没有拿到足够可用的材料证据。")
        lines.append("- 若继续回答，请明确缩小结论范围，并把通用知识当作补充而不是替代。")
    else:
        return ""

    return "\n" + "\n".join(lines)


def _format_process_scaffolding_section(*, user_context: dict) -> str:
    profile_context = _extract_profile_context_payload(user_context)
    payload = None
    if isinstance(profile_context, dict):
        payload = profile_context.get("metacognition_process_scaffolding")
    if not isinstance(payload, dict) and isinstance(user_context, dict):
        payload = user_context.get("metacognition_process_scaffolding")
    if not isinstance(payload, dict):
        return ""

    body = str(payload.get("body") or "").strip()
    if not body:
        return ""

    lines = [
        "## 过程复盘支架 [L2 引导]",
        f"- {body}",
        "- 只帮助用户回看判断过程，不要把这类观察写成人格、身份或诊断结论。",
    ]
    return "\n" + "\n".join(lines)


def _format_scaffolding_state_section(*, user_context: dict) -> str:
    payload = user_context.get("scaffolding_fsm_snapshot") if isinstance(user_context, dict) else None
    if not isinstance(payload, dict):
        return ""
    if str(payload.get("mode") or "off").strip().lower() != "live":
        return ""

    current_stage = str(payload.get("current_scaffolding_stage") or "").strip()
    intervention_intensity = str(payload.get("intervention_intensity") or "").strip()
    template_support_level = payload.get("template_support_level")
    if not current_stage or not intervention_intensity:
        return ""

    lines = [
        "## 脚手架状态 [L2 引导]",
        f"- 当前脚手架阶段: {current_stage}",
        f"- 当前干预强度: {intervention_intensity}",
    ]
    if template_support_level is not None:
        lines.append(f"- 当前模板支架级别: {template_support_level}")
    reflection_prompt_style = str(payload.get("reflection_prompt_style") or "").strip()
    if reflection_prompt_style:
        lines.append(f"- 复盘提示风格: {reflection_prompt_style}")
    lines.append("- 先按当前支架强度组织回答，不要突然提高要求或切成高压推进。")
    return "\n" + "\n".join(lines)


def _format_galaxy_snapshot_section(*, user_context: dict) -> str:
    payload = user_context.get("galaxy_snapshot") if isinstance(user_context, dict) else None
    if not isinstance(payload, dict):
        return ""
    if str(payload.get("mode") or "off").strip().lower() != "live":
        return ""
    nodes = payload.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        return ""

    lines = [
        "## 知识星图节点 [L2 引导]",
        "- 若回答涉及路径、前置关系或复盘，优先用这些当前目标附近的节点来落地。",
    ]
    for item in nodes[:5]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        role = str(item.get("role") or "related").strip()
        mastery_score = item.get("mastery_score")
        description = str(item.get("description") or "").strip()
        detail_bits = [role]
        if mastery_score is not None:
            detail_bits.append(f"mastery {mastery_score}")
        line = (
            f"- {name} ({', '.join(detail_bits)}): {description}"
            if description
            else f"- {name} ({', '.join(detail_bits)})"
        )
        lines.append(line[:180])
    return "\n" + "\n".join(lines)


def _format_idiographic_section(*, user_context: dict) -> str:
    profile_context = _extract_profile_context_payload(user_context)
    payload = profile_context.get("idiographic_summary") if isinstance(profile_context, dict) else None
    if not isinstance(payload, dict):
        return ""

    if str(payload.get("mode") or "off").strip().lower() != "live":
        if isinstance(user_context, dict):
            user_context["idiographic_associations_injected"] = []
        return ""

    disclaimer_text = str(payload.get("disclaimer_text") or "").strip()
    confidence = float(payload.get("confidence") or 0.0)
    if confidence < 0.5 or not disclaimer_text:
        if isinstance(user_context, dict):
            user_context["idiographic_associations_injected"] = []
        return ""

    injected_rows: list[dict[str, Any]] = []
    rendered_lines: list[str] = []
    for item in payload.get("top_associations") or []:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("displayed")):
            continue
        rendered_text = str(item.get("rendered_text") or "").strip()
        if not rendered_text:
            continue
        rendered_lines.append(f"- {rendered_text}")
        injected_rows.append(
            {
                "dim_pair": str(item.get("dim_pair") or "").strip(),
                "r_rounded": round(float(item.get("correlation") or 0.0), 2),
                "displayed": True,
            }
        )
        if len(rendered_lines) >= 3:
            break

    if isinstance(user_context, dict):
        user_context["idiographic_associations_injected"] = injected_rows

    if not rendered_lines:
        return ""

    lines = [
        "## 个体内关联观察 [L2 引导]",
        "- 这些观察只能当作近期模式参考，不能写成因果判断、诊断或路由条件。",
        *rendered_lines,
    ]
    return "\n" + "\n".join(lines)


def _resolve_preference_instructions(
    *,
    user_context: dict,
    llm_profile: dict[str, Any],
    context_focus: dict[str, Any] | None,
) -> str:
    focus_decision = ContextFocusDecision.from_dict(context_focus)
    semantic_control = _resolve_semantic_control_from_context(user_context)
    strategy_lines = format_semantic_control_lines(semantic_control, language="zh", section="strategy")
    if focus_decision and focus_decision.focus_mode == "emotional_focus":
        tone = str(llm_profile.get("tone") or "稳定、温和").strip()
        verbosity = str(llm_profile.get("verbosity_target") or "concise").strip()
        instruction = (
            "## 用户偏好适配\n"
            f"- 当前优先语气：{tone}\n"
            f"- 当前优先长度：{verbosity}\n"
            "- 回答先降低认知负荷，再给可执行下一步"
        )
        if strategy_lines:
            instruction += "\n" + "\n".join(strategy_lines)
        return instruction

    base_instruction = llm_profile.get(
        "system_prompt_additions",
        _get_default_preference_instructions(user_context),
    )
    if strategy_lines:
        base_instruction = "\n".join([str(base_instruction).strip(), *strategy_lines]).strip()
    return base_instruction


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
    other_facts = {k: v for k, v in facts.items() if k not in ("difficulty_preference", "session_length_preference")}
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


def _extract_canonical_insight_state(context: dict[str, Any] | None) -> UserInsightState | None:
    """Try to extract a compiled UserInsightState from the context dict.

    Lookup order:
      1. context["user_insight_state"]  (direct top-level)
      2. context["profile_context"].user_insight_state  (attribute on ProfileContext)
      3. context["profile_context"]["user_insight_state"]  (serialised dict form)
    """
    if not isinstance(context, dict):
        return None

    # 1. Direct top-level
    candidate = context.get("user_insight_state")
    if isinstance(candidate, UserInsightState):
        return candidate
    if isinstance(candidate, dict) and candidate:
        try:
            return UserInsightState(**candidate)
        except Exception:
            logger.debug("Failed to construct UserInsightState from candidate dict", exc_info=True)

    # 2. Attribute on profile_context object
    profile_ctx = context.get("profile_context")
    if profile_ctx is not None and hasattr(profile_ctx, "user_insight_state"):
        attr = getattr(profile_ctx, "user_insight_state", None)
        if isinstance(attr, UserInsightState):
            return attr
        if isinstance(attr, dict) and attr:
            try:
                return UserInsightState(**attr)
            except Exception:
                logger.debug("Failed to construct UserInsightState from profile_ctx attr", exc_info=True)

    # 3. Dict form inside profile_context
    if isinstance(profile_ctx, dict):
        inner = profile_ctx.get("user_insight_state")
        if isinstance(inner, UserInsightState):
            return inner
        if isinstance(inner, dict) and inner:
            try:
                return UserInsightState(**inner)
            except Exception:
                logger.debug("Failed to construct UserInsightState from profile_ctx dict inner", exc_info=True)

    return None


def _extract_cognitive_context_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = context.get("cognitive_context") if isinstance(context, dict) else None
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _extract_profile_context_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = context.get("profile_context") if isinstance(context, dict) else None
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _resolve_stage33_feature_mode(context: dict[str, Any] | None, feature: str) -> str:
    payload = context if isinstance(context, dict) else {}
    modes = payload.get("aurora_stage33_modes")
    if isinstance(modes, dict):
        raw = str(modes.get(feature) or modes.get("mode") or "").strip().lower()
        if raw in {"off", "shadow", "live"}:
            return raw
    fallback_attr = {
        "social": "AURORA_STAGE33_SOCIAL_MODE",
        "srl": "AURORA_STAGE33_SRL_MODE",
        "wm_prompt": "AURORA_STAGE33_WM_PROMPT_MODE",
        "events": "AURORA_STAGE33_EVENTS_MODE",
    }.get(feature)
    raw = str(getattr(settings, fallback_attr or "", "off") or "off").strip().lower()
    return raw if raw in {"off", "shadow", "live"} else "off"


def _extract_stage33_social_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = context if isinstance(context, dict) else {}
    cognitive_context = _extract_cognitive_context_payload(payload)
    for candidate in (
        payload.get("social_signals_summary"),
        payload.get("social_context_v1"),
        cognitive_context.get("social_signals_summary"),
        cognitive_context.get("social_context_v1"),
    ):
        if isinstance(candidate, dict) and candidate:
            nested_value = candidate.get("value")
            if isinstance(nested_value, dict) and nested_value:
                return nested_value
            return candidate

    legacy_social = payload.get("social_context")
    if not isinstance(legacy_social, dict) or not legacy_social:
        return {}

    mention_count = len(legacy_social.get("recent_person_mentions") or [])
    relationship_count = int(legacy_social.get("relationship_count") or 0)
    pending_commitments_count = int(legacy_social.get("pending_commitments_count") or 0)
    summary_lines: list[str] = []
    if mention_count > 0:
        summary_lines.append(f"最近 7 天提到过 {mention_count} 位学习相关人物。")
    if relationship_count > 0:
        summary_lines.append(f"当前有 {relationship_count} 条关系型背景需要在建议里保持边界感。")
    if pending_commitments_count > 0:
        summary_lines.append(f"目前有 {pending_commitments_count} 条到期承诺待跟进。")
    if not summary_lines:
        return {}
    return {
        "mention_count": mention_count,
        "relationship_count": relationship_count,
        "pending_commitments_count": pending_commitments_count,
        "summary_lines": summary_lines,
        "summary_text": "；".join(summary_lines),
    }


def _extract_stage33_srl_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = context if isinstance(context, dict) else {}
    cognitive_context = _extract_cognitive_context_payload(payload)
    profile_context = _extract_profile_context_payload(payload)
    insight_state = profile_context.get("user_insight_state") if isinstance(profile_context, dict) else None
    insight_state = insight_state if isinstance(insight_state, dict) else {}

    for candidate in (
        payload.get("srl_phase"),
        cognitive_context.get("srl_phase"),
        profile_context.get("srl_phase") if isinstance(profile_context, dict) else None,
        insight_state.get("srl_phase"),
    ):
        if isinstance(candidate, dict) and candidate:
            nested_value = candidate.get("value")
            if isinstance(nested_value, dict) and nested_value:
                return nested_value
            return candidate
    return {}


def _format_stage33_social_signal_section(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict) or not payload:
        return ""

    summary_lines = [str(item).strip() for item in (payload.get("summary_lines") or []) if str(item).strip()]
    if not summary_lines and str(payload.get("summary_text") or "").strip():
        summary_lines = [part.strip() for part in str(payload.get("summary_text") or "").split("；") if part.strip()]
    if not summary_lines:
        mention_count = int(payload.get("mention_count") or 0)
        relationship_count = int(payload.get("relationship_count") or 0)
        pending_commitments_count = int(payload.get("pending_commitments_count") or 0)
        if mention_count > 0:
            summary_lines.append(f"最近 7 天提到过 {mention_count} 位学习相关人物。")
        if relationship_count > 0:
            summary_lines.append(f"当前有 {relationship_count} 条关系型背景需要在建议里保持边界感。")
        if pending_commitments_count > 0:
            summary_lines.append(f"目前有 {pending_commitments_count} 条到期承诺待跟进。")
    if not summary_lines:
        return ""

    lines = ["## 社群信号 [L2 引导]"]
    lines.extend(f"- {item}" for item in summary_lines[:3])
    lines.append("- 这些信号只用于帮助保持协作边界和启动方式，不代表必须把学习社交化。")
    return "\n".join(lines)


def _format_stage33_srl_phase_section(payload: dict[str, Any] | None) -> str:
    hint = SRLPhaseHint.from_payload(payload if isinstance(payload, dict) else None)
    if hint is None:
        return ""

    lines = ["## 学习自调节阶段"]
    lines.extend(f"- {item}" for item in hint.to_summary_lines()[:4])
    lines.append("- 仅把它当作当前引导姿态，不把阶段标签说教式地压给用户。")
    return "\n".join(lines)


def _extract_working_memory_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = context if isinstance(context, dict) else {}
    cognitive_context = _extract_cognitive_context_payload(payload)
    for candidate in (
        payload.get("working_memory_snapshot"),
        cognitive_context.get("working_memory_snapshot"),
    ):
        if isinstance(candidate, dict) and candidate:
            nested_value = candidate.get("value")
            if isinstance(nested_value, dict) and nested_value:
                return nested_value
            return candidate
    return {}


def _resolve_stage34_capsule_mode(context: dict[str, Any] | None) -> str:
    payload = context if isinstance(context, dict) else {}
    modes = payload.get("aurora_stage34_modes")
    if isinstance(modes, dict):
        value = str(modes.get("capsule_mode") or "").strip().lower()
        if value in {"off", "shadow", "live"}:
            return value
    fallback = str(getattr(settings, "AURORA_STAGE34_CAPSULE_MODE", "shadow") or "shadow").strip().lower()
    return fallback if fallback in {"off", "shadow", "live"} else "shadow"


def _format_working_memory_section(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict) or not payload:
        return ""

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return ""

    lines = ["## 工作记忆（近 30 分钟）"]
    kept_items = 0
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        subject_type = str(item.get("subject_type") or "").strip()
        prefix = f"{subject_type}: " if subject_type else ""
        lines.append(f"- {prefix}{summary}")
        kept_items += 1

    if kept_items == 0:
        return ""

    lines.append("- 这些内容只用于保持短时连续性，过期或无关内容不要强行引用。")
    return _truncate_section("\n".join(lines), target_tokens=300)


def _has_signal_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, set, str)):
        return bool(value)
    return True


def _build_prompt_signal_telemetry(context: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    cognitive_context = _extract_cognitive_context_payload(context)
    profile_context = _extract_profile_context_payload(context)
    canonical_insight = _extract_canonical_insight_state(context)
    tracked_fields = (
        "preferences",
        "knowledge_summary",
        "error_summary",
        "recent_errors",
        "recent_mastery_changes",
        "active_tasks",
        "focus_stats",
        "achievement_summary",
        "calendar_context",
        "idiographic_summary",
        "social_context",
        "social_signals_summary",
        "srl_phase",
        "working_memory_snapshot",
        "engagement_state",
        "learning_state",
        "traits_prior",
        "metacognition_profile",
    )
    field_status: dict[str, Any] = {}
    for key in tracked_fields:
        stage33_feature = {
            "social_signals_summary": "social",
            "srl_phase": "srl",
            "working_memory_snapshot": "wm_prompt",
        }.get(key)
        if stage33_feature and _resolve_stage33_feature_mode(context, stage33_feature) != "live":
            normalized_value = normalized.get(key)
            item_count = 0
            if isinstance(normalized_value, (list, dict)):
                item_count = len(normalized_value)
            elif _has_signal_payload(normalized_value):
                item_count = 1
            field_status[key] = {
                "collected": False,
                "collected_sources": [],
                "normalized": _has_signal_payload(normalized_value),
                "rendered": False,
                "item_count": item_count,
            }
            continue

        sources: list[str] = []
        if _has_signal_payload(_extract_canonical_signal(canonical_insight, key)):
            sources.append("canonical_insight_state")
        if _has_signal_payload(context.get(key)):
            sources.append("context")
        if _has_signal_payload(cognitive_context.get(key)):
            sources.append("cognitive_context")
        if _has_signal_payload(profile_context.get(key)):
            sources.append("profile_context")
        knowledge_summary = profile_context.get("knowledge_summary") if isinstance(profile_context, dict) else {}
        if (
            key == "recent_mastery_changes"
            and isinstance(knowledge_summary, dict)
            and _has_signal_payload(knowledge_summary.get("recent_mastery_changes"))
        ):
            sources.append("profile_context.knowledge_summary")
        if key == "social_signals_summary":
            social_payload = _extract_stage33_social_payload(context)
            if _has_signal_payload(social_payload):
                sources.append("stage33_social_payload")
        if key == "srl_phase":
            srl_payload = _extract_stage33_srl_payload(context)
            if _has_signal_payload(srl_payload):
                sources.append("stage33_srl_payload")
        if key == "working_memory_snapshot":
            working_memory_payload = _extract_working_memory_payload(context)
            if _has_signal_payload(working_memory_payload):
                sources.append("working_memory_payload")

        normalized_value = normalized.get(key)
        item_count = 0
        if isinstance(normalized_value, (list, dict)):
            item_count = len(normalized_value)
        elif _has_signal_payload(normalized_value):
            item_count = 1

        field_status[key] = {
            "collected": bool(sources),
            "collected_sources": sources,
            "normalized": _has_signal_payload(normalized_value),
            "rendered": False,
            "item_count": item_count,
        }

    return {
        "tracked_fields": list(tracked_fields),
        "collected_high_value_fields": [key for key, meta in field_status.items() if meta["collected"]],
        "normalized_high_value_fields": [key for key, meta in field_status.items() if meta["normalized"]],
        "rendered_high_value_fields": [],
        "dropped_high_value_fields": [],
        "high_value_fields": field_status,
        "section_sizes": {},
    }


def _build_prompt_utilization_snapshot(
    *,
    pre_budget_section_map: dict[str, str],
    model_facing_section_map: dict[str, str],
    prompt_signal_telemetry: dict[str, Any],
) -> dict[str, Any]:
    selected_signal_blocks = [
        alias
        for section_name, alias in _PROMPT_UTILIZATION_SECTION_ALIASES.items()
        if str(pre_budget_section_map.get(section_name) or "").strip()
    ]
    rendered_signal_blocks = [
        alias
        for section_name, alias in _PROMPT_UTILIZATION_SECTION_ALIASES.items()
        if str(model_facing_section_map.get(section_name) or "").strip()
    ]
    return {
        "selected_signal_block_count": len(selected_signal_blocks),
        "rendered_signal_block_count": len(rendered_signal_blocks),
        "selected_signal_blocks": selected_signal_blocks,
        "rendered_signal_blocks": rendered_signal_blocks,
        "selected_high_value_fields": list(prompt_signal_telemetry.get("collected_high_value_fields") or []),
        "prompt_visible_high_value_fields": list(prompt_signal_telemetry.get("prompt_visible_high_value_fields") or []),
    }


def _format_error_summary_line(summary: dict[str, Any]) -> str:
    if not isinstance(summary, dict) or not summary:
        return ""
    parts: list[str] = []
    total_errors = summary.get("total_errors")
    if total_errors is not None:
        parts.append(f"累计错题 {int(total_errors)}")
    need_review = summary.get("need_review_count") or summary.get("due_for_review")
    if need_review is not None:
        parts.append(f"待复习 {int(need_review)}")
    review_streak = summary.get("review_streak_days")
    if review_streak:
        parts.append(f"复盘连续 {int(review_streak)} 天")
    distribution = summary.get("subject_distribution")
    if isinstance(distribution, dict) and distribution:
        ranked = sorted(
            ((str(subject).strip(), int(count)) for subject, count in distribution.items() if str(subject).strip()),
            key=lambda item: (-item[1], item[0]),
        )
        if ranked:
            top_subjects = "、".join(f"{subject}({count})" for subject, count in ranked[:2])
            parts.append(f"高频科目 {top_subjects}")
    return "；".join(parts)


def _format_achievement_context_line(summary: dict[str, Any]) -> str:
    if not isinstance(summary, dict) or not summary:
        return ""
    parts: list[str] = []
    recent_unlocks = summary.get("recent_unlocks") or []
    if recent_unlocks:
        recent_names = "、".join(
            str(item.get("name") or item.get("achievement_id") or "").strip()
            for item in recent_unlocks[:2]
            if isinstance(item, dict)
        )
        if recent_names:
            parts.append(f"最近解锁 {recent_names}")
    progress_items = summary.get("in_progress_achievements") or []
    if progress_items:
        top = progress_items[0] if isinstance(progress_items[0], dict) else {}
        if top:
            progress = top.get("progress")
            if progress is not None:
                try:
                    parts.append(f"{top.get('name') or '一项成就'} 进度 {float(progress):.0%}")
                except Exception:
                    parts.append(f"{top.get('name') or '一项成就'} 正在推进")
    progress_events = summary.get("recent_progress_events") or []
    if progress_events:
        top_event = progress_events[0] if isinstance(progress_events[0], dict) else {}
        if top_event:
            name = top_event.get("achievement_name") or top_event.get("achievement_id") or "一项成就"
            progress_percent = top_event.get("progress_percent")
            if progress_percent is not None:
                try:
                    parts.append(f"{name} 刚推进到 {int(float(progress_percent))}%")
                except Exception:
                    parts.append(f"{name} 刚有新进展")
    score = summary.get("total_achievement_score")
    if score is not None:
        try:
            parts.append(f"成就总分 {float(score):.1f}")
        except Exception:
            parts.append(f"成就总分 {score}")
    return "；".join(parts)


def _format_calendar_context_lines(calendar_context: dict[str, Any]) -> list[str]:
    if not isinstance(calendar_context, dict) or not calendar_context:
        return []
    lines: list[str] = []
    workload_density = str(calendar_context.get("workload_density") or "").strip()
    if workload_density:
        lines.append(f"- 本周任务密度: {workload_density}")
    deadlines = calendar_context.get("upcoming_deadlines") or []
    if deadlines:
        labels: list[str] = []
        for item in deadlines[:3]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "未命名日程").strip()
            start_time = str(item.get("start_time") or "")
            date_label = start_time[5:10] if len(start_time) >= 10 else start_time
            labels.append(f"{title}({date_label})" if date_label else title)
        if labels:
            lines.append(f"- 近 7 天截止: {'、'.join(labels)}")
    time_blocks = calendar_context.get("time_blocks_today") or []
    if time_blocks:
        slots = []
        for block in time_blocks[:3]:
            if not isinstance(block, dict):
                continue
            start = str(block.get("start") or "").strip()
            end = str(block.get("end") or "").strip()
            if start and end:
                slots.append(f"{start}-{end}")
        if slots:
            lines.append(f"- 今日可用时间段: {'、'.join(slots)}")
    exam_urgency = calendar_context.get("exam_urgency")
    if isinstance(exam_urgency, dict) and exam_urgency.get("days_left") is not None:
        urgency_label = "紧急" if exam_urgency.get("urgent") else "一般"
        lines.append(f"- 考试倒计时: {exam_urgency.get('days_left')} 天 ({urgency_label})")
    return lines


def _resolve_stage40_calendar_mode(calendar_context: dict[str, Any] | None) -> str:
    if isinstance(calendar_context, dict):
        raw = calendar_context.get("_stage40_mode")
        if raw is not None:
            return normalize_mode(raw, fallback="live")
    return normalize_mode(getattr(settings, "AURORA_STAGE40_CALENDAR_MODE", "live"), fallback="live")


def _format_recent_error_line(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    preview = str(item.get("question_preview") or item.get("title") or "").strip()
    subject = str(item.get("subject") or "").strip()
    error_type = str(item.get("error_type") or "").strip()
    mastery = item.get("mastery")
    bits = [bit for bit in (subject, error_type) if bit]
    if mastery is not None:
        try:
            bits.append(f"掌握度 {float(mastery):.0%}")
        except Exception:
            bits.append(f"掌握度 {mastery}")
    if bits:
        return f"{preview or '最近有一道题反复卡住'} ({', '.join(bits)})"
    return preview or "最近有一道题反复卡住"


def _format_mastery_change_line(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    node_name = str(item.get("node_name") or item.get("node_id") or "").strip()
    if not node_name:
        return ""
    old_mastery = item.get("old_mastery")
    new_mastery = item.get("new_mastery")
    if old_mastery is None or new_mastery is None:
        return f"{node_name} 最近掌握度有提升"
    try:
        old_val = float(old_mastery)
        new_val = float(new_mastery)
        return f"{node_name} 掌握度从 {old_val:.0f}% 提升到 {new_val:.0f}% (+{new_val - old_val:.0f})"
    except Exception:
        return f"{node_name} 掌握度从 {old_mastery} 提升到 {new_mastery}"


def _render_user_context_content(
    context: dict,
    *,
    context_level: str = "full",
    context_focus: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    lines: list[str] = []
    normalized = _normalize_user_context(context)
    telemetry = _build_prompt_signal_telemetry(context, normalized)
    focus_decision = ContextFocusDecision.from_dict(context_focus)
    section_weights = focus_decision.section_weights if focus_decision else {}
    section_caps = focus_decision.section_caps if focus_decision else {}

    def _mark_rendered(field_name: str) -> None:
        meta = telemetry["high_value_fields"].get(field_name)
        if not isinstance(meta, dict):
            return
        meta["rendered"] = True
        if field_name not in telemetry["rendered_high_value_fields"]:
            telemetry["rendered_high_value_fields"].append(field_name)

    identity = normalized.get("identity")
    if identity:
        lines.append("【身份信息】")
        lines.append(f"- 昵称: {identity.get('nickname', '未知')}")
        lines.append(f"- 时区: {identity.get('timezone', 'Asia/Shanghai')}")
        lines.append(f"- Pro状态: {'是' if identity.get('is_pro') else '否'}")

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

    if identity and identity.get("flame_level") is not None:
        lines.append(f"火花等级: {identity['flame_level']}")

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
        _mark_rendered("preferences")

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
            _mark_rendered("knowledge_summary")

    learning_gaps_summary = normalized.get("learning_gaps_summary")
    if learning_gaps_summary:
        lines.append("【当前学习状态】")
        lines.append(f"- {learning_gaps_summary}")

    pain_limit = section_caps.get("recent_pain_points") or (1 if context_level == "light" else 3)
    pain_lines: list[str] = []
    error_summary_line = _format_error_summary_line(normalized.get("error_summary") or {})
    if error_summary_line:
        pain_lines.append(error_summary_line)
        _mark_rendered("error_summary")
    remaining_error_items = max(0, pain_limit - len(pain_lines))
    for item in (normalized.get("recent_errors") or [])[:remaining_error_items]:
        line = _format_recent_error_line(item)
        if not line:
            continue
        pain_lines.append(line)
        _mark_rendered("recent_errors")
    if pain_lines:
        lines.append("【近期痛点】")
        lines.extend(f"- {line}" for line in pain_lines)
        telemetry["section_sizes"]["recent_pain_points"] = {
            "items": len(pain_lines),
            "approx_tokens": _estimate_prompt_tokens("\n".join(pain_lines)),
        }

    win_limit = section_caps.get("recent_wins") or (1 if context_level == "light" else 3)
    win_lines: list[str] = []
    for item in (normalized.get("recent_mastery_changes") or [])[:win_limit]:
        line = _format_mastery_change_line(item)
        if not line:
            continue
        win_lines.append(line)
        _mark_rendered("recent_mastery_changes")
    if win_lines:
        lines.append("【近期进展】")
        lines.extend(f"- {line}" for line in win_lines)
        telemetry["section_sizes"]["recent_wins"] = {
            "items": len(win_lines),
            "approx_tokens": _estimate_prompt_tokens("\n".join(win_lines)),
        }

    achievement_line = _format_achievement_context_line(normalized.get("achievement_summary") or {})
    if achievement_line:
        if "【近期进展】" not in lines:
            lines.append("【近期进展】")
        lines.append(f"- {achievement_line}")
        _mark_rendered("achievement_summary")

    next_actions = normalized.get("next_actions") or []
    task_weight = section_weights.get("task_summary", "medium")
    if next_actions and task_weight != "off":
        lines.append("【待办任务】")
        limit = section_caps.get("next_actions") or (1 if context_level == "light" else 3)
        lines.append(f"Top {limit}:")
        for task in next_actions[:limit]:
            lines.append(f"- {task.get('title')} ({task.get('estimated_minutes')}m, {task.get('type')})")
        _mark_rendered("active_tasks")

    if normalized.get("focus_stats"):
        stats = normalized["focus_stats"]
        lines.append("【专注统计】")
        lines.append(f"- 今日专注: {stats.get('total_minutes', 0)} 分钟")
        lines.append(f"- 番茄钟次数: {stats.get('pomodoro_count', 0)}")
        _mark_rendered("focus_stats")

    understanding_depth = normalized.get("understanding_depth")
    if isinstance(understanding_depth, dict) and understanding_depth.get("level"):
        lines.append("【理解深度】")
        lines.append(f"- 当前等级: {understanding_depth.get('level')}")

    strategy_semantic_control = _resolve_semantic_control_from_context(context)
    strategy_doctrine = format_semantic_control_lines(strategy_semantic_control, language="zh", section="strategy")
    if strategy_doctrine:
        lines.append("【当前交互策略】")
        lines.extend(f"- {item}" for item in strategy_doctrine)

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

    if normalized.get("preferred_tools"):
        lines.append("【工具偏好】")
        lines.append(f"- 常用工具: {', '.join(normalized['preferred_tools'])}")

    stage33_social_mode = _resolve_stage33_feature_mode(context, "social")
    if stage33_social_mode == "live":
        social_signal_section = _format_stage33_social_signal_section(normalized.get("social_signals_summary"))
        if social_signal_section:
            lines.append(social_signal_section)
            _mark_rendered("social_signals_summary")
            telemetry["section_sizes"]["social_signals"] = {
                "items": len(
                    [
                        item
                        for item in str(normalized.get("social_signals_summary", {}).get("summary_text") or "").split(
                            "；"
                        )
                        if item.strip()
                    ]
                )
                or len((normalized.get("social_signals_summary") or {}).get("summary_lines") or []),
                "approx_tokens": _estimate_prompt_tokens(social_signal_section),
            }
    elif settings.SPARKLE_ROUTER_SOCIAL_CONTEXT_READ_ENABLED or settings.SPARKLE_PROMPT_SOCIAL_CONTEXT_RENDER_ENABLED:
        social_context = context.get("social_context") if isinstance(context, dict) else None
        social_lines = render_social_context_lines(social_context if isinstance(social_context, dict) else None)
        if social_lines:
            lines.extend(social_lines)
            _mark_rendered("social_context")

    stage33_srl_mode = _resolve_stage33_feature_mode(context, "srl")
    if stage33_srl_mode == "live":
        srl_section = _format_stage33_srl_phase_section(normalized.get("srl_phase"))
        if srl_section:
            lines.append(srl_section)
            _mark_rendered("srl_phase")
            telemetry["section_sizes"]["srl_phase"] = {
                "items": len(srl_section.splitlines()) - 1,
                "approx_tokens": _estimate_prompt_tokens(srl_section),
            }

    working_memory_mode = _resolve_stage33_feature_mode(context, "wm_prompt")
    if working_memory_mode == "live":
        working_memory_section = _format_working_memory_section(normalized.get("working_memory_snapshot"))
        if working_memory_section:
            lines.append(working_memory_section)
            _mark_rendered("working_memory_snapshot")
            telemetry["section_sizes"]["working_memory_snapshot"] = {
                "items": len(
                    [
                        item
                        for item in (normalized.get("working_memory_snapshot") or {}).get("items", [])
                        if isinstance(item, dict) and str(item.get("summary") or "").strip()
                    ]
                ),
                "approx_tokens": _estimate_prompt_tokens(working_memory_section),
            }

    calendar_context = normalized.get("calendar_context") or {}
    calendar_mode = _resolve_stage40_calendar_mode(calendar_context if isinstance(calendar_context, dict) else None)
    calendar_lines = _format_calendar_context_lines(calendar_context if isinstance(calendar_context, dict) else {})
    if calendar_mode == "live" and calendar_lines:
        lines.append("【时间约束】")
        lines.extend(calendar_lines)
        _mark_rendered("calendar_context")
    elif calendar_mode == "live" and isinstance(normalized.get("exam_urgency"), dict):
        urgency = normalized["exam_urgency"]
        days_left = urgency.get("days_left")
        if days_left is not None:
            lines.append("【考试紧迫度】")
            urgency_label = "紧急" if urgency.get("urgent") else "一般"
            lines.append(f"考试倒计时: {days_left} 天 ({urgency_label})")

    # --- Inline snapshot from canonical insight state ---
    inline_snapshot = normalized.get("_inline_snapshot")
    if isinstance(inline_snapshot, dict) and inline_snapshot.get("available"):
        snapshot_body = str(inline_snapshot.get("body") or "").strip()
        if snapshot_body:
            lines.append("【画像快照】")
            lines.append(snapshot_body)

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

    for key, meta in telemetry["high_value_fields"].items():
        if meta.get("collected") and not meta.get("rendered"):
            telemetry["dropped_high_value_fields"].append(key)

    return ("\n".join(lines) if lines else "暂无上下文信息", telemetry)


def format_user_context(
    context: dict,
    context_level: str = "full",
    context_focus: dict[str, Any] | None = None,
) -> str:
    """格式化用户上下文"""
    rendered, _telemetry = _render_user_context_content(
        context,
        context_level=context_level,
        context_focus=context_focus,
    )
    return rendered


def _format_past_session_memory_section(user_context: dict[str, Any] | None) -> str:
    if not isinstance(user_context, dict):
        return ""
    raw_items = user_context.get("past_session_memory") or []
    if not isinstance(raw_items, list):
        return ""

    lines: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        summary = ""
        subject = ""
        source = ""
        occurred_at = None
        tags: list[str] = []
        if isinstance(item, dict):
            summary = str(
                item.get("summary") or item.get("text") or item.get("content") or item.get("title") or ""
            ).strip()
            subject = str(item.get("subject_type") or "").strip()
            source = str(item.get("source_type") or "").strip()
            occurred_at = item.get("occurred_at")
            raw_tags = item.get("tags") or []
            if isinstance(raw_tags, list):
                tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        else:
            summary = str(getattr(item, "summary", item) or "").strip()
            subject = str(getattr(item, "subject_type", "") or "").strip()
            source = str(getattr(item, "source_type", "") or "").strip()
            occurred_at = getattr(item, "occurred_at", None)
            raw_tags = getattr(item, "tags", []) or []
            if isinstance(raw_tags, list):
                tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        if not summary or summary in seen:
            continue
        seen.add(summary)
        qualifiers = [
            label
            for label in (
                _format_memory_recency_label(occurred_at),
                subject,
                source,
            )
            if label
        ]
        prefix = f"[{' / '.join(qualifiers)}] " if qualifiers else ""
        tag_suffix = f" tags={', '.join(tags[:3])}" if tags else ""
        lines.append(f"{prefix}{summary}{tag_suffix}")
        if len(lines) >= 3:
            break

    if not lines:
        return ""
    return (
        "## 跨会话记忆 [L2 引导]\n"
        "当用户问候、含糊开场、请求继续学习，或本轮内容与以下记忆相关时，"
        "请自然衔接上次内容；不要生硬复述，也不要引用与当前请求无关的记忆。\n"
        + "\n".join(f"- {line}" for line in lines)
    )


def _format_memory_recency_label(value: Any) -> str:
    occurred_at = _parse_memory_datetime(value)
    if occurred_at is None:
        return ""

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = now - occurred_at
    if delta.total_seconds() < 0:
        return "刚才"
    if delta.total_seconds() < 2 * 3600:
        return "刚才"
    days = delta.days
    if days == 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days <= 6:
        return f"{days}天前"
    if days <= 13:
        return "上周"
    return occurred_at.date().isoformat()


def _parse_memory_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _format_capsule_preference_section(user_context: dict[str, Any] | None) -> str:
    preferences = _extract_capsule_preferences(user_context)
    if not preferences:
        return ""

    favorite_count = int(preferences.get("favorite_count") or 0)
    depth = str(preferences.get("content_depth_preference") or "").strip()
    subjects = [
        str(subject).strip()
        for subject in list(preferences.get("subject_affinity") or preferences.get("content_subject_affinities") or [])
        if str(subject).strip()
    ][:3]
    notes = [str(note).strip() for note in list(preferences.get("recent_notes") or []) if str(note).strip()][:3]
    methods = [
        method
        for method in list(preferences.get("method_preferences") or preferences.get("capsule_method_preferences") or [])
        if isinstance(method, dict) and str(method.get("label") or "").strip()
    ][:3]
    method_summaries = [
        str(item).strip() for item in list(preferences.get("method_preference_summary") or []) if str(item).strip()
    ][:3]
    if not method_summaries:
        method_summaries = [f"用户偏好{str(method.get('label') or '').strip()}" for method in methods]
    if favorite_count <= 0 and not depth and not subjects and not notes and not method_summaries:
        return ""

    lines = [
        "## 胶囊内容偏好 [L2 引导]",
        "这些信号来自用户收藏过的认知胶囊，用来调整讲解深度、例子选择和推送密度；当前请求冲突时，以当前请求为准。",
    ]
    if favorite_count > 0:
        lines.append(f"- 收藏样本: {favorite_count} 个胶囊")
    if depth:
        lines.append(f"- 内容深度偏好: {depth}")
    if subjects:
        lines.append(f"- 主题亲和: {', '.join(subjects)}")
    if notes:
        lines.append(f"- 收藏备注: {'; '.join(notes)}")
    if method_summaries:
        lines.append(f"- 方法偏好: {'; '.join(method_summaries)}")

    if depth == "deep":
        lines.append("- 行为适配: 优先给完整推理链、关键反例和体系化小结，减少碎片化提示。")
    elif depth == "shallow":
        lines.append("- 行为适配: 优先给短步骤和轻量提醒，只在用户要求时展开。")
    elif depth:
        lines.append("- 行为适配: 保持标准深度，先给主线，再按用户反应补充。")
    if subjects:
        lines.append("- 行为适配: 当任务涉及上述主题时，给更具体的例子、检查点和复盘提示。")
    if methods or method_summaries:
        lines.append("- 行为适配: 当用户要安排学习节奏、启动任务或复盘方法时，优先尝试这些方法偏好。")
    return "\n".join(lines)


def _format_spine_model_claims_section(user_context: dict[str, Any] | None) -> str:
    """R5-DF1: Render Spine model-write claims as prompt context for AI."""
    if not isinstance(user_context, dict):
        return ""
    claims = user_context.get("spine_model_claims")
    if not isinstance(claims, list) or not claims:
        return ""
    lines = [
        "## 系统推断的用户特征 [Spine Signal]",
        "以下特征由 Signal-to-Action Spine 从用户行为中推断得出。在响应中自然体现，但不要直接提及 '系统推断'。",
    ]
    for claim in claims[:5]:
        if not isinstance(claim, dict):
            continue
        model = str(claim.get("target_model") or "").strip()
        scope = str(claim.get("scope") or "").strip()
        value = str(claim.get("value") or "").strip()
        if model or scope:
            lines.append(f"- {model}/{scope}: {value}" if scope else f"- {model}: {value}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _format_spine_community_skill_section(user_context: dict[str, Any] | None) -> str:
    """R5-DF2/DF3: Render Community + Skill directives as prompt context."""
    if not isinstance(user_context, dict):
        return ""
    lines = []
    comm = user_context.get("spine_community_directive")
    if isinstance(comm, dict) and comm:
        hint = str(comm.get("hint") or comm.get("summary") or "").strip()
        if hint:
            lines.append("## 社群信号指导 [Spine Community]")
            lines.append(hint)
    skill = user_context.get("spine_skill_directive")
    if isinstance(skill, dict) and skill:
        hint = str(skill.get("hint") or skill.get("summary") or "").strip()
        if hint:
            lines.append("## 技能建议 [Spine Skill]")
            lines.append(hint)
    return "\n\n".join(lines) if lines else ""


def _extract_capsule_preferences(user_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(user_context, dict):
        return {}

    candidates: list[dict[str, Any]] = []

    def add_candidate(value: Any) -> None:
        if isinstance(value, dict):
            candidates.append(value)

    add_candidate(user_context.get("capsule_preferences"))
    cognitive_context = user_context.get("cognitive_context")
    if isinstance(cognitive_context, dict):
        add_candidate(cognitive_context.get("capsule_preferences"))

    preferences = user_context.get("preferences")
    if isinstance(preferences, dict):
        add_candidate(preferences.get("capsule_preferences"))
        if "capsule_preferences" not in preferences and (
            preferences.get("content_depth_preference")
            or preferences.get("content_subject_affinities")
            or preferences.get("capsule_method_preferences")
        ):
            candidates.append(
                {
                    "content_depth_preference": preferences.get("content_depth_preference"),
                    "subject_affinity": preferences.get("content_subject_affinities") or [],
                    "favorite_count": preferences.get("capsule_favorite_count") or 0,
                    "method_preferences": preferences.get("capsule_method_preferences") or [],
                }
            )

    profile_context = user_context.get("profile_context")
    if isinstance(profile_context, dict):
        insight_state = profile_context.get("user_insight_state")
        if isinstance(insight_state, dict):
            stable_preferences = insight_state.get("stable_preferences") or {}
            if isinstance(stable_preferences, dict):
                add_candidate(stable_preferences.get("capsule"))
                if "capsule" not in stable_preferences and (
                    stable_preferences.get("content_depth_preference")
                    or stable_preferences.get("content_subject_affinities")
                    or stable_preferences.get("capsule_method_preferences")
                ):
                    candidates.append(
                        {
                            "content_depth_preference": stable_preferences.get("content_depth_preference"),
                            "subject_affinity": stable_preferences.get("content_subject_affinities") or [],
                            "favorite_count": stable_preferences.get("capsule_favorite_count") or 0,
                            "method_preferences": stable_preferences.get("capsule_method_preferences") or [],
                        }
                    )

    merged: dict[str, Any] = {}
    for candidate in candidates:
        for key in (
            "favorite_count",
            "content_depth_preference",
            "subject_affinity",
            "recent_notes",
            "method_preferences",
            "method_preference_summary",
        ):
            value = candidate.get(key)
            if value not in (None, "", [], {}) and key not in merged:
                merged[key] = value
    return merged


def _extract_canonical_signal(
    insight: UserInsightState | None,
    key: str,
) -> Any:
    """Extract a high-value signal from the canonical UserInsightState.

    Maps the normalizer key names to the compiled state fields:
      - error_summary → signal_evidence with signal_id="error_summary" → value
      - recent_errors → signal_evidence with signal_id="recent_errors" → value
      - recent_mastery_changes → recent_wins shaped as mastery-change dicts
    """
    if insight is None:
        return None

    if key == "error_summary":
        for evidence in insight.signal_evidence:
            if evidence.signal_id == "error_summary" and _has_signal_payload(evidence.value):
                return evidence.value
        return None

    if key == "recent_errors":
        for evidence in insight.signal_evidence:
            if evidence.signal_id == "recent_errors" and _has_signal_payload(evidence.value):
                return evidence.value
        return None

    if key == "recent_mastery_changes":
        wins = insight.recent_wins or []
        if not wins:
            return None
        shaped: list[dict[str, Any]] = []
        for win in wins[:5]:
            if not isinstance(win, dict):
                continue
            shaped.append(
                {
                    "node_name": win.get("label") or win.get("node_name") or "",
                    "old_mastery": win.get("old_mastery"),
                    "new_mastery": win.get("new_mastery"),
                }
            )
        return shaped if shaped else None

    return None


def _normalize_user_context(context: dict) -> dict:
    """统一用户画像结构，避免字段重复与冲突"""
    normalized: dict[str, Any] = {}
    cognitive_context = _extract_cognitive_context_payload(context)
    profile_context = _extract_profile_context_payload(context)
    canonical_insight = _extract_canonical_insight_state(context)

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
    if "knowledge_summary" not in normalized:
        profile_knowledge_summary = (
            profile_context.get("knowledge_summary") if isinstance(profile_context, dict) else None
        )
        if isinstance(profile_knowledge_summary, dict):
            normalized["knowledge_summary"] = profile_knowledge_summary

    for key in ("error_summary", "recent_errors", "recent_mastery_changes"):
        # --- canonical insight state (priority) ---
        canonical_value = _extract_canonical_signal(canonical_insight, key)
        if _has_signal_payload(canonical_value):
            normalized[key] = canonical_value
            normalized["_canonical_signal_source"] = normalized.get("_canonical_signal_source") or set()
            normalized["_canonical_signal_source"].add(key)
            continue
        # --- original raw-dict cascade (fallback) ---
        direct_value = context.get(key)
        if _has_signal_payload(direct_value):
            normalized[key] = direct_value
            continue
        cognitive_value = cognitive_context.get(key)
        if _has_signal_payload(cognitive_value):
            normalized[key] = cognitive_value
            continue
        profile_value = profile_context.get(key) if isinstance(profile_context, dict) else None
        if _has_signal_payload(profile_value):
            normalized[key] = profile_value
            continue
        if key == "recent_mastery_changes" and isinstance(profile_context, dict):
            knowledge_summary = profile_context.get("knowledge_summary")
            if isinstance(knowledge_summary, dict):
                nested_value = knowledge_summary.get("recent_mastery_changes")
                if _has_signal_payload(nested_value):
                    normalized[key] = nested_value

    llm_profile = context.get("llm_profile")
    if isinstance(llm_profile, dict):
        normalized["llm_profile"] = llm_profile

    if context.get("analytics_summary"):
        normalized["analytics_summary"] = context["analytics_summary"]

    if context.get("next_actions"):
        normalized["next_actions"] = context["next_actions"]
    if context.get("active_tasks"):
        normalized["active_tasks"] = context["active_tasks"]
        if not normalized.get("next_actions"):
            normalized["next_actions"] = context["active_tasks"]

    if context.get("focus_stats"):
        normalized["focus_stats"] = context["focus_stats"]

    if isinstance(context.get("achievement_summary"), dict):
        normalized["achievement_summary"] = context["achievement_summary"]

    if isinstance(context.get("calendar_context"), dict):
        normalized["calendar_context"] = context["calendar_context"]
        if not normalized.get("exam_urgency"):
            exam_urgency = context["calendar_context"].get("exam_urgency")
            if isinstance(exam_urgency, dict):
                normalized["exam_urgency"] = exam_urgency

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

    if isinstance(context.get("user_strategy_state"), dict):
        normalized["user_strategy_state"] = context["user_strategy_state"]
    if isinstance(context.get("residual_decision_context"), dict):
        normalized["residual_decision_context"] = context["residual_decision_context"]
    if isinstance(context.get("user_material_grounding"), dict):
        normalized["user_material_grounding"] = context["user_material_grounding"]
    stage33_social_payload = _extract_stage33_social_payload(context)
    if isinstance(stage33_social_payload, dict) and stage33_social_payload:
        normalized["social_signals_summary"] = stage33_social_payload
    stage33_srl_payload = _extract_stage33_srl_payload(context)
    if isinstance(stage33_srl_payload, dict) and stage33_srl_payload:
        normalized["srl_phase"] = stage33_srl_payload
    working_memory_snapshot = _extract_working_memory_payload(context)
    if isinstance(working_memory_snapshot, dict) and working_memory_snapshot:
        normalized["working_memory_snapshot"] = working_memory_snapshot
    if isinstance(context.get("social_context"), dict):
        normalized["social_context"] = context["social_context"]

    # --- Canonical insight state enrichment ---
    if canonical_insight is not None:
        # Inline snapshot for prompt injection
        normalized["_inline_snapshot"] = canonical_insight.to_inline_snapshot(
            capsule_mode=_resolve_stage34_capsule_mode(context)
        )
        # Goals from compiled state, only if not already provided
        if not normalized.get("active_goals") and canonical_insight.goals:
            normalized["active_goals"] = [
                {"title": str(g.get("label") or g.get("type") or ""), "status": "active"}
                for g in canonical_insight.goals[:3]
                if isinstance(g, dict)
            ]
        # Preferred tools from compiled state
        if not normalized.get("preferred_tools"):
            tools = (canonical_insight.inferred_work_style or {}).get("preferred_tools")
            if isinstance(tools, list) and tools:
                normalized["preferred_tools"] = tools
        # Exam urgency from compiled state
        if not normalized.get("exam_urgency"):
            cal = (canonical_insight.temporal_patterns or {}).get("calendar")
            if isinstance(cal, dict) and cal.get("exam_urgency"):
                normalized["exam_urgency"] = cal["exam_urgency"]

    return normalized


def _resolve_semantic_control_from_context(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context if isinstance(context, dict) else {}
    situation_brief = context.get("situation_brief")
    if isinstance(situation_brief, dict):
        semantic_control = situation_brief.get("semantic_control")
        if isinstance(semantic_control, dict) and semantic_control:
            return semantic_control

    decision_context = context.get("residual_decision_context")
    if not isinstance(decision_context, dict) and isinstance(situation_brief, dict):
        decision_context = situation_brief.get("decision_context")
    planning_strategy = {}
    if isinstance(situation_brief, dict) and isinstance(situation_brief.get("planning_strategy"), dict):
        planning_strategy = situation_brief.get("planning_strategy") or {}

    return build_semantic_control(
        decision_context=decision_context if isinstance(decision_context, dict) else {},
        planning_strategy=planning_strategy,
        body_awareness_guidance=(
            decision_context.get("body_awareness_guidance") if isinstance(decision_context, dict) else {}
        ),
        user_strategy_state=(
            context.get("user_strategy_state") if isinstance(context.get("user_strategy_state"), dict) else {}
        ),
        outcome_learning=(situation_brief.get("outcome_learning") if isinstance(situation_brief, dict) else {}),
        language="zh",
    ).to_dict()


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
            type_names = {"cognitive": "认知", "emotional": "情绪", "execution": "执行"}
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
        tail = prompt[-(max_chars // 2) :]
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
