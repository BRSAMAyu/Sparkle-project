from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass(frozen=True)
class ReviewProfile:
    id: str
    display_name: str
    objective: str
    evaluation_focus: list[str]
    metric_specs: list[dict[str, Any]]
    issue_guidance: list[str]
    reflection_targets: list[str]


@dataclass
class HandoffPacket:
    agent: str
    summary: str
    key_conclusions: list[str]
    evidence_or_reasoning: list[str]
    open_questions: list[str]
    constraints_for_next_agent: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "key_conclusions": list(self.key_conclusions),
            "evidence_or_reasoning": list(self.evidence_or_reasoning),
            "open_questions": list(self.open_questions),
            "constraints_for_next_agent": list(self.constraints_for_next_agent),
        }

    def to_prompt_block(self) -> str:
        sections = [f"### {self.agent}", f"- 摘要: {self.summary}"]
        if self.key_conclusions:
            sections.append("- 关键结论: " + "；".join(self.key_conclusions[:3]))
        if self.evidence_or_reasoning:
            sections.append("- 依据/推理: " + "；".join(self.evidence_or_reasoning[:2]))
        if self.open_questions:
            sections.append("- 未决问题: " + "；".join(self.open_questions[:2]))
        if self.constraints_for_next_agent:
            sections.append("- 下游约束: " + "；".join(self.constraints_for_next_agent[:2]))
        return "\n".join(sections)


_DEFAULT_REVIEW_PROFILE = ReviewProfile(
    id="default_response",
    display_name="通用回答审查",
    objective="评估回答是否准确、完整、相关、清晰且对用户真正有帮助。",
    evaluation_focus=[
        "优先检查事实准确性、任务完成度和用户意图贴合度。",
        "发现问题时必须指出具体位置，并给出可执行修复建议。",
    ],
    metric_specs=[
        {"metric": "accuracy", "weight": 1.5, "threshold": 0.8, "note": "事实是否正确"},
        {"metric": "completeness", "weight": 1.2, "threshold": 0.7, "note": "是否完整回应用户需求"},
        {"metric": "relevance", "weight": 1.3, "threshold": 0.7, "note": "是否紧贴用户意图"},
        {"metric": "clarity", "weight": 1.0, "threshold": 0.65, "note": "表达是否清晰有条理"},
        {"metric": "helpfulness", "weight": 1.1, "threshold": 0.7, "note": "是否可直接帮助用户"},
        {"metric": "safety", "weight": 2.0, "threshold": 0.9, "note": "是否安全、无误导"},
    ],
    issue_guidance=[
        "问题描述要定位到段落或结构位置。",
        "若整体可用但仍需打磨，优先给 needs_refinement 而不是 failed。",
    ],
    reflection_targets=[
        "补全遗漏信息",
        "修正不准确表述",
        "增强结构清晰度和可执行性",
    ],
)

_STUDY_PLAN_REVIEW_PROFILE = ReviewProfile(
    id="study_plan",
    display_name="任务拆解/学习规划审查",
    objective="评估计划是否完整、可执行、依赖顺序合理，并且适合真实落地。",
    evaluation_focus=[
        "重点关注 completeness / feasibility / dependency_order / actionability / safety。",
        "弱化文采和语气，重点看是否能真正执行。",
    ],
    metric_specs=[
        {"metric": "completeness", "weight": 1.4, "threshold": 0.75, "note": "关键步骤是否齐全"},
        {"metric": "feasibility", "weight": 1.5, "threshold": 0.75, "note": "执行成本和资源是否现实"},
        {"metric": "efficiency", "weight": 1.1, "threshold": 0.65, "note": "步骤排序是否高效"},
        {"metric": "helpfulness", "weight": 1.1, "threshold": 0.7, "note": "是否提供明确行动路径"},
        {"metric": "safety", "weight": 1.8, "threshold": 0.9, "note": "是否规避高风险建议"},
    ],
    issue_guidance=[
        "优先指出缺失前置条件、时间预算不现实、依赖顺序混乱的问题。",
        "若计划缺少可操作动作或里程碑，应明确标为 warning 或 critical。",
    ],
    reflection_targets=[
        "补齐缺失步骤与前置条件",
        "重排依赖顺序",
        "把建议改写为更可执行的动作",
    ],
)

