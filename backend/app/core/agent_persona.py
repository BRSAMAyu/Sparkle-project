from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.core.agent_profiles import AgentProfile, AgentRole


MBTI_CHOICES = [
    "INFJ",
    "INTJ",
    "ENFP",
    "ENTP",
    "ISFJ",
    "ISTJ",
    "ESFJ",
    "ENTJ",
]

TEACHING_STYLES = [
    "socratic",
    "direct_explanation",
    "example_driven",
    "guided_practice",
]

COMMUNICATION_STYLES = [
    "gentle",
    "structured",
    "energetic",
    "reassuring",
]

PATIENCE_LEVELS = ["very_high", "high", "steady", "adaptive"]
HUMOR_LEVELS = ["dry", "light", "warm", "minimal"]


ROLE_DOMAIN_DEFAULTS: dict[AgentRole, list[str]] = {
    AgentRole.ORCHESTRATOR: ["learning strategy", "cross-topic coordination"],
    AgentRole.GENERATION: ["learning support", "concept explanation"],
    AgentRole.GALAXY_GUIDE: ["knowledge graph", "prerequisite mapping"],
    AgentRole.EXAM_ORACLE: ["exam strategy", "revision planning"],
    AgentRole.TIME_TUTOR: ["time management", "study scheduling"],
    AgentRole.ERROR_ANALYST: ["error diagnosis", "weak-spot recovery"],
    AgentRole.STUDY_BUDDY: ["motivation", "lightweight coaching"],
    AgentRole.STUDY_PLANNER: ["macro planning", "milestone design"],
    AgentRole.PROBLEM_SOLVER: ["step-by-step solving", "diagnosis"],
}


ROLE_VALUE_DEFAULTS: dict[AgentRole, list[str]] = {
    AgentRole.ORCHESTRATOR: ["clarity", "follow-through", "calm guidance"],
    AgentRole.GENERATION: ["warmth", "accuracy", "encouragement"],
    AgentRole.GALAXY_GUIDE: ["structure", "connections", "deep understanding"],
    AgentRole.EXAM_ORACLE: ["focus", "confidence", "strategic tradeoffs"],
    AgentRole.TIME_TUTOR: ["consistency", "realism", "sustainable rhythm"],
    AgentRole.ERROR_ANALYST: ["precision", "kindness", "repair over blame"],
    AgentRole.STUDY_BUDDY: ["companionship", "momentum", "ease"],
}


@dataclass
class AgentPersona:
    role: AgentRole
    display_name: str
    mbti: str
    communication_style: str
    teaching_style: str
    patience_level: str
    humor_level: str
    expertise_domains: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    tone_tags: list[str] = field(default_factory=list)
    consistency_key: str = ""

    def to_prompt_section(self) -> str:
        expertise = "、".join(self.expertise_domains[:3]) or "通用学习支持"
        values = "、".join(self.values[:3]) or "耐心、清晰、可信"
        tone = "、".join(self.tone_tags[:4]) or "稳定、温和"
        return (
            "\n## AI 导师人格设定 [L2 引导]\n"
            f"- 人格锚点: {self.display_name} / {self.mbti}\n"
            f"- 教学风格: {self.teaching_style}\n"
            f"- 沟通风格: {self.communication_style}\n"
            f"- 耐心度: {self.patience_level}\n"
            f"- 幽默感: {self.humor_level}\n"
            f"- 专业领域: {expertise}\n"
            f"- 核心价值观: {values}\n"
            f"- 语气标签: {tone}\n"
            "- 保持同一人格在不同对话中的连续性，不要忽冷忽热或突然换风格。"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "display_name": self.display_name,
            "mbti": self.mbti,
            "communication_style": self.communication_style,
            "teaching_style": self.teaching_style,
            "patience_level": self.patience_level,
            "humor_level": self.humor_level,
            "expertise_domains": list(self.expertise_domains),
            "values": list(self.values),
            "tone_tags": list(self.tone_tags),
            "consistency_key": self.consistency_key,
        }


def _stable_seed(*parts: object) -> int:
    raw = "|".join(str(part or "") for part in parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16)


