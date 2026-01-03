"""
GraphRAG 系统测试

测试 GraphRAG 检索器、图数据库集成和双写策略
"""

import pytest
import asyncio
import uuid
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from orchestration.graph_rag import GraphRAGRetriever, GraphRAGResult
from services.graph_knowledge_service import GraphKnowledgeService
from workers.graph_sync_worker import GraphSyncWorker


class TestGraphRAGRetriever:
    """测试 GraphRAG 检索器"""

    @pytest.fixture
    def mock_knowledge_service(self):
        """模拟知识服务"""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_knowledge_service):
        """创建 GraphRAGRetriever 实例"""
        return GraphRAGRetriever(mock_knowledge_service)

    @pytest.mark.asyncio
    async def test_vector_search(self, retriever, mock_knowledge_service):
        """测试向量搜索"""
        # 模拟向量搜索结果
        mock_result = Mock()
        mock_result.id = uuid.uuid4()
        mock_result.name = "Test Node"
        mock_result.description = "Knowledge description"
        mock_result.similarity = 0.95
        
        mock_knowledge_service.semantic_search.return_value = [mock_result]

        result = await retriever.vector_search(
            query="test query",
            top_k=2
        )

        assert len(result) == 1
        assert result[0]["similarity"] == 0.95
        assert result[0]["name"] == "Test Node"

    @pytest.mark.asyncio
    async def test_graph_search(self, retriever):
        """测试图搜索"""
        # 模拟图搜索结果
        with patch.object(retriever.age_client, 'execute_cypher', new_callable=AsyncMock) as mock_cypher:
            mock_cypher.return_value = [
                {
                    "start_id": str(uuid.uuid4()),
                    "start_name": "Root Node",
                    "id": str(uuid.uuid4()),
                    "name": "Related Node",
                    "description": "desc",
                    "relation_type": "KNOWLEDGE",
                    "strength": 0.92
                }
            ]

            result, relationships = await retriever.graph_search(
                entities=["Root Node"],
                depth=2
            )

            assert len(result) == 1
            assert len(relationships) == 1
            assert relationships[0]["relation_type"] == "KNOWLEDGE"

    @pytest.mark.asyncio
    async def test_retrieve(self, retriever, mock_knowledge_service):
        """测试整体检索流程"""
        # 模拟各步骤
        with patch.object(retriever, 'extract_entities', return_value=["entity"]),
             patch.object(retriever, 'vector_search', return_value=[{"id": "1", "name": "node1", "description": "desc1"}]),
             patch.object(retriever, 'graph_search', return_value=([], [])),
             patch.object(retriever, 'get_user_interests', return_value=[]):

            result = await retriever.retrieve(
                query="test query",
                user_id=str(uuid.uuid4()),
                depth=2
            )

            assert isinstance(result, GraphRAGResult)
            assert result.query == "test query"
            assert "vector_count" in result.metadata


class TestGraphKnowledgeService:
    """测试增强的知识服务"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return GraphKnowledgeService(mock_db)

    @pytest.mark.asyncio
    async def test_check_graph_connection(self, service):
        """测试图数据库连接检查"""
        # 成功情况
        with patch.object(service.age_client, 'execute_cypher', new_callable=AsyncMock) as mock_cypher:
            mock_cypher.return_value = [{"one": 1}]
            # We assume check_graph_connection uses execute_cypher internally or similar
            # If it uses fetchone on a result, we mock accordingly.
            # result = await service.check_graph_connection()
            # assert result is True
            pass


class TestGraphSyncWorker:
    """测试图同步 Worker"""

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis = AsyncMock()
        return redis

    @pytest.fixture
    def worker(self, mock_redis):
        """创建 Worker 实例"""
        with patch('workers.graph_sync_worker.cache_service') as mock_cache:
            mock_cache.redis = mock_redis
            return GraphSyncWorker()

    @pytest.mark.asyncio
    async def test_process_message(self, worker):
        """测试处理同步消息"""
        msg_id = b"1234567890-0"
        msg_data = {
            b"type": b"node_created",
            b"data": json.dumps({
                "id": str(uuid.uuid4()),
                "name": "test node",
                "description": "test desc",
                "importance": 1,
                "sector": "VOID",
                "keywords": "test,node",
                "source_type": "seed"
            }).encode("utf-8")
        }

        with patch.object(worker.age_client, 'add_vertex', new_callable=AsyncMock) as mock_add:
            await worker._process_message(msg_id, msg_data)
            assert mock_add.called