_DEEP_ANALYSIS_REVIEW_PROFILE = ReviewProfile(
    id="deep_analysis",
    display_name="讲解/深度分析审查",
    objective="评估讲解是否准确、层层递进、证据对齐，并能真正帮助用户理解。",
    evaluation_focus=[
        "重点关注 accuracy / clarity / pedagogical_progression / evidence_alignment / conceptual_gaps。",
        "如果解释跳步、没有过渡、缺少关键概念桥梁，要明确指出。",
    ],
    metric_specs=[
        {"metric": "accuracy", "weight": 1.5, "threshold": 0.8, "note": "概念和事实是否准确"},
        {"metric": "clarity", "weight": 1.3, "threshold": 0.7, "note": "是否易懂、层次清晰"},
        {"metric": "completeness", "weight": 1.1, "threshold": 0.7, "note": "关键解释链条是否完整"},
        {"metric": "relevance", "weight": 1.0, "threshold": 0.7, "note": "是否紧扣用户想理解的点"},
        {"metric": "helpfulness", "weight": 1.2, "threshold": 0.75, "note": "是否真正提升理解"},
        {"metric": "safety", "weight": 1.5, "threshold": 0.9, "note": "是否避免错误类比或误导"},
    ],
    issue_guidance=[
        "优先指出概念跳跃、类比误导、证据不足、解释链条断裂。",
        "若内容正确但难以理解，应该给 needs_refinement 并要求重构表达顺序。",
    ],
    reflection_targets=[
        "补上关键过渡",
        "修正概念跳步",
        "增加更贴切的解释或例子",
    ],
)

_ERROR_DIAGNOSIS_REVIEW_PROFILE = ReviewProfile(
    id="error_diagnosis",
    display_name="错题分析审查",
    objective="评估错因定位是否精准，误区覆盖是否充分，补救建议和迁移练习是否有效。",
    evaluation_focus=[
        "重点关注 root_cause_precision / misconception_coverage / remediation_quality / transfer_exercise_quality。",
        "弱化泛泛安慰，重点看是否真正抓住错因。",
    ],
    metric_specs=[
        {"metric": "accuracy", "weight": 1.4, "threshold": 0.78, "note": "错因判断是否准确"},
        {"metric": "completeness", "weight": 1.2, "threshold": 0.72, "note": "是否覆盖关键误区"},
        {"metric": "helpfulness", "weight": 1.4, "threshold": 0.78, "note": "补救动作是否有效"},
        {"metric": "clarity", "weight": 1.0, "threshold": 0.68, "note": "诊断结构是否清晰"},
        {"metric": "relevance", "weight": 1.1, "threshold": 0.72, "note": "是否直击用户这道题/这个误区"},
        {"metric": "safety", "weight": 1.4, "threshold": 0.9, "note": "是否避免误导学习方向"},
    ],
    issue_guidance=[
        "优先指出把症状当根因、缺少误区覆盖、补救动作不具体、迁移练习无针对性的问题。",
        "如果回答停留在表面描述而没有诊断逻辑，应至少标 warning。",
    ],
    reflection_targets=[
        "重新定位根因",
        "补上误区解释与修复动作",
        "提供更贴近原题型的迁移练习",
    ],
)

