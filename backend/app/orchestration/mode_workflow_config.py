from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.orchestration.chat_modes import (
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_STUDY_PLAN,
)


@dataclass
class ModeWorkflowConfig:
    chat_mode: str
    collaboration_mode: Literal["single", "sequential", "parallel"] = "sequential"
    collaboration_agents: list[str] = field(default_factory=list)
    collaboration_order: list[dict[str, str]] = field(default_factory=list)
    requires_plan_execution: bool = True
    synthesis_template: str = ""
    tool_policy: dict[str, Any] = field(default_factory=dict)
    fallback_policy: dict[str, Any] = field(default_factory=dict)


MODE_WORKFLOWS: dict[str, ModeWorkflowConfig] = {
    CHAT_MODE_DEEP_ANALYSIS: ModeWorkflowConfig(
        chat_mode=CHAT_MODE_DEEP_ANALYSIS,
        collaboration_mode="sequential",
        collaboration_agents=["galaxy_guide", "deep_analyst"],
        collaboration_order=[
            {"agent": "galaxy_guide", "task": "Gather evidence from knowledge graph and identify key concepts."},
            {"agent": "deep_analyst", "task": "Build a multi-perspective analysis grounded in retrieved evidence."},
        ],
        synthesis_template=(
            "You are a Deep Analysis Synthesizer.\n"
            "Use execution results to produce sections: 关键结论, 证据链, 反方与边界, 应用建议."
        ),
        tool_policy={
            "allow_record_error_without_confirmation": False,
        },
        fallback_policy={
            "on_empty_plan": "llm_only",
            "on_tool_failure": "partial_synthesis",
        },
    ),
    CHAT_MODE_STUDY_PLAN: ModeWorkflowConfig(
        chat_mode=CHAT_MODE_STUDY_PLAN,
        collaboration_mode="sequential",
        collaboration_agents=["galaxy_guide", "exam_oracle", "time_tutor"],
        collaboration_order=[
            {"agent": "galaxy_guide", "task": "Identify knowledge prerequisites and weak spots."},
            {"agent": "exam_oracle", "task": "Decompose exam-oriented milestones and strategy."},
            {"agent": "time_tutor", "task": "Generate executable schedule and focus sessions."},
        ],
        synthesis_template=(
            "You are a Study Plan Synthesizer.\n"
            "Use execution results to produce sections: 目标, 里程碑, 每周计划, 每日执行模板, 复盘机制."
        ),
        tool_policy={
            "allow_record_error_without_confirmation": False,
        },
        fallback_policy={
            "on_empty_plan": "llm_only",
            "on_tool_failure": "partial_synthesis",
        },
    ),
    CHAT_MODE_ERROR_DIAGNOSIS: ModeWorkflowConfig(
        chat_mode=CHAT_MODE_ERROR_DIAGNOSIS,
        collaboration_mode="sequential",
        collaboration_agents=["error_analyst", "galaxy_guide", "time_tutor"],
        collaboration_order=[
            {"agent": "error_analyst", "task": "Classify error type and root cause from the user input."},
            {"agent": "galaxy_guide", "task": "Locate missing prerequisite knowledge and evidence."},
            {"agent": "time_tutor", "task": "Create targeted remediation tasks and study routine."},
        ],
        synthesis_template=(
            "You are an Error Diagnosis Synthesizer.\n"
            "Use execution results to produce sections: 错误类型, 根因分析, 正确路径, 针对性练习, 复发预防."
        ),
        tool_policy={
            "allow_record_error_without_confirmation": False,
        },
        fallback_policy={
            "on_empty_plan": "llm_only",
            "on_tool_failure": "partial_synthesis",
        },
    ),
}


def get_workflow_config(chat_mode: str) -> ModeWorkflowConfig | None:
    return MODE_WORKFLOWS.get(chat_mode)

