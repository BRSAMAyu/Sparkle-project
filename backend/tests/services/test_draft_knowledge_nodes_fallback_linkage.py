"""演示缺陷 ❌#5 · 文档 fallback 路径补建 knowledge_node_documents 关联.

背景（docs/competition/大创市赛/演示路径盘点_2026-09-20.md §❌#5）：
ontology 主路径失败后静默 fallback 到启发式分节，但 fallback 建的节点
不写 knowledge_node_documents（user/node/file 三元关联）——导致
drafts/summary=0 与 galaxy/drafts=N 自相矛盾、节点拖动归属判非 owned。

本测试钉住：fallback 路径产出的每个节点（根 + 分节）都有归属行，
且根节点 is_primary=True、分节 is_primary=False（与 galaxy 主路径一致）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.models.user import User
from app.services.document_service import VectorChunk, DocumentService
from app.services.node_sector_service import build_sector_visuals


def _chunk(content: str, section_title: str | None) -> VectorChunk:
    return VectorChunk(
        content=content,
        page_numbers=[1],
        section_title=section_title,
        metadata={},
    )


@pytest.mark.asyncio
async def test_fallback_creates_document_link_rows(db_session):
    """ontology 失败 → fallback：根+分节节点全部有 KnowledgeNodeDocument 归属行."""
    user = User(username="fallback_owner", email="fallback_owner@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    stored = StoredFile(
        user_id=user.id,
        file_name="机器学习入门.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="docs",
        object_key="docs/机器学习入门.pdf",
        status="processed",
    )
    db_session.add(stored)
    await db_session.flush()

    chunks = [
        _chunk("监督学习 是最常见的学习范式，通过标注数据训练模型。", "监督学习"),
        _chunk("无监督学习 从未标注数据中发现结构。", "无监督学习"),
    ]

    service = DocumentService()

    classified = build_sector_visuals("监督学习", importance_level=1, sector_weights={"COSMOS": 100})
    with patch(
        "app.services.galaxy_service.GalaxyService.create_nodes_from_document",
        new=AsyncMock(side_effect=RuntimeError("ontology unavailable in demo")),
    ), patch(
        "app.services.expansion_service.embedding_service.get_embedding",
        new=AsyncMock(return_value=[0.1, 0.2]),
    ), patch(
        "app.services.node_sector_service.NodeSectorService.classify_payload",
        new=AsyncMock(return_value=classified),
    ), patch(
        "app.services.expansion_service.ExpansionService._invalidate_after_graph_mutation",
        new=AsyncMock(),
    ):
        await service.draft_knowledge_nodes(db_session, stored.id, user.id, chunks)

    # fallback 确实走了（根节点存在）
    root = await db_session.scalar(
        select(KnowledgeNode).where(KnowledgeNode.name == "机器学习入门.pdf")
    )
    assert root is not None

    links = (
        await db_session.execute(
            select(KnowledgeNodeDocument).where(KnowledgeNodeDocument.file_id == stored.id)
        )
    ).scalars().all()

    # 每个产出节点都有归属行（根 + 至少一个分节）
    linked_node_ids = {link.node_id for link in links}
    created_nodes = (await db_session.execute(
        select(KnowledgeNode).where(KnowledgeNode.source_file_id == stored.id)
    )).scalars().all()
    assert len(created_nodes) >= 2, "fallback 应产出根节点和分节节点"
    assert {node.id for node in created_nodes} == linked_node_ids, "每个 fallback 节点都必须有归属行"

    # 三元归属正确 + is_primary 语义与 galaxy 主路径一致
    for link in links:
        assert link.user_id == user.id
        assert link.file_id == stored.id
    primary_links = [link for link in links if link.is_primary]
    assert len(primary_links) == 1
    assert primary_links[0].node_id == root.id