_EXPLICIT_COLLAB_REVIEW_PROFILE = ReviewProfile(
    id="explicit_expert_collaboration",
    display_name="显式多专家协作审查",
    objective="评估多视角是否被保留、冲突是否被处理、综合结论是否清晰可信。",
    evaluation_focus=[
        "重点关注 viewpoint_diversity_retention / contradiction_handling / synthesis_quality / final_recommendation_clarity。",
        "不要把多专家答案按单一普通回答标准粗暴压平。",
    ],
    metric_specs=[
        {"metric": "accuracy", "weight": 1.3, "threshold": 0.78, "note": "最终结论是否可靠"},
        {"metric": "completeness", "weight": 1.2, "threshold": 0.72, "note": "是否覆盖主要专家视角"},
        {"metric": "relevance", "weight": 1.1, "threshold": 0.72, "note": "综合是否贴合用户任务"},
        {"metric": "clarity", "weight": 1.1, "threshold": 0.7, "note": "综合表达是否清晰"},
        {"metric": "helpfulness", "weight": 1.3, "threshold": 0.78, "note": "是否给出可执行最终建议"},
        {"metric": "safety", "weight": 1.5, "threshold": 0.9, "note": "是否避免错误综合或遗漏风险"},
    ],
    issue_guidance=[
        "优先指出观点被抹平、分歧未解释、综合结论无依据、建议不够明确的问题。",
        "允许存在合理分歧，但必须看见分歧并给出最后判断。",
    ],
    reflection_targets=[
        "保留关键分歧",
        "补充综合依据",
        "把最终建议写得更清晰",
    ],
)

_REVIEW_PROFILES = {
    _DEFAULT_REVIEW_PROFILE.id: _DEFAULT_REVIEW_PROFILE,
    _STUDY_PLAN_REVIEW_PROFILE.id: _STUDY_PLAN_REVIEW_PROFILE,
    _DEEP_ANALYSIS_REVIEW_PROFILE.id: _DEEP_ANALYSIS_REVIEW_PROFILE,
    _ERROR_DIAGNOSIS_REVIEW_PROFILE.id: _ERROR_DIAGNOSIS_REVIEW_PROFILE,
    _EXPLICIT_COLLAB_REVIEW_PROFILE.id: _EXPLICIT_COLLAB_REVIEW_PROFILE,
}

_BUILTIN_FEW_SHOT_EXAMPLES: dict[tuple[str, str, str], list[dict[str, Any]]] = {
    ("task_decomposition", "collaboration", "study_planner"): [
        {
            "input": "帮我在两周内准备离散数学期中考试。",
            "output": "先拆出知识模块、每日任务和复盘节点，再给出可执行时间表与优先级。",
            "explanation": "强调计划拆解、依赖顺序和可执行动作。",
        }
    ],
    ("task_decomposition", "synthesis", "synthesis"): [
        {
            "input": "综合多个学习建议，输出统一计划。",
            "output": "先总结主线，再把不同专家建议映射到每日/每周动作，最后给关键提醒。",
            "explanation": "综合时先落行动，再补解释。",
        }
    ],
    ("progressive_exploration", "collaboration", "math"): [
        {
            "input": "解释一个复杂概念。",
            "output": "先给核心原理，再逐步推导关键公式或逻辑，不要一次跳到结论。",
            "explanation": "强调层层递进。",
        }
    ],
    ("progressive_exploration", "collaboration", "science"): [
        {
            "input": "给出跨学科类比。",
            "output": "类比只服务于理解，不替代原概念；先说相似点，再提醒边界。",
            "explanation": "避免误导类比。",
        }
    ],
    ("progressive_exploration", "collaboration", "writing"): [
        {
            "input": "将多角度解释整理成笔记。",
            "output": "先写一句总纲，再按概念、例子、记忆钩子三段压缩，不重复上游原文。",
            "explanation": "强调压缩与连贯。",
        }
    ],
    ("error_diagnosis", "collaboration", "problem_solver"): [
        {
            "input": "分析一道经常做错的题。",
            "output": "先区分症状和根因，再指出误区，最后给修复动作与迁移练习建议。",
            "explanation": "重点抓根因，而不是只重述错误。",
        }
    ],
    ("explicit_expert_collaboration", "synthesis", "synthesis"): [
        {
            "input": "综合多位专家观点。",
            "output": "保留关键分歧，用一句话说明谁支持什么，再给最终判断和适用条件。",
            "explanation": "避免把多视角答案压成单一口径。",
        }
    ],
}


