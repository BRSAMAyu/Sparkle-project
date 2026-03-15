from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_STANDARD,
    CHAT_MODE_STUDY_PLAN,
    CHAT_MODE_TEAM_PREFIX,
    parse_team_spec,
)


@dataclass
class ModeStrategyOverride:
    """Mode-specific strategy overrides on top of the unified orchestration chain.

    The system keeps a single orchestration brain. Chat modes now only bias
    routing, planning, review strictness, and synthesis structure.
    """

    chat_mode: str
    force_execution_mode: Literal["direct", "langgraph", "hybrid"] | None = None
    min_confidence_for_direct: float | None = 0.92
    preferred_agents: list[str] = field(default_factory=list)
    required_agents: list[str] = field(default_factory=list)
    collaboration_mode: Literal["auto", "single", "sequential", "parallel", "debate", "delegation"] = "auto"
    review_strictness: float = 1.0
    require_alignment_check: bool = True
    synthesis_instruction: str = ""
    output_structure: list[str] = field(default_factory=list)
    tool_policy: dict[str, Any] = field(default_factory=dict)
    fallback_policy: dict[str, Any] = field(default_factory=dict)
    excluded_agents: list[str] = field(default_factory=list)

    @property
    def collaboration_agents(self) -> list[str]:
        return list(self.required_agents or self.preferred_agents)

    @property
    def collaboration_order(self) -> list[dict[str, str]]:
        agents = self.collaboration_agents
        if not agents:
            return []
        return [{"agent": agent, "task": "mode_required"} for agent in agents]

    @property
    def requires_plan_execution(self) -> bool:
        return True

    @property
    def synthesis_template(self) -> str:
        instruction = self.synthesis_instruction.strip()
        if self.output_structure:
            sections = "、".join(self.output_structure)
            template = f"请严格按以下章节组织最终回答：{sections}。"
            return f"{instruction}\n{template}".strip() if instruction else template
        return instruction


MODE_STRATEGIES: dict[str, ModeStrategyOverride] = {
    CHAT_MODE_STANDARD: ModeStrategyOverride(
        chat_mode=CHAT_MODE_STANDARD,
        force_execution_mode=None,
        min_confidence_for_direct=0.92,
        require_alignment_check=False,
    ),
    CHAT_MODE_DEEP_ANALYSIS: ModeStrategyOverride(
        chat_mode=CHAT_MODE_DEEP_ANALYSIS,
        force_execution_mode="langgraph",
        min_confidence_for_direct=0.98,
        required_agents=["galaxy_guide", "deep_analyst"],
        collaboration_mode="sequential",
        review_strictness=1.5,
        synthesis_instruction=(
            "你是深度分析整合器。先给综合判断，再展开证据、反方边界和可执行建议。"
        ),
        output_structure=["关键结论", "证据链", "反方与边界", "应用建议"],
        tool_policy={"allow_record_error_without_confirmation": False},
        fallback_policy={"on_empty_plan": "llm_only", "on_tool_failure": "partial_synthesis"},
    ),
    CHAT_MODE_STUDY_PLAN: ModeStrategyOverride(
        chat_mode=CHAT_MODE_STUDY_PLAN,
        force_execution_mode="langgraph",
        min_confidence_for_direct=0.98,
        required_agents=["galaxy_guide", "exam_oracle", "time_tutor"],
        collaboration_mode="sequential",
        review_strictness=1.25,
        require_alignment_check=True,
        synthesis_instruction=(
            "你是学习规划整合器。必须把知识前置、考试目标、时间安排和复盘节奏整合成一份可执行计划。"
        ),
        output_structure=["目标", "里程碑", "每周计划", "每日执行模板", "复盘机制"],
        tool_policy={"allow_record_error_without_confirmation": False},
        fallback_policy={"on_empty_plan": "llm_only", "on_tool_failure": "partial_synthesis"},
    ),
    CHAT_MODE_ERROR_DIAGNOSIS: ModeStrategyOverride(
        chat_mode=CHAT_MODE_ERROR_DIAGNOSIS,
        force_execution_mode="langgraph",
        min_confidence_for_direct=0.98,
        required_agents=["error_analyst", "galaxy_guide", "time_tutor"],
        collaboration_mode="sequential",
        review_strictness=1.15,
        require_alignment_check=True,
        synthesis_instruction=(
            "你是错因诊断整合器。必须把错误类型、根因、矫正动作和复发预防连接成闭环。"
        ),
        output_structure=["错误类型", "根因分析", "正确路径", "针对性练习", "复发预防"],
        tool_policy={"allow_record_error_without_confirmation": False},
        fallback_policy={"on_empty_plan": "llm_only", "on_tool_failure": "partial_synthesis"},
    ),
    CHAT_MODE_EXPERT_AUTO: ModeStrategyOverride(
        chat_mode=CHAT_MODE_EXPERT_AUTO,
        force_execution_mode=None,
        min_confidence_for_direct=0.85,
        preferred_agents=["deep_analyst"],
        collaboration_mode="auto",
        review_strictness=1.0,
        require_alignment_check=False,
        synthesis_instruction="你需要保留专家协同痕迹，明确综合结论由哪些专家支撑。",
        tool_policy={"allow_record_error_without_confirmation": False},
        fallback_policy={"on_empty_plan": "llm_only", "on_tool_failure": "partial_synthesis"},
    ),
}


def get_mode_strategy(chat_mode: str | None) -> ModeStrategyOverride | None:
    mode = str(chat_mode or "").strip()
    if mode.startswith(CHAT_MODE_TEAM_PREFIX):
        team_spec = parse_team_spec(mode)
        if team_spec:
            return build_team_strategy(team_spec)
    return MODE_STRATEGIES.get(mode.lower())


def get_workflow_config(chat_mode: str | None) -> ModeStrategyOverride | None:
    """Backward-compatible alias for callers not yet migrated."""
    return get_mode_strategy(chat_mode)


def build_team_strategy(team_spec: dict) -> ModeStrategyOverride:
    """Build a ModeStrategyOverride from user-configured team spec."""
    agents = [str(a).strip() for a in (team_spec.get("agents") or []) if str(a).strip()]
    excluded = {str(a).strip() for a in (team_spec.get("excluded") or []) if str(a).strip()}
    mode = str(team_spec.get("mode") or "auto").strip().lower()

    agents = [agent for agent in agents if agent not in excluded]

    from app.agents.graph.expert_registry import resolve_node_name

    resolved_agents = []
    for agent in agents:
        resolved = resolve_node_name(agent)
        if resolved and resolved not in resolved_agents:
            resolved_agents.append(resolved)

    if not resolved_agents:
        return MODE_STRATEGIES[CHAT_MODE_STANDARD]

    collaboration_mode = mode if mode in {"sequential", "parallel", "debate", "delegation"} else "auto"

    return ModeStrategyOverride(
        chat_mode=f"team_custom_{len(resolved_agents)}",
        force_execution_mode="langgraph",
        min_confidence_for_direct=0.98,
        required_agents=resolved_agents,
        collaboration_mode=collaboration_mode,
        review_strictness=1.0,
        require_alignment_check=False,
        synthesis_instruction="保留各参与专家的贡献痕迹，明确综合结论由哪些专家支撑。",
        excluded_agents=sorted(excluded),
    )
