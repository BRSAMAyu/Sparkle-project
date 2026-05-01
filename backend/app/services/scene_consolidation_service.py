from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean
from uuid import UUID

from loguru import logger
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge, Histogram
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import SCENE_CREATED, SCENE_UPDATED
from app.core.metrics import get_or_create_metric
from app.models.memory import EpisodicMemory, Scene
from app.schemas.scene import SceneSummary
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.embedding_service import embedding_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


SCENE_CREATED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_scene_created_total",
    "Total scenes created by mode",
    ["mode"],
)
SCENE_MERGED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_scene_merged_total",
    "Total scene merges by mode",
    ["mode"],
)
SCENE_QUALITY_AVG = get_or_create_metric(
    Gauge,
    "sparkle_scene_quality_avg",
    "Latest scene quality average by mode",
    ["mode"],
)
SCENE_QUALITY_DISTRIBUTION = get_or_create_metric(
    Histogram,
    "sparkle_scene_quality_distribution",
    "Scene quality distribution",
    ["mode"],
    buckets=[0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0],
)
SCENE_FILTERED_BELOW_THRESHOLD = get_or_create_metric(
    PrometheusCounter,
    "sparkle_scene_filtered_below_threshold_total",
    "Scenes filtered from aggregator due to low quality",
    ["mode"],
)
SCENE_CLUSTER_LATENCY_SECONDS = get_or_create_metric(
    Histogram,
    "sparkle_cluster_latency_seconds",
    "Scene clustering latency in seconds",
    ["mode", "operation"],
    buckets=[0.005, 0.01, 0.02, 0.04, 0.08, 0.12, 0.25, 0.5, 1.0],
)
SCENE_CLUSTER_BATCH_THROUGHPUT = get_or_create_metric(
    Histogram,
    "sparkle_cluster_batch_throughput",
    "Scene clustering batch throughput in items per run",
    ["mode"],
    buckets=[1, 5, 10, 25, 50, 100, 200],
)

_TOPIC_STOPWORDS = {
    "今天",
    "最近",
    "这个",
    "那个",
    "一下",
    "一个",
    "我们",
    "已经",
    "还是",
    "因为",
    "然后",
    "需要",
    "进行",
    "完成",
    "学习",
}


@dataclass(frozen=True)
class SceneConsolidationResult:
    action: str
    mode: str
    scene: Scene | None


def build_scene_id(*, user_id: UUID, member_memory_ids: Sequence[str], version: str) -> str:
    normalized_members = sorted({str(member_id) for member_id in member_memory_ids if str(member_id).strip()})
    digest = hashlib.sha256(
        f"{user_id}|{version}|{'|'.join(normalized_members)}".encode()
    ).hexdigest()
    return f"scene_{digest}"


def assert_rule_ak_algorithm_constraint(*, similarity_threshold: float, time_window_hours: int) -> None:
    if similarity_threshold <= 0 or similarity_threshold > 1:
        raise ValueError("Rule AK requires a similarity threshold within (0, 1].")
    if time_window_hours <= 0:
        raise ValueError("Rule AK requires a positive time window.")


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def _mean_embedding(vectors: Iterable[Sequence[float]]) -> list[float] | None:
    materialized = [list(vector) for vector in vectors if vector]
    if not materialized:
        return None
    dimension = len(materialized[0])
    if any(len(vector) != dimension for vector in materialized):
        return None
    return [
        fmean(vector[index] for vector in materialized)
        for index in range(dimension)
    ]


