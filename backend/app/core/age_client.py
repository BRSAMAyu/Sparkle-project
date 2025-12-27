"""
Apache AGE 客户端封装

提供异步 AGE 连接池和便捷的 Cypher 查询接口
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
import asyncpg
from asyncpg.pool import Pool
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

    def __init__(self, config: AgeConfig):
        self.config = config
        self.pool: Optional[Pool] = None
        self._lock = asyncio.Lock()

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
                    server_settings={
                        'search_path': 'ag_catalog, public'
                    }
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

    async def execute_cypher(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
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
            # 包装 Cypher 查询
            full_query = f"""
            SELECT * FROM cypher('{self.config.graph_name}', $$
                {cypher}
            $$) as (result agtype);
            """

            async with self.pool.acquire() as conn:
                # 设置 search_path
                await conn.execute("SET search_path = ag_catalog, public;")

                # 执行查询
                if params:
                    rows = await conn.fetch(full_query, params)
                else:
                    rows = await conn.fetch(full_query)

                # 解析结果
                results = []
                for row in rows:
                    if row['result']:
                        # agtype 是 JSON 格式，直接解析
                        import json
                        results.append(json.loads(row['result']))

                logger.debug(f"AGE 查询执行成功: {len(results)} 条结果")
                return results

        except Exception as e:
            logger.error(f"AGE 查询失败: {e}\nCypher: {cypher}\nParams: {params}")
            raise

    async def create_graph(self, graph_name: str):
        """创建图谱"""
        await self.execute_cypher(f"CREATE GRAPH IF NOT EXISTS {graph_name}")
        logger.info(f"图谱已创建: {graph_name}")

    async def create_vertex_label(self, label_name: str, properties: List[str] = None):
        """创建顶点标签"""
        if properties:
            props = ", ".join([f"{prop}: string" for prop in properties])
            cypher = f"CREATE VLABEL {label_name} IF NOT EXISTS PROPERTIES ({props})"
        else:
            cypher = f"CREATE VLABEL {label_name} IF NOT EXISTS"

        await self.execute_cypher(cypher)
        logger.info(f"顶点标签已创建: {label_name}")

    async def create_edge_label(self, label_name: str, properties: List[str] = None):
        """创建边标签"""
        if properties:
            props = ", ".join([f"{prop}: string" for prop in properties])
            cypher = f"CREATE ELABEL {label_name} IF NOT EXISTS PROPERTIES ({props})"
        else:
            cypher = f"CREATE ELABEL {label_name} IF NOT EXISTS"

        await self.execute_cypher(cypher)
        logger.info(f"边标签已创建: {label_name}")

    async def add_vertex(self, label: str, properties: Dict[str, Any]) -> str:
        """
        添加顶点

        Returns:
            顶点 ID
        """
        props_str = ", ".join([f"{k}: '{v}'" for k, v in properties.items()])
        cypher = f"""
        CREATE (v:{label} {{{props_str}}})
        RETURN id(v) as vertex_id
        """

        result = await self.execute_cypher(cypher)
        if result:
            return result[0]['vertex_id']
        return None

    async def add_edge(self, from_label: str, from_props: Dict[str, Any],
                       to_label: str, to_props: Dict[str, Any],
                       edge_label: str, edge_props: Dict[str, Any] = None):
        """添加边"""
        from_match = " AND ".join([f"v.{k} = '{v}'" for k, v in from_props.items()])
        to_match = " AND ".join([f"u.{k} = '{v}'" for k, v in to_props.items()])

        edge_props_str = ""
        if edge_props:
            edge_props_str = " " + ", ".join([f"{k}: '{v}'" for k, v in edge_props.items()])

        cypher = f"""
        MATCH (v:{from_label} {{{from_match}}}), (u:{to_label} {{{to_match}}})
        CREATE (v)-[r:{edge_label}{edge_props_str}]->(u)
        """

        await self.execute_cypher(cypher)

    async def get_neighbors(self, label: str, properties: Dict[str, Any],
                           depth: int = 1, edge_filter: Optional[str] = None) -> List[Dict[str, Any]]:
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

        cypher = f"""
        MATCH (n:{label} {{{match_clause}}})-[r{edge_filter_clause}*1..{depth}]-(neighbor)
        RETURN
            neighbor.name as name,
            neighbor.description as description,
            type(r[0]) as relation_type,
            r[0].strength as strength
        ORDER BY r[0].strength DESC
        """

        return await self.execute_cypher(cypher)

    async def find_path(self, from_props: Dict[str, Any], to_props: Dict[str, Any],
                       max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        查找最短路径

        Args:
            from_props: 起点属性
            to_props: 终点属性
            max_depth: 最大深度
        """
        from_match = " AND ".join([f"a.{k} = '{v}'" for k, v in from_props.items()])
        to_match = " AND ".join([f"b.{k} = '{v}'" for k, v in to_props.items()])

        cypher = f"""
        MATCH path = shortestPath((a)-[*1..{max_depth}]-(b))
        WHERE {from_match} AND {to_match}
        RETURN nodes(path) as nodes, relationships(path) as edges
        """

        return await self.execute_cypher(cypher)


# 全局实例
_age_client: Optional[AgeClient] = None


def get_age_client() -> AgeClient:
    """获取 AGE 客户端单例"""
    global _age_client

    if _age_client is None:
        config = AgeConfig(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            graph_name="sparkle_galaxy"
        )
        _age_client = AgeClient(config)

    return _age_client


async def init_age():
    """初始化 AGE 客户端"""
    client = get_age_client()
    await client.init_pool()
    return client
