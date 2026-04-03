from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
from app.models.subject import Subject
from app.services.galaxy.structure_service import GraphStructureService
from app.models.user import User
from app.services.expansion_service import ExpansionService
from app.services.galaxy_service import GalaxyService
from app.services.galaxy.ontology_generator import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATION_TYPES,
    FALLBACK_ENTITY_TYPE,
    FALLBACK_RELATION_TYPE,
    KnowledgeNodeCandidate,
    OntologyExtractionResult,
)
from app.services.graph_knowledge_service import GraphKnowledgeService
from app.services.knowledge_integration_service import KnowledgeIntegrationService
from app.services.knowledge_service import KnowledgeService
from app.services.node_sector_service import NodeSectorService, build_sector_visuals


async def _discard_background_task(coro, **_kwargs):
    coro.close()
    return None


@pytest.mark.asyncio
async def test_upsert_node_from_candidate_enriches_sector_and_unlocks_user(db_session):
    user = User(
        username="expansion_owner",
        email="expansion_owner@example.com",
        hashed_password="hashed",
    )
    trigger = KnowledgeNode(
        name="线性代数",
        description="矩阵与向量空间",
        importance_level=4,
        sector_weights={"COSMOS": 100},
        dominant_sector_code="COSMOS",
        sector_classification_status="completed",
        position_x=10,
        position_y=20,
    )
    db_session.add_all([user, trigger])
    await db_session.flush()

    service = ExpansionService(db_session)
    classified = build_sector_visuals(
        "矩阵分解",
        importance_level=4,
        sector_weights={"COSMOS": 70, "TECH": 30},
    )

    with patch.object(
        NodeSectorService,
        "classify_payload",
        new=AsyncMock(return_value=classified),
    ), patch(
        "app.services.expansion_service.embedding_service.get_embedding",
        new=AsyncMock(return_value=[0.1, 0.2]),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ):
        node, created = await service.upsert_node_from_candidate(
            user_id=user.id,
            candidate={
                "name": "矩阵分解",
                "description": "把矩阵拆成更容易计算和分析的结构。",
                "importance_level": 4,
                "relation_to_trigger": "evolution",
                "relation_strength": 0.82,
                "keywords": ["矩阵", "分解"],
            },
            trigger_node_id=trigger.id,
            parent_node_id=trigger.id,
        )

    await db_session.refresh(node)
    status = await db_session.scalar(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.node_id == node.id,
        )
    )
    relation = await db_session.scalar(
        select(NodeRelation).where(
            NodeRelation.source_node_id == trigger.id,
            NodeRelation.target_node_id == node.id,
        )
    )

    assert created is True
    assert node.parent_id == trigger.id
    assert node.sector_weights == {"COSMOS": 70, "TECH": 30}
    assert node.dominant_sector_code == "COSMOS"
    assert node.sector_classification_model == "expansion_sector_classifier"
    assert node.position_x is not None
    assert node.position_y is not None
    assert status is not None
    assert status.is_unlocked is True
    assert relation is not None
    assert relation.relation_type == "evolution"


@pytest.mark.asyncio
async def test_apply_expansion_candidates_reports_reused_nodes(db_session):
    user = User(
        username="reuse_owner",
        email="reuse_owner@example.com",
        hashed_password="hashed",
    )
    trigger = KnowledgeNode(
        name="概率论",
        description="研究随机现象的数学分支",
        importance_level=4,
        sector_weights={"COSMOS": 100},
        dominant_sector_code="COSMOS",
        sector_classification_status="completed",
        position_x=12,
        position_y=18,
    )
    reused = KnowledgeNode(
        id=uuid4(),
        name="条件概率",
        description="在已知事件发生条件下计算概率。",
        importance_level=3,
        sector_weights={"COSMOS": 100},
        dominant_sector_code="COSMOS",
        sector_classification_status="completed",
        position_x=22,
        position_y=28,
    )
    created = KnowledgeNode(
        id=uuid4(),
        name="贝叶斯推断",
        description="根据先验与观测更新概率判断。",
        importance_level=4,
        sector_weights={"COSMOS": 100},
        dominant_sector_code="COSMOS",
        sector_classification_status="completed",
        position_x=32,
        position_y=38,
    )
    db_session.add_all([user, trigger, reused])
    await db_session.flush()

    service = ExpansionService(db_session)

    async def _fake_find_semantic_duplicate(item):
        if item["name"] == "条件概率":
            return reused
        return None

    async def _fake_upsert_node_from_candidate(**kwargs):
        name = kwargs["candidate"]["name"]
        if name == "随机变量":
            return reused, False
        if name == "贝叶斯推断":
            return created, True
        raise AssertionError(f"Unexpected candidate: {name}")

    with patch.object(
        settings,
        "EXPANSION_SEMANTIC_DEDUP_ENABLED",
        True,
    ), patch.object(
        ExpansionService,
        "_find_semantic_duplicate",
        new=AsyncMock(side_effect=_fake_find_semantic_duplicate),
    ), patch.object(
        ExpansionService,
        "upsert_node_from_candidate",
        new=AsyncMock(side_effect=_fake_upsert_node_from_candidate),
    ), patch.object(
        ExpansionService,
        "_ensure_user_node_status",
        new=AsyncMock(),
    ), patch.object(
        ExpansionService,
        "_ensure_relation",
        new=AsyncMock(),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ):
        result = await service.apply_expansion_candidates(
            trigger.id,
            user.id,
            candidates=[
                {
                    "candidate_id": "reuse-semantic",
                    "name": "条件概率",
                    "description": "用已有节点复用已有知识。",
                },
                {
                    "candidate_id": "reuse-exact",
                    "name": "随机变量",
                    "description": "命中已有节点，不重复创建。",
                },
                {
                    "candidate_id": "create-new",
                    "name": "贝叶斯推断",
                    "description": "需要新建的拓展节点。",
                },
            ],
        )

    assert result.applied_count == 3
    assert result.created_count == 1
    assert result.reused_count == 2
    assert [node.name for node in result.created_nodes] == ["贝叶斯推断"]
    assert [node.id for node in result.reused_nodes] == [reused.id]


