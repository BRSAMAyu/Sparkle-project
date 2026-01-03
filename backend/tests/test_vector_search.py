import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.models.knowledge import KnowledgeNode

@pytest.mark.asyncio
async def test_semantic_search_nodes():
    """测试 pgvector 语义检索"""
    # 模拟 DB session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # 模拟 embedding service
    mock_embedding_service = AsyncMock()
    mock_embedding_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    
    # 初始化 service
    service = KnowledgeRetrievalService(mock_db)
    
    # Patch get_embedding to use our mock
    # 注意：这里需要 patch 实际导入 embedding_service 的地方
    # 假设 retrieval_service.py 中 import 了 embedding_service
    with patch('app.services.galaxy.retrieval_service.embedding_service', mock_embedding_service):
        
        # 模拟 DB 执行结果
        mock_result = MagicMock()
        mock_node = KnowledgeNode(id=1, name="Test Node")
        mock_result.all.return_value = [(mock_node, 0.1)] # Node, distance
        mock_db.execute.return_value = mock_result

        # 执行检索
        results = await service.semantic_search_nodes("test query", limit=5)
        
        # 验证结果
        assert len(results) == 1
        assert results[0].name == "Test Node"
        
        # 验证调用
        mock_embedding_service.get_embedding.assert_called_with("test query")
        mock_db.execute.assert_called_once()
        
        # 验证 SQL 构建 (简单验证)
        # 这里的 call_args 比较复杂，通常只要验证 execute 被调用即可
        # 也可以验证 select 语句中包含了 distance 排序

@pytest.mark.asyncio
async def test_semantic_search_threshold_filtering():
    """测试相似度阈值过滤"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_embedding_service = AsyncMock()
    mock_embedding_service.get_embedding.return_value = [0.1, 0.1, 0.1]
    
    service = KnowledgeRetrievalService(mock_db)
    
    with patch('app.services.galaxy.retrieval_service.embedding_service', mock_embedding_service):
        mock_result = MagicMock()
        # 两个结果：一个距离很小(相似)，一个距离很大(不相似)
        node_good = KnowledgeNode(id=1, name="Good Match")
        node_bad = KnowledgeNode(id=2, name="Bad Match")
        
        mock_result.all.return_value = [
            (node_good, 0.1), # distance 0.1 < threshold 0.3
            (node_bad, 0.8)   # distance 0.8 > threshold 0.3
        ]
        mock_db.execute.return_value = mock_result
        
        # 执行检索，设置阈值为 0.3
        results = await service.semantic_search_nodes("test", threshold=0.3)
        
        # 应该只返回 Good Match
        assert len(results) == 1
        assert results[0].name == "Good Match"
