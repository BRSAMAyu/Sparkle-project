"""WT651-D04（V3-FIX-345）：EnhancedOrchestratorAgent 休眠 mock 轨退役守卫。

背景（v3-output/WT651-D04/audit.md §P1）：
- agents/enhanced_orchestrator.py 全仓零生产调用方（multi-agent/chat 实际走
  orchestrator_agent.create_multi_agent_workflow），其 ``_build_enhanced_context``
  硬编码假知识图谱/假掌握度/假遗忘风险（自述「模拟数据（实际应调用真实服务）」）；
- 该类经 AGENT_REGISTRY 被 GET /multi-agent/agents 宣称为可用专家（宣称面大于
  接线面），与 FIX-331「休眠残轨自供 mock」同形态。

裁决=删除残轨（非接线）：真实数据路径已由 enhanced_agents.StudyPlannerAgent 等
（GalaxyKnowledgeService 真源）覆盖。本守卫防再犯：模块不得复活、注册表与
包导出面不得再宣称该智能体。
"""

from __future__ import annotations

import importlib.util

import app.agents as agents_pkg
from app.agents import AGENT_REGISTRY


def test_enhanced_orchestrator_module_is_gone():
    assert importlib.util.find_spec("app.agents.enhanced_orchestrator") is None


def test_registry_no_longer_advertises_enhanced_orchestrator():
    assert "enhanced_orchestrator" not in AGENT_REGISTRY
    assert not hasattr(agents_pkg, "EnhancedOrchestratorAgent")
    assert not hasattr(agents_pkg, "create_enhanced_orchestrator")


def test_get_agent_rejects_retired_agent_type():
    import pytest

    from app.agents import get_agent

    with pytest.raises(ValueError, match="enhanced_orchestrator"):
        get_agent("enhanced_orchestrator")