@pytest.mark.asyncio
async def test_galaxy_service_create_node_uses_enriched_creation_pipeline(db_session):
    user = User(
        username="galaxy_creator",
        email="galaxy_creator@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    service = GalaxyService(db_session)
    classified = build_sector_visuals(
        "傅里叶分析",
        importance_level=5,
        sector_weights={"COSMOS": 85, "TECH": 15},
    )

    with patch.object(
        NodeSectorService,
        "classify_payload",
        new=AsyncMock(return_value=classified),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ), patch(
        "app.core.task_manager.task_manager.spawn",
        new=_discard_background_task,
    ):
        node = await service.create_node(
            user_id=user.id,
            title="傅里叶分析",
            summary="理解频域和时域之间的转换。",
            tags=["信号", "频域"],
            importance_level=5,
        )

    status = await db_session.scalar(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.node_id == node.id,
        )
    )

    assert node.source_type == "user_created"
    assert node.sector_weights == {"COSMOS": 85, "TECH": 15}
    assert node.dominant_sector_code == "COSMOS"
    assert node.sector_classification_status == "completed"
    assert node.position_x is not None
    assert node.position_y is not None
    assert status is not None
    assert status.is_unlocked is True


@pytest.mark.asyncio
async def test_graph_structure_service_direct_create_populates_sector_metadata(db_session):
    user = User(
        username="structure_creator",
        email="structure_creator@example.com",
        hashed_password="hashed",
    )
    parent = KnowledgeNode(
        name="编程基础",
        importance_level=3,
        sector_weights={"TECH": 100},
        dominant_sector_code="TECH",
        sector_classification_status="completed",
    )
    db_session.add_all([user, parent])
    await db_session.flush()

    node = await GraphStructureService(db_session).create_node(
        user_id=user.id,
        title="算法复杂度",
        summary="理解时间复杂度和空间复杂度。",
        parent_node_id=parent.id,
    )

    assert node.sector_weights == {"TECH": 100}
    assert node.dominant_sector_code == "TECH"
    assert node.sector_classification_status == "completed"
    assert node.position_x is not None
    assert node.position_y is not None


@pytest.mark.asyncio
async def test_graph_knowledge_service_create_node_reuses_unified_creation(db_session):
    with patch(
        "app.services.graph_knowledge_service.get_age_client",
        return_value=object(),
    ):
        service = GraphKnowledgeService(db_session)

    with patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ):
        node = await service.create_knowledge_node(
            name="文艺复兴",
            description="欧洲思想与艺术的重要转折点。",
            sector_code="CIVILIZATION",
            importance_level=4,
            keywords=["历史", "艺术"],
        )

    assert node.sector_weights == {"CIVILIZATION": 100}
    assert node.dominant_sector_code == "CIVILIZATION"
    assert node.sector_classification_model == "graph_knowledge_service"
    assert node.position_x is not None
    assert node.position_y is not None


@pytest.mark.asyncio
async def test_knowledge_service_plan_helpers_create_sectorized_nodes_and_links(db_session):
    user = User(
        username="plan_owner",
        email="plan_owner@example.com",
        hashed_password="hashed",
    )
    subject = Subject(name="数学", sector_code="COSMOS")
    db_session.add_all([user, subject])
    await db_session.flush()

    async def _fake_classify_payload(**kwargs):
        weights = {"COSMOS": 100} if kwargs["name"] == "数学" else {"COSMOS": 80, "TECH": 20}
        return build_sector_visuals(
            kwargs["name"],
            importance_level=kwargs.get("importance_level", 3),
            sector_weights=weights,
        )

    service = KnowledgeService(db_session)

    with patch.object(
        NodeSectorService,
        "classify_payload",
        new=AsyncMock(side_effect=_fake_classify_payload),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ), patch(
        "app.core.task_manager.task_manager.spawn",
        new=_discard_background_task,
    ):
        created = await service.create_or_update_link(
            user_id=user.id,
            source_name="数学",
            target_name="极限",
            relation_type="contains",
            strength=0.7,
        )

    source_node = await service.find_node_by_name(user.id, "数学")
    target_node = await service.find_node_by_name(user.id, "极限")
    relation = await db_session.scalar(
        select(NodeRelation).where(
            NodeRelation.source_node_id == source_node.id,
            NodeRelation.target_node_id == target_node.id,
        )
    )

    assert created is True
    assert source_node is not None
    assert target_node is not None
    assert source_node.sector_weights == {"COSMOS": 100}
    assert target_node.sector_weights == {"COSMOS": 80, "TECH": 20}
    assert relation is not None
    assert relation.relation_type == "contains"


