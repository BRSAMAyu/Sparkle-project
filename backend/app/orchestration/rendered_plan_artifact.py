from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.orchestration.plan_quality_contract import (
    SECTION_ADAPTATION_TRIGGER,
    SECTION_ASSUMPTIONS,
    SECTION_FAILURE_GUARD,
    SECTION_FALLBACK_UNCERTAINTY,
    SECTION_GOAL_FRAME,
    SECTION_GROUNDING_BASIS,
    SECTION_NEXT_ACTION,
    SECTION_READINESS_FIT,
    SECTION_SCOPE_AND_HORIZON,
    SECTION_SEQUENCE,
    SECTION_UNLOCK_QUESTION,
    SECTION_WITHHOLD_REASON,
    SECTION_WORKLOAD_MODEL,
)

SECTION_LABELS: dict[str, tuple[str, ...]] = {
    SECTION_GOAL_FRAME: ("goal frame", "goal", "明确目标", "目标"),
    SECTION_ASSUMPTIONS: ("key assumptions", "assumptions", "关键假设", "假设"),
    SECTION_READINESS_FIT: ("readiness fit", "plan type", "fit analysis", "计划类型说明", "类型", "状态"),
    SECTION_WORKLOAD_MODEL: (
        "workload model",
        "time and energy assumptions",
        "时间/精力/难度假设",
        "时间假设",
        "精力假设",
        "难度假设",
    ),
    SECTION_SEQUENCE: ("sequence and rationale", "sequence", "先后顺序与理由"),
    SECTION_GROUNDING_BASIS: ("grounding basis", "材料、约束与薄弱点的使用", "materials, constraints, and weak spots"),
    SECTION_NEXT_ACTION: ("next action within 24 hours", "next action", "未来 24 小时内可执行的下一步", "行动"),
    SECTION_ADAPTATION_TRIGGER: ("adaptation trigger", "什么信号会触发调整", "trigger"),
    SECTION_FAILURE_GUARD: ("failure guard", "fallback", "太难、太空或过度乐观时怎么办", "止损策略", "降级策略"),
    SECTION_SCOPE_AND_HORIZON: ("narrowed scope and horizon", "缩窄后的范围与时间窗", "新范围", "时间窗"),
    SECTION_FALLBACK_UNCERTAINTY: ("fallback path and uncertainty", "暂定路径与待确认点", "待确认点", "限制声明"),
    SECTION_WITHHOLD_REASON: ("why a full plan is withheld", "为什么现在不该给完整计划", "拒绝生成完整计划的理由"),
    SECTION_UNLOCK_QUESTION: ("unlock question", "one unlock question or blocker", "最高价值的解锁问题", "unlocking question"),
}

SECTION_MATCH_ORDER = (
    SECTION_GOAL_FRAME,
    SECTION_ASSUMPTIONS,
    SECTION_READINESS_FIT,
    SECTION_WORKLOAD_MODEL,
    SECTION_SEQUENCE,
    SECTION_GROUNDING_BASIS,
    SECTION_NEXT_ACTION,
    SECTION_ADAPTATION_TRIGGER,
    SECTION_SCOPE_AND_HORIZON,
    SECTION_FALLBACK_UNCERTAINTY,
    SECTION_WITHHOLD_REASON,
    SECTION_UNLOCK_QUESTION,
    SECTION_FAILURE_GUARD,
)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _normalize_header(line: str) -> str:
    normalized = _strip(line).lower()
    normalized = re.sub(r"^[#>*\-\d\.\)\(\s:：]+", "", normalized)
    normalized = normalized.replace("**", "").replace("__", "")
    return normalized.strip()


def _excerpt(text: str, *, max_chars: int = 240) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return compact[:max_chars]


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


@dataclass(frozen=True)
class RenderedPlanArtifact:
    text: str
    language: str
    sections: dict[str, str]
    material_mentions: list[str]
    explicit_next_action: str
    explicit_unlock_question: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "sections": dict(self.sections),
            "material_mentions": list(self.material_mentions),
            "explicit_next_action": self.explicit_next_action,
            "explicit_unlock_question": self.explicit_unlock_question,
        }


def parse_rendered_plan_artifact(raw: dict[str, Any] | str | None) -> RenderedPlanArtifact | None:
    text = _strip(raw.get("text")) if isinstance(raw, dict) else _strip(raw)
    if not text:
        return None

    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if current_section and current_lines:
            content = "\n".join(line for line in current_lines if _strip(line)).strip()
            if content and current_section not in sections:
                sections[current_section] = content[:1200]
        current_lines = []

    for line in text.splitlines():
        normalized = _normalize_header(line)
        matched = None
        for section in SECTION_MATCH_ORDER:
            labels = SECTION_LABELS.get(section, ())
            if any(label in normalized for label in labels):
                matched = section
                break
        if matched:
            flush()
            current_section = matched
            continue
        if current_section:
            current_lines.append(line)
    flush()

    material_mentions = sorted(
        {
            match.group(0)
            for match in re.finditer(r"[\w\-]+\.(?:pdf|csv|md|json|txt)", text, re.IGNORECASE)
        }
    )
    explicit_next_action = _excerpt(sections.get(SECTION_NEXT_ACTION, ""))
    explicit_unlock_question = ""
    unlock_text = sections.get(SECTION_UNLOCK_QUESTION, "")
    for line in (unlock_text or text).splitlines():
        stripped = _strip(line)
        if "?" in stripped or "？" in stripped:
            explicit_unlock_question = stripped[:240]
            break

    return RenderedPlanArtifact(
        text=text,
        language="zh" if _contains_chinese(text) else "en",
        sections=sections,
        material_mentions=material_mentions,
        explicit_next_action=explicit_next_action,
        explicit_unlock_question=explicit_unlock_question,
    )
