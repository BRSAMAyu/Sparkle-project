"""
GraphReasoningService Tests
测试基于拓扑排序的动态学习路径生成
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.graph_reasoning_service import GraphReasoningService
from app.models.galaxy import KnowledgeNode, NodeRelation


def _mock_execute_result(rows, *, scalar_rows=None):
    result = MagicMock()
    result.all.return_value = rows
    result.scalars.return_value.all.return_value = scalar_rows if scalar_rows is not None else rows
    return result

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def service(mock_db):
    return GraphReasoningService(mock_db)

@pytest.mark.asyncio
async def test_generate_simple_path(service, mock_db):
    """Test path generation for A -> B -> C"""
    
    # Setup Data
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()
    user_id = uuid.uuid4()
    
    nodes = [
        KnowledgeNode(id=id_a, name="Node A"),
        KnowledgeNode(id=id_b, name="Node B"),
        KnowledgeNode(id=id_c, name="Node C")
    ]
    
    edges = [
        NodeRelation(source_node_id=id_a, target_node_id=id_b, relation_type="PREREQUISITE"),
        NodeRelation(source_node_id=id_b, target_node_id=id_c, relation_type="PREREQUISITE")
    ]
    
    # Mock DB returns
    mock_db.execute.side_effect = [
        # 1. Load nodes
        _mock_execute_result([], scalar_rows=nodes),
        # 2. Load edges
        _mock_execute_result([], scalar_rows=edges),
        # 3. Get mastered nodes (empty)
        _mock_execute_result([])
    ]
    
    # Run
    path = await service.generate_learning_path(user_id, id_c)
    
    # Verify
    assert len(path) == 3
    assert path[0]["id"] == str(id_a)
    assert path[1]["id"] == str(id_b)
    assert path[2]["id"] == str(id_c)
    assert path[0]["status"] == "unlocked" # A has no prerequisites, so it is unlocked
    assert path[1]["status"] == "locked"   # B needs A
    assert path[2]["status"] == "locked"   # C needs B

@pytest.mark.asyncio
async def test_generate_path_with_mastery(service, mock_db):
    """Test path with mastered nodes"""
    # A -> B -> C. User mastered A.
    
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()
    user_id = uuid.uuid4()
    
    nodes = [
        KnowledgeNode(id=id_a, name="Node A"),
        KnowledgeNode(id=id_b, name="Node B"),
        KnowledgeNode(id=id_c, name="Node C")
    ]
    
    edges = [
        NodeRelation(source_node_id=id_a, target_node_id=id_b, relation_type="PREREQUISITE"),
        NodeRelation(source_node_id=id_b, target_node_id=id_c, relation_type="PREREQUISITE")
    ]
    
    mock_db.execute.side_effect = [
        _mock_execute_result([], scalar_rows=nodes),
        _mock_execute_result([], scalar_rows=edges),
        # User mastered A with mastery above the unlock threshold
        _mock_execute_result([(id_a, 100.0)])
    ]
    
    path = await service.generate_learning_path(user_id, id_c)
    
    assert len(path) == 3
    assert path[0]["id"] == str(id_a)
    assert path[0]["status"] == "mastered"
    
    assert path[1]["id"] == str(id_b)
    assert path[1]["status"] == "unlocked" # B's prereq A is mastered
    
    assert path[2]["id"] == str(id_c)
    assert path[2]["status"] == "locked"

@pytest.mark.asyncio
async def test_cycle_detection(service, mock_db):
    """Test cycle detection A -> B -> A"""
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    user_id = uuid.uuid4()
    
    nodes = [
        KnowledgeNode(id=id_a, name="Node A"),
        KnowledgeNode(id=id_b, name="Node B")
    ]
    
    edges = [
        NodeRelation(source_node_id=id_a, target_node_id=id_b, relation_type="PREREQUISITE"),
        NodeRelation(source_node_id=id_b, target_node_id=id_a, relation_type="PREREQUISITE")
    ]
    
    mock_db.execute.side_effect = [
        _mock_execute_result([], scalar_rows=nodes),
        _mock_execute_result([], scalar_rows=edges),
        _mock_execute_result([])
    ]
    
    path = await service.generate_learning_path(user_id, id_b)
    
    # Should handle cycle gracefully (return error or partial)
    # Our implementation returns [{"error": "Cyclic dependency detected"}]
    assert len(path) == 1
    assert "error" in path[0]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