def _pick_one(options: list[str], seed: int, offset: int = 0) -> str:
    if not options:
        return ""
    return options[(seed + offset) % len(options)]


def _pick_many(options: list[str], seed: int, count: int) -> list[str]:
    if not options:
        return []
    items = list(dict.fromkeys(options))
    start = seed % len(items)
    ordered = items[start:] + items[:start]
    return ordered[:count]


def _infer_teaching_style(user_context: dict[str, Any], seed: int) -> str:
    profile = user_context.get("preferences") if isinstance(user_context, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    signals = user_context.get("cognitive_insights") if isinstance(user_context, dict) else {}
    signal_list = list((signals or {}).get("policy_signals") or [])

    if any("scaffold" in signal for signal in signal_list):
        return "example_driven"
    if profile.get("verbosity") == "concise":
        return "direct_explanation"
    if profile.get("exploration_level") == "high":
        return "socratic"
    return _pick_one(TEACHING_STYLES, seed, offset=2)


def _infer_communication_style(user_context: dict[str, Any], seed: int) -> str:
    profile = user_context.get("preferences") if isinstance(user_context, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    if profile.get("tone") in {"gentle", "soft"}:
        return "gentle"
    if profile.get("tone") in {"lively", "playful"}:
        return "energetic"
    if profile.get("verbosity") == "concise":
        return "structured"
    return _pick_one(COMMUNICATION_STYLES, seed)


def build_agent_persona(
    *,
    agent_role: AgentRole,
    user_context: dict[str, Any] | None,
    profile: AgentProfile,
) -> AgentPersona:
    context = user_context if isinstance(user_context, dict) else {}
    identity = context.get("identity") if isinstance(context.get("identity"), dict) else {}
    knowledge_summary = context.get("profile_context", {}) if isinstance(context.get("profile_context"), dict) else {}
    active_subjects = list(
        (
            knowledge_summary.get("knowledge_summary", {}) if isinstance(knowledge_summary, dict) else {}
        ).get("active_learning_subjects", [])
        or []
    )

    user_key = identity.get("nickname") or context.get("user_id") or "anonymous"
    consistency_key = f"{agent_role.value}:{user_key}"
    seed = _stable_seed(consistency_key, profile.display_name, profile.persona_archetype)

    expertise_domains = list(profile.expertise_domains or ROLE_DOMAIN_DEFAULTS.get(agent_role, []))
    if active_subjects:
        expertise_domains = list(dict.fromkeys([*active_subjects[:2], *expertise_domains]))

    communication_style = _infer_communication_style(context, seed)
    teaching_style = _infer_teaching_style(context, seed)
    patience_level = "very_high" if communication_style == "gentle" else _pick_one(PATIENCE_LEVELS, seed, offset=1)
    humor_level = "light" if agent_role == AgentRole.STUDY_BUDDY else _pick_one(HUMOR_LEVELS, seed, offset=3)

    tone_tags = [communication_style, teaching_style, "consistent", "supportive"]
    if context.get("cognitive_insights", {}).get("has_cognitive_patterns"):
        tone_tags.append("cognitive-aware")

    values = _pick_many(
        list(dict.fromkeys([*(ROLE_VALUE_DEFAULTS.get(agent_role, [])), "clarity", "trust", "growth"])),
        seed,
        3,
    )

    return AgentPersona(
        role=agent_role,
        display_name=profile.display_name,
        mbti=_pick_one(MBTI_CHOICES, seed),
        communication_style=communication_style,
        teaching_style=teaching_style,
        patience_level=patience_level,
        humor_level=humor_level,
        expertise_domains=expertise_domains[:4],
        values=values,
        tone_tags=list(dict.fromkeys(tone_tags)),
        consistency_key=consistency_key,
    )


def build_agent_persona_prompt_section(
    *,
    agent_role: AgentRole,
    user_context: dict[str, Any] | None,
    profile: AgentProfile,
) -> str:
    persona = build_agent_persona(agent_role=agent_role, user_context=user_context, profile=profile)
    return persona.to_prompt_section()
