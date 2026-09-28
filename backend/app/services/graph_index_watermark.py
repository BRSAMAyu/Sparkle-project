"""GraphRAG 索引时效（watermark）与关系型 fallback 权威面（V4-D06）。

设计真源：v4/03_intelligence/DATA_AND_GRAPH.md §星图权威——

    "当前主星图是关系型 knowledge_nodes/node_relations/...；AGE 是另一路
    GraphRAG 且写生产者存在空缺。V4 前台优先关系型当前真源。AGE 只能作
    可检查版本/覆盖率的派生检索索引，落后时回到关系查询/普通检索；不因
    为想做'世界模型'新建第二套掌握度。"

三个事实（V4-B02/D06 盘点，2026-09-28 main=f9729cc5）：
1. ``stream:graph_sync`` 只有 node_created/relation_created/user_status_updated
   三种消息——关系型 UPDATE/DELETE（含 galaxy_service 草稿评审硬删、
   BaseModel 软删 deleted_at）从不进 AGE → AGE 永久落后且无人知道落后多少。
2. ``GraphRAGRetriever.graph_search`` 直查 AGE，异常被逐实体吞成 warning，
   降级零元数据零指标（不静默假数据的反面：静默空结果）。
3. 无任何 watermark：没有记录"AGE 已覆盖到关系型哪一版"。

本模块给出最小增量（不造第二权威，不迁移 DB）：

- **关系型 watermark**：``max(updated_at) + 行数``（knowledge_nodes 与
  node_relations 双表；行数进版是 E-05 修过的 delete-isolation 判例——
  只用 max(updated_at)，删除非最新行版本不动）。写路径在入队同步消息时
  携带当时 watermark；worker 成功消费且流内无积压（XPENDING==0，保守不
  越权声称覆盖更早未处理消息）后记录为 AGE 覆盖水位。
- **读门**：fresh（覆盖==当前）才允许 AGE 作答；stale/uncovered/unknown
  一律显式降级关系型一跳查询（软删安全），降级原因进 metadata 与指标，
  不静默。fresh 读加双读栅栏（读前/读后 watermark 相等，D03 epoch 栅栏
  同型）+ 关系型存在性/软删守卫（AGE 行的节点若已删除即丢弃——删除
  不复活）。
- **可复算**：``recompute_graph_sources`` 对同一实体并列跑关系型/AGE 两路
  并保留各自失败原文，供对照与审查复算。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation

# AGE 覆盖水位键（业务键，非安全前缀；cache_service 在 Redis 缺席时有本地兜底，
# 单测进程可用）。值：{"covered": <relational watermark>, "synced_at": iso}
AGE_WATERMARK_CACHE_KEY = "graph:index:age_watermark"

# 一跳邻接查询（graph_search 的 AGE 主路径与其关系型 fallback 语义对齐）：
# 无向一跳、strength 下限、LIMIT 上限一致 → 同题两路可复算对照。
AGE_ONE_HOP_CYPHER = """
MATCH (start:KnowledgeNode {name: $entity})
-[rel]-(related:KnowledgeNode)
WHERE toFloat(rel.strength) > $min_strength
RETURN {
    start_id: start.id,
    start_name: start.name,
    id: related.id,
    name: related.name,
    description: related.description,
    relation_type: type(rel),
    strength: toFloat(rel.strength),
    sector: related.sector
} as result
ORDER BY toFloat(rel.strength) DESC
LIMIT 10
"""

RELATIONAL_ONE_HOP_LIMIT = 10

# GraphIndexState.state 取值
STATE_FRESH = "fresh"  # AGE 覆盖水位 == 关系型当前水位 → 派生索引可作答
STATE_STALE = "stale"  # 两水位已知但不等 → AGE 落后，禁止 AGE 压过关系型
STATE_UNCOVERED = "uncovered"  # 无覆盖记录（新功能首启/Redis 缺席/全量重建前）
STATE_UNKNOWN = "unknown"  # 水位解析失败（DB/Redis 异常）→ 保守回关系型真源

STATE_VALUES = (STATE_FRESH, STATE_STALE, STATE_UNCOVERED, STATE_UNKNOWN)


@dataclass(frozen=True)
class GraphIndexState:
    """图索引时效态（一次 graph_search 的判定快照，进检索 metadata 可观测）。"""

    state: str
    relational_watermark: str | None = None
    age_watermark: str | None = None
    reason: str = ""  # index_covered | watermark_mismatch | index_uncovered | resolution_failed
    detail: str | None = None  # 失败原文（失败保留，不复写）

    def to_metadata(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "relational_watermark": self.relational_watermark,
            "age_watermark": self.age_watermark,
            "reason": self.reason,
            "detail": self.detail,
        }


def _watermark_token(node_max: datetime | None, node_count: int, rel_max: datetime | None, rel_count: int) -> str:
    candidates = [dt for dt in (node_max, rel_max) if dt]
    latest = max(candidates) if candidates else None
    ts_ms = int(latest.timestamp() * 1000) if latest else 0
    # 行数进版：删除（含软删/硬删/草稿评审硬删）不改 max(updated_at) 时仍能翻版本
    # （E-05 delete-isolation 同款判例，见 KnowledgeRetrievalService._compute_knowledge_version）。
    return f"gtsms:{ts_ms}:n{int(node_count)}:r{int(rel_count)}"


class GraphIndexWatermark:
    """AGE 派生索引对关系型真源的覆盖水位（读判定 + 写推进的唯一权威面）。"""

    def __init__(self, db: AsyncSession | None):
        self.db = db

    async def relational_watermark(self) -> str | None:
        """关系型当前真源版本（同事务可见未提交写；失败返回 None 不猜）。"""
        if self.db is None:
            return None
        try:
            node_result = await self.db.execute(
                select(func.max(KnowledgeNode.updated_at), func.count(KnowledgeNode.id))
            )
            node_max, node_count = node_result.one()
            rel_result = await self.db.execute(select(func.max(NodeRelation.updated_at), func.count(NodeRelation.id)))
            rel_max, rel_count = rel_result.one()
            return _watermark_token(node_max, int(node_count or 0), rel_max, int(rel_count or 0))
        except Exception as e:  # noqa: BLE001 — 水位失败必须显式 unknown，不猜 fresh
            logger.warning(f"关系型图水位计算失败: {e}")
            return None

    async def age_covered_watermark(self) -> str | None:
        """AGE 已覆盖的关系型版本（worker/sync_all 成功后推进；无记录→None）。"""
        try:
            record = await cache_service.get(AGE_WATERMARK_CACHE_KEY)
        except Exception as e:  # noqa: BLE001 — Redis 异常按无记录保守处理
            logger.warning(f"读取 AGE 覆盖水位失败（按无记录处理）: {e}")
            return None
        if isinstance(record, dict):
            covered = record.get("covered")
            if isinstance(covered, str) and covered:
                return covered
        return None

    async def record_age_coverage(self, covered: str) -> bool:
        """推进 AGE 覆盖水位（仅 worker 成功消费 / sync_all_to_age 全量重建后调用）。

        只允许写入真实算得的关系型水位串；调用方不得传占位/编造值。
        """
        if not covered:
            return False
        try:
            await cache_service.set(
                AGE_WATERMARK_CACHE_KEY,
                {"covered": covered, "synced_at": datetime.now().isoformat()},
                ttl=None,
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"推进 AGE 覆盖水位失败: {e}")
            return False

    async def resolve_state(self) -> GraphIndexState:
        """判定 AGE 派生索引当前是否可作答（fresh 才可；其余显式降级）。"""
        try:
            relational = await self.relational_watermark()
            age = await self.age_covered_watermark()
        except Exception as e:  # noqa: BLE001 — 双读之外的一切解析失败
            return GraphIndexState(
                state=STATE_UNKNOWN,
                reason="resolution_failed",
                detail=str(e),
            )
        if relational is None:
            return GraphIndexState(state=STATE_UNKNOWN, reason="resolution_failed")
        if age is None:
            return GraphIndexState(
                state=STATE_UNCOVERED,
                relational_watermark=relational,
                reason="index_uncovered",
            )
        if age == relational:
            return GraphIndexState(
                state=STATE_FRESH,
                relational_watermark=relational,
                age_watermark=age,
                reason="index_covered",
            )
        return GraphIndexState(
            state=STATE_STALE,
            relational_watermark=relational,
            age_watermark=age,
            reason="watermark_mismatch",
        )


async def relational_one_hop(
    db: AsyncSession,
    entity: str,
    *,
    min_strength: float,
    limit: int = RELATIONAL_ONE_HOP_LIMIT,
) -> list[dict[str, Any]]:
    """关系型一跳邻接（AGE_ONE_HOP_CYPHER 的关系型对偶，主真源作答面）。

    与 AGE 版语义对齐：无向一跳、strength 严格下限、按强度降序、同 LIMIT；
    另加软删安全（两端节点与关系行 deleted_at 过滤）——这是关系型作为主真源
    的差异优势，AGE 版没有该信息。
    """
    src = aliased(KnowledgeNode)
    tgt = aliased(KnowledgeNode)
    stmt = (
        select(NodeRelation, src, tgt)
        .join(src, NodeRelation.source_node_id == src.id)
        .join(tgt, NodeRelation.target_node_id == tgt.id)
        .where(
            NodeRelation.deleted_at.is_(None),
            src.deleted_at.is_(None),
            tgt.deleted_at.is_(None),
            NodeRelation.strength.isnot(None),
            NodeRelation.strength > min_strength,
            (src.name == entity) | (tgt.name == entity),
        )
        .order_by(NodeRelation.strength.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items: list[dict[str, Any]] = []
    for relation, source_node, target_node in rows:
        if source_node.name == entity:
            start_node, related_node = source_node, target_node
        else:
            start_node, related_node = target_node, source_node
        items.append(
            {
                "start_id": str(start_node.id),
                "start_name": start_node.name,
                "id": str(related_node.id),
                "name": related_node.name,
                "description": related_node.description,
                "relation_type": relation.relation_type,
                "strength": float(relation.strength),
                "sector": getattr(related_node, "dominant_sector_code", None),
            }
        )
    return items


async def recompute_graph_sources(
    db: AsyncSession,
    age_client: Any,
    entity: str,
    *,
    min_strength: float,
    limit: int = RELATIONAL_ONE_HOP_LIMIT,
) -> dict[str, Any]:
    """同题双源复算：关系型/AGE 各自作答并保留失败原文（验收面 3）。

    两侧独立执行、互不兜底——失败以 ``*_error`` 字符串原样保留，不静默丢弃，
    供对照审查复算（同一实体两路结果在各自快照下确定性可重放）。
    """
    relational_rows: list[dict[str, Any]] | None = None
    relational_error: str | None = None
    try:
        relational_rows = await relational_one_hop(db, entity, min_strength=min_strength, limit=limit)
    except Exception as e:  # noqa: BLE001 — 失败保留
        relational_error = f"{type(e).__name__}: {e}"

    age_rows: list[dict[str, Any]] | None = None
    age_error: str | None = None
    try:
        raw = await age_client.execute_cypher(AGE_ONE_HOP_CYPHER, {"entity": entity, "min_strength": min_strength})
        age_rows = [dict(item) for item in raw if isinstance(item, dict)]
    except Exception as e:  # noqa: BLE001 — 失败保留
        age_error = f"{type(e).__name__}: {e}"

    return {
        "entity": entity,
        "relational": relational_rows,
        "relational_error": relational_error,
        "age": age_rows,
        "age_error": age_error,
        "match": (
            _comparable(relational_rows, relational_error) == _comparable(age_rows, age_error)
            if relational_error is None and age_error is None
            else None
        ),
    }


def _comparable(rows: list[dict[str, Any]] | None, error: str | None) -> list[tuple[Any, ...]] | None:
    """把一路结果规约为可比较元组列表（失败侧返回 None 表示不可比）。"""
    if error is not None or rows is None:
        return None
    comparable: list[tuple[Any, ...]] = []
    for row in rows:
        comparable.append(
            (
                _uuid_or_none(row.get("start_id")),
                _uuid_or_none(row.get("id")),
                str(row.get("relation_type") or ""),
                round(float(row.get("strength") or 0.0), 6),
            )
        )
    return sorted(comparable)


def _uuid_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return str(value)
