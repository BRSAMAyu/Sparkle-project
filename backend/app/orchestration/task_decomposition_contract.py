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
    score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "constraints": self.constraints,
            "resources": self.resources,
            "milestones": self.milestones,
            "acceptance_criteria": self.acceptance_criteria,
            "risks": self.risks,
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

    score = _score_contract(
        goal=goal,
        constraints=constraints,
        resources=resources,
        milestones=milestones,
        acceptance_criteria=acceptance,
        risks=risks,
    )

    return TaskDecompositionContract(
        goal=goal,
        constraints=constraints,
        resources=resources,
        milestones=milestones,
        acceptance_criteria=acceptance,
        risks=risks,
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
) -> float:
    score = 0.0
    if goal:
        score += 0.25
    if constraints:
        score += 0.16
    if resources:
        score += 0.12
    if milestones:
        score += 0.2
    if acceptance_criteria:
        score += 0.22
    if risks:
        score += 0.05
    return max(0.0, min(score, 1.0))
