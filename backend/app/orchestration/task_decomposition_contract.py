from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


@dataclass
class TaskDecompositionContract:
    """Normalized contract for decomposition-quality planning."""

    goal: str
    constraints: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    success_evidence: list[str] = field(default_factory=list)
    goal_hierarchy: dict[str, Any] = field(default_factory=dict)
    goal_hierarchy_score: float = 0.0
    score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    version: str = "v2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "constraints": self.constraints,
            "resources": self.resources,
            "milestones": self.milestones,
            "acceptance_criteria": self.acceptance_criteria,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "tradeoffs": self.tradeoffs,
            "success_evidence": self.success_evidence,
            "goal_hierarchy": self.goal_hierarchy,
            "goal_hierarchy_score": round(float(self.goal_hierarchy_score), 4),
            "score": round(float(self.score), 4),
            "gaps": self.gaps,
            "version": self.version,
        }


def build_task_decomposition_contract(
    *,
    message: str,
    intent: str | None = None,
    extracted_entities: dict[str, Any] | None = None,
    conversation_context: list[dict[str, Any]] | None = None,
) -> TaskDecompositionContract:
    text = _clean_text(message)
    intent_value = (intent or "").strip().lower()
    entities = extracted_entities if isinstance(extracted_entities, dict) else {}
    context = conversation_context if isinstance(conversation_context, list) else []

    goal = _extract_goal(text=text, entities=entities, context=context)
    constraints = _extract_constraints(text)
    resources = _extract_resources(text)
    milestones = _extract_milestones(text)
    acceptance = _extract_acceptance_criteria(text)
    risks = _extract_risks(text)
    assumptions = _extract_assumptions(text)
    tradeoffs = _extract_tradeoffs(text)
    success_evidence = _extract_success_evidence(
        text=text,
        acceptance_criteria=acceptance,
    )
    goal_hierarchy = _build_goal_hierarchy(
        text=text,
        goal=goal,
        constraints=constraints,
        milestones=milestones,
    )
    goal_hierarchy_score = _score_goal_hierarchy(goal_hierarchy)

    decomposition_request = _is_decomposition_request(intent=intent_value, text=text)
    # Planning/decomposition intents require full contract by default.
    must_have_milestones = decomposition_request
    must_have_acceptance = decomposition_request
    must_have_risks = decomposition_request

    gaps: list[str] = []
    if not goal:
        gaps.append("missing_goal")
    if not constraints and decomposition_request:
        gaps.append("missing_constraints")
    if must_have_milestones and not milestones:
        gaps.append("missing_milestones")
    if must_have_acceptance and not acceptance:
        gaps.append("missing_acceptance_criteria")
    if must_have_risks and not risks:
        gaps.append("missing_risks")
    if decomposition_request and goal_hierarchy_score < 0.55:
        gaps.append("missing_goal_hierarchy")
    if decomposition_request and not _is_hierarchy_traceable(goal_hierarchy):
        gaps.append("broken_goal_traceability")

    score = _score_contract(
        goal=goal,
        constraints=constraints,
        resources=resources,
        milestones=milestones,
        acceptance_criteria=acceptance,
        risks=risks,
        assumptions=assumptions,
        tradeoffs=tradeoffs,
        success_evidence=success_evidence,
        goal_hierarchy_score=goal_hierarchy_score,
    )

    return TaskDecompositionContract(
        goal=goal,
        constraints=constraints,
        resources=resources,
        milestones=milestones,
        acceptance_criteria=acceptance,
        risks=risks,
        assumptions=assumptions,
        tradeoffs=tradeoffs,
        success_evidence=success_evidence,
        goal_hierarchy=goal_hierarchy,
        goal_hierarchy_score=goal_hierarchy_score,
        score=score,
        gaps=gaps,
    )


def generate_contract_clarification_questions(gaps: list[str]) -> list[str]:
    mapping = {
        "missing_goal": "你的最终目标是什么？请描述你希望达成的结果。",
        "missing_constraints": "有哪些约束条件（时间、精力、预算、截止日期）？",
        "missing_milestones": "你希望分成哪些阶段推进？至少给出 2-3 个里程碑。",
        "missing_acceptance_criteria": "怎样算完成？请给出可验证的验收标准。",
        "missing_risks": "这件事最可能失败的风险是什么？请至少给出 1-2 个风险。",
        "missing_goal_hierarchy": "请补充层级目标：愿景、12周目标、每周里程碑、每日行动。",
        "broken_goal_traceability": "请明确每日行动分别归属哪个周里程碑，保证可追溯。",
    }
    questions: list[str] = []
    for gap in gaps:
        question = mapping.get(gap)
        if question and question not in questions:
            questions.append(question)
    return questions


