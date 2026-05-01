from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.sector import SectorCode
from app.services.llm_service import get_llm_service, get_llm_service_for_specific_model


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


SECTOR_ORDER: tuple[SectorCode, ...] = (
    SectorCode.COSMOS,
    SectorCode.TECH,
    SectorCode.ART,
    SectorCode.CIVILIZATION,
    SectorCode.LIFE,
    SectorCode.WISDOM,
    SectorCode.VOID,
)
NON_VOID_SECTORS: tuple[SectorCode, ...] = tuple(
    sector for sector in SECTOR_ORDER if sector != SectorCode.VOID
)
SECTOR_ANGLES: dict[SectorCode, float] = {
    SectorCode.COSMOS: 0.0,
    SectorCode.TECH: 60.0,
    SectorCode.ART: 120.0,
    SectorCode.CIVILIZATION: 180.0,
    SectorCode.LIFE: 240.0,
    SectorCode.WISDOM: 300.0,
    SectorCode.VOID: 0.0,
}
SECTOR_COLORS: dict[SectorCode, tuple[str, str]] = {
    SectorCode.COSMOS: ("#78A3D1", "#A8C8F3"),
    SectorCode.TECH: ("#5AB8CC", "#92E1E9"),
    SectorCode.ART: ("#C97C8F", "#F4B0C1"),
    SectorCode.CIVILIZATION: ("#D0A05F", "#F2D5A1"),
    SectorCode.LIFE: ("#5FAF80", "#9FDEB6"),
    SectorCode.WISDOM: ("#A181C8", "#D0B8EE"),
    SectorCode.VOID: ("#70798B", "#AAB2C4"),
}


@dataclass(frozen=True)
class SectorClassificationResult:
    sector_weights: dict[str, int]
    dominant_sector_code: SectorCode
    base_color: str
    glow_color: str
    position_angle: float
    position_radius: float
    position_x: float
    position_y: float


def parse_sector_code(raw: object) -> SectorCode | None:
    if raw is None:
        return None
    normalized = str(raw).strip().upper()
    if not normalized:
        return None
    try:
        return SectorCode(normalized)
    except ValueError:
        return None


def normalize_sector_weights(
    raw_weights: Any,
    *,
    fallback_sector: SectorCode | None = None,
) -> dict[str, int]:
    parsed: dict[SectorCode, float] = {}
    if isinstance(raw_weights, dict):
        source = raw_weights.items()
    elif isinstance(raw_weights, list):
        source = []
        for item in raw_weights:
            if not isinstance(item, dict):
                continue
            source.append(
                (
                    item.get("sector")
                    or item.get("sector_code")
                    or item.get("name"),
                    item.get("weight") or item.get("percentage") or item.get("value"),
                )
            )
    else:
        source = []

    for raw_sector, raw_value in source:
        sector = parse_sector_code(raw_sector)
        if sector is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        parsed[sector] = parsed.get(sector, 0.0) + value

    if not parsed:
        fallback = fallback_sector or SectorCode.VOID
        return {fallback.value: 100}

    total = sum(parsed.values())
    if total <= 0:
        fallback = fallback_sector or SectorCode.VOID
        return {fallback.value: 100}

    scaled = {sector: (value / total) * 100.0 for sector, value in parsed.items()}
    floored = {sector: int(math.floor(value)) for sector, value in scaled.items()}
    remainder = 100 - sum(floored.values())
    ranked = sorted(
        scaled.items(),
        key=lambda item: (item[1] - floored[item[0]], item[1]),
        reverse=True,
    )
    for sector, _ in ranked:
        if remainder <= 0:
            break
        floored[sector] += 1
        remainder -= 1

    normalized = {
        sector.value: weight
        for sector, weight in floored.items()
        if weight > 0
    }
    if normalized:
        return normalized

    fallback = fallback_sector or SectorCode.VOID
    return {fallback.value: 100}


def dominant_sector_from_weights(
    sector_weights: dict[str, int] | None,
    *,
    fallback_sector: SectorCode = SectorCode.VOID,
) -> SectorCode:
    if not sector_weights:
        return fallback_sector
    dominant = max(
        sector_weights.items(),
        key=lambda item: (
            int(item[1] or 0),
            -SECTOR_ORDER.index(parse_sector_code(item[0]) or SectorCode.VOID),
        ),
    )[0]
    return parse_sector_code(dominant) or fallback_sector


