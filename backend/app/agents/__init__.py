"""
Multi-Agent Collaboration System

多智能体协作系统 - 专业化AI智能体共同解决复杂问题
"""

from typing import Dict, Type
from .base_agent import BaseAgent
from .orchestrator_agent import OrchestratorAgent
from .specialist_agents import MathAgent, CodeAgent, WritingAgent, ScienceAgent


# Agent Registry
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "orchestrator": OrchestratorAgent,
    "math": MathAgent,
    "code": CodeAgent,
    "writing": WritingAgent,
    "science": ScienceAgent,
}


def get_agent(agent_type: str) -> BaseAgent:
    """获取指定类型的智能体实例"""
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class()


__all__ = [
    "BaseAgent",
    "OrchestratorAgent",
    "MathAgent",
    "CodeAgent",
    "WritingAgent",
    "ScienceAgent",
    "AGENT_REGISTRY",
    "get_agent",
]