def _clip_text(value: str, *, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", value or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


class SceneConsolidationService:
    ALGORITHM_VERSION = "scene.v1"
    DEFAULT_SIMILARITY_THRESHOLD = 0.75
    DEFAULT_TIME_WINDOW_HOURS = 72
    AGGREGATOR_LOOKBACK_DAYS = 7
    AGGREGATOR_LIMIT = 5
    ALLOWED_SOURCE_LANE = "inferred_extraction"
    BLOCKED_SOURCE_TYPES = {"reflection"}

    def __init__(
        self,
        db: AsyncSession,
        *,
        similarity_threshold: float | None = None,
        time_window_hours: int | None = None,
        quality_threshold: float | None = None,
        now_fn=_utcnow,
    ) -> None:
        self.db = db
        self.similarity_threshold = float(
            similarity_threshold
            if similarity_threshold is not None
            else settings.AURORA_SCENE_SIMILARITY_THRESHOLD
        )
        self.time_window_hours = int(
            time_window_hours
            if time_window_hours is not None
            else settings.AURORA_SCENE_TIME_WINDOW_HOURS
        )
        self.quality_threshold = float(
            quality_threshold
            if quality_threshold is not None
            else settings.AURORA_SCENE_QUALITY_THRESHOLD
        )
        assert_rule_ak_algorithm_constraint(
            similarity_threshold=self.similarity_threshold,
            time_window_hours=self.time_window_hours,
        )
        self.kill_switch = AuroraStage26SceneKillSwitchService()
        self._now_fn = now_fn

    async def consolidate_memory_id(self, *, memory_id: UUID) -> SceneConsolidationResult:
        memory = await EpisodicMemory.get_by_id(self.db, memory_id)
        if memory is None:
            return SceneConsolidationResult(action="missing", mode=await self.kill_switch.get_mode(), scene=None)
        return await self.consolidate_memory(memory)

    async def consolidate_memory(self, memory: EpisodicMemory) -> SceneConsolidationResult:
        started_at = self._now_fn()
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            return SceneConsolidationResult(action="disabled", mode=mode, scene=None)
        if not self._is_memory_eligible(memory):
            return SceneConsolidationResult(action="skipped", mode=mode, scene=None)

        lock_key = f"scene:{memory.user_id}"
        from app.core.cache import cache_service

        async with cache_service.distributed_lock(lock_key, expire=5):
            embedding = await self._ensure_embedding(memory)
            if not embedding:
                return SceneConsolidationResult(action="missing_embedding", mode=mode, scene=None)

            candidate_scenes = await self._load_candidate_scenes(
                user_id=memory.user_id,
                occurred_at=memory.occurred_at,
            )
            selected = self._select_scene(memory=memory, embedding=embedding, scenes=candidate_scenes)
            if selected is None:
                scene = await self._create_scene(memory=memory, embedding=embedding)
                action = "created"
                SCENE_CREATED_TOTAL.labels(mode=mode).inc()
                await self._publish_scene_event(SCENE_CREATED, scene, memory_id=str(memory.id))
            else:
                scene = await self._merge_into_scene(scene=selected, memory=memory, embedding=embedding)
                action = "merged"
                SCENE_MERGED_TOTAL.labels(mode=mode).inc()
                await self._publish_scene_event(SCENE_UPDATED, scene, memory_id=str(memory.id))

        duration = max(0.0, (self._now_fn() - started_at).total_seconds())
        SCENE_CLUSTER_LATENCY_SECONDS.labels(mode=mode, operation="single").observe(duration)
        SCENE_QUALITY_AVG.labels(mode=mode).set(scene.quality_score)
        SCENE_QUALITY_DISTRIBUTION.labels(mode=mode).observe(scene.quality_score)
        await self.kill_switch.record_quality_average(scene.quality_score)
        return SceneConsolidationResult(action=action, mode=mode, scene=scene)

    async def backfill_user_scenes(self, *, user_id: UUID, limit: int = 100) -> list[Scene]:
        mode = await self.kill_switch.get_mode()
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                EpisodicMemory.source_lane == self.ALLOWED_SOURCE_LANE,
            )
            .order_by(EpisodicMemory.occurred_at.asc(), EpisodicMemory.created_at.asc())
            .limit(limit)
        )
        memories = list((await self.db.execute(stmt)).scalars().all())
        for memory in memories:
            await self.consolidate_memory(memory)
        SCENE_CLUSTER_BATCH_THROUGHPUT.labels(mode=mode).observe(len(memories))
        scene_rows = list(
            (
                await self.db.execute(
                    select(Scene)
                    .where(Scene.user_id == user_id, Scene.deleted_at.is_(None))
                    .order_by(Scene.time_end.desc(), Scene.updated_at.desc())
                )
            ).scalars().all()
        )
        return scene_rows

    async def list_recent_scenes_for_aggregator(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> list[SceneSummary]:
        mode = await self.kill_switch.get_mode()
        if mode != "live":
            return []
        reference_time = now or self._now_fn()
        window_start = reference_time - timedelta(days=self.AGGREGATOR_LOOKBACK_DAYS)
        stmt = (
            select(Scene)
            .where(
                Scene.user_id == user_id,
                Scene.deleted_at.is_(None),
                Scene.time_end >= window_start,
            )
            .order_by(Scene.time_end.desc(), Scene.updated_at.desc())
            .limit(self.AGGREGATOR_LIMIT * 2)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        items: list[SceneSummary] = []
        for row in rows:
            if row.quality_score < self.quality_threshold:
                SCENE_FILTERED_BELOW_THRESHOLD.labels(mode=mode).inc()
                continue
            items.append(
                SceneSummary(
                    scene_id=row.scene_id,
                    title=row.title,
                    time_start=row.time_start,
                    time_end=row.time_end,
                    member_count=len(row.member_memory_ids or []),
                    quality_score=max(0.0, min(1.0, float(row.quality_score))),
                )
            )
            if len(items) >= self.AGGREGATOR_LIMIT:
                break
        return items

    async def assert_scene_user_isolation(
        self,
        *,
        scene: Scene,
        expected_user_id: UUID,
    ) -> None:
        if scene.user_id != expected_user_id:
            raise ValueError("Rule Z/AK violation: cross-user scene access blocked.")
        member_ids = [UUID(str(member_id)) for member_id in (scene.member_memory_ids or [])]
        if not member_ids:
            return
        stmt = select(EpisodicMemory).where(EpisodicMemory.id.in_(member_ids))
        rows = list((await self.db.execute(stmt)).scalars().all())
        if len(rows) != len(member_ids):
            raise ValueError("Scene references missing episodic memories.")
        if any(row.user_id != expected_user_id for row in rows):
            raise ValueError("Rule AK violation: scene members must never cross user boundaries.")

    async def _ensure_embedding(self, memory: EpisodicMemory) -> list[float] | None:
        if memory.embedding:
            return list(memory.embedding)
        embedding = await embedding_service.get_embedding(memory.summary, text_type="document")
        memory.embedding = embedding
        await self.db.commit()
        await self.db.refresh(memory)
        return embedding

    async def _load_candidate_scenes(self, *, user_id: UUID, occurred_at: datetime) -> list[Scene]:
        window = timedelta(hours=self.time_window_hours)
        stmt = (
            select(Scene)
            .where(
                Scene.user_id == user_id,
                Scene.deleted_at.is_(None),
                Scene.time_end >= occurred_at - window,
                Scene.time_start <= occurred_at + window,
            )
            .order_by(Scene.time_end.desc(), Scene.time_start.asc(), Scene.scene_id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    def _select_scene(
        self,
        *,
        memory: EpisodicMemory,
        embedding: Sequence[float],
        scenes: Sequence[Scene],
    ) -> Scene | None:
        ranked: list[tuple[float, float, str, Scene]] = []
        for scene in scenes:
            if not scene.centroid_embedding:
                continue
            if not self._within_time_window(memory=memory, scene=scene):
                continue
            similarity = cosine_similarity(embedding, list(scene.centroid_embedding))
            if similarity < self.similarity_threshold:
                continue
            time_distance = self._scene_time_distance_hours(memory.occurred_at, scene)
            ranked.append((similarity, -time_distance, scene.scene_id, scene))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return ranked[0][3]

    async def _create_scene(self, *, memory: EpisodicMemory, embedding: Sequence[float]) -> Scene:
        title, summary = self._compose_title_summary(
            memories=[memory],
            time_start=memory.occurred_at,
            time_end=memory.occurred_at,
        )
        scene = Scene(
            scene_id=build_scene_id(
                user_id=memory.user_id,
                member_memory_ids=[str(memory.id)],
                version=self.ALGORITHM_VERSION,
            ),
            user_id=memory.user_id,
            title=title,
            summary=summary,
            member_memory_ids=[str(memory.id)],
            centroid_embedding=list(embedding),
            time_start=memory.occurred_at,
            time_end=memory.occurred_at,
            quality_score=self._score_scene(
                embeddings=[embedding],
                centroid=list(embedding),
                time_start=memory.occurred_at,
                time_end=memory.occurred_at,
            ),
            version=self.ALGORITHM_VERSION,
        )
        self.db.add(scene)
        await self.db.commit()
        await self.db.refresh(scene)
        return scene

    async def _merge_into_scene(
        self,
        *,
        scene: Scene,
        memory: EpisodicMemory,
        embedding: Sequence[float],
    ) -> Scene:
        member_ids = list(scene.member_memory_ids or [])
        if str(memory.id) in member_ids:
            return scene
        member_ids.append(str(memory.id))
        memories = await self._load_scene_memories(user_id=scene.user_id, member_memory_ids=member_ids)
        embeddings = [await self._ensure_embedding(item) for item in memories]
        materialized_embeddings = [item for item in embeddings if item]
        centroid = _mean_embedding(materialized_embeddings) or list(embedding)
        time_start = min(item.occurred_at for item in memories)
        time_end = max(item.occurred_at for item in memories)
        title, summary = self._compose_title_summary(memories=memories, time_start=time_start, time_end=time_end)
        scene.scene_id = build_scene_id(
            user_id=scene.user_id,
            member_memory_ids=member_ids,
            version=self.ALGORITHM_VERSION,
        )
        scene.member_memory_ids = member_ids
        scene.centroid_embedding = centroid
        scene.time_start = time_start
        scene.time_end = time_end
        scene.title = title
        scene.summary = summary
        scene.quality_score = self._score_scene(
            embeddings=materialized_embeddings,
            centroid=centroid,
            time_start=time_start,
            time_end=time_end,
        )
        scene.version = self.ALGORITHM_VERSION
        await self.assert_scene_user_isolation(scene=scene, expected_user_id=scene.user_id)
        await self.db.commit()
        await self.db.refresh(scene)
        return scene

    async def _load_scene_memories(self, *, user_id: UUID, member_memory_ids: Sequence[str]) -> list[EpisodicMemory]:
        uuids = [UUID(str(member_id)) for member_id in member_memory_ids]
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.id.in_(uuids),
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
            .order_by(EpisodicMemory.occurred_at.asc(), EpisodicMemory.created_at.asc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        if len(rows) != len(uuids):
            raise ValueError("Scene members must all exist for the same user.")
        return rows

    def _score_scene(
        self,
        *,
        embeddings: Sequence[Sequence[float]],
        centroid: Sequence[float],
        time_start: datetime,
        time_end: datetime,
    ) -> float:
        count = len(embeddings)
        if count >= 3:
            member_component = 1.0
        elif count == 2:
            member_component = 0.55
        else:
            member_component = 0.35

        cohesion_component = (
            max(0.0, min(1.0, fmean(cosine_similarity(vector, centroid) for vector in embeddings)))
            if embeddings
            else 0.0
        )

        span_hours = max(0.0, (time_end - time_start).total_seconds() / 3600)
        if span_hours < 0.25:
            time_component = 0.45
        elif span_hours <= 48:
            time_component = 1.0
        elif span_hours <= self.time_window_hours:
            time_component = 0.75
        else:
            time_component = 0.35

        score = (0.35 * member_component) + (0.45 * cohesion_component) + (0.20 * time_component)
        return round(max(0.0, min(1.0, score)), 4)

    def _compose_title_summary(
        self,
        *,
        memories: Sequence[EpisodicMemory],
        time_start: datetime,
        time_end: datetime,
    ) -> tuple[str, str]:
        time_label = self._time_label(time_start)
        subject_counter = Counter(memory.subject_type or "self" for memory in memories)
        dominant_subject = self._subject_label(subject_counter.most_common(1)[0][0] if subject_counter else "self")
        topics = self._extract_topics(memories)
        topic_label = " / ".join(topics[:2]) if topics else "学习主题"
        title = _clip_text(f"{time_label}{dominant_subject}场景 · {topic_label}", limit=200)
        summary = _clip_text(
            f"{time_label}聚合了 {len(memories)} 条{dominant_subject}相关记忆，主题集中在 {topic_label}。",
            limit=200,
        )
        return title, summary

    @staticmethod
    def _time_label(moment: datetime) -> str:
        weekend = moment.weekday() >= 5
        hour = moment.hour
        if hour < 6:
            slot = "凌晨"
        elif hour < 12:
            slot = "早晨"
        elif hour < 18:
            slot = "下午"
        else:
            slot = "晚上"
        prefix = "周末" if weekend else "工作日"
        return f"{prefix}{slot}"

    @staticmethod
    def _subject_label(subject_type: str) -> str:
        mapping = {
            "commitment": "承诺",
            "self": "自我",
            "study": "学习",
            "goal": "目标",
            "person_mention": "互动",
            "relationship": "关系",
        }
        return mapping.get(subject_type, "学习")

    def _extract_topics(self, memories: Sequence[EpisodicMemory]) -> list[str]:
        tags: list[str] = []
        for memory in memories:
            for item in memory.tags or []:
                value = str(item or "").strip()
                if value.startswith("topic:"):
                    tags.append(value.split(":", 1)[1])
                elif value.startswith("reflection_category:"):
                    tags.append(value.split(":", 1)[1].replace("_", " "))
        if tags:
            return [item for item, _ in Counter(tags).most_common(3)]

        tokens: Counter[str] = Counter()
        for memory in memories:
            for raw in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z]{4,}", memory.summary or ""):
                token = raw.strip().lower()
                if token in _TOPIC_STOPWORDS:
                    continue
                tokens[token] += 1
        return [item for item, _ in tokens.most_common(3)]

    def _within_time_window(self, *, memory: EpisodicMemory, scene: Scene) -> bool:
        occurred_at = memory.occurred_at
        return scene.time_start <= occurred_at <= scene.time_end or SceneConsolidationService._scene_time_distance_hours(
            occurred_at,
            scene,
        ) <= self.time_window_hours

    @staticmethod
    def _scene_time_distance_hours(occurred_at: datetime, scene: Scene) -> float:
        if scene.time_start <= occurred_at <= scene.time_end:
            return 0.0
        if occurred_at < scene.time_start:
            return (scene.time_start - occurred_at).total_seconds() / 3600
        return (occurred_at - scene.time_end).total_seconds() / 3600

    def _is_memory_eligible(self, memory: EpisodicMemory) -> bool:
        if memory.source_lane != self.ALLOWED_SOURCE_LANE:
            return False
        if memory.source_type in self.BLOCKED_SOURCE_TYPES:
            return False
        if memory.deleted_at or memory.archived_at or memory.retracted_at or memory.revoked_at:
            return False
        return True

    async def _publish_scene_event(self, event_type: str, scene: Scene, *, memory_id: str) -> None:
        try:
            await event_bus.publish(
                event_type,
                {
                    "event_type": event_type,
                    "scene_id": scene.scene_id,
                    "user_id": str(scene.user_id),
                    "memory_id": memory_id,
                    "member_count": len(scene.member_memory_ids or []),
                    "quality_score": scene.quality_score,
                    "version": scene.version,
                    "timestamp": self._now_fn().isoformat(),
                },
            )
        except Exception as exc:  # pragma: no cover - telemetry side effect only
            logger.warning(f"Failed to publish scene event {event_type}: {exc}")