def resolve_sector_weights(node: KnowledgeNode) -> dict[str, int]:
    fallback_sector = (
        parse_sector_code(getattr(node, "dominant_sector_code", None))
        or parse_sector_code(getattr(getattr(node, "subject", None), "sector_code", None))
        or SectorCode.VOID
    )
    raw_weights = getattr(node, "sector_weights", None)
    if raw_weights:
        return normalize_sector_weights(raw_weights, fallback_sector=fallback_sector)
    if fallback_sector != SectorCode.VOID:
        return {fallback_sector.value: 100}
    return {SectorCode.VOID.value: 100}


def blend_sector_colors(sector_weights: dict[str, int]) -> tuple[str, str]:
    rgb_sum = [0.0, 0.0, 0.0]
    glow_sum = [0.0, 0.0, 0.0]
    total = 0.0

    for raw_sector, raw_weight in sector_weights.items():
        sector = parse_sector_code(raw_sector) or SectorCode.VOID
        weight = float(raw_weight or 0)
        if weight <= 0:
            continue
        base_hex, glow_hex = SECTOR_COLORS.get(sector, SECTOR_COLORS[SectorCode.VOID])
        base_rgb = _hex_to_rgb(base_hex)
        glow_rgb = _hex_to_rgb(glow_hex)
        total += weight
        for index in range(3):
            rgb_sum[index] += base_rgb[index] * weight
            glow_sum[index] += glow_rgb[index] * weight

    if total <= 0:
        return SECTOR_COLORS[SectorCode.VOID]

    base = _rgb_to_hex(tuple(int(channel / total) for channel in rgb_sum))
    glow = _rgb_to_hex(tuple(int(channel / total) for channel in glow_sum))
    return base, glow


def build_sector_visuals(
    node: KnowledgeNode | UUID | str,
    *,
    importance_level: int,
    sector_weights: dict[str, int],
    keep_position: tuple[float | None, float | None] | None = None,
) -> SectorClassificationResult:
    dominant_sector = dominant_sector_from_weights(sector_weights)
    base_color, glow_color = blend_sector_colors(sector_weights)

    if keep_position and keep_position[0] is not None and keep_position[1] is not None:
        position_x = float(keep_position[0])
        position_y = float(keep_position[1])
        position_radius = math.hypot(position_x, position_y)
        position_angle = (math.degrees(math.atan2(position_y, position_x)) + 360.0) % 360.0
        return SectorClassificationResult(
            sector_weights=sector_weights,
            dominant_sector_code=dominant_sector,
            base_color=base_color,
            glow_color=glow_color,
            position_angle=position_angle,
            position_radius=position_radius,
            position_x=position_x,
            position_y=position_y,
        )

    anchor_x = 0.0
    anchor_y = 0.0
    total_weight = 0.0
    non_void_weight = 0.0
    for raw_sector, raw_weight in sector_weights.items():
        sector = parse_sector_code(raw_sector) or SectorCode.VOID
        weight = float(raw_weight or 0)
        if weight <= 0:
            continue
        angle = math.radians(SECTOR_ANGLES.get(sector, 0.0))
        anchor_x += math.cos(angle) * weight
        anchor_y += math.sin(angle) * weight
        total_weight += weight
        if sector != SectorCode.VOID:
            non_void_weight += weight

    if total_weight <= 0:
        angle_deg = SECTOR_ANGLES[SectorCode.VOID]
    else:
        angle_deg = (math.degrees(math.atan2(anchor_y, anchor_x)) + 360.0) % 360.0

    weight_entropy = 0.0
    for weight in sector_weights.values():
        ratio = max(float(weight), 0.0) / 100.0
        if ratio > 0:
            weight_entropy -= ratio * math.log(ratio, 2)

    seed_str = str(node.id if isinstance(node, KnowledgeNode) else node)
    seed = sum((index + 1) * ord(char) for index, char in enumerate(seed_str)) % 10000
    jitter_angle = ((seed % 19) - 9) * 1.35
    jitter_radius = 22.0 + (seed % 31)
    position_angle = (angle_deg + jitter_angle + 360.0) % 360.0
    position_radius = (
        155.0
        + (5 - max(1, min(5, int(importance_level or 3)))) * 44.0
        + jitter_radius
        + weight_entropy * 28.0
        + max(0.0, (100.0 - non_void_weight) * 0.35)
    )
    angle_rad = math.radians(position_angle)
    position_x = math.cos(angle_rad) * position_radius
    position_y = math.sin(angle_rad) * position_radius
    return SectorClassificationResult(
        sector_weights=sector_weights,
        dominant_sector_code=dominant_sector,
        base_color=base_color,
        glow_color=glow_color,
        position_angle=position_angle,
        position_radius=position_radius,
        position_x=position_x,
        position_y=position_y,
    )