def normalize_agent_role_key(role: str | None) -> str:
    value = str(role or "").strip().lower().replace(" ", "_")
    aliases = {
        "math_expert": "math",
        "code_expert": "code",
        "writing_expert": "writing",
        "science_expert": "science",
        "problemsolver": "problem_solver",
        "problem_solveragent": "problem_solver",
        "studyplanner": "study_planner",
        "study_planneragent": "study_planner",
        "search": "search",
        "searchexpert": "search",
    }
    return aliases.get(value, value)


def build_workflow_context(
    *,
    workflow_type: str | None = None,
    chat_mode: str | None = None,
    collaboration_mode: str | None = None,
    target_type: str | None = None,
) -> dict[str, str]:
    return {
        "workflow_type": str(workflow_type or "").strip().lower(),
        "chat_mode": str(chat_mode or "").strip().lower(),
        "collaboration_mode": str(collaboration_mode or "").strip().lower(),
        "target_type": str(target_type or "").strip().lower(),
    }


def resolve_review_profile_id(
    review_profile_id: str | None = None,
    workflow_context: dict[str, Any] | None = None,
    *,
    target_type: str = "response",
) -> str:
    if review_profile_id and review_profile_id in _REVIEW_PROFILES:
        return review_profile_id

    workflow_context = workflow_context or {}
    workflow_type = str(workflow_context.get("workflow_type") or "").strip().lower()
    chat_mode = str(workflow_context.get("chat_mode") or "").strip().lower()

    if target_type == "plan":
        return _STUDY_PLAN_REVIEW_PROFILE.id
    if workflow_type in {"task_decomposition"} or chat_mode == "study_plan":
        return _STUDY_PLAN_REVIEW_PROFILE.id
    if workflow_type in {"progressive_exploration"} or chat_mode == "deep_analysis":
        return _DEEP_ANALYSIS_REVIEW_PROFILE.id
    if workflow_type in {"error_diagnosis"} or chat_mode == "error_diagnosis":
        return _ERROR_DIAGNOSIS_REVIEW_PROFILE.id
    if workflow_type in {"explicit_expert_collaboration"}:
        return _EXPLICIT_COLLAB_REVIEW_PROFILE.id
    return _DEFAULT_REVIEW_PROFILE.id


def get_review_profile(
    review_profile_id: str | None = None,
    workflow_context: dict[str, Any] | None = None,
    *,
    target_type: str = "response",
) -> ReviewProfile:
    profile_id = resolve_review_profile_id(
        review_profile_id=review_profile_id,
        workflow_context=workflow_context,
        target_type=target_type,
    )
    return _REVIEW_PROFILES.get(profile_id, _DEFAULT_REVIEW_PROFILE)


def build_reviewer_system_prompt(profile: ReviewProfile) -> str:
    metric_lines = []
    for spec in profile.metric_specs:
        metric_lines.append(
            f"| {spec['metric']} | {spec['note']} | {float(spec['weight']):.1f} | {float(spec['threshold']):.2f} |"
        )

    focus_lines = "\n".join(f"- {item}" for item in profile.evaluation_focus)
    guidance_lines = "\n".join(f"- {item}" for item in profile.issue_guidance)
    return f"""你是一位严格但公正的内容审查专家。你的职责是评估 AI 生成内容的质量。

## 当前审查画像

- 画像ID: {profile.id}
- 名称: {profile.display_name}
- 目标: {profile.objective}

## 审查重点
{focus_lines}

## 评估维度

| 维度 | 说明 | 权重 | 阈值 |
|------|------|------|------|
{chr(10).join(metric_lines)}

## 问题标注要求
{guidance_lines}

## 输出格式

请以 JSON 返回审查结果：
{{
  "overall_score": 0.0-1.0,
  "decision": "passed|failed|needs_refinement",
  "metrics": [
    {{"metric": "accuracy", "score": 0.8, "weight": 1.5, "threshold": 0.8}}
  ],
  "issues": [
    {{
      "category": "类别",
      "severity": "critical|warning|info",
      "location": "具体位置",
      "description": "精准描述问题",
      "affected_content": "受影响片段",
      "suggested_fix": "可执行修复建议",
      "confidence": 0.0-1.0
    }}
  ],
  "improvement_suggestions": ["建议1", "建议2"],
  "requires_reflection": true/false,
  "timestamp": "ISO时间戳"
}}

返回时不要添加 Markdown 包裹。"""