@pytest.mark.asyncio
async def test_galaxy_service_create_nodes_from_document_enriches_all_nodes(db_session):
    user = User(
        username="document_owner",
        email="document_owner@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    stored_file = StoredFile(
        user_id=user.id,
        file_name="signals.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key="signals.pdf",
        status="ready",
    )
    db_session.add(stored_file)
    await db_session.flush()

    service = GalaxyService(db_session)
    ontology = OntologyExtractionResult(
        entity_types=DEFAULT_ENTITY_TYPES,
        fallback_entity_type=FALLBACK_ENTITY_TYPE,
        relation_types=DEFAULT_RELATION_TYPES,
        fallback_relation_type=FALLBACK_RELATION_TYPE,
        nodes=[
            KnowledgeNodeCandidate(
                name="傅里叶变换",
                summary="把信号从时域映射到频域。",
                node_type="Method",
                keywords=["信号", "频域"],
                importance_level=4,
            )
        ],
        relations=[],
    )

    async def _fake_classify_payload(**kwargs):
        weights = {"TECH": 100} if kwargs["name"] == "傅里叶变换" else {"WISDOM": 100}
        return build_sector_visuals(
            kwargs["name"],
            importance_level=kwargs.get("importance_level", 3),
            sector_weights=weights,
        )

    with patch.object(
        GalaxyService,
        "auto_generate_ontology",
        new=AsyncMock(return_value=ontology),
    ), patch.object(
        NodeSectorService,
        "classify_payload",
        new=AsyncMock(side_effect=_fake_classify_payload),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ):
        result = await service.create_nodes_from_document(
            user_id=user.id,
            file_id=stored_file.id,
            file_name=stored_file.file_name,
            document_text="signal processing fundamentals",
        )

    root_node = result["root_node"]
    child_node = result["created_nodes"][0]
    root_status = await db_session.scalar(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.node_id == root_node.id,
        )
    )
    child_status = await db_session.scalar(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.node_id == child_node.id,
        )
    )
    relation = await db_session.scalar(
        select(NodeRelation).where(
            NodeRelation.source_node_id == root_node.id,
            NodeRelation.target_node_id == child_node.id,
        )
    )

    assert root_node.status == "draft"
    assert root_node.source_file_id == stored_file.id
    assert root_node.sector_classification_status == "completed"
    assert child_node.status == "draft"
    assert child_node.source_file_id == stored_file.id
    assert child_node.sector_weights == {"TECH": 100}
    assert root_status is not None
    assert child_status is not None
    assert relation is not None
    assert relation.relation_type == "parent_child"


@pytest.mark.asyncio
async def test_knowledge_integration_service_new_vocabulary_node_is_sectorized(db_session):
    user = User(
        username="vocabulary_owner",
        email="vocabulary_owner@example.com",
        hashed_password="hashed",
    )
    subject = Subject(name="计算机科学", sector_code="TECH")
    db_session.add_all([user, subject])
    await db_session.flush()

    service = KnowledgeIntegrationService(db_session)
    classified = build_sector_visuals(
        "polymorphism",
        importance_level=1,
        sector_weights={"TECH": 100},
    )

    with patch.object(
        NodeSectorService,
        "classify_payload",
        new=AsyncMock(return_value=classified),
    ), patch.object(
        ExpansionService,
        "_invalidate_after_graph_mutation",
        new=AsyncMock(),
    ), patch.object(
        KnowledgeIntegrationService,
        "_generate_embedding_async",
        new=AsyncMock(),
    ):
        node = await service.create_vocabulary_node(
            user_id=user.id,
            source_text="polymorphism",
            translation="多态",
            context="Polymorphism lets one interface support many implementations.",
            language="en",
            domain="oop",
            subject_id=subject.id,
        )

    status = await db_session.scalar(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user.id,
            UserNodeStatus.node_id == node.id,
        )
    )

    assert node.source_type == "translation"
    assert node.status == "draft"
    assert node.sector_weights == {"TECH": 100}
    assert node.dominant_sector_code == "TECH"
    assert status is not None
    assert status.is_unlocked is True
    assert status.next_review_at is not None
