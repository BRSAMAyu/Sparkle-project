"""附带缺陷 · galaxy ontology 启发式 fallback 的纯标点标题行剔除.

背景（2026-09-20 演示盘点 · 造数员报告「create_nodes_from_document 先行失败」）：
OntologyGenerator._fallback_extraction 把 markdown 的 ``====`` / ``----``
分隔行、表格分隔线等纯标点行当标题候选 → 下游
``upsert_node_from_candidate`` 节点名校验（is_valid_knowledge_node_name /
_sanitize_text 拒绝纯标点）raise ValueError →
``GalaxyService.create_nodes_from_document`` 整体失败，被
document_service 的 warning 吞掉后静默 fallback（且曾不建关联行）。

本测试钉住：LLM 不可用时（启发式 fallback 路径）产出的全部节点候选名
都能通过 ``is_valid_knowledge_node_name`` 校验——galaxy 主路径在
零 LLM 环境确定性成功。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.expansion_service import is_valid_knowledge_node_name
from app.services.galaxy.ontology_generator import OntologyGenerator

_DEMO_MARKDOWN = """机器学习入门讲义
================

第一章 绪论
----------

机器学习是人工智能的核心分支。

| 方法 | 说明 |
|------|------|
| 监督学习 | 有标注 |

总结与展望
==========
"""


def test_fallback_extraction_rejects_punct_only_headings():
    gen = OntologyGenerator()
    result = gen._fallback_extraction(_DEMO_MARKDOWN, subject="机器学习")
    assert result.nodes, "启发式 fallback 应产出节点候选"
    for node in result.nodes:
        assert is_valid_knowledge_node_name(node.name), (
            f"纯标点/无效候选名漏进 fallback: {node.name!r}"
        )
    # 真实标题应保留
    names = {node.name for node in result.nodes}
    assert any("绪论" in name for name in names)


@pytest.mark.asyncio
async def test_generate_with_unavailable_llm_produces_valid_nodes(monkeypatch):
    """LLM 不可用（json_call 降级）→ generate 全链路产出合法节点候选."""
    # analysis_llm 是模块级单例 wrapper——打桩其 json_call 方法（返回 None →
    # generate 内部走 `payload or fallback.to_dict()` 兜底，即零 LLM 语义）
    monkeypatch.setattr(
        "app.services.galaxy.ontology_generator.analysis_llm.json_call",
        AsyncMock(return_value=None),
    )
    gen = OntologyGenerator()
    result = await gen.generate(document_text=_DEMO_MARKDOWN, subject="机器学习")
    assert result.nodes, "LLM 不可用时应有启发式节点候选"
    for node in result.nodes:
        assert is_valid_knowledge_node_name(node.name), (
            f"generate 兜底路径漏进无效候选名: {node.name!r}"
        )