def build_response_review_prompt(
    *,
    profile: ReviewProfile,
    user_query: str,
    llm_response: str,
    turn_count: int,
    has_tools: bool,
    tool_list: list[str] | str,
    workflow_context: dict[str, Any] | None = None,
) -> str:
    workflow_context = workflow_context or {}
    tool_text = "、".join(tool_list) if isinstance(tool_list, list) else str(tool_list)
    reflection_targets = "\n".join(f"- {item}" for item in profile.reflection_targets)
    return f"""请审查以下 AI 响应：

【审查画像】
- profile_id: {profile.id}
- workflow_type: {workflow_context.get("workflow_type") or "unknown"}
- chat_mode: {workflow_context.get("chat_mode") or "unknown"}
- collaboration_mode: {workflow_context.get("collaboration_mode") or "unknown"}

【用户原始问题】
{user_query}

【AI 响应】
{llm_response[:2200]}

【上下文信息】
- 对话轮次: {turn_count}
- 是否包含工具调用: {"是" if has_tools else "否"}
- 工具列表: {tool_text}

【本轮特别关注】
{reflection_targets}

请严格按照当前审查画像评估，不要套用通用模板。"""


def build_plan_review_prompt(
    *,
    profile: ReviewProfile,
    user_query: str,
    plan_content: str,
    confidence: str,
    tool_count: int,
    risk_flags: str,
    workflow_context: dict[str, Any] | None = None,
) -> str:
    workflow_context = workflow_context or {}
    return f"""请审查以下执行计划：

【审查画像】
- profile_id: {profile.id}
- workflow_type: {workflow_context.get("workflow_type") or "unknown"}
- chat_mode: {workflow_context.get("chat_mode") or "unknown"}

【用户原始问题】
{user_query}

【执行计划】
{plan_content[:2200]}

【计划元信息】
- 计划置信度: {confidence}
- 工具调用数: {tool_count}
- 风险标记: {risk_flags}

请重点检查计划完整性、可执行性、依赖顺序和风险控制。"""


def build_reflection_system_prompt(profile: ReviewProfile) -> str:
    targets = "\n".join(f"- {item}" for item in profile.reflection_targets)
    focus = "\n".join(f"- {item}" for item in profile.evaluation_focus)
    return f"""你是一位内容优化专家，负责基于审查反馈修正 AI 生成的内容。

## 当前修正画像
- 画像ID: {profile.id}
- 名称: {profile.display_name}
- 目标: {profile.objective}

## 修正重点
{targets}

## 审查关注点回放
{focus}

## 修正原则
1. 只针对审查指出的问题做精准修复。
2. 保留原回答已经做对的部分。
3. 优先修复 critical 和 warning，再考虑 info。
4. 输出修正后的完整内容，不要附加解释。"""


