from __future__ import annotations

from typing import Any


_PATTERN_COPY_ALIASES: dict[str, str] = {
    "夜间能量错配循环": "the night-time energy mismatch loop",
    "完美主义回避循环": "the perfectionism-avoidance loop",
    "完美主义卡顿": "perfectionism paralysis",
    "理想化排程循环": "idealistic scheduling loop",
    "计划乐观偏差": "planning optimism",
    "专注衰减": "focus decay",
    "怀疑驱动的反复修改循环": "doubt-driven revision loop",
    "认知盲点": "cognitive blindspot",
}

_PATTERN_COPY: dict[str, dict[str, str]] = {
    "the night-time energy mismatch loop": {
        "display_name": "夜间能量错配循环",
        "description": "你经常把需要高认知负荷的学习安排在精力明显下滑的时段，导致投入了时间却难以真正吸收。",
        "solution_text": "把最费脑的任务前移到你最清醒的两个小时，夜间只保留复盘、整理和轻练习。",
    },
    "the perfectionism-avoidance loop": {
        "display_name": "完美主义回避循环",
        "description": "一想到必须做得足够好才值得开始，就更难启动，最后把真正重要的任务反复往后推。",
        "solution_text": "把任务压缩成 10 分钟可完成的最小版本，只要求开始，不要求一步到位。",
    },
    "perfectionism paralysis": {
        "display_name": "完美主义卡顿",
        "description": "你更容易在开始前反复衡量标准，结果卡在准备阶段，迟迟进不到真正执行。",
        "solution_text": "先交付一个粗糙可运行版本，再安排第二轮精修，用两段式推进取代一次做到完美。",
    },
    "the perfectionist's paralysis": {
        "display_name": "完美主义卡顿",
        "description": "你更容易在开始前反复衡量标准，结果卡在准备阶段，迟迟进不到真正执行。",
        "solution_text": "先交付一个粗糙可运行版本，再安排第二轮精修，用两段式推进取代一次做到完美。",
    },
    "idealistic scheduling loop": {
        "display_name": "理想化排程循环",
        "description": "计划排得很满，但没有给波动、回补和临时打断留出缓冲，所以一执行就容易脱轨。",
        "solution_text": "每天只保留 1 个核心任务和 1 个兜底任务，并给全天预留至少 20% 的缓冲时间。",
    },
    "planning optimism": {
        "display_name": "计划乐观偏差",
        "description": "你往往低估任务所需时间，高估自己在当天能推进的工作量。",
        "solution_text": "做计划时先给关键任务乘上 1.5 倍时间系数，再决定当天是否继续加项。",
    },
    "focus decay": {
        "display_name": "专注衰减",
        "description": "进入状态后不久就会出现明显走神或效率滑落，导致学习质量前高后低。",
        "solution_text": "把长任务拆成 25-40 分钟一段，每段结束后强制站起、换环境或做简短回顾。",
    },
    "doubt-driven revision loop": {
        "display_name": "怀疑驱动的反复修改循环",
        "description": "你容易在做出初步判断后立刻怀疑自己，于是频繁回头修改，消耗了推进节奏和决策信心。",
        "solution_text": "给关键题目或任务设置一次“首答承诺”：先在限定时间内完成第一版，再只做一轮必要修订。",
    },
    "cognitive blindspot": {
        "display_name": "认知盲点",
        "description": "你已经形成了某种稳定误区，自己在当下却不容易察觉，所以会在相似场景里重复犯错。",
        "solution_text": "每次做错后补一句“我刚才默认了什么”，把盲点写成一句可反驳的判断。",
    },
}

_PATTERN_POLICY_KEYS: dict[str, str] = {
    "the night-time energy mismatch loop": "night_time_energy_mismatch",
    "the perfectionism-avoidance loop": "perfectionism_avoidance",
    "perfectionism paralysis": "perfectionism_paralysis",
    "the perfectionist's paralysis": "perfectionism_paralysis",
    "idealistic scheduling loop": "planning_optimism",
    "planning optimism": "planning_optimism",
    "focus decay": "focus_decay",
    "doubt-driven revision loop": "doubt_driven_revision",
    "cognitive blindspot": "cognitive_blindspot",
}


def _normalize_pattern_name(name: str | None) -> str:
    return str(name or "").strip().lower()


def resolve_pattern_copy_key(name: str | None) -> str:
    normalized = _normalize_pattern_name(name)
    if not normalized:
        return ""
    alias = _PATTERN_COPY_ALIASES.get(normalized)
    if alias:
        return alias
    return normalized


def canonical_pattern_key(name: str | None) -> str:
    resolved = resolve_pattern_copy_key(name)
    if not resolved:
        return ""
    return _PATTERN_POLICY_KEYS.get(resolved, resolved)


def present_pattern_name(name: str | None) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    mapped = _PATTERN_COPY.get(resolve_pattern_copy_key(raw))
    if mapped:
        return mapped["display_name"]
    return raw


def present_pattern_description(name: str | None, description: str | None = None) -> str:
    raw_description = str(description or "").strip()
    mapped = _PATTERN_COPY.get(resolve_pattern_copy_key(name))
    if mapped:
        if raw_description and any("\u4e00" <= ch <= "\u9fff" for ch in raw_description):
            return raw_description
        return mapped["description"]
    return raw_description


def present_pattern_solution(name: str | None, solution_text: str | None = None) -> str:
    raw_solution = str(solution_text or "").strip()
    mapped = _PATTERN_COPY.get(resolve_pattern_copy_key(name))
    if mapped:
        if raw_solution and any("\u4e00" <= ch <= "\u9fff" for ch in raw_solution):
            return raw_solution
        return mapped["solution_text"]
    return raw_solution


def present_pattern_entry(
    *,
    name: str | None,
    confidence: float | None = None,
    description: str | None = None,
    solution_text: str | None = None,
) -> dict[str, Any]:
    display_name = present_pattern_name(name)
    payload: dict[str, Any] = {
        "pattern_name": display_name,
        "raw_pattern_name": str(name or "").strip(),
    }
    if confidence is not None:
        payload["confidence"] = float(confidence)
    localized_description = present_pattern_description(name, description)
    if localized_description:
        payload["description"] = localized_description
    localized_solution = present_pattern_solution(name, solution_text)
    if localized_solution:
        payload["solution_text"] = localized_solution
    return payload