def node_belongs_to_sector(node: KnowledgeNode, sector_code: str) -> bool:
    target = parse_sector_code(sector_code)
    if target is None:
        return False
    sector_weights = resolve_sector_weights(node)
    return int(sector_weights.get(target.value, 0)) > 0 or (
        target == dominant_sector_from_weights(sector_weights)
    )


class NodeSectorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def classify_payload(
        self,
        *,
        name: str,
        description: str | None = None,
        name_en: str | None = None,
        keywords: list[str] | None = None,
        importance_level: int = 3,
        parent_name: str | None = None,
        subject_name: str | None = None,
        subject_sector_hint: str | None = None,
        neighbors: list[dict[str, str]] | None = None,
        fallback_sector: SectorCode = SectorCode.VOID,
        stable_seed: str | UUID | None = None,
        model_key: str | None = None,
    ) -> SectorClassificationResult:
        prompt = self._build_payload_prompt(
            {
                "node_name": name,
                "node_name_en": name_en,
                "description": description,
                "keywords": list(keywords or []),
                "importance_level": importance_level,
                "parent_name": parent_name,
                "subject_name": subject_name,
                "subject_sector_hint": subject_sector_hint,
                "neighbors": list(neighbors or []),
            }
        )
        sector_weights = await self._request_sector_weights(
            prompt,
            fallback_sector=fallback_sector,
            model_key=model_key,
        )
        return build_sector_visuals(
            stable_seed or name,
            importance_level=importance_level,
            sector_weights=sector_weights,
        )

    async def classify_node(
        self,
        node: KnowledgeNode,
        *,
        model_key: str | None = None,
    ) -> SectorClassificationResult:
        fallback_sector = (
            parse_sector_code(getattr(getattr(node, "subject", None), "sector_code", None))
            or SectorCode.VOID
        )
        neighbors_result = await self.db.execute(
            select(KnowledgeNode.name, NodeRelation.relation_type)
            .join(
                NodeRelation,
                or_(
                    and_(NodeRelation.source_node_id == node.id, NodeRelation.target_node_id == KnowledgeNode.id),
                    and_(NodeRelation.target_node_id == node.id, NodeRelation.source_node_id == KnowledgeNode.id),
                ),
            )
            .where(KnowledgeNode.id != node.id)
            .limit(8)
        )
        neighbors = [
            {"name": name, "relation": relation_type}
            for name, relation_type in neighbors_result.all()
        ]
        return await self.classify_payload(
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            keywords=list(node.keywords or []),
            importance_level=node.importance_level,
            parent_name=getattr(getattr(node, "parent", None), "name", None),
            subject_name=getattr(getattr(node, "subject", None), "name", None),
            subject_sector_hint=getattr(getattr(node, "subject", None), "sector_code", None),
            neighbors=neighbors,
            fallback_sector=fallback_sector,
            stable_seed=node,
            model_key=model_key,
        )

    async def update_node_classification(
        self,
        node: KnowledgeNode,
        classification: SectorClassificationResult,
        *,
        model_key: str | None,
        status: str = "completed",
    ) -> None:
        previous_sector = parse_sector_code(getattr(node, "dominant_sector_code", None)) or SectorCode.VOID
        node.sector_weights = classification.sector_weights
        node.dominant_sector_code = classification.dominant_sector_code.value
        node.sector_classification_status = status
        node.sector_classification_model = model_key
        node.sector_classified_at = _utcnow()
        if (
            node.position_x is None
            or node.position_y is None
            or previous_sector == SectorCode.VOID
            or classification.dominant_sector_code != previous_sector
        ):
            node.position_x = classification.position_x
            node.position_y = classification.position_y
        self.db.add(node)

    async def classify_nodes_by_ids(
        self,
        *,
        user_id: UUID,
        node_ids: list[UUID],
        model_key: str | None = None,
    ) -> dict[str, int]:
        if not node_ids:
            return {"processed": 0, "updated": 0}

        result = await self.db.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.id.in_(node_ids))
            .order_by(KnowledgeNode.created_at.asc())
        )
        nodes = list(result.scalars().all())
        updated = 0

        for node in nodes:
            try:
                node.sector_classification_status = "processing"
                self.db.add(node)
                await self.db.flush()
                classification = await self.classify_node(node, model_key=model_key)
                await self.update_node_classification(
                    node,
                    classification,
                    model_key=model_key,
                    status="completed",
                )
                updated += 1
            except Exception as exc:
                node.sector_classification_status = "failed"
                node.sector_classification_model = model_key
                self.db.add(node)
                logger.warning("Node sector classification failed for {}: {}", node.id, exc)

        await self.db.commit()
        await self.invalidate_user_graph_cache(user_id)
        return {"processed": len(nodes), "updated": updated}

    async def mark_nodes_pending(
        self,
        node_ids: list[UUID],
    ) -> list[UUID]:
        if not node_ids:
            return []
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
        )
        nodes = list(result.scalars().all())
        accepted: list[UUID] = []
        for node in nodes:
            status = str(getattr(node, "sector_classification_status", "pending") or "pending")
            if status == "processing":
                continue
            node.sector_classification_status = "pending"
            self.db.add(node)
            accepted.append(node.id)
        if accepted:
            await self.db.commit()
        return accepted

    async def find_nodes_needing_backfill(
        self,
        *,
        user_id: UUID,
        limit: int = 24,
    ) -> list[UUID]:
        stmt = (
            select(KnowledgeNode.id)
            .where(
                or_(
                    KnowledgeNode.sector_weights.is_(None),
                    KnowledgeNode.dominant_sector_code == SectorCode.VOID.value,
                    KnowledgeNode.sector_classification_status.in_(["pending", "failed"]),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def enqueue_backfill_for_nodes(
        self,
        *,
        user_id: UUID,
        node_ids: list[UUID],
    ) -> bool:
        from app.services.glm_batch_service import glm_batch_service

        accepted = await self.mark_nodes_pending(node_ids)
        if not accepted:
            return False
        try:
            glm_batch_service.enqueue_node_sector_backfill(
                user_id=user_id,
                node_ids=accepted,
            )
        except Exception as exc:
            logger.warning(
                "Node sector backfill enqueue failed for user {} with {} nodes: {}",
                user_id,
                len(accepted),
                exc,
            )
            return False
        return True

    async def ensure_backfill_for_user(
        self,
        *,
        user_id: UUID,
        candidate_nodes: list[KnowledgeNode] | None = None,
        limit: int = 24,
    ) -> bool:
        if candidate_nodes is not None:
            node_ids = [
                node.id
                for node in candidate_nodes
                if not getattr(node, "sector_weights", None)
                or str(getattr(node, "dominant_sector_code", "VOID") or "VOID") == SectorCode.VOID.value
                or str(getattr(node, "sector_classification_status", "pending") or "pending") in {"pending", "failed"}
            ][:limit]
        else:
            node_ids = await self.find_nodes_needing_backfill(user_id=user_id, limit=limit)
        return await self.enqueue_backfill_for_nodes(user_id=user_id, node_ids=node_ids)

    async def invalidate_user_graph_cache(self, user_id: UUID) -> None:
        await cache_service.delete_pattern(f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*")

    async def _request_sector_weights(
        self,
        prompt: str,
        *,
        fallback_sector: SectorCode,
        model_key: str | None,
    ) -> dict[str, int]:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是知识星图星域分类器。请只输出 JSON。"
                    "必须给出 6+1 星域（COSMOS, TECH, ART, CIVILIZATION, LIFE, WISDOM, VOID）"
                    "的百分比归属，总和必须为 100。"
                    "优先把概念分到六个主星域，只有在信息明显不足或确实无法归类时才给 VOID 较高占比。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        if model_key:
            llm = await get_llm_service_for_specific_model(model_key, agent_role="generation")
            payload = await llm.chat_json(messages=messages, temperature=0.2)
        else:
            llm = get_llm_service("generation")
            payload = await llm.chat_json(messages=messages, temperature=0.25)

        if not isinstance(payload, dict):
            raise ValueError("Invalid node sector classification payload")

        return normalize_sector_weights(
            payload.get("sector_weights") or payload.get("weights"),
            fallback_sector=fallback_sector,
        )

    def _build_payload_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "请判断下面这个知识节点在 6+1 星域中的归属百分比，总和必须为 100。\n"
            "输出 JSON 结构："
            '{"sector_weights":{"COSMOS":0,"TECH":0,"ART":0,"CIVILIZATION":0,"LIFE":0,"WISDOM":0,"VOID":0}}。\n'
            "要求：\n"
            "1. 百分比必须是整数。\n"
            "2. 尽量反映跨学科混合归属，不要无脑把节点放进 VOID。\n"
            "3. 如果节点明显跨多个星域，请给出多星域分布。\n"
            f"4. 节点上下文如下：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    normalized = color.strip().lstrip("#")
    if len(normalized) != 6:
        return (112, 121, 139)
    return tuple(int(normalized[index:index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{max(0, min(255, rgb[0])):02X}{max(0, min(255, rgb[1])):02X}{max(0, min(255, rgb[2])):02X}"
