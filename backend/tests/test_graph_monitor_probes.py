"""
GraphRAG 监控探针测试（wt308）

回归背景：graph_monitor 端点调用的 check_graph_connection / check_vector_connection /
get_graph_statistics / get_detailed_statistics 曾在 GraphKnowledgeService 上不存在，
监控端点一被调用即 AttributeError → 500（生产监控盲区）。

本文件两类断言：
1. 探针分支逻辑单测（mock session / mock age_client）
2. detailed_health_check 组装层契约测试（全组件字典结构断言，防字段再漂移）
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.graph_monitor import detailed_health_check
from app.services.graph_knowledge_service import GraphKnowledgeService


def _make_service() -> GraphKnowledgeService:
    return GraphKnowledgeService(AsyncMock())


def _full_graph_statistics() -> dict:
    return {
        "total_nodes": 12,
        "total_relations": 7,
        "node_types": {"KnowledgeNode": 10, "User": 2},
        "relation_types": {"RELATED": 5, "PREREQUISITE": 2},
    }


class TestCheckGraphConnection:
    """AGE 连接探针：真往返 + 超时 + 异常归一化"""

    @pytest.fixture
    def service(self) -> GraphKnowledgeService:
        return _make_service()

    @pytest.mark.asyncio
    async def test_success_returns_true(self, service):
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.return_value = [{"result": 1}]
            assert await service.check_graph_connection() is True
            mock_cypher.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connection_error_returns_false_not_raises(self, service):
        """图库不可达必须归一化为 False（监控端点依赖它产出 degraded 报告而非 500）"""
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = ConnectionError("age unreachable")
            assert await service.check_graph_connection() is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, service):
        """探针超时必须被吞掉并返回 False，不能拖垮监控端点"""

        async def slow_probe(*_args, **_kwargs):
            await asyncio.sleep(5)

        with (
            patch.object(service, "GRAPH_PROBE_TIMEOUT_SECONDS", 0.05),
            patch.object(service.age_client, "execute_cypher", side_effect=slow_probe),
        ):
            assert await service.check_graph_connection() is False


class TestCheckVectorConnection:
    """pgvector 连接探针：向量列真实 SQL 往返"""

    @pytest.fixture
    def service(self) -> GraphKnowledgeService:
        return _make_service()

    @pytest.mark.asyncio
    async def test_success_returns_true(self, service):
        service.db.scalar = AsyncMock(return_value=42)
        assert await service.check_vector_connection() is True
        service.db.scalar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_embedding_table_still_connected(self, service):
        """无嵌入数据 != 连接失败：count=0 仍算探针通过"""
        service.db.scalar = AsyncMock(return_value=0)
        assert await service.check_vector_connection() is True

    @pytest.mark.asyncio
    async def test_query_failure_returns_false(self, service):
        """pgvector 扩展缺失时向量列查询会失败 → False"""
        service.db.scalar = AsyncMock(side_effect=RuntimeError("type vector does not exist"))
        assert await service.check_vector_connection() is False


class TestGetGraphStatistics:
    """图统计：端点消费字段一字不差对齐（total_nodes/total_relations/node_types/relation_types）"""

    @pytest.fixture
    def service(self) -> GraphKnowledgeService:
        return _make_service()

    @staticmethod
    def _age_side_effect(_cypher: str, _params: dict | None = None) -> list[dict]:
        if "total_nodes" in _cypher:
            return [{"total_nodes": 12}]
        if "total_relations" in _cypher:
            return [{"total_relations": 7}]
        if "labels(" in _cypher:
            return [
                {"type_name": "KnowledgeNode", "type_count": 10},
                {"type_name": "User", "type_count": 2},
            ]
        return [
            {"type_name": "RELATED", "type_count": 5},
            {"type_name": "PREREQUISITE", "type_count": 2},
        ]

    @pytest.mark.asyncio
    async def test_field_contract_exact(self, service):
        """端点 .get 读取的四个字段必须存在且类型正确"""
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = self._age_side_effect
            stats = await service.get_graph_statistics()

        assert set(stats) >= {"total_nodes", "total_relations", "node_types", "relation_types"}
        assert isinstance(stats["total_nodes"], int) and stats["total_nodes"] == 12
        assert isinstance(stats["total_relations"], int) and stats["total_relations"] == 7
        assert stats["node_types"] == {"KnowledgeNode": 10, "User": 2}
        assert stats["relation_types"] == {"RELATED": 5, "PREREQUISITE": 2}

    @pytest.mark.asyncio
    async def test_empty_graph_returns_zeros(self, service):
        """空图（无节点）必须返回零值统计而非异常——端点有 'Graph database is empty' 分支"""

        def empty_side_effect(_cypher: str, _params: dict | None = None) -> list[dict]:
            if "total_nodes" in _cypher:
                return [{"total_nodes": 0}]
            if "total_relations" in _cypher:
                return [{"total_relations": 0}]
            return []

        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = empty_side_effect
            stats = await service.get_graph_statistics()

        assert stats == {
            "total_nodes": 0,
            "total_relations": 0,
            "node_types": {},
            "relation_types": {},
        }

    @pytest.mark.asyncio
    async def test_distribution_failure_degrades_gracefully(self, service):
        """类型分布查询失败降级为空分布，总量计数仍然真实返回"""

        async def totals_only(cypher: str, _params: dict | None = None) -> list[dict]:
            if "total_nodes" in cypher:
                return [{"total_nodes": 3}]
            if "total_relations" in cypher:
                return [{"total_relations": 1}]
            raise RuntimeError("aggregation not supported")

        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = totals_only
            stats = await service.get_graph_statistics()

        assert stats["total_nodes"] == 3
        assert stats["total_relations"] == 1
        assert stats["node_types"] == {}
        assert stats["relation_types"] == {}

    @pytest.mark.asyncio
    async def test_total_count_failure_propagates(self, service):
        """总量计数失败必须向上抛出（端点侧有 try/except 兜底分支）"""
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = RuntimeError("graph does not exist")
            with pytest.raises(RuntimeError, match="graph does not exist"):
                await service.get_graph_statistics()


class TestGetDetailedStatistics:
    """/monitor/graph/statistics 端点背后的详细统计"""

    @pytest.fixture
    def service(self) -> GraphKnowledgeService:
        return _make_service()

    @pytest.mark.asyncio
    async def test_combines_graph_pg_and_sync_backlog(self, service):
        with (
            patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher,
            patch.object(service, "redis", AsyncMock()) as mock_redis,
        ):
            mock_cypher.side_effect = TestGetGraphStatistics._age_side_effect
            service.db.scalar = AsyncMock(side_effect=[100, 55])
            mock_redis.xlen = AsyncMock(return_value=3)

            stats = await service.get_detailed_statistics()

        assert stats["total_nodes"] == 12
        assert stats["total_relations"] == 7
        assert stats["pg_total_nodes"] == 100
        assert stats["pg_total_relations"] == 55
        assert stats["sync_stream_length"] == 3
        assert isinstance(stats["graph_name"], str)

    @pytest.mark.asyncio
    async def test_no_redis_defaults_sync_backlog_to_zero(self, service):
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = TestGetGraphStatistics._age_side_effect
            service.db.scalar = AsyncMock(side_effect=[0, 0])
            with patch.object(service, "redis", None):
                stats = await service.get_detailed_statistics()

        assert stats["sync_stream_length"] == 0

    @pytest.mark.asyncio
    async def test_redis_failure_degrades_sync_backlog(self, service):
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.side_effect = TestGetGraphStatistics._age_side_effect
            service.db.scalar = AsyncMock(side_effect=[0, 0])
            mock_redis = AsyncMock()
            mock_redis.xlen = AsyncMock(side_effect=RuntimeError("redis down"))
            with patch.object(service, "redis", mock_redis):
                stats = await service.get_detailed_statistics()

        assert stats["sync_stream_length"] == 0


class TestDetailedHealthEndpointAssembly:
    """
    detailed_health_check 组装层契约测试

    防再漂移：锁住端点消费的全部组件/指标字段结构。
    """

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def no_redis(self):
        with patch("app.api.v1.graph_monitor.cache_service") as mock_cache:
            mock_cache.redis = None
            yield mock_cache

    @pytest.fixture
    def patched_probes(self):
        """按类打补丁：组装层只关心探针返回值与报告结构"""
        with (
            patch.object(GraphKnowledgeService, "check_graph_connection", AsyncMock(return_value=True)) as mock_graph,
            patch.object(GraphKnowledgeService, "check_vector_connection", AsyncMock(return_value=True)) as mock_vector,
            patch.object(
                GraphKnowledgeService, "get_graph_statistics", AsyncMock(return_value=_full_graph_statistics())
            ) as mock_stats,
            patch.object(GraphKnowledgeService, "graph_rag_search", AsyncMock(return_value={"context": "ok"})),
        ):
            yield {
                "graph": mock_graph,
                "vector": mock_vector,
                "stats": mock_stats,
            }

    @pytest.mark.asyncio
    async def test_all_healthy_report_structure(self, mock_db, no_redis, patched_probes):
        report = await detailed_health_check(db=mock_db)

        # 顶层结构
        assert report["status"] == "healthy"
        assert isinstance(report["uptime_ms"], (int, float))
        assert isinstance(report["alerts"], list)
        assert isinstance(report["recommendations"], list)

        # 组件结构（graph_db / vector_db / redis）
        assert report["components"]["graph_db"] == {
            "status": "connected",
            "latency_ms": report["components"]["graph_db"]["latency_ms"],
            "type": "Apache AGE",
        }
        assert set(report["components"]["vector_db"]) == {"status", "latency_ms", "type"}
        assert report["components"]["vector_db"]["type"] == "pgvector"
        assert report["components"]["redis"]["status"] == "disabled"

        # 数据完整性指标：探针字段契约对齐
        integrity = report["metrics"]["data_integrity"]
        assert integrity == {
            "total_nodes": 12,
            "total_relations": 7,
            "node_types": {"KnowledgeNode": 10, "User": 2},
            "relation_types": {"RELATED": 5, "PREREQUISITE": 2},
        }

        # 性能与健康评分
        assert set(report["metrics"]["performance"]) == {"simple", "moderate"}
        score = report["metrics"]["health_score"]
        assert set(score) == {"score", "rating", "deductions"}
        # redis 未配置 → "disabled" 分支扣 5 分，其余组件满健康
        assert score["score"] == 95
        assert score["rating"] == "excellent"
        assert score["deductions"] == ["redis: disabled"]

        # 摘要
        assert report["summary"]["alert_count"] == 0
        assert report["summary"]["message"] == "All systems operational"

    @pytest.mark.asyncio
    async def test_vector_disconnected_yields_degraded(self, mock_db, no_redis, patched_probes):
        patched_probes["vector"].return_value = False

        report = await detailed_health_check(db=mock_db)

        assert report["status"] == "degraded"
        assert report["components"]["vector_db"]["status"] == "disconnected"
        warning_alerts = [a for a in report["alerts"] if a.get("component") == "vector_db"]
        assert warning_alerts and warning_alerts[0]["severity"] == "warning"
        # 图侧数据完整性仍然产出
        assert report["metrics"]["data_integrity"]["total_nodes"] == 12

    @pytest.mark.asyncio
    async def test_vector_error_yields_degraded_with_error_component(self, mock_db, no_redis, patched_probes):
        patched_probes["vector"].side_effect = RuntimeError("pgvector boom")

        report = await detailed_health_check(db=mock_db)

        assert report["status"] == "degraded"
        assert report["components"]["vector_db"]["status"] == "error"
        assert "pgvector boom" in report["components"]["vector_db"]["error"]

    @pytest.mark.asyncio
    async def test_graph_unreachable_yields_unhealthy_with_recommendation(self, mock_db, no_redis, patched_probes):
        patched_probes["graph"].return_value = False

        report = await detailed_health_check(db=mock_db)

        assert report["status"] == "unhealthy"
        assert report["components"]["graph_db"]["status"] == "disconnected"
        critical_alerts = [a for a in report["alerts"] if a.get("component") == "graph_db"]
        assert critical_alerts and critical_alerts[0]["severity"] == "critical"
        assert any("Apache AGE" in r for r in report["recommendations"])
        # 图不可达时跳过数据完整性，但报告仍结构完整
        assert "data_integrity" not in report["metrics"]
        assert "health_score" in report["metrics"]

    @pytest.mark.asyncio
    async def test_stats_failure_keeps_structured_report(self, mock_db, no_redis, patched_probes):
        """统计失败不再导致 500：降级为 warning 告警 + error 指标"""
        patched_probes["stats"].side_effect = RuntimeError("aggregation failed")

        report = await detailed_health_check(db=mock_db)

        assert report["status"] in ("healthy", "degraded")
        assert "aggregation failed" in report["metrics"]["data_integrity"]["error"]
        assert any("Cannot verify data integrity" in a["message"] for a in report["alerts"])
