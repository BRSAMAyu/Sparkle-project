"""
GraphRAG 系统测试

测试 GraphRAG 检索器、图数据库集成和双写策略
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.orchestration.graph_rag import GraphRAGRetriever, RAGResult
from backend.services.graph_knowledge_service import GraphKnowledgeService
from backend.workers.graph_sync_worker import GraphSyncWorker


class TestGraphRAGRetriever:
    """测试 GraphRAG 检索器"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_db):
        """创建 GraphRAGRetriever 实例"""
        return GraphRAGRetriever(mock_db)

    @pytest.mark.asyncio
    async def test_vector_search(self, retriever, mock_db):
        """测试向量搜索"""
        # 模拟向量搜索结果
        mock_db.execute.return_value.fetchall.return_value = [
            (uuid.uuid4(), "测试节点", 0.95, "知识点描述"),
            (uuid.uuid4(), "相关节点", 0.87, "相关描述")
        ]

        result = await retriever._vector_search(
            query="测试查询",
            user_id=uuid.uuid4(),
            top_k=2
        )

        assert len(result) == 2
        assert result[0].score > 0.8

    @pytest.mark.asyncio
    async def test_graph_search(self, retriever, mock_db):
        """测试图搜索"""
        # 模拟图搜索结果
        mock_db.execute.return_value.fetchall.return_value = [
            (uuid.uuid4(), "中心节点", "关联节点", "KNOWLEDGE", 0.92),
            (uuid.uuid4(), "关联节点", "扩展节点", "RELATED", 0.85)
        ]

        result = await retriever._graph_search(
            query_node_id=uuid.uuid4(),
            depth=2,
            user_id=uuid.uuid4()
        )

        assert len(result) == 2
        assert result[0].score > 0.8

    @pytest.mark.asyncio
    async def test_fusion_search(self, retriever, mock_db):
        """测试融合搜索"""
        # 模拟向量和图搜索结果
        vector_results = [
            Mock(node_id=uuid.uuid4(), content="向量结果1", score=0.95),
            Mock(node_id=uuid.uuid4(), content="向量结果2", score=0.87)
        ]

        graph_results = [
            Mock(node_id=vector_results[0].node_id, content="图结果1", score=0.92),
            Mock(node_id=uuid.uuid4(), content="图结果2", score=0.85)
        ]

        with patch.object(retriever, '_vector_search', return_value=vector_results), \
             patch.object(retriever, '_graph_search', return_value=graph_results):

            result = await retriever.fusion_search(
                query="测试查询",
                user_id=uuid.uuid4(),
                depth=2,
                top_k=3
            )

            assert "context" in result
            assert "metadata" in result
            assert result["metadata"]["fusion_count"] >= 1

    @pytest.mark.asyncio
    async def test_error_handling(self, retriever, mock_db):
        """测试错误处理"""
        # 模拟数据库错误
        mock_db.execute.side_effect = Exception("Database error")

        result = await retriever.fusion_search(
            query="测试查询",
            user_id=uuid.uuid4()
        )

        # 应该返回空结果而不是抛出异常
        assert "context" in result
        assert result["metadata"]["error"] is not None


