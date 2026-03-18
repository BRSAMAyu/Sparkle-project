"""
Apache AGE 客户端封装

提供异步 AGE 连接池和便捷的 Cypher 查询接口
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import asyncpg
from asyncpg.pool import Pool
from loguru import logger

from app.config import settings


@dataclass
class AgeConfig:
    """AGE 配置"""
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "sparkle"
    pool_size: int = 10
    graph_name: str = "sparkle_galaxy"


class AgeClient:
    """Apache AGE 客户端"""

    _IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(self, config: AgeConfig):
        self.config = config
        self.pool: Pool | None = None
        self._lock = asyncio.Lock()

    @classmethod
    def _validate_identifier(cls, identifier: str) -> str:
        if not cls._IDENTIFIER_RE.match(identifier):
            raise ValueError(f"Invalid AGE identifier: {identifier}")
        return identifier

    @classmethod
    def _cypher_literal(cls, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, uuid.UUID):
            return json.dumps(str(value), ensure_ascii=False)
        if isinstance(value, list):
            return "[" + ", ".join(cls._cypher_literal(item) for item in value) + "]"
        if isinstance(value, dict):
            parts = []
            for key, item in value.items():
                safe_key = cls._validate_identifier(str(key))
                parts.append(f"{safe_key}: {cls._cypher_literal(item)}")
            return "{" + ", ".join(parts) + "}"
        return json.dumps(str(value), ensure_ascii=False)

    @classmethod
    def _property_assignments(cls, alias: str, properties: dict[str, Any]) -> str:
        assignments = []
        for key, value in properties.items():
            safe_key = cls._validate_identifier(str(key))
            assignments.append(f"{alias}.{safe_key} = {cls._cypher_literal(value)}")
        return ", ".join(assignments)

    @classmethod
    def _property_filters(cls, alias: str, properties: dict[str, Any]) -> str:
        filters = []
        for key, value in properties.items():
            safe_key = cls._validate_identifier(str(key))
            filters.append(f"{alias}.{safe_key} = {cls._cypher_literal(value)}")
        return " AND ".join(filters)

    @staticmethod
    def _parse_agtype(value: Any) -> Any:
        if value is None or isinstance(value, (dict, list, int, float, bool)):
            return value
        if not isinstance(value, str):
            return value

        cleaned = value.strip()
        if "::" in cleaned:
            cleaned = cleaned.split("::", 1)[0]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return cleaned.strip('"')

    async def _prepare_connection(self, conn: asyncpg.Connection):
        await conn.execute("LOAD 'age';")
        await conn.execute('SET search_path = ag_catalog, "$user", public;')

    async def init_pool(self):
        """初始化连接池"""
        if self.pool:
            return

        async with self._lock:
            if self.pool:
                return

            try:
                self.pool = await asyncpg.create_pool(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database,
                    min_size=2,
                    max_size=self.config.pool_size,
                    init=self._prepare_connection,
                )
                logger.info(f"AGE 连接池已初始化: {self.config.database}")
            except Exception as e:
                logger.error(f"初始化 AGE 连接池失败: {e}")
                raise

    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("AGE 连接池已关闭")

    async def execute_cypher(self, cypher: str, params: dict[str, Any] = None) -> list[dict[str, Any]]:
        """
        执行 Cypher 查询

        Args:
            cypher: Cypher 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        if not self.pool:
            await self.init_pool()

        try:
            async with self.pool.acquire() as conn:
                await self._prepare_connection(conn)

                if params:
                    rows = await conn.fetch(
                        "SELECT * FROM cypher($1, $2, $3::agtype) AS (result agtype);",
                        self.config.graph_name,
                        cypher,
                        json.dumps(params, ensure_ascii=False),
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT * FROM cypher($1, $2) AS (result agtype);",
                        self.config.graph_name,
                        cypher,
                    )

                results = []
                for row in rows:
                    if row["result"] is not None:
                        results.append(self._parse_agtype(row["result"]))

                logger.debug(f"AGE 查询执行成功: {len(results)} 条结果")
                return results

        except Exception as e:
            logger.error(f"AGE 查询失败: {e}\nCypher: {cypher}\nParams: {params}")
            raise

    async def create_graph(self, graph_name: str):
        """创建图谱"""
        if not self.pool:
            await self.init_pool()

        async with self.pool.acquire() as conn:
            await self._prepare_connection(conn)
            exists = await conn.fetchval(
                "SELECT 1 FROM ag_catalog.ag_graph WHERE name = $1",
                graph_name,
            )
            if not exists:
                await conn.execute("SELECT ag_catalog.create_graph($1)", graph_name)
        logger.info(f"图谱已创建: {graph_name}")

    async def create_vertex_label(self, label_name: str, properties: list[str] = None):
        """创建顶点标签"""
        safe_label = self._validate_identifier(label_name)
        await self.create_graph(self.config.graph_name)
        seed_value = f"schema:{safe_label}:{uuid.uuid4().hex}"
        await self.execute_cypher(
            f"""
            CREATE (n:{safe_label} {{__schema_seed__: "{seed_value}"}})
            RETURN {{label: "{safe_label}"}} as result
            """
        )
        await self.execute_cypher(
            f"""
            MATCH (n:{safe_label} {{__schema_seed__: "{seed_value}"}})
            DELETE n
            RETURN {{label: "{safe_label}"}} as result
            """
        )
        logger.info(f"顶点标签已创建: {label_name}")

    async def create_edge_label(self, label_name: str, properties: list[str] = None):
        """创建边标签"""
        safe_label = self._validate_identifier(label_name)
        await self.create_graph(self.config.graph_name)
        seed_value = f"schema:{safe_label}:{uuid.uuid4().hex}"
        await self.execute_cypher(
            f"""
            CREATE (a:__SchemaSeed {{seed: "{seed_value}"}})
            CREATE (b:__SchemaSeed {{seed: "{seed_value}"}})
            CREATE (a)-[r:{safe_label} {{__schema_seed__: "{seed_value}"}}]->(b)
            RETURN {{label: "{safe_label}"}} as result
            """
        )
        await self.execute_cypher(
            f"""
            MATCH (a:__SchemaSeed {{seed: "{seed_value}"}})-[r:{safe_label}]->(b:__SchemaSeed {{seed: "{seed_value}"}})
            DELETE r, a, b
            RETURN {{label: "{safe_label}"}} as result
            """
        )
        logger.info(f"边标签已创建: {label_name}")

    async def add_vertex(self, label: str, properties: dict[str, Any]) -> str:
        """
        添加顶点

        Returns:
            顶点 ID
        """
        safe_label = self._validate_identifier(label)
        props_str = self._property_assignments("v", properties)
        node_id = properties.get("id")
        if node_id is not None:
            cypher = f"""
            MERGE (v:{safe_label} {{id: {self._cypher_literal(node_id)}}})
            SET {props_str}
            RETURN {{vertex_id: id(v)}} as result
            """
        else:
            cypher = f"""
            CREATE (v:{safe_label})
            SET {props_str}
            RETURN {{vertex_id: id(v)}} as result
            """

        result = await self.execute_cypher(cypher)
        if result:
            return result[0]["vertex_id"]
        return None

    async def add_edge(self, from_label: str, from_props: dict[str, Any],
                       to_label: str, to_props: dict[str, Any],
                       edge_label: str, edge_props: dict[str, Any] = None):
        """添加边"""
        safe_from_label = self._validate_identifier(from_label)
        safe_to_label = self._validate_identifier(to_label)
        safe_edge_label = self._validate_identifier(edge_label)
        from_match = self._property_filters("v", from_props)
        to_match = self._property_filters("u", to_props)
        edge_props = edge_props or {}
        edge_props_str = self._property_assignments("r", edge_props)
        cypher = f"""
        MATCH (v:{safe_from_label}), (u:{safe_to_label})
        WHERE {from_match} AND {to_match}
        MERGE (v)-[r:{safe_edge_label}]->(u)
        {f"SET {edge_props_str}" if edge_props_str else ""}
        RETURN {{created: true}} as result
        """

        await self.execute_cypher(cypher)

    async def get_neighbors(self, label: str, properties: dict[str, Any],
                           depth: int = 1, edge_filter: str | None = None) -> list[dict[str, Any]]:
        """
        获取邻居节点

        Args:
            label: 节点标签
            properties: 节点属性（用于定位）
            depth: 搜索深度
            edge_filter: 边类型过滤
        """
        match_clause = " AND ".join([f"n.{k} = '{v}'" for k, v in properties.items()])
        edge_filter_clause = f"|{edge_filter}|" if edge_filter else "*"
        filters = self._property_filters("n", properties)

        cypher = f"""
        MATCH (n:{self._validate_identifier(label)})-[r{edge_filter_clause}*1..{depth}]-(neighbor)
        WHERE {filters}
        RETURN {{
            name: neighbor.name,
            description: neighbor.description,
            relation_type: type(r[0]),
            strength: r[0].strength
        }} as result
        ORDER BY r[0].strength DESC
        """

        return await self.execute_cypher(cypher)

    async def find_path(self, from_props: dict[str, Any], to_props: dict[str, Any],
                       max_depth: int = 5) -> list[dict[str, Any]]:
        """
        查找最短路径

        Args:
            from_props: 起点属性
            to_props: 终点属性
            max_depth: 最大深度
        """
        from_match = self._property_filters("a", from_props)
        to_match = self._property_filters("b", to_props)

        cypher = f"""
        MATCH path = shortestPath((a)-[*1..{max_depth}]-(b))
        WHERE {from_match} AND {to_match}
        RETURN {{
            nodes: [node IN nodes(path) | node.name],
            edges: [edge IN relationships(path) | type(edge)]
        }} as result
        """

        return await self.execute_cypher(cypher)


# 全局实例
_age_client: AgeClient | None = None


def get_age_client() -> AgeClient:
    """获取 AGE 客户端单例"""
    global _age_client

    if _age_client is None:
        # Parse connection details from DATABASE_URL
        # Format: postgresql://user:password@host:port/dbname
        parsed = urlparse(settings.DATABASE_URL)
        config = AgeConfig(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "sparkle",
            graph_name="sparkle_galaxy"
        )
        _age_client = AgeClient(config)

    return _age_client


async def init_age():
    """初始化 AGE 客户端"""
    client = get_age_client()
    await client.init_pool()
    return client
