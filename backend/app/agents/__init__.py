"""
Multi-Agent Collaboration System

多智能体协作系统 - 专业化AI智能体共同解决复杂问题

Version 2.0 - Enhanced with Knowledge Graph Integration
"""

from typing import Dict, Type
from .base_agent import BaseAgent, AgentContext, AgentResponse
from .orchestrator_agent import OrchestratorAgent
from .specialist_agents import MathAgent, CodeAgent, WritingAgent, ScienceAgent

# Enhanced Agents (v2.0)
from .enhanced_agents import (
    StudyPlannerAgent,
    ProblemSolverAgent,
    EnhancedAgentContext,
    EnhancedAgentRole
)
from .enhanced_orchestrator import EnhancedOrchestratorAgent, create_enhanced_orchestrator
from .collaboration_workflows import (
    TaskDecompositionWorkflow,
    ProgressiveExplorationWorkflow,
    ErrorDiagnosisWorkflow,
    CollaborationResult
)


# Agent Registry
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    # Original Agents
    "orchestrator": OrchestratorAgent,
    "math": MathAgent,
    "code": CodeAgent,
    "writing": WritingAgent,
    "science": ScienceAgent,
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