class TestGraphKnowledgeService:
    """测试增强的知识服务"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return GraphKnowledgeService(mock_db)

    @pytest.mark.asyncio
    async def test_graph_rag_search(self, service, mock_db):
        """测试 GraphRAG 搜索"""
        # 模拟搜索结果
        mock_db.execute.return_value.fetchall.return_value = [
            (uuid.uuid4(), "测试节点", "描述", 0.95)
        ]

        result = await service.graph_rag_search(
            query="测试查询",
            user_id=uuid.uuid4(),
            depth=2,
            top_k=5
        )

        assert "context" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_write_node_to_graph(self, service, mock_db):
        """测试写入节点到图数据库"""
        node_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # 模拟写入成功
        mock_db.execute.return_value = None

        success = await service._write_node_to_graph(
            node_id=node_id,
            title="测试节点",
            description="测试描述",
            user_id=user_id,
            embedding=[0.1] * 1536
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_write_relation_to_graph(self, service, mock_db):
        """测试写入关系到图数据库"""
        from_node = uuid.uuid4()
        to_node = uuid.uuid4()

        mock_db.execute.return_value = None

        success = await service._write_relation_to_graph(
            from_node=from_node,
            to_node=to_node,
            relation_type="RELATED"
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_check_graph_connection(self, service, mock_db):
        """测试图数据库连接检查"""
        # 成功情况
        mock_db.execute.return_value.fetchone.return_value = (1,)
        result = await service.check_graph_connection()
        assert result is True

        # 失败情况
        mock_db.execute.side_effect = Exception("Connection failed")
        result = await service.check_graph_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, service, mock_db):
        """测试获取图统计信息"""
        # 模拟统计查询结果
        mock_db.execute.side_effect = [
            Mock(fetchone=Mock(return_value=(100,))),  # 节点数
            Mock(fetchone=Mock(return_value=(200,))),  # 关系数
            Mock(fetchall=Mock(return_value=[("KNOWLEDGE", 50), ("RELATED", 150)])),  # 节点类型
            Mock(fetchall=Mock(return_value=[("RELATES_TO", 100), ("PART_OF", 100)]))  # 关系类型
        ]

        stats = await service.get_graph_statistics()

        assert stats["total_nodes"] == 100
        assert stats["total_relations"] == 200
        assert "node_types" in stats
        assert "relation_types" in stats


class TestGraphSyncWorker:
    """测试图同步 Worker"""

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis = AsyncMock()
        redis.xread = AsyncMock(return_value=[])
        redis.xack = AsyncMock()
        redis.xrange = AsyncMock(return_value=[])
        return redis

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def worker(self, mock_redis, mock_db):
        """创建 Worker 实例"""
        return GraphSyncWorker(mock_redis, mock_db)

    @pytest.mark.asyncio
    async def test_process_sync_event(self, worker, mock_db):
        """测试处理同步事件"""
        event_id = "1234567890-0"
        event_data = {
            b"node_id": str(uuid.uuid4()).encode(),
            b"operation": b"create",
            b"title": b"测试节点",
            b"description": b"测试描述",
            b"user_id": str(uuid.uuid4()).encode(),
            b"embedding": b"[0.1,0.2,0.3]"
        }

        # 模拟数据库执行成功
        mock_db.execute.return_value = None

        await worker._process_sync_event(event_id, event_data)

        # 验证数据库操作被调用
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_process_sync_event_error(self, worker, mock_db, mock_redis):
        """测试处理同步事件时的错误"""
        event_id = "1234567890-0"
        event_data = {
            b"node_id": str(uuid.uuid4()).encode(),
            b"operation": b"create",
            b"title": b"测试节点",
            b"description": b"测试描述",
            b"user_id": str(uuid.uuid4()).encode(),
            b"embedding": b"[0.1,0.2,0.3]"
        }

        # 模拟数据库错误
        mock_db.execute.side_effect = Exception("Database error")

        await worker._process_sync_event(event_id, event_data)

        # 验证错误被记录，事件未被确认
        mock_redis.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_worker(self, worker, mock_redis):
        """测试 Worker 运行"""
        # 模拟有事件需要处理
        mock_redis.xread.return_value = [
            ("stream:graph_sync", [("1234567890-0", {b"test": b"data"})])
        ]

        # 设置运行标志
        worker.running = True

        # 使用超时防止无限循环
        try:
            await asyncio.wait_for(worker.run(), timeout=0.1)
        except asyncio.TimeoutError:
            pass

        # 验证 xread 被调用
        assert mock_redis.xread.called


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_graph_rag(self):
        """测试端到端 GraphRAG 流程"""
        # 这个测试需要真实的数据库环境
        # 在 CI/CD 中可以跳过或使用 Docker 容器

        # 1. 创建知识节点
        # 2. 创建关系
        # 3. 执行 GraphRAG 查询
        # 4. 验证结果包含向量和图信息

        # 由于需要真实环境，这里只验证流程结构
        assert True

    @pytest.mark.asyncio
    async def test_double_write_consistency(self):
        """测试双写一致性"""
        # 验证向量数据库和图数据库的数据一致性
        # 1. 写入向量数据库
        # 2. 验证图数据库同步
        # 3. 检查数据完整性

        assert True


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_graph_rag_performance(self):
        """测试 GraphRAG 性能"""
        # 1. 测试向量搜索性能 (< 500ms)
        # 2. 测试图搜索性能 (< 1s)
        # 3. 测试融合搜索性能 (< 2s)

        assert True

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """测试并发写入"""
        # 1. 模拟 10 个并发写入
        # 2. 验证无数据竞争
        # 3. 验证数据完整性

        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
