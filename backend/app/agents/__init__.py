"""
Multi-Agent Collaboration System

多智能体协作系统 - 专业化AI智能体共同解决复杂问题

Version 2.0 - Enhanced with Knowledge Graph Integration
"""

from typing import Dict, Type

from .base_agent import AgentContext, AgentResponse, BaseAgent
from .collaboration_workflows import (
    CollaborationResult,
    ErrorDiagnosisWorkflow,
    ProgressiveExplorationWorkflow,
    TaskDecompositionWorkflow,
)

# Enhanced Agents (v2.0)
from .enhanced_agents import EnhancedAgentContext, EnhancedAgentRole, ProblemSolverAgent, StudyPlannerAgent
from .enhanced_orchestrator import EnhancedOrchestratorAgent, create_enhanced_orchestrator
from .orchestrator_agent import OrchestratorAgent
from .search_agent import SearchAgent
from .specialist_agents import CodeAgent, MathAgent, ScienceAgent, WritingAgent

# Agent Registry
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    # Original Agents
    "orchestrator": OrchestratorAgent,
    "math": MathAgent,
    "code": CodeAgent,
    "writing": WritingAgent,
    "science": ScienceAgent,
    "search": SearchAgent,
    # Enhanced Agents (v2.0)
    "enhanced_orchestrator": EnhancedOrchestratorAgent,
    "study_planner": StudyPlannerAgent,
    "problem_solver": ProblemSolverAgent,
}


def get_agent(agent_type: str) -> BaseAgent:
    """获取指定类型的智能体实例"""
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class()


__all__ = [
    # Base Classes
    "BaseAgent",
    "AgentContext",
    "AgentResponse",
    # Original Agents
    "OrchestratorAgent",
    "MathAgent",
    "CodeAgent",
    "WritingAgent",
    "ScienceAgent",
    "SearchAgent",
    # Enhanced Agents (v2.0)
    "EnhancedOrchestratorAgent",
    "StudyPlannerAgent",
    "ProblemSolverAgent",
    "EnhancedAgentContext",
    "EnhancedAgentRole",
    # Workflows
    "TaskDecompositionWorkflow",
    "ProgressiveExplorationWorkflow",
    "ErrorDiagnosisWorkflow",
    "CollaborationResult",
    # Factory Functions
    "create_enhanced_orchestrator",
    "AGENT_REGISTRY",
    "get_agent",
]
