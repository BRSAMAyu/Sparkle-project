"""
E2E Test: Knowledge Galaxy System
=================================

Tests the complete knowledge graph flow:
Node Creation → Relationship Building → Visualization → Interaction

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select

from app.models.knowledge import (
    KnowledgeNode,
    KnowledgeRelationship,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
)
from app.services.galaxy_service import GalaxyService
from app.services.rag_service import RAGService


# =============================================================================
# Test 1: Knowledge Node Creation and Persistence
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_node_creation_flow(
    db_session,
    test_user,
    test_assertions,
):
    """
    E2E: User creates knowledge node → Node persisted → Relationships established

    Scenario:
    1. User learns new concept: "Python变量"
    2. System creates knowledge node
    3. Node linked to parent: "Python基础"
    4. Relationship type: "part_of"
    5. Node persisted to database
    6. Node available in galaxy view
    """
    # Arrange: Initialize galaxy service
    galaxy_service = GalaxyService(db_session)

    # Create parent node first
    parent_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="Python基础",
        node_type=NodeType.SUBJECT,
        description="Python编程基础知识",
        metadata={"level": "beginner"},
    )
    db_session.add(parent_node)
    await db_session.commit()

    # Act: User creates child node
    child_node = await galaxy_service.create_node(
        user_id=test_user.id,
        title="Python变量",
        node_type=NodeType.CONCEPT,
        description="Python中变量的定义和使用",
        parent_id=str(parent_node.id),
        relationship_type=RelationshipType.PART_OF,
        metadata={
            "difficulty": 1,
            "importance": 0.8,
            "mastery_level": 0.3,
        },
    )

    # Assert: Node created
    assert child_node is not None
    assert child_node.title == "Python变量"
    assert child_node.node_type == NodeType.CONCEPT
    assert child_node.user_id == test_user.id

    # Assert: Relationship established
    result = await db_session.execute(
        select(KnowledgeRelationship).where(
            KnowledgeRelationship.source_node_id == child_node.id,
            KnowledgeRelationship.target_node_id == parent_node.id,
        )
    )
    relationship = result.scalar_one_or_none()
    assert relationship is not None
    assert relationship.relationship_type == RelationshipType.PART_OF

    # Assert: Node queryable in galaxy
    nodes = await galaxy_service.get_nodes_by_user(test_user.id)
    assert len(nodes) == 2
    assert any(n.title == "Python变量" for n in nodes)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_relationship_types_and_traversal(
    db_session,
    test_user,
):
    """
    E2E: Multiple relationship types → Graph traversal → Path finding

    Scenario:
    1. Create knowledge graph: Python → 变量 → 数据类型 → 字符串
    2. Relationships: part_of, uses, type_of
    3. Traverse from "字符串" back to "Python"
    4. Find shortest path
    5. Verify all relationships
    """
    # Arrange: Initialize galaxy service
    galaxy_service = GalaxyService(db_session)

    # Create nodes
    python_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="Python",
        node_type=NodeType.SUBJECT,
        description="Python编程语言",
    )
    variable_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="变量",
        node_type=NodeType.CONCEPT,
        description="变量的概念",
    )
    datatype_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="数据类型",
        node_type=NodeType.CONCEPT,
        description="Python数据类型",
    )
    string_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="字符串",
        node_type=NodeType.CONCEPT,
        description="字符串类型",
    )
    db_session.add_all([python_node, variable_node, datatype_node, string_node])
    await db_session.commit()

    # Create relationships
    # Python → 变量 (part_of)
    rel1 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=variable_node.id,
        target_node_id=python_node.id,
        relationship_type=RelationshipType.PART_OF,
        strength=0.9,
    )
    # 变量 → 数据类型 (uses)
    rel2 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=datatype_node.id,
        target_node_id=variable_node.id,
        relationship_type=RelationshipType.USES,
        strength=0.8,
    )
    # 数据类型 → 字符串 (type_of)
    rel3 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=string_node.id,
        target_node_id=datatype_node.id,
        relationship_type=RelationshipType.IS_A,
        strength=0.95,
    )
    db_session.add_all([rel1, rel2, rel3])
    await db_session.commit()

    # Act: Traverse from "字符串" to "Python"
    path = await galaxy_service.find_shortest_path(
        source_node_id=string_node.id,
        target_node_id=python_node.id,
        user_id=test_user.id,
    )

    # Assert: Path found with 3 hops
    assert path is not None, "Should find path"
    assert len(path) == 4, "Path should have 4 nodes: 字符串 → 数据类型 → 变量 → Python"
    assert path[0].id == string_node.id
    assert path[-1].id == python_node.id

    # Act: Get connected components
    connected_nodes = await galaxy_service.get_connected_nodes(
        node_id=variable_node.id,
        user_id=test_user.id,
        max_depth=2,
    )

    # Assert: All nodes reachable
    assert len(connected_nodes) == 4, "All nodes should be connected"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_mastery_tracking_and_update(
    db_session,
    test_user,
):
    """
    E2E: User practices concept → Mastery tracked → Galaxy visualization updated

    Scenario:
    1. User has node "循环" with mastery_level=0.2
    2. User completes quiz on loops → 80% score
    3. Mastery updated to 0.6 (0.2 + 0.8*0.5)
    4. Node color changes in galaxy visualization
    5. Related nodes also affected (prerequisite strength)
    """
    # Arrange: Create knowledge node with low mastery
    node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="for循环",
        node_type=NodeType.CONCEPT,
        description="Python for循环",
        metadata={
            "mastery_level": 0.2,  # 20% mastered
            "practice_count": 1,
        },
    )
    db_session.add(node)
    await db_session.commit()

    # Arrange: Initialize galaxy service
    galaxy_service = GalaxyService(db_session)

    # Act: User completes practice with 80% score
    await galaxy_service.update_mastery(
        node_id=node.id,
        user_id=test_user.id,
        practice_score=0.8,  # 80% correct
        practice_type="quiz",
    )

    # Assert: Mastery updated
    await db_session.refresh(node)
    # Formula: old_mastery + (score * weight * (1 - old_mastery))
    # 0.2 + (0.8 * 0.5 * 0.8) = 0.2 + 0.32 = 0.52
    expected_mastery = 0.2 + (0.8 * 0.5 * (1 - 0.2))
    assert abs(node.metadata["mastery_level"] - expected_mastery) < 0.01

    # Assert: Practice count incremented
    assert node.metadata["practice_count"] == 2

    # Assert: Visualization data updated
    viz_data = await galaxy_service.get_visualization_data(
        user_id=test_user.id,
        center_node_id=node.id,
        depth=1,
    )
    assert viz_data is not None
    assert len(viz_data["nodes"]) > 0

    # Find the for_loop node in visualization
    for_loop_node = next((n for n in viz_data["nodes"] if n["title"] == "for循环"), None)
    assert for_loop_node is not None
    # Color should reflect mastery (e.g., green for high mastery)
    assert "color" in for_loop_node


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_prerequisite_validation(
    db_session,
    test_user,
):
    """
    E2E: User attempts advanced concept → Prerequisites checked → Recommendations

    Scenario:
    1. User wants to learn "装饰器" (advanced)
    2. System checks prerequisites: 函数 → 作用域 → 高阶函数
    3. Prerequisite "高阶函数" not mastered (< 0.5)
    4. System recommends learning path
    5. User sees what to learn first
    """
    # Arrange: Create knowledge graph with prerequisites
    decorator_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="装饰器",
        node_type=NodeType.CONCEPT,
        description="Python装饰器模式",
        metadata={"difficulty": 5, "mastery_level": 0.0},
    )

    higher_order_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="高阶函数",
        node_type=NodeType.CONCEPT,
        description="函数作为参数",
        metadata={"difficulty": 4, "mastery_level": 0.3},  # Not mastered
    )

    function_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="函数",
        node_type=NodeType.CONCEPT,
        description="Python函数定义",
        metadata={"difficulty": 2, "mastery_level": 0.7},  # Mastered
    )
    db_session.add_all([decorator_node, higher_order_node, function_node])
    await db_session.commit()

    # Create prerequisite relationships
    # 装饰器 requires 高阶函数
    req_rel1 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=decorator_node.id,
        target_node_id=higher_order_node.id,
        relationship_type=RelationshipType.REQUIRES,
        strength=1.0,
    )
    # 高阶函数 requires 函数
    req_rel2 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=higher_order_node.id,
        target_node_id=function_node.id,
        relationship_type=RelationshipType.REQUIRES,
        strength=1.0,
    )
    db_session.add_all([req_rel1, req_rel2])
    await db_session.commit()

    # Arrange: Initialize galaxy service
    galaxy_service = GalaxyService(db_session)

    # Act: User attempts to learn "装饰器"
    prereq_check = await galaxy_service.check_prerequisites(
        node_id=decorator_node.id,
        user_id=test_user.id,
    )

    # Assert: Prerequisites not satisfied
    assert prereq_check["satisfied"] is False, "Prerequisites should not be satisfied"
    assert len(prereq_check["missing"]) == 1, "Should have 1 missing prerequisite"
    assert prereq_check["missing"][0]["title"] == "高阶函数"

    # Assert: Learning path recommended
    assert "learning_path" in prereq_check
    assert len(prereq_check["learning_path"]) == 2  # 函数 → 高阶函数


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_graph_visualization_layout(
    db_session,
    test_user,
):
    """
    E2E: Large knowledge graph → Force-directed layout → Interactive rendering

    Scenario:
    1. User has 20 interconnected knowledge nodes
    2. System generates force-directed layout
    3. Nodes positioned to minimize overlap
    4. Relationships rendered as edges
    5. User can drag, zoom, pan
    6. Layout persists and loads quickly
    """
    # Arrange: Create knowledge graph with 20 nodes
    galaxy_service = GalaxyService(db_session)

    nodes = []
    concepts = [
        "变量", "数据类型", "字符串", "数字", "列表",
        "字典", "元组", "集合", "条件语句", "循环",
        "函数", "类", "对象", "继承", "多态",
        "模块", "包", "文件", "异常", "装饰器",
    ]

    for i, concept in enumerate(concepts):
        node = KnowledgeNode(
            id=uuid4(),
            user_id=test_user.id,
            title=concept,
            node_type=NodeType.CONCEPT,
            description=f"Python {concept}",
            metadata={
                "difficulty": (i % 5) + 1,
                "mastery_level": 0.5,
            },
        )
        nodes.append(node)
        db_session.add(node)

    await db_session.commit()

    # Create relationships (each node connects to 2-3 others)
    for i in range(len(nodes)):
        for j in range(i + 1, min(i + 4, len(nodes))):
            rel = KnowledgeRelationship(
                id=uuid4(),
                user_id=test_user.id,
                source_node_id=nodes[i].id,
                target_node_id=nodes[j].id,
                relationship_type=RelationshipType.RELATED,
                strength=0.7,
            )
            db_session.add(rel)

    await db_session.commit()

    # Act: Generate visualization layout
    layout_data = await galaxy_service.generate_layout(
        user_id=test_user.id,
        algorithm="force_directed",
        center_node_id=nodes[0].id,
        max_nodes=50,
    )

    # Assert: Layout includes all nodes
    assert len(layout_data["nodes"]) == 20

    # Assert: Each node has x, y coordinates
    for node in layout_data["nodes"]:
        assert "x" in node
        assert "y" in node
        assert isinstance(node["x"], (int, float))
        assert isinstance(node["y"], (int, float))

    # Assert: Edges included
    assert len(layout_data["edges"]) > 0

    # Assert: No node overlap (positions are unique)
    positions = [(n["x"], n["y"]) for n in layout_data["nodes"]]
    assert len(positions) == len(set(positions)), "All node positions should be unique"

    # Assert: Layout cached for fast loading
    cached_layout = await galaxy_service.get_cached_layout(
        user_id=test_user.id,
        center_node_id=nodes[0].id,
    )
    assert cached_layout is not None


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_knowledge_search_and_discovery(
    db_session,
    test_user,
):
    """
    E2E: User searches knowledge → RAG retrieves → Galaxy highlights path

    Scenario:
    1. User searches "如何遍历列表"
    2. RAG finds relevant nodes: "列表", "循环", "for循环"
    3. Galaxy highlights these nodes
    4. Shows relationships between them
    5. User can click to explore
    """
    # Arrange: Create relevant knowledge nodes
    list_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="列表",
        node_type=NodeType.CONCEPT,
        description="Python列表数据结构",
        metadata={
            "keywords": ["list", "array", "序列"],
            "mastery_level": 0.6,
        },
    )

    loop_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="循环",
        node_type=NodeType.CONCEPT,
        description="循环控制结构",
        metadata={
            "keywords": ["loop", "迭代", "遍历"],
            "mastery_level": 0.5,
        },
    )

    for_loop_node = KnowledgeNode(
        id=uuid4(),
        user_id=test_user.id,
        title="for循环",
        node_type=NodeType.CONCEPT,
        description="for循环遍历序列",
        metadata={
            "keywords": ["for", "遍历", "迭代器"],
            "mastery_level": 0.4,
        },
    )
    db_session.add_all([list_node, loop_node, for_loop_node])
    await db_session.commit()

    # Create relationships
    rel1 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=for_loop_node.id,
        target_node_id=list_node.id,
        relationship_type=RelationshipType.USES,
        strength=0.9,
    )
    rel2 = KnowledgeRelationship(
        id=uuid4(),
        user_id=test_user.id,
        source_node_id=for_loop_node.id,
        target_node_id=loop_node.id,
        relationship_type=RelationshipType.IS_A,
        strength=1.0,
    )
    db_session.add_all([rel1, rel2])
    await db_session.commit()

    # Arrange: Initialize services
    galaxy_service = GalaxyService(db_session)
    rag_service = RAGService(db_session)

    # Act: User searches
    search_query = "如何遍历列表"

    # RAG search
    search_results = await rag_service.search_knowledge(
        query=search_query,
        user_id=test_user.id,
        limit=5,
    )

    # Assert: Relevant nodes found
    assert len(search_results) > 0

    # Should find for_loop_node (most relevant)
    result_titles = [r["title"] for r in search_results]
    assert "for循环" in result_titles or "循环" in result_titles

    # Act: Highlight in galaxy
    highlighted_nodes = await galaxy_service.highlight_search_results(
        node_ids=[r["id"] for r in search_results],
        user_id=test_user.id,
    )

    # Assert: Subgraph includes connected nodes
    assert len(highlighted_nodes["nodes"]) >= 3  # At least the 3 main nodes

    # Assert: Path shown
    assert len(highlighted_nodes["edges"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
