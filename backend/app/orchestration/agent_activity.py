"""Agent activity event definitions and display configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AGENT_DISPLAY_CONFIG: dict[str, dict[str, str]] = {
    "galaxy_guide": {
        "display_name": "星图导航",
        "icon": "constellation",
        "color": "#6C5CE7",
        "description": "知识图谱导航与关联",
    },
    "exam_oracle": {
        "display_name": "考试策略师",
        "icon": "target",
        "color": "#E17055",
        "description": "考试规划与出题策略",
    },
    "time_tutor": {
        "display_name": "时间教练",
        "icon": "clock",
        "color": "#00B894",
        "description": "时间管理与学习节奏",
    },
    "deep_analyst": {
        "display_name": "深度分析师",
        "icon": "microscope",
        "color": "#0984E3",
        "description": "概念深入分析与拆解",
    },
    "error_analyst": {
        "display_name": "纠错专家",
        "icon": "debug",
        "color": "#D63031",
        "description": "错误诊断与纠正",
    },
    "study_buddy": {
        "display_name": "学伴",
        "icon": "handshake",
        "color": "#FDCB6E",
        "description": "日常学习陪伴与鼓励",
    },
    "math_expert": {
        "display_name": "数学专家",
        "icon": "calculator",
        "color": "#6C5CE7",
        "description": "数学推理与解题",
    },
    "math_agent": {
        "display_name": "数学专家",
        "icon": "calculator",
        "color": "#6C5CE7",
        "description": "数学推理与解题",
    },
    "code_expert": {
        "display_name": "编程专家",
        "icon": "code",
        "color": "#00CEC9",
        "description": "代码分析与编写",
    },
    "code_agent": {
        "display_name": "编程专家",
        "icon": "code",
        "color": "#00CEC9",
        "description": "代码分析与编写",
    },
    "writing_expert": {
        "display_name": "写作专家",
        "icon": "pen",
        "color": "#E84393",
        "description": "文本写作与润色",
    },
    "writing_agent": {
        "display_name": "写作专家",
        "icon": "pen",
        "color": "#E84393",
        "description": "文本写作与润色",
    },
    "science_expert": {
        "display_name": "理科专家",
        "icon": "flask",
        "color": "#00B894",
        "description": "自然科学分析",
    },
    "science_agent": {
        "display_name": "理科专家",
        "icon": "flask",
        "color": "#00B894",
        "description": "自然科学分析",
    },
    "search_expert": {
        "display_name": "搜索专家",
        "icon": "search",
        "color": "#636E72",
        "description": "信息检索与整合",
    },
    "search_agent": {
        "display_name": "搜索专家",
        "icon": "search",
        "color": "#636E72",
        "description": "信息检索与整合",
    },
}


@dataclass
class AgentActivityEvent:
    """Single agent activity event emitted during graph execution."""

    agent_id: str
    status: Literal["pending", "active", "completed", "error"]
    display_name: str = ""
    icon: str = ""
    color: str = ""
    description: str = ""
    duration_ms: float | None = None
    result_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        config = AGENT_DISPLAY_CONFIG.get(self.agent_id, {})
        if not self.display_name:
            self.display_name = config.get("display_name", self.agent_id)
        if not self.icon:
            self.icon = config.get("icon", "bot")
        if not self.color:
            self.color = config.get("color", "#636E72")
        if not self.description:
            self.description = config.get("description", "")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


async def emit_agent_activity(
    stream_callback: Any | None,
    *,
    agent_id: str,
    status: Literal["pending", "active", "completed", "error"],
    duration_ms: float | None = None,
    result_summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit an agent_activity event through the stream callback."""
    if stream_callback is None:
        return

    event = AgentActivityEvent(
        agent_id=agent_id,
        status=status,
        duration_ms=duration_ms,
        result_summary=result_summary,
        metadata=metadata or {},
    )

    from app.gen.agent.v1 import agent_service_pb2
    import json

    await stream_callback(
        agent_service_pb2.ChatResponse(
            metadata={
                "event_type": "agent_activity",
                "payload": json.dumps(event.to_dict(), ensure_ascii=False),
            }
        )
    )


def get_stream_callback(config: dict[str, Any] | None) -> Any | None:
    """Extract stream_callback from LangGraph RunnableConfig."""
    if config is None:
        return None
    configurable = config.get("configurable", {})
    return configurable.get("stream_callback")