def inject_examples_into_user_context(
    user_context: dict[str, Any] | None,
    examples: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = dict(user_context or {})
    if not examples:
        return payload
    payload["seed_library"] = {
        "has_seed_library": True,
        "few_shot_examples": examples[:3],
    }
    return payload


def should_inject_few_shot(
    *,
    workflow_type: str,
    stage: str,
    agent_role: str,
    is_final_target: bool = False,
) -> bool:
    role = normalize_agent_role_key(agent_role)
    workflow = str(workflow_type or "").strip().lower()
    stage_value = str(stage or "").strip().lower()

    if workflow == "task_decomposition":
        return role in {"study_planner", "synthesis"} and stage_value in {"collaboration", "synthesis"}
    if workflow == "progressive_exploration":
        return role in {"math", "science", "writing"} and stage_value == "collaboration"
    if workflow == "error_diagnosis":
        return role == "problem_solver" and stage_value == "collaboration"
    if workflow == "explicit_expert_collaboration":
        return stage_value == "synthesis" or is_final_target
    return False


def _make_tag_combinations(
    *,
    workflow_type: str,
    chat_mode: str,
    agent_role: str,
    stage: str,
) -> list[list[str]]:
    workflow_tag = f"workflow:{workflow_type}" if workflow_type else ""
    mode_tag = f"mode:{chat_mode}" if chat_mode else ""
    role_tag = f"role:{agent_role}" if agent_role else ""
    stage_tag = f"stage:{stage}" if stage else ""

    candidates = [
        [workflow_tag, mode_tag, role_tag, stage_tag],
        [workflow_tag, role_tag, stage_tag],
        [workflow_tag, stage_tag],
        [role_tag, stage_tag],
        [workflow_tag],
    ]
    return [[tag for tag in combo if tag] for combo in candidates if any(combo)]


async def resolve_few_shot_examples(
    *,
    db_session: Any | None,
    user_id: str | uuid.UUID | None,
    workflow_type: str,
    chat_mode: str,
    agent_role: str,
    stage: str,
    count: int = 1,
) -> list[dict[str, Any]]:
    normalized_role = normalize_agent_role_key(agent_role)
    workflow = str(workflow_type or "").strip().lower()
    stage_value = str(stage or "").strip().lower()
    mode = str(chat_mode or "").strip().lower()

    if db_session is not None and user_id:
        try:
            from app.services.seed_library_service import SeedLibraryService

            service = SeedLibraryService()
            user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            seen: set[tuple[str, str]] = set()
            collected: list[dict[str, Any]] = []
            for tags in _make_tag_combinations(
                workflow_type=workflow,
                chat_mode=mode,
                agent_role=normalized_role,
                stage=stage_value,
            ):
                examples = await service.get_few_shot_examples(
                    db_session,
                    user_id=user_uuid,
                    count=count,
                    tags=tags,
                    match_all_tags=True,
                )
                for item in examples:
                    key = (str(item.get("input") or ""), str(item.get("output") or ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append(item)
                    if len(collected) >= count:
                        return collected
        except Exception as exc:
            logger.warning(f"[WorkflowExperience] Seed library lookup failed: {exc}")

    builtin = _BUILTIN_FEW_SHOT_EXAMPLES.get((workflow, stage_value, normalized_role), [])
    return builtin[:count]


def format_few_shot_examples(examples: list[dict[str, Any]]) -> str:
    if not examples:
        return ""
    lines = ["## 协作示例参考"]
    for example in examples[:1]:
        input_text = str(example.get("input") or "").strip()
        output_text = str(example.get("output") or "").strip()
        explanation = str(example.get("explanation") or "").strip()
        if input_text:
            lines.append(f"- 示例任务: {input_text}")
        if output_text:
            lines.append(f"- 示例输出风格: {output_text}")
        if explanation:
            lines.append(f"- 示例提示: {explanation}")
    return "\n".join(lines)


def _split_sentences(text: str) -> list[str]:
    normalized = str(text or "").replace("\r", "\n")
    segments: list[str] = []
    for raw in normalized.splitlines():
        cleaned = raw.strip(" -*\t")
        if not cleaned:
            continue
        parts = [
            part.strip()
            for part in cleaned.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").splitlines()
            if part.strip()
        ]
        segments.extend(parts or [cleaned])
    return segments


def _clip_text(text: str, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 1, 0)].rstrip() + "…"


def _workflow_constraints(workflow_type: str) -> list[str]:
    workflow = str(workflow_type or "").strip().lower()
    if workflow == "task_decomposition":
        return ["保留依赖顺序", "输出明确动作与前置条件"]
    if workflow == "progressive_exploration":
        return ["避免重复上游原文", "补充新的理解维度"]
    if workflow == "error_diagnosis":
        return ["优先定位根因", "给出可执行补救动作"]
    if workflow == "explicit_expert_collaboration":
        return ["保留关键分歧", "给出清晰最终判断"]
    return ["保留关键信息", "避免重复和空泛总结"]


async def _summarize_with_fast_model(response_text: str, workflow_type: str) -> str:
    try:
        from app.core.agent_profiles import TaskType
        from app.services.llm_service import get_llm_service_for_task

        summarizer = get_llm_service_for_task(TaskType.ROUTING)
        prompt = (
            "请用中文输出 1 句桥接摘要（120字以内），给下一个协作 agent 使用。\n"
            f"工作流: {workflow_type}\n"
            "要求：只保留最关键结论、依据和未解决点，不要复述全文。\n\n"
            f"{response_text[:1600]}"
        )
        summary = await summarizer.chat(
            messages=[
                {"role": "system", "content": "你是多智能体协作摘要助手。只输出摘要正文。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        cleaned = _clip_text(summary, 180)
        if cleaned:
            return cleaned
    except Exception as exc:
        logger.warning(f"[WorkflowExperience] FAST handoff summary failed: {exc}")
    return _clip_text("；".join(_split_sentences(response_text)[:2]), 180)


async def build_handoff_packet(
    *,
    agent: str,
    response_text: str,
    workflow_type: str,
    reasoning: str | None = None,
    target_summary_chars: int = 160,
) -> HandoffPacket:
    sentences = _split_sentences(response_text)
    key_conclusions = [_clip_text(item, 90) for item in sentences[:3] if item][:3]
    evidence = []
    if reasoning:
        evidence.append(_clip_text(reasoning, 90))
    if len(sentences) >= 4:
        evidence.append(_clip_text(sentences[3], 90))
    questions = [_clip_text(item, 80) for item in sentences if "?" in item or "？" in item][:2]
    summary = _clip_text("；".join(key_conclusions[:2]) or response_text, target_summary_chars)
    if len(summary) > 180 or len(response_text) > 900:
        summary = await _summarize_with_fast_model(response_text, workflow_type=workflow_type)
        key_conclusions = [_clip_text(summary, 70)]
        if reasoning:
            evidence = [_clip_text(reasoning, 70)]

    packet = HandoffPacket(
        agent=agent,
        summary=summary,
        key_conclusions=key_conclusions,
        evidence_or_reasoning=evidence[:2],
        open_questions=questions,
        constraints_for_next_agent=_workflow_constraints(workflow_type),
    )

    prompt_size = len(packet.to_prompt_block())
    if prompt_size > 450:
        packet.summary = _clip_text(packet.summary, 140)
        packet.key_conclusions = [_clip_text(item, 70) for item in packet.key_conclusions[:2]]
        packet.evidence_or_reasoning = [_clip_text(item, 70) for item in packet.evidence_or_reasoning[:1]]
        packet.open_questions = [_clip_text(item, 70) for item in packet.open_questions[:1]]

    return packet


def format_handoff_packets(
    packets: list[HandoffPacket | dict[str, Any]],
    *,
    title: str = "上游协作桥接摘要包",
) -> str:
    if not packets:
        return ""
    rendered = [f"## {title}"]
    for raw in packets:
        packet = raw if isinstance(raw, HandoffPacket) else HandoffPacket(**raw)
        rendered.append(packet.to_prompt_block())
    return "\n\n".join(rendered)


def build_collaboration_user_query(
    *,
    base_query: str,
    workflow_type: str,
    handoff_packets: list[HandoffPacket | dict[str, Any]] | None = None,
    few_shot_examples: list[dict[str, Any]] | None = None,
    extra_instruction: str | None = None,
) -> str:
    sections = [f"用户任务：{base_query.strip()}"]
    if handoff_packets:
        sections.append(
            format_handoff_packets(
                list(handoff_packets),
                title="上游专家桥接摘要",
            )
        )
    few_shot_section = format_few_shot_examples(few_shot_examples or [])
    if few_shot_section:
        sections.append(few_shot_section)
    if extra_instruction:
        sections.append(extra_instruction.strip())
    sections.append(f"请按 {workflow_type} 工作流目标继续推进，优先吸收摘要中的关键结论，避免重复上游原文。")
    return "\n\n".join(section for section in sections if section)