def _extract_goal(*, text: str, entities: dict[str, Any], context: list[dict[str, Any]]) -> str:
    for key in ("goal", "plan_title", "topic", "task_title"):
        value = entities.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_text(value)

    # "我想/我要/目标是/希望" style goal extraction
    patterns = [
        r"(?:我想|我要|目标是|希望|我计划)\s*([^。！？\n]{4,120})",
        r"(?:i want to|my goal is|i plan to)\s*([^.!?\n]{4,120})",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    if text:
        return _clean_text(text[:120])

    # fallback from recent user context
    for item in reversed(context[-3:]):
        if item.get("role") == "user":
            content = _clean_text(str(item.get("content", "")))
            if content:
                return content[:120]
    return ""


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(\d+\s*(?:天|周|月|小时|分钟))",
        r"(?:deadline|due|截止|在.*之前)[^。！？\n]{0,24}",
        r"(?:每天|每周|daily|weekly)[^。！？\n]{0,24}",
        r"(?:预算|budget)[^。！？\n]{0,24}",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in constraints:
                constraints.append(value)
    return constraints[:6]


def _extract_resources(text: str) -> list[str]:
    resources: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:我有|已有|currently have|i have)\s*([^。！？\n]{2,80})",
        r"(?:用|using|with)\s*([^。！？\n]{2,60})",
        r"(?:资料|资源|materials|resource)[^。！？\n]{0,40}",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in resources:
                resources.append(value)
    return resources[:6]


def _extract_milestones(text: str) -> list[str]:
    milestones: list[str] = []
    lowered = text.lower()

    if any(token in lowered for token in ("阶段", "里程碑", "milestone", "phase")):
        chunks = re.split(r"[，,。;\n]", lowered)
        for chunk in chunks:
            value = _clean_text(chunk)
            if any(token in value for token in ("阶段", "里程碑", "milestone", "phase", "step")):
                milestones.append(value)

    # sequential markers imply implicit milestones
    if not milestones and any(token in lowered for token in ("先", "然后", "接着", "最后", "first", "then", "finally")):
        milestones = ["阶段1", "阶段2", "阶段3"]
    return milestones[:8]


def _extract_acceptance_criteria(text: str) -> list[str]:
    criteria: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:达到|完成|掌握|实现|achieve|finish|complete)\s*([^。！？\n]{2,80})",
        r"(\d+\s*[%％]|score\s*\d+|分数\s*\d+)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in criteria:
                criteria.append(value)
    return criteria[:6]


def _extract_risks(text: str) -> list[str]:
    risks: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:担心|风险|困难|怕|problem|risk|blocker)\s*([^。！？\n]{0,60})",
        r"(?:拖延|注意力|分心|时间不够|burnout|overload)[^。！？\n]{0,40}",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in risks:
                risks.append(value)
    return risks[:6]


def _extract_assumptions(text: str) -> list[str]:
    assumptions: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:假设|前提|assumption|assume)\s*[:：]?\s*([^。！？\n]{4,96})",
        r"(?:默认|默认情况下|by default)\s*([^。！？\n]{4,96})",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in assumptions:
                assumptions.append(value)
    return assumptions[:6]


def _extract_tradeoffs(text: str) -> list[str]:
    tradeoffs: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:取舍|权衡|trade[- ]?off)\s*[:：]?\s*([^。！？\n]{4,96})",
        r"(?:优先|priority)\s*([^。！？\n]{4,96})",
        r"(?:牺牲|sacrifice)\s*([^。！？\n]{4,96})",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in tradeoffs:
                tradeoffs.append(value)
    return tradeoffs[:6]


def _extract_success_evidence(*, text: str, acceptance_criteria: list[str]) -> list[str]:
    evidences: list[str] = []
    lowered = text.lower()
    patterns = [
        r"(?:证据|证明|evidence)\s*[:：]?\s*([^。！？\n]{4,96})",
        r"(?:结果显示|数据显示|result shows)\s*([^。！？\n]{4,96})",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, lowered, flags=re.IGNORECASE):
            value = _clean_text(match if isinstance(match, str) else "".join(match))
            if value and value not in evidences:
                evidences.append(value)

    if not evidences:
        for item in acceptance_criteria:
            text_item = _clean_text(str(item))
            if not text_item:
                continue
            if any(token in text_item.lower() for token in ("%", "分", "score", "完成", "达成", "通过")):
                evidences.append(f"验收达成证据：{text_item}")
            if len(evidences) >= 4:
                break
    return evidences[:6]


def _build_goal_hierarchy(
    *,
    text: str,
    goal: str,
    constraints: list[str],
    milestones: list[str],
) -> dict[str, Any]:
    vision = _extract_vision(text=text, goal=goal)
    goal_12w = _extract_12w_goal(text=text, goal=goal, constraints=constraints)

    weekly_milestones: list[dict[str, str]] = []
    for idx, item in enumerate(milestones[:12], start=1):
        weekly_milestones.append(
            {
                "week": f"W{idx}",
                "milestone": _clean_text(item),
            }
        )

    if not weekly_milestones and goal:
        weekly_milestones = [
            {"week": "W1", "milestone": f"明确目标并搭建执行环境：{goal[:48]}"},
            {"week": "W2", "milestone": "推进关键任务并完成阶段复盘"},
        ]

    daily_actions = _extract_daily_actions(text=text, weekly_milestones=weekly_milestones)
    if not daily_actions and weekly_milestones:
        for idx, item in enumerate(weekly_milestones, start=1):
            daily_actions.append(
                {
                    "day": f"D{idx}",
                    "action": f"围绕 {item['milestone'][:32]} 执行一个最小可交付任务",
                    "milestone_ref": item["week"],
                }
            )

    return {
        "vision": vision,
        "goal_12w": goal_12w,
        "weekly_milestones": weekly_milestones,
        "daily_actions": daily_actions,
    }


def _extract_vision(*, text: str, goal: str) -> str:
    patterns = [
        r"(?:愿景|长期目标|终极目标|最终想达到)\s*[:：]?\s*([^。！？\n]{6,120})",
        r"(?:vision|long[- ]term goal)\s*[:：]?\s*([^.!?\n]{6,120})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))
    if goal:
        return f"围绕“{goal[:48]}”实现可持续成长与稳定成果"
    return ""


def _extract_12w_goal(*, text: str, goal: str, constraints: list[str]) -> str:
    patterns = [
        r"(?:12周目标|三个月目标|12-week goal|12 week goal)\s*[:：]?\s*([^。！？\n]{6,120})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    constraint_hint = ""
    for item in constraints:
        value = str(item)
        if "周" in value or "week" in value.lower() or "月" in value:
            constraint_hint = value
            break
    if goal and constraint_hint:
        return f"{constraint_hint} 内达成：{goal[:72]}"
    if goal:
        return f"12周内达成：{goal[:72]}"
    return ""


def _extract_daily_actions(*, text: str, weekly_milestones: list[dict[str, str]]) -> list[dict[str, str]]:
    chunks = re.split(r"[。！？\n]", text)
    actions: list[dict[str, str]] = []
    week_refs = [item["week"] for item in weekly_milestones]
    for chunk in chunks:
        clean = _clean_text(chunk)
        if not clean:
            continue
        lowered = clean.lower()
        if not any(token in lowered for token in ("每天", "daily", "今日", "today", "day", "打卡", "复盘")):
            continue
        milestone_ref = week_refs[min(len(actions), len(week_refs) - 1)] if week_refs else ""
        actions.append(
            {
                "day": f"D{len(actions) + 1}",
                "action": clean[:96],
                "milestone_ref": milestone_ref,
            }
        )
        if len(actions) >= 14:
            break
    return actions


def _score_goal_hierarchy(hierarchy: dict[str, Any]) -> float:
    if not isinstance(hierarchy, dict):
        return 0.0
    score = 0.0
    if _clean_text(str(hierarchy.get("vision", ""))):
        score += 0.25
    if _clean_text(str(hierarchy.get("goal_12w", ""))):
        score += 0.25
    weekly = hierarchy.get("weekly_milestones")
    if isinstance(weekly, list) and any(isinstance(item, dict) and _clean_text(str(item.get("milestone", ""))) for item in weekly):
        score += 0.25
    if _is_hierarchy_traceable(hierarchy):
        score += 0.25
    return max(0.0, min(score, 1.0))


def _is_hierarchy_traceable(hierarchy: dict[str, Any]) -> bool:
    if not isinstance(hierarchy, dict):
        return False
    weekly = hierarchy.get("weekly_milestones")
    daily = hierarchy.get("daily_actions")
    if not isinstance(weekly, list) or not isinstance(daily, list) or not weekly or not daily:
        return False
    valid_weeks = {
        str(item.get("week", "")).strip()
        for item in weekly
        if isinstance(item, dict) and str(item.get("week", "")).strip()
    }
    if not valid_weeks:
        return False
    for item in daily:
        if not isinstance(item, dict):
            return False
        action = _clean_text(str(item.get("action", "")))
        ref = str(item.get("milestone_ref", "")).strip()
        if not action or not ref or ref not in valid_weeks:
            return False
    return True


def _is_decomposition_request(*, intent: str, text: str) -> bool:
    if intent in {"create_plan", "time_planning", "plan", "sprint_plan", "task_decomposition", "study_plan"}:
        return True
    lowered = (text or "").lower()
    keywords = (
        "任务拆解",
        "分解",
        "计划",
        "规划",
        "里程碑",
        "执行计划",
        "roadmap",
        "milestone",
        "plan",
        "step by step",
        "阶段",
    )
    return any(token in lowered for token in keywords)


def _score_contract(
    *,
    goal: str,
    constraints: list[str],
    resources: list[str],
    milestones: list[str],
    acceptance_criteria: list[str],
    risks: list[str],
    assumptions: list[str],
    tradeoffs: list[str],
    success_evidence: list[str],
    goal_hierarchy_score: float,
) -> float:
    score = 0.0
    if goal:
        score += 0.16
    if constraints:
        score += 0.12
    if resources:
        score += 0.08
    if milestones:
        score += 0.14
    if acceptance_criteria:
        score += 0.16
    if risks:
        score += 0.08
    if assumptions:
        score += 0.05
    if tradeoffs:
        score += 0.05
    if success_evidence:
        score += 0.05
    score += 0.11 * max(0.0, min(goal_hierarchy_score, 1.0))
    return max(0.0, min(score, 1.0))